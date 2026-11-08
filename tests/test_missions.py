"""Mission tests: every destination mission can be completed on every map layout, and the mission data is sound.

Destination objectives that use "min_axis" count every stop at least that far along the Start-to-Pacific line, so
the check that matters is: whatever road the convoy takes to the coast, it passes through a stop that counts
(reaching the coast ends the run, so the coast itself does not count here).
"""
import json
import unittest
from unittest import mock

import map_data
from game import Game
from game import event_data
from game.effect_handler import RESOURCE_FIELDS, validate_effect
from game.mission_data import MISSIONS
from game.mission_manager import MissionManager
from game.null_audio import NullAudio
from vehicle_data import VEHICLE_SPECS

from tests.helpers import LayoutTestCase


class MissionGame:
    """Just enough of Game for MissionManager and its resource rewards."""

    def __init__(self):
        self.position = map_data.START
        self.fuel = self.food = self.water = self.scrap = 0
        self.vehicles = []   # vehicle type names (owned_vehicle_names reads them)
        self.travel_count = 0
        self.log = []

    def say(self, message):
        self.log.append(message)

    def convoy_stats(self):
        return {"fuel_capacity": 9999}


def objective_groups(mission):
    """The objective lists of a mission that must hold together: one per stage, or the flat list."""
    if mission.get("stages"):
        return [stage["objectives"] for stage in mission["stages"]]
    return [mission["objectives"]]


def all_objectives(mission):
    """Every objective of a mission, in every stage."""
    return [objective for group in objective_groups(mission) for objective in group]


def all_rewards(mission):
    """The mission's own rewards plus those of each stage."""
    return list(mission["rewards"]) + [r for stage in mission.get("stages", []) for r in stage.get("rewards", [])]


def destination_objectives():
    """(mission id, objective) for every destination objective of every mission (every stage)."""
    return [(mission["id"], objective)
            for mission in MISSIONS for objective in all_objectives(mission) if objective["type"] == "destination"]


def routes_to_coast():
    """Every simple road route (list of stop ids) from the start to the Pacific Coast on the active layout."""
    routes = []

    def walk(path):
        if path[-1] == map_data.PACIFIC:
            routes.append(path)
            return
        for nxt, _km in map_data.ADJACENT[path[-1]]:
            if nxt not in path:
                walk(path + [nxt])

    walk([map_data.START])
    return routes


class DestinationMissionTests(LayoutTestCase):
    def test_there_are_destination_missions(self):
        self.assertTrue(destination_objectives())

    def test_objectives_are_well_formed(self):
        def check():
            for mission_id, objective in destination_objectives():
                keys = [key for key in ("stop_id", "stop_ids", "min_axis", "node_flag") if key in objective]
                self.assertEqual(len(keys), 1, f"{mission_id}: use exactly one of stop_id / stop_ids / min_axis / node_flag")
                if "node_flag" in objective:
                    self.assertTrue(any(node.get(objective["node_flag"]) for node in map_data.NODES),
                                    f"{mission_id}: no stop has the flag {objective['node_flag']!r}")
                stops = [objective["stop_id"]] if "stop_id" in objective else list(objective.get("stop_ids", []))
                for stop in stops:
                    self.assertIn(stop, range(len(map_data.NODES)), f"{mission_id}: no stop {stop}")
                if "min_axis" in objective:
                    self.assertLessEqual(objective["min_axis"], map_data.NODES[map_data.PACIFIC]["axis"],
                                         f"{mission_id}: min_axis is beyond the Pacific Coast")

        self.for_each_layout(check)

    def test_a_stop_before_the_coast_counts(self):
        def check():
            for mission_id, objective in destination_objectives():
                matching = [stop for stop in range(len(map_data.NODES))
                            if stop != map_data.PACIFIC and MissionManager._stop_matches(objective, stop)]
                self.assertTrue(matching, f"{mission_id}: no stop before the coast satisfies {objective}")

        self.for_each_layout(check)

    def test_no_road_to_the_coast_bypasses_a_destination(self):
        """Walk every route start -> coast through a real MissionManager: each destination objective must be done
        before the coast is reached, so a bypass road can never make a mission impossible."""
        def check():
            routes = routes_to_coast()
            self.assertTrue(routes)
            for route in routes:
                manager, game = MissionManager(), MissionGame()
                for state in manager.missions.values():
                    state["status"] = "Active"        # prerequisites are not the point here
                for stop in route[:-1]:                # the coast itself ends the run
                    manager.on_destination_reached(game, stop)
                for mission_id, state in manager.missions.items():
                    for index, objective in enumerate(state["data"]["objectives"]):   # the first stage of a staged mission
                        if objective["type"] == "destination" and "node_flag" not in objective:
                            self.assertGreaterEqual(
                                state["progress"][index], objective.get("target", 1),
                                f"{mission_id}: route {route} never reaches {objective}")

        self.for_each_layout(check)


    def test_a_flagged_stop_can_always_be_reached_from_the_road_to_the_coast(self):
        """A "node_flag" stop (the Military Base) is a dead-end spur, so a route to the coast does not pass it, but the
        convoy always drives through the stop it hangs off and can turn in."""
        def check():
            flagged = {i for i, node in enumerate(map_data.NODES)
                       if any(node.get(o["node_flag"]) for _m, o in destination_objectives() if "node_flag" in o)}
            self.assertTrue(flagged)
            for route in routes_to_coast():
                self.assertTrue(any(nxt in flagged for stop in route for nxt, _km in map_data.ADJACENT[stop]),
                                f"route {route} never passes a road to a flagged stop")

        self.for_each_layout(check)


