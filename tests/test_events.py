"""Tests for event_data.py and the event manager (selection, ambush pool, locked choices, resolving, the result screen).

The manager tests use small events defined in this file, so changing the numbers in event_data.py never breaks them.
The DATA tests (EventDataTests) check the rules written at the top of event_data.py against every real event.
"""

import random
import unittest
from unittest import mock

import widgets
from game import event_data, event_manager
from game.effect_handler import check_events, is_payment, shortfalls, unmet_requirement_notes

from tests.helpers import make_game


def make_event(event_id, weight=1, **extra):
    """A minimal valid event with two harmless choices."""
    event = {"id": event_id, "weight": weight, "title": event_id.title(), "description": "Something happened.",
             "choices": [{"label": "OK", "outcome": "Fine.", "effects": []},
                         {"label": "Leave", "outcome": "You drive on.", "effects": []}]}
    event.update(extra)
    return event


CACHE = {
    "id": "test_cache", "weight": 1, "title": "Supply cache", "description": "A cache beside the road.",
    "choices": [
        {"label": "Take everything", "outcome": "You load it all.",
         "effects": [{"type": "resource", "resource": "scrap", "amount": 4}, {"type": "horde_gap", "amount": -2}]},
        {"label": "Take only the scrap", "outcome": "You grab the scrap.",
         "effects": [{"type": "resource", "resource": "scrap", "amount": 2}, {"type": "horde_gap", "amount": -1}]},
        {"label": "Leave it alone", "outcome": "You drive on.", "effects": []},
    ],
}

PAY = {"label": "Pay the mechanic", "payment": True, "outcome": "Fixed.",
       "effects": [{"type": "resource", "resource": "scrap", "amount": -5}]}
LEAVE = {"label": "Drive on", "outcome": "You drive on.", "effects": []}
MECHANIC = {"id": "test_mechanic", "weight": 1, "title": "Mechanic", "description": "A garage.",
            "choices": [PAY, LEAVE]}

RESCUE = {
    "id": "test_rescue", "weight": 1, "title": "Rescue", "description": "People wave at you.",
    "choices": [
        {"label": "Take them aboard", "payment": True, "requires": {"free_seats_at_least": 1},
         "outcome": "They climb aboard.",
         "effects": [{"type": "resource", "resource": "scrap", "amount": -8},
                     {"type": "survivors", "amount": 4}, {"type": "horde_gap", "amount": -2}]},
        {"label": "Leave", "outcome": "You drive on.", "effects": []},
    ],
}


def requirement(event, choice, key):
    """The value of a "requires" key on the event or on the choice (the larger one; 0 / False when neither has it)."""
    return max((requires.get(key, 0) for requires in (event.get("requires") or {}, choice.get("requires") or {})),
               default=0)