class MissionDataTests(unittest.TestCase):
    def test_prerequisites_exist_and_have_no_cycle(self):
        ids = {mission["id"] for mission in MISSIONS}
        self.assertEqual(len(ids), len(MISSIONS), "duplicate mission id")
        prerequisites = {mission["id"]: mission.get("prerequisites", []) for mission in MISSIONS}
        for mission_id, needed in prerequisites.items():
            for other in needed:
                self.assertIn(other, ids, f"{mission_id}: unknown prerequisite {other!r}")

        def has_cycle(mission_id, chain):
            return mission_id in chain or any(has_cycle(o, chain | {mission_id}) for o in prerequisites[mission_id])

        for mission_id in ids:
            self.assertFalse(has_cycle(mission_id, frozenset()), f"{mission_id}: prerequisite cycle")

    def test_rewards_are_valid_effects(self):
        for mission in MISSIONS:
            for reward in all_rewards(mission):
                self.assertEqual(validate_effect(reward), [], f"{mission['id']}: bad reward {reward}")


# ---------------------------------------------------------------------------
# "stockpile" objectives: HOLD at least N of a resource (a level, not a running total like "collection").
# ---------------------------------------------------------------------------
def stockpile_objectives():
    """(mission id, objective) for every stockpile objective of every mission."""
    return [(mission["id"], objective)
            for mission in MISSIONS for objective in all_objectives(mission) if objective["type"] == "stockpile"]


def open_mission(manager, game, mission_id):
    """Accept a mission whatever its prerequisites are (they are not the point of these tests)."""
    manager.missions[mission_id]["status"] = "Available"
    assert manager.accept_mission(game, mission_id)


class StockpileDataTests(unittest.TestCase):
    def test_there_are_stockpile_missions(self):
        self.assertTrue(stockpile_objectives())

    def test_objectives_are_well_formed(self):
        for mission_id, objective in stockpile_objectives():
            self.assertIn(objective.get("resource"), RESOURCE_FIELDS, f"{mission_id}: unknown resource")
            target = objective.get("target")
            self.assertTrue(isinstance(target, int) and not isinstance(target, bool) and target > 0,
                            f"{mission_id}: target must be a positive integer, got {target!r}")
            self.assertTrue(objective.get("description"), f"{mission_id}: a stockpile objective needs a description")

    def test_targets_fit_the_starting_convoy(self):
        """A target above what the three starting vehicles can carry would need a recovered vehicle or an upgrade
        first. Fuel has its own capacity; food, water and scrap share the cargo capacity, so a mission's cargo
        targets must fit it together."""
        start = [VEHICLE_SPECS[name] for name in ("Pickup Truck", "Passenger Van", "School Bus")]
        fuel_capacity = sum(spec["fuel_capacity"] for spec in start)
        cargo_capacity = sum(spec["cargo"] for spec in start)
        for mission in MISSIONS:
            for group in objective_groups(mission):   # the objectives of one stage must hold together
                cargo_total = 0
                for objective in group:
                    if objective["type"] != "stockpile":
                        continue
                    if objective["resource"] == "fuel":
                        self.assertLessEqual(objective["target"], fuel_capacity, f"{mission['id']}: fuel target too high")
                    else:
                        cargo_total += objective["target"]
                self.assertLessEqual(cargo_total, cargo_capacity, f"{mission['id']}: cargo targets do not fit")

    def test_no_stockpile_mission_is_met_at_the_start_of_a_run(self):
        """A fresh run's supplies must not complete a stockpile mission the moment it is accepted."""
        game = Game(music=NullAudio(), sound=NullAudio())
        first_stage = {m["id"] for m in MISSIONS for o in objective_groups(m)[0] if o["type"] == "stockpile"}
        for mission_id in sorted(first_stage):   # a later stage may be met at once: its event still gates the mission
            game.reset()
            open_mission(game.mission_manager, game, mission_id)
            self.assertEqual(game.mission_manager.missions[mission_id]["status"], "Active",
                             f"{mission_id} is already met by the starting supplies")


class StockpileBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.manager = MissionManager()
        self.game = MissionGame()

    def status(self, mission_id):
        return self.manager.missions[mission_id]["status"]

    def progress(self, mission_id):
        return self.manager.missions[mission_id]["progress"]

    def test_completes_when_the_amount_is_held(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "full_tank")
        open_mission(self.manager, self.game, "full_tank")
        self.game.fuel = target - 1
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.status("full_tank"), "Active")
        self.assertEqual(self.progress("full_tank"), [target - 1])
        self.game.fuel = target
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.status("full_tank"), "Completed")

    def test_progress_falls_when_the_resource_is_spent(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "full_tank")
        open_mission(self.manager, self.game, "full_tank")
        self.game.fuel = target - 5
        self.manager.on_resources_changed(self.game)
        self.game.fuel = 3
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.progress("full_tank"), [3])
        self.assertEqual(self.status("full_tank"), "Active")

    def test_progress_is_capped_at_the_target(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "scrap_reserve")
        open_mission(self.manager, self.game, "scrap_reserve")
        self.game.scrap = target - 1
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.progress("scrap_reserve"), [target - 1])

    def test_collecting_alone_does_not_count(self):
        """Collection is a running total; a stockpile is only what is held. Collecting 99 fuel the game never
        actually added (it was spent again) must not advance a stockpile mission."""
        open_mission(self.manager, self.game, "full_tank")
        self.manager.on_resource_collected(self.game, "fuel", 99)
        self.assertEqual(self.progress("full_tank"), [0])
        self.assertEqual(self.status("full_tank"), "Active")

    def test_every_objective_must_hold_at_the_same_time(self):
        food, water = [o["target"] for mid, o in stockpile_objectives() if mid == "well_stocked"]
        open_mission(self.manager, self.game, "well_stocked")
        self.game.food = food
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.status("well_stocked"), "Active")   # water is still short
        self.game.food = 0                                          # the food is used up ...
        self.game.water = water
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.status("well_stocked"), "Active")   # ... before the water was there: not done
        self.game.food = food
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.status("well_stocked"), "Completed")

    def test_already_held_when_accepted_completes_at_once(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "full_tank")
        self.game.fuel = target + 10
        open_mission(self.manager, self.game, "full_tank")
        self.assertEqual(self.status("full_tank"), "Completed")

    def test_reward_is_given_once(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "full_tank")
        reward = next(r for m in MISSIONS if m["id"] == "full_tank" for r in m["rewards"])
        open_mission(self.manager, self.game, "full_tank")
        self.game.fuel = target
        for _ in range(3):
            self.manager.on_resources_changed(self.game)
        self.assertEqual(getattr(self.game, reward["resource"]), reward["amount"])

    def test_abandon_resets_and_reaccepting_rereads_the_stock(self):
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "scrap_reserve")
        open_mission(self.manager, self.game, "scrap_reserve")
        self.game.scrap = target - 2
        self.manager.on_resources_changed(self.game)
        self.manager.abandon_mission(self.game, "scrap_reserve")
        self.assertEqual(self.status("scrap_reserve"), "Available")
        self.assertEqual(self.progress("scrap_reserve"), [0])
        self.manager.accept_mission(self.game, "scrap_reserve")
        self.assertEqual(self.progress("scrap_reserve"), [target - 2])

    def test_a_reward_can_complete_another_stockpile_mission(self):
        """Mission A's reward leaves the convoy holding what mission B asks for: B completes without waiting for
        some other change."""
        self.manager.missions["bonus_a"] = {
            "data": {"id": "bonus_a", "title": "A", "prerequisites": [], "failure_conditions": [],
                     "objectives": [{"type": "collection", "resource": "scrap", "target": 1}],
                     "rewards": [{"type": "resource", "resource": "food", "amount": 10}]},
            "status": "Active", "progress": [0]}
        self.manager.missions["bonus_b"] = {
            "data": {"id": "bonus_b", "title": "B", "prerequisites": [], "failure_conditions": [],
                     "objectives": [{"type": "stockpile", "resource": "food", "target": 10}],
                     "rewards": []},
            "status": "Active", "progress": [0]}
        self.manager.on_resource_collected(self.game, "scrap", 1)
        self.assertEqual(self.status("bonus_a"), "Completed")
        self.assertEqual(self.status("bonus_b"), "Completed")