class EventDataTests(unittest.TestCase):
    def test_every_event_passes_the_validator(self):
        check_events(event_data.EVENTS)   # raises ValueError listing every typo at once

    def test_there_are_events_with_unique_ids(self):
        ids = [event["id"] for event in event_data.EVENTS]
        self.assertGreater(len(ids), 0)
        self.assertEqual(len(ids), len(set(ids)), "duplicate event ids")

    def test_every_event_is_complete(self):
        for event in event_data.EVENTS:
            with self.subTest(event=event.get("id")):
                weight = event.get("weight")
                self.assertTrue(isinstance(weight, (int, float)) and not isinstance(weight, bool),
                                "weights are numbers (fractions are fine: the vehicle events use 0.3)")
                if event.get("trigger") in ("evacuation", "mission"):
                    self.assertGreaterEqual(weight, 0)   # scripted events are opened by id, never drawn
                else:
                    self.assertGreater(weight, 0)
                self.assertTrue(event.get("title"))
                self.assertTrue(event.get("description"))
                # Number keys 1-4 select a choice, and a single choice is not a decision.
                self.assertTrue(2 <= len(event["choices"]) <= 4, "events need 2-4 choices")
                lines = widgets.wrap_text(event["description"], 76)
                self.assertLessEqual(len(lines), 3, "description is too long for the overlay")

    def test_every_choice_is_complete(self):
        for event in event_data.EVENTS:
            for choice in event["choices"]:
                with self.subTest(event=event["id"], choice=choice.get("label")):
                    self.assertTrue(choice.get("label"))
                    self.assertLessEqual(len(choice["label"]), 60)
                    self.assertTrue(choice.get("outcome"))
                    self.assertIsInstance(choice.get("effects"), list)

    def test_trigger_is_none_ambush_evacuation_or_mission(self):
        for event in event_data.EVENTS:
            with self.subTest(event=event["id"]):
                self.assertIn(event.get("trigger"), (None, "ambush", "evacuation", "mission"))

    def test_there_are_ordinary_and_ambush_events(self):
        triggers = [event.get("trigger") for event in event_data.EVENTS]
        self.assertIn(None, triggers)
        self.assertIn("ambush", triggers)

    def test_every_choice_can_be_played_on_a_fresh_game(self):
        """Choices a fresh convoy cannot take (a requirement it does not meet, a payment it cannot afford) are locked
        and must say why; every other choice resolves, ends the event and does not lose the game."""
        for event in event_data.EVENTS:
            playable = 0
            for index, choice in enumerate(event["choices"]):
                with self.subTest(event=event["id"], choice=choice["label"]):
                    game = make_game()
                    manager = event_manager.EventManager()
                    manager.current_event = event
                    if not manager.can_choose(game, index):
                        self.assertTrue(unmet_requirement_notes(game, choice) or shortfalls(game, choice),
                                        "locked, but nothing tells the player why")
                        continue
                    outcome = manager.resolve_choice(game, index)
                    self.assertIsInstance(outcome, str)
                    self.assertFalse(manager.active)
                    self.assertEqual(game.status, "playing")
                    playable += 1
            with self.subTest(event=event["id"], check="something can be picked"):
                self.assertGreater(playable, 0)

    # --- the rules written at the top of event_data.py
    def test_ambush_events_have_a_choice_that_needs_nothing(self):
        for event in event_data.EVENTS:
            if event.get("trigger") != "ambush":
                continue
            with self.subTest(event=event["id"]):
                self.assertTrue(any(not is_payment(c) and not c.get("requires") for c in event["choices"]),
                                "an ambush needs a penalty choice that is always pickable")

    def test_every_event_has_a_choice_that_is_never_locked(self):
        """A penalty (not a payment) without a "requires" can always be picked, so the player is never stuck."""
        for event in event_data.EVENTS:
            with self.subTest(event=event["id"]):
                self.assertTrue(any(not is_payment(c) and not c.get("requires") for c in event["choices"]))

    def test_choices_that_take_people_aboard_need_a_free_seat(self):
        for event in event_data.EVENTS:
            for choice in event["choices"]:
                gains = any(e.get("type") == "survivors" and e.get("amount", 0) > 0 for e in choice["effects"])
                if gains:
                    with self.subTest(event=event["id"], choice=choice["label"]):
                        self.assertGreaterEqual(requirement(event, choice, "free_seats_at_least"), 1)

    def test_vehicle_gain_events_need_a_slot_and_are_very_rare(self):
        for event in event_data.EVENTS:
            for choice in event["choices"]:
                if any(e.get("type") == "vehicle_gain" for e in choice["effects"]):
                    with self.subTest(event=event["id"], choice=choice["label"]):
                        self.assertTrue(requirement(event, choice, "vehicle_slot"))
                        self.assertLess(event["weight"], 1)

    def test_vehicle_loss_choices_need_at_least_two_vehicles(self):
        for event in event_data.EVENTS:
            for choice in event["choices"]:
                if any(e.get("type") == "vehicle_loss" for e in choice["effects"]):
                    with self.subTest(event=event["id"], choice=choice["label"]):
                        self.assertGreaterEqual(requirement(event, choice, "vehicles_at_least"), 2)


def mission_events():
    return [event for event in event_data.EVENTS if event.get("trigger") == "mission"]