class StockpileGameHookTests(unittest.TestCase):
    """The real Game credits a stockpile mission as soon as scavenged / gained supplies reach the target."""

    def test_gain_completes_a_hold_mission(self):
        game = Game(music=NullAudio(), sound=NullAudio())
        open_mission(game.mission_manager, game, "scrap_reserve")
        target = next(o["target"] for mid, o in stockpile_objectives() if mid == "scrap_reserve")
        game.gain_cargo({"scrap": target})
        self.assertEqual(game.mission_manager.missions["scrap_reserve"]["status"], "Completed")

    def test_spending_afterwards_does_not_undo_a_completed_mission(self):
        game = Game(music=NullAudio(), sound=NullAudio())
        open_mission(game.mission_manager, game, "scrap_reserve")
        game.gain_cargo({"scrap": 30})
        game.scrap = 0
        game.mission_manager.on_resources_changed(game)
        self.assertEqual(game.mission_manager.missions["scrap_reserve"]["status"], "Completed")


# ---------------------------------------------------------------------------
# Multi-stage missions ("stages", dedicated "event" objectives, "vehicle" and "travel" objectives).
# ---------------------------------------------------------------------------
class _Owned:
    """A vehicle as owned_vehicle_names reads it."""

    def __init__(self, vehicle_type):
        self.vehicle_type = vehicle_type


def owned(*names):
    return [_Owned(name) for name in names]


def staged_missions():
    return [mission for mission in MISSIONS if mission.get("stages")]


def mission_event_ids():
    return {event["id"] for event in event_data.EVENTS if event.get("trigger") == "mission"}


def vehicles_gained_by(event_id):
    """Vehicle types an event can give (its vehicle_gain effects)."""
    event = next(e for e in event_data.EVENTS if e["id"] == event_id)
    return {effect["vehicle"] for choice in event["choices"] for effect in choice["effects"]
            if effect.get("type") == "vehicle_gain"}


def accept_stage(manager, game, mission_id, stage):
    """Accept a mission and jump to a later stage (what earlier stages did is not the point)."""
    open_mission(manager, game, mission_id)
    assert manager.restore_stage(mission_id, stage)


class StageDataTests(unittest.TestCase):
    def test_there_are_staged_missions(self):
        self.assertGreaterEqual(len(staged_missions()), 6)

    def test_a_mission_has_objectives_or_stages_not_both(self):
        for mission in MISSIONS:
            with self.subTest(mission=mission["id"]):
                self.assertNotEqual("stages" in mission, "objectives" in mission)

    def test_every_stage_is_complete(self):
        for mission in staged_missions():
            for number, stage in enumerate(mission["stages"], start=1):
                with self.subTest(mission=mission["id"], stage=number):
                    self.assertTrue(stage.get("title"))
                    self.assertTrue(stage.get("description"))
                    self.assertTrue(stage.get("objectives"))
                    for objective in stage["objectives"]:
                        self.assertTrue(objective.get("description"), f"{objective} needs a description")
                    for reward in stage.get("rewards", []):
                        self.assertEqual(validate_effect(reward), [])

    def test_event_objectives_name_mission_events_and_each_is_used_once(self):
        used = [o["event_id"] for m in MISSIONS for o in all_objectives(m) if o["type"] == "event"]
        self.assertEqual(len(used), len(set(used)), "an event is the objective of two stages")
        self.assertEqual(set(used), mission_event_ids(), "a mission event no stage uses, or a stage naming no event")

    def test_a_stage_has_at_most_one_event_objective(self):
        for mission in MISSIONS:
            for group in objective_groups(mission):
                with self.subTest(mission=mission["id"]):
                    self.assertLessEqual(sum(1 for o in group if o["type"] == "event"), 1)

    def test_vehicle_and_travel_objectives_name_real_vehicles(self):
        for mission in MISSIONS:
            for objective in all_objectives(mission):
                if objective["type"] in ("vehicle", "travel") and "vehicle" in objective:
                    with self.subTest(mission=mission["id"]):
                        self.assertIn(objective["vehicle"], VEHICLE_SPECS)

    def test_a_vehicle_a_stage_asks_for_was_offered_by_an_earlier_stage(self):
        """Never ask for the Excavator unless an earlier stage's event hands it out."""
        for mission in staged_missions():
            offered = set()
            for number, stage in enumerate(mission["stages"], start=1):
                for objective in stage["objectives"]:
                    if objective["type"] == "vehicle":
                        with self.subTest(mission=mission["id"], stage=number):
                            self.assertIn(objective["vehicle"], offered)
                for objective in stage["objectives"]:
                    if objective["type"] == "event":
                        offered |= vehicles_gained_by(objective["event_id"])

    def test_every_event_achievement_has_its_mission(self):
        from achievement_data import ACHIEVEMENTS
        used = {o["event_id"] for m in MISSIONS for o in all_objectives(m) if o["type"] == "event"}
        for achievement in ACHIEVEMENTS:
            if achievement["condition"]["kind"] == "event":
                for event_id in achievement["condition"]["events"]:
                    self.assertIn(event_id, used, achievement["id"])


class StageBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.manager = MissionManager()
        self.game = MissionGame()

    def state(self, mission_id):
        return self.manager.missions[mission_id]

    def test_accepting_shows_the_first_stage(self):
        open_mission(self.manager, self.game, "clear_the_road")
        data = self.state("clear_the_road")["data"]
        self.assertEqual((data["stage"], data["stage_count"]), (1, 2))
        self.assertEqual(data["objectives"], MISSIONS[[m["id"] for m in MISSIONS].index("clear_the_road")]
                         ["stages"][0]["objectives"])
        self.assertEqual(len(self.state("clear_the_road")["progress"]), 2)

    def test_the_event_waits_until_the_other_objectives_are_met(self):
        open_mission(self.manager, self.game, "clear_the_road")
        self.assertEqual(self.manager.pending_event_ids(self.game), [])
        self.manager.on_resource_collected(self.game, "scrap", 10)
        self.assertEqual(self.manager.pending_event_ids(self.game), ["construction_yard"])

    def test_resolving_the_event_finishes_the_stage_and_pays_its_reward_once(self):
        open_mission(self.manager, self.game, "clear_the_road")
        self.manager.on_resource_collected(self.game, "scrap", 10)
        self.manager.on_event_resolved(self.game, "construction_yard")
        state = self.state("clear_the_road")
        self.assertEqual((state["data"]["stage"], state["status"]), (2, "Active"))
        self.assertEqual(self.game.fuel, 8)                         # the stage's reward
        self.manager.on_event_resolved(self.game, "construction_yard")
        self.assertEqual(self.game.fuel, 8)                         # nothing is paid twice

    def test_an_event_of_a_later_stage_counts_for_nothing_yet(self):
        open_mission(self.manager, self.game, "clear_the_road")
        self.manager.on_event_resolved(self.game, "heavy_machinery")
        self.assertEqual(self.state("clear_the_road")["progress"], [0, 0])

    def test_the_last_stage_completes_the_mission_and_pays_the_mission_reward(self):
        accept_stage(self.manager, self.game, "clear_the_road", 1)
        self.game.vehicles = owned("Excavator")
        self.manager.on_resources_changed(self.game)
        self.manager.on_event_resolved(self.game, "heavy_machinery")
        self.assertEqual(self.state("clear_the_road")["status"], "Completed")
        self.assertEqual((self.game.scrap, self.game.fuel), (12, 10))

    def test_a_vehicle_objective_is_a_level(self):
        accept_stage(self.manager, self.game, "clear_the_road", 1)
        self.assertEqual(self.state("clear_the_road")["progress"][0], 0)
        self.game.vehicles = owned("Excavator")
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.state("clear_the_road")["progress"][0], 1)
        self.game.vehicles = []                                       # the excavator is lost
        self.manager.on_resources_changed(self.game)
        self.assertEqual(self.state("clear_the_road")["progress"][0], 0)
        self.assertEqual(self.manager.pending_event_ids(self.game), [])

    def test_travel_only_counts_with_the_vehicle(self):
        accept_stage(self.manager, self.game, "armour_up", 1)
        progress = lambda: self.state("armour_up")["progress"]
        self.manager.on_journey_completed(self.game)                  # no tank: not counted
        self.assertEqual(progress()[1], 0)
        self.game.vehicles = owned("Tank")
        self.manager.on_journey_completed(self.game)
        self.manager.on_journey_completed(self.game)
        self.manager.on_journey_completed(self.game)                  # capped at the target
        self.assertEqual(progress()[1], 2)

    def test_a_travel_objective_without_a_vehicle_counts_every_journey(self):
        accept_stage(self.manager, self.game, "strange_music", 1)
        self.manager.on_journey_completed(self.game)
        self.assertEqual(self.state("strange_music")["progress"][0], 1)

    def test_a_flagged_destination_counts_only_that_stop(self):
        open_mission(self.manager, self.game, "armour_up")
        for stop, node in enumerate(map_data.NODES):
            if not node.get("military_base"):
                self.manager.on_destination_reached(self.game, stop)
        self.assertEqual(self.state("armour_up")["progress"][0], 0)
        self.manager.on_destination_reached(self.game, map_data.MILITARY_BASE)
        self.assertEqual(self.state("armour_up")["progress"][0], 1)

    def test_a_destination_already_reached_counts_when_a_stage_begins(self):
        self.game.position = 4                                        # City 4: further than every stage-one distance
        open_mission(self.manager, self.game, "last_broadcast")
        self.assertEqual(self.state("last_broadcast")["progress"][0], 1)
        self.manager.on_event_resolved(self.game, "news_van_signal")
        self.assertEqual(self.state("last_broadcast")["data"]["stage"], 2)

    def test_abandoning_goes_back_to_the_first_stage(self):
        accept_stage(self.manager, self.game, "the_package", 2)
        self.manager.abandon_mission(self.game, "the_package")
        state = self.state("the_package")
        self.assertEqual((state["status"], state["data"]["stage"], state["stage"]), ("Available", 1, 0))
        self.assertEqual(state["progress"], [0])

    def test_restore_stage_rejects_what_does_not_fit(self):
        self.assertFalse(self.manager.restore_stage("fuel_run", 1))           # a plain mission
        self.assertFalse(self.manager.restore_stage("no_such_mission", 0))
        for bad in (-1, 99, True, "1", None):
            self.assertFalse(self.manager.restore_stage("the_package", bad), repr(bad))
        self.assertTrue(self.manager.restore_stage("the_package", 2))
        self.assertEqual(self.state("the_package")["data"]["stage_title"], "Presidential Protection")

    def test_a_mission_naming_an_unknown_event_is_refused(self):
        bad = {"id": "bad", "title": "B", "description": "", "prerequisites": [], "rewards": [], "failure_conditions": [],
               "stages": [{"title": "S", "description": "d", "objectives": [{"type": "event", "event_id": "nope"}]}]}
        with mock.patch("game.mission_manager.MISSIONS", MISSIONS + [bad]):
            with self.assertRaises(ValueError):
                MissionManager()
        ordinary = dict(bad, id="bad2", stages=[{"title": "S", "description": "d", "objectives": [
            {"type": "event", "event_id": "roadside_cache"}]}])   # an ordinary event is not a mission event
        with mock.patch("game.mission_manager.MISSIONS", MISSIONS + [ordinary]):
            with self.assertRaises(ValueError):
                MissionManager()