class MissionEventDataTests(unittest.TestCase):
    """The dedicated events of the multi-stage missions (mission_event_data.py)."""

    def test_the_mission_events_are_part_of_the_event_list(self):
        from game.mission_event_data import MISSION_EVENTS
        self.assertTrue(MISSION_EVENTS)
        ids = {event["id"] for event in event_data.EVENTS}
        for event in MISSION_EVENTS:
            self.assertIn(event["id"], ids)
            self.assertEqual(event["trigger"], "mission")

    def test_every_mission_event_has_a_not_now_choice_that_needs_nothing(self):
        """The player is never stuck: a "declines_mission" choice is never a payment and never has a requirement."""
        for event in mission_events():
            declines = [c for c in event["choices"] if c.get("declines_mission")]
            with self.subTest(event=event["id"]):
                self.assertTrue(declines, "needs a choice with declines_mission")
                for choice in declines:
                    self.assertFalse(is_payment(choice))
                    self.assertFalse(choice.get("requires"))
                    for effect in choice["effects"]:   # saying "not now" never gives a vehicle or survivors
                        self.assertNotIn(effect["type"], ("vehicle_gain", "survivors"))

    def test_at_least_one_choice_moves_the_mission_on(self):
        for event in mission_events():
            with self.subTest(event=event["id"]):
                self.assertTrue(any(not c.get("declines_mission") for c in event["choices"]))

    def test_declines_mission_is_only_used_by_mission_events(self):
        for event in event_data.EVENTS:
            if event.get("trigger") != "mission":
                with self.subTest(event=event["id"]):
                    self.assertFalse(any(c.get("declines_mission") for c in event["choices"]))

    def test_mission_events_are_never_drawn_at_random(self):
        ids = {event["id"] for event in mission_events()}
        game = make_game()
        random.seed(3)
        for trigger in (None, "ambush"):
            manager = event_manager.EventManager()
            for _ in range(60):
                event = manager.start_for_arrival(game, trigger)
                if event is not None:
                    self.assertNotIn(event["id"], ids)
                manager.current_event = None

    def test_vehicle_choices_name_vehicles_that_exist(self):
        from vehicle_data import VEHICLE_SPECS
        for event in mission_events():
            for choice in event["choices"]:
                for effect in choice["effects"]:
                    if effect.get("type") == "vehicle_gain":
                        with self.subTest(event=event["id"]):
                            self.assertIn(effect.get("vehicle"), VEHICLE_SPECS)

    def test_start_event_opens_one_by_id(self):
        game, manager = make_game(), event_manager.EventManager()
        event = manager.start_event(game, "tank_depot", announce="Mission")
        self.assertEqual(event["id"], "tank_depot")
        self.assertTrue(any(str(line).startswith("Mission: The Armoured Depot") for line in game.log), game.log)
        self.assertIsNone(manager.start_event(game, "heavy_machinery"))   # one is open already

    def test_a_vehicle_choice_is_locked_without_the_vehicle(self):
        game, manager = make_game(), event_manager.EventManager()
        manager.current_event = next(e for e in mission_events() if e["id"] == "heavy_machinery")
        self.assertFalse(manager.can_choose(game, 0))   # needs the Excavator
        self.assertTrue(manager.can_choose(game, 1))    # "Not now"


class EventManagerTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()
        self.em = event_manager.EventManager()

    def test_starts_inactive(self):
        self.assertFalse(self.em.active)
        self.assertIsNone(self.em.current_event)
        self.assertIsNone(self.em.result)

    def test_start_selects_an_event_and_logs_it(self):
        event = self.em.start_for_arrival(self.g)
        self.assertIn(event, event_data.EVENTS)
        self.assertTrue(self.em.active)
        self.assertTrue(any(str(line).startswith("Unexpected situation") for line in self.g.log))

    def test_start_does_nothing_while_an_event_is_active(self):
        first = self.em.start_for_arrival(self.g)
        self.assertIsNone(self.em.start_for_arrival(self.g))
        self.assertIs(self.em.current_event, first)

    def test_start_does_nothing_after_the_game_ended(self):
        self.g.status = "lost"
        self.assertIsNone(self.em.start_for_arrival(self.g))
        self.assertFalse(self.em.active)

    def test_no_event_repeats_within_the_last_two(self):
        random.seed(12345)
        ids = []
        for _ in range(80):
            ids.append(self.em.start_for_arrival(self.g)["id"])
            self.em.current_event = None
        for i, event_id in enumerate(ids):
            self.assertNotIn(event_id, ids[max(0, i - 2):i], f"repeat at position {i}")

    def test_only_the_last_two_events_are_remembered(self):
        events = [make_event(f"e{i}") for i in range(6)]
        with mock.patch.object(event_manager, "EVENTS", events):
            for _ in range(10):
                self.em.start_for_arrival(self.g)
                self.em.current_event = None
        self.assertEqual(len(self.em.last_event_ids), 2)

    def test_zero_weight_events_are_never_chosen(self):
        events = [make_event("never", weight=0), make_event("always", weight=1)]
        with mock.patch.object(event_manager, "EVENTS", events):
            for _ in range(20):
                self.assertEqual(self.em.start_for_arrival(self.g)["id"], "always")
                self.em.current_event = None

    def test_an_event_without_a_weight_counts_as_one(self):
        event = make_event("plain")
        del event["weight"]
        with mock.patch.object(event_manager, "EVENTS", [event]):
            self.assertEqual(self.em.start_for_arrival(self.g)["id"], "plain")

    def test_no_events_defined(self):
        with mock.patch.object(event_manager, "EVENTS", []):
            self.assertIsNone(self.em.start_for_arrival(self.g))

    # --- the ambush pool
    def test_ordinary_arrivals_never_draw_ambush_events(self):
        ambush = make_event("raiders", trigger="ambush")
        with mock.patch.object(event_manager, "EVENTS", [ambush]):
            self.assertIsNone(self.em.start_for_arrival(self.g))
        random.seed(7)
        for _ in range(60):
            event = self.em.start_for_arrival(self.g)
            self.assertIsNone(event.get("trigger"), event["id"])
            self.em.current_event = None

    def test_an_ambush_draws_only_ambush_events(self):
        events = [make_event("ordinary"), make_event("raiders", trigger="ambush")]
        with mock.patch.object(event_manager, "EVENTS", events):
            for _ in range(15):
                self.assertEqual(self.em.start_for_arrival(self.g, "ambush")["id"], "raiders")
                self.em.current_event = None

    def test_an_ambush_is_logged_as_one(self):
        with mock.patch.object(event_manager, "EVENTS", [make_event("raiders", trigger="ambush")]):
            self.em.start_for_arrival(self.g, "ambush")
        self.assertTrue(any(str(line).startswith("Road ambush: Raiders") for line in self.g.log), self.g.log)

    def test_an_ambush_with_no_ambush_events_returns_none(self):
        with mock.patch.object(event_manager, "EVENTS", [make_event("ordinary")]):
            self.assertIsNone(self.em.start_for_arrival(self.g, "ambush"))

    def test_the_real_ambush_events_open_on_a_fresh_game(self):
        for _ in range(10):
            event = self.em.start_for_arrival(self.g, "ambush")
            self.assertIsNotNone(event)
            self.assertEqual(event["trigger"], "ambush")
            self.em.current_event = None

    # --- resolving
    def test_resolving_applies_effects_and_ends_the_event(self):
        g = self.g
        g.horde = 200
        g.scrap = 5
        self.em.current_event = CACHE
        outcome = self.em.resolve_choice(g, 1)         # "Take only the scrap": +2 scrap, -1 km gap
        self.assertIn("Scrap +2", outcome)
        self.assertEqual(g.scrap, 7)
        self.assertEqual(g.horde, 199)
        self.assertFalse(self.em.active)

    def test_resolving_with_no_effects_still_gives_the_outcome(self):
        self.em.current_event = CACHE
        outcome = self.em.resolve_choice(self.g, 2)    # "Leave it alone": no effects
        self.assertEqual(outcome, CACHE["choices"][2]["outcome"])

    def test_resolving_records_the_result_for_the_result_screen(self):
        g = self.g
        g.horde = 200
        g.scrap = 5
        self.em.current_event = CACHE
        self.assertIsNone(self.em.result)
        outcome = self.em.resolve_choice(g, 1)                       # "Take only the scrap"
        result = self.em.result
        self.assertEqual(result["title"], CACHE["title"])
        self.assertEqual(result["choice"], CACHE["choices"][1]["label"])
        self.assertEqual(result["outcome"], CACHE["choices"][1]["outcome"])   # plain text, no effect notes
        self.assertIn(("Scrap +2", True), result["changes"])
        self.assertIn("Scrap +2", outcome)                           # the event log keeps the notes
        self.assertNotIn("(", result["outcome"])
        self.em.clear_result()
        self.assertIsNone(self.em.result)

    def test_a_choice_without_effects_has_no_changes(self):
        self.em.current_event = CACHE
        self.em.resolve_choice(self.g, 2)                            # "Leave it alone"
        self.assertEqual(self.em.result["changes"], [])

    def test_changes_are_listed_as_good_or_bad(self):
        self.em.current_event = {"title": "T", "choices": [{"label": "L", "outcome": "O", "effects": [
            {"type": "resource", "resource": "scrap", "amount": 2},
            {"type": "survivors", "amount": -1},
        ]}]}
        self.em.resolve_choice(self.g, 0)
        self.assertEqual(dict(self.em.result["changes"]), {"Scrap +2": True, "Survivors -1": False})

    def test_invalid_choices_leave_no_result(self):
        self.em.current_event = CACHE
        self.em.resolve_choice(self.g, 99)
        self.assertIsNone(self.em.result)

    def test_invalid_choices_are_ignored(self):
        self.em.current_event = CACHE
        for bad in (-1, 99, "1", None, 1.0):
            self.assertIsNone(self.em.resolve_choice(self.g, bad), repr(bad))
            self.assertTrue(self.em.active)

    def test_resolving_without_an_event_does_nothing(self):
        self.assertIsNone(self.em.resolve_choice(self.g, 0))

    # --- locked choices
    def test_can_choose(self):
        self.g.scrap = 1
        self.assertFalse(self.em.can_choose(self.g, 0))              # no event open
        self.em.current_event = MECHANIC
        self.assertFalse(self.em.can_choose(self.g, 0))              # a payment the convoy cannot afford
        self.assertTrue(self.em.can_choose(self.g, 1))               # a penalty-free choice
        for bad in (-1, 2, 99, "1", None, 1.0):
            self.assertFalse(self.em.can_choose(self.g, bad), repr(bad))
        self.g.scrap = 5
        self.assertTrue(self.em.can_choose(self.g, 0))

    def test_a_locked_choice_cannot_be_resolved(self):
        self.g.scrap = 1
        self.em.current_event = MECHANIC
        self.assertIsNone(self.em.resolve_choice(self.g, 0))
        self.assertTrue(self.em.active)                              # the event stays open
        self.assertEqual(self.g.scrap, 1)                            # nothing was spent
        self.assertIsNone(self.em.result)

    def test_paying_takes_the_cost(self):
        self.g.scrap = 8
        self.em.current_event = MECHANIC
        outcome = self.em.resolve_choice(self.g, 0)
        self.assertEqual(self.g.scrap, 3)
        self.assertIn("Scrap -5", outcome)
        self.assertIn(("Scrap -5", False), self.em.result["changes"])

    def test_when_nothing_is_pickable_nobody_is_stuck(self):
        self.g.scrap = 0
        self.em.current_event = dict(MECHANIC, choices=[PAY, dict(PAY, label="Pay double")])
        self.assertTrue(self.em.can_choose(self.g, 0))
        self.assertTrue(self.em.can_choose(self.g, 1))

    def test_a_choice_with_an_unmet_requirement_is_locked(self):
        locked = {"label": "Sacrifice a vehicle", "outcome": "Gone.", "effects": [{"type": "vehicle_loss"}],
                  "requires": {"vehicles_at_least": 99}}
        self.em.current_event = make_event("sacrifice", choices=[locked, LEAVE])
        self.assertFalse(self.em.can_choose(self.g, 0))
        self.assertTrue(self.em.can_choose(self.g, 1))
        self.assertIsNone(self.em.resolve_choice(self.g, 0))

    def test_a_rescue_is_locked_when_every_seat_is_taken(self):
        seats = self.g.convoy_stats()["passengers"]
        self.g.scrap = 20
        self.em.current_event = RESCUE
        self.g.survivors = seats
        self.assertFalse(self.em.can_choose(self.g, 0))
        self.g.survivors = seats - 1
        self.assertTrue(self.em.can_choose(self.g, 0))

    def test_a_rescue_that_does_not_fit_costs_only_what_came(self):
        g = self.g
        seats = g.convoy_stats()["passengers"]
        g.survivors = seats - 3                                      # 3 free seats for the 4 offered
        g.scrap = 20
        g.horde = 200
        self.em.current_event = RESCUE
        outcome = self.em.resolve_choice(g, 0)
        self.assertEqual(g.survivors, seats)
        self.assertEqual(g.scrap, 20 - 6)                            # 8 * 3/4
        self.assertEqual(g.horde, 198)                               # the time it took is not scaled
        self.assertIn("Only 3 of 4 could fit aboard", self.em.result["outcome"])
        self.assertIn("Only 3 of 4 could fit aboard", outcome)
        self.assertIn(("Scrap -6", False), self.em.result["changes"])

    def test_a_rescue_that_fits_has_no_scaling_note(self):
        g = self.g
        g.survivors = 0
        g.scrap = 20
        self.em.current_event = RESCUE
        self.em.resolve_choice(g, 0)
        self.assertNotIn("Only", self.em.result["outcome"])
        self.assertEqual(g.scrap, 12)

    # --- the result popup
    def test_show_result_is_used_by_anyone_who_wants_the_popup(self):
        self.em.show_result("Scavenged", "", "You found food.", [("Food +3", True)])
        self.assertEqual(self.em.result, {"title": "Scavenged", "choice": "", "outcome": "You found food.",
                                          "changes": [("Food +3", True)]})
        self.em.clear_result()
        self.assertIsNone(self.em.result)