class StageGameTests(unittest.TestCase):
    """The real Game: mission events open by themselves, "not now" defers them, achievements follow."""

    def setUp(self):
        self.game = Game(music=NullAudio(), sound=NullAudio())
        self.game.screen = "convoy"                                  # a new Game starts on the title screen
        open_mission(self.game.mission_manager, self.game, "clear_the_road")
        self.manager = self.game.mission_manager
        self.game.gain_cargo({"scrap": 10})                          # stage one: collect 10 scrap

    def open_event(self):
        self.assertTrue(self.manager.open_stage_event(self.game))
        return self.game.event_manager.current_event["id"]

    def test_the_event_opens_once_the_stage_is_ready(self):
        self.assertEqual(self.open_event(), "construction_yard")

    def test_nothing_opens_mid_journey_or_while_another_popup_is_open(self):
        self.game.journey = {"dest": 1, "days": 2, "day": 1}
        self.assertFalse(self.manager.open_stage_event(self.game))
        self.game.journey = None
        self.game.screen = "map"
        self.assertFalse(self.manager.open_stage_event(self.game))
        self.game.screen = "convoy"
        self.assertEqual(self.open_event(), "construction_yard")
        self.assertFalse(self.manager.open_stage_event(self.game))   # one is open already

    def test_not_now_defers_the_event_to_the_next_stop_and_awards_nothing(self):
        self.open_event()
        index = next(i for i, c in enumerate(self.game.event_manager.current_event["choices"]) if c.get("declines_mission"))
        self.game.resolve_event_choice(index)
        self.game.dismiss_event_result()
        self.assertEqual(self.manager.missions["clear_the_road"]["data"]["stage"], 1)
        self.assertFalse(self.manager.open_stage_event(self.game))   # same stop: not again
        self.game.travel_count += 1                                  # the convoy reached another stop
        self.assertEqual(self.open_event(), "construction_yard")

    def test_the_whole_mission_ends_in_the_heavy_machinery_achievement(self):
        game = self.game
        with mock.patch("game.effect_handler.has_spare_driver", return_value=True):   # a driver for the new vehicle
            self.assertEqual(self.open_event(), "construction_yard")
            game.scrap = 15
            game.resolve_event_choice(0)                              # pay 8 scrap for the excavator
            game.dismiss_event_result()
            self.assertIn("Excavator", [v.vehicle_type for v in game.vehicles])
            self.assertEqual(self.manager.missions["clear_the_road"]["data"]["stage"], 2)
            self.assertEqual(self.open_event(), "heavy_machinery")
            game.resolve_event_choice(0)                              # dig through with the excavator
            game.dismiss_event_result()
        self.assertEqual(self.manager.missions["clear_the_road"]["status"], "Completed")
        self.assertTrue(game.achievements.is_complete("heavy_machinery"))
        self.assertIn("Excavator", game.achievements.unlocked_vehicles())

    def test_the_stage_is_saved_and_loaded(self):
        import savegame
        self.manager.on_event_resolved(self.game, "construction_yard")          # now at stage two
        data = json.loads(json.dumps(savegame.to_dict(self.game)))
        self.assertEqual(data["missions"]["clear_the_road"]["stage"], 1)
        fresh = Game(music=NullAudio(), sound=NullAudio())
        savegame.load_into(fresh, data)
        state = fresh.mission_manager.missions["clear_the_road"]
        self.assertEqual((state["stage"], state["data"]["stage"]), (1, 2))
        self.assertEqual(len(state["progress"]), len(state["data"]["objectives"]))

    def test_an_old_save_without_a_stage_loads_at_the_first_stage(self):
        import savegame
        data = json.loads(json.dumps(savegame.to_dict(self.game)))
        for saved in data["missions"].values():
            saved.pop("stage", None)
        fresh = Game(music=NullAudio(), sound=NullAudio())
        savegame.load_into(fresh, data)
        self.assertEqual(fresh.mission_manager.missions["clear_the_road"]["stage"], 0)


if __name__ == "__main__":
    unittest.main()