class SnapGame:
    """The numbers snapshot() reads, all settable."""

    def __init__(self):
        self.fuel = self.food = self.water = self.scrap = 10
        self.survivors, self.horde, self.day, self.injured, self.health = 5, 50, 3, 0, 100
        self.vehicles = [object(), object()]

    def injured_count(self):
        return self.injured

    def convoy_health_pct(self):
        return self.health


class ChangesTests(unittest.TestCase):
    """snapshot() and changes(): what the result screen lists after a choice."""

    def diff(self, **new):
        game = SnapGame()
        before = event_manager.snapshot(game)
        for name, value in new.items():
            setattr(game, name, value)
        return event_manager.changes(before, game)

    def test_snapshot_has_every_number_a_choice_can_change(self):
        keys = set(event_manager.snapshot(SnapGame()))
        self.assertEqual(keys, {"fuel", "food", "water", "scrap", "survivors", "injured", "vehicles", "health",
                                "horde", "day", "berths"})

    def test_nothing_changed_nothing_listed(self):
        self.assertEqual(self.diff(), [])

    def test_gains_are_good_and_losses_bad(self):
        self.assertEqual(self.diff(fuel=13, water=8),
                         [("Fuel +3", True), ("Water -2", False)])

    def test_more_injured_survivors_is_bad_and_treatment_is_good(self):
        self.assertEqual(self.diff(injured=2), [("Injured +2", False)])
        game = SnapGame()
        game.injured = 3
        before = event_manager.snapshot(game)
        game.injured = 1
        self.assertEqual(event_manager.changes(before, game), [("Injured -2", True)])

    def test_units_and_vehicles(self):
        self.assertEqual(self.diff(health=90), [("Convoy health -10%", False)])
        self.assertEqual(self.diff(horde=55), [("Horde gap +5 km", True)])
        self.assertEqual(self.diff(horde=44), [("Horde gap -6 km", False)])
        self.assertEqual(self.diff(vehicles=[object()]), [("Vehicles -1", False)])
        self.assertEqual(self.diff(survivors=6), [("Survivors +1", True)])

    def test_days_that_pass_are_listed_last(self):
        self.assertEqual(self.diff(day=5, scrap=11), [("Scrap +1", True), ("2 day(s) pass", False)])


if __name__ == "__main__":
    unittest.main()
