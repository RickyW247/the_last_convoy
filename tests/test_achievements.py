"""Achievement tests (pygame-free). Run: python test_achievements.py"""
import os
import tempfile

import achievements
from achievement_data import ACHIEVEMENTS, BY_ID
from config import COLLECTOR_VEHICLE_TYPES
from achievements import AchievementTracker


ARMOURED_CONVOY = ("Military Humvee", "Military Cargo Truck", "Armored Personnel Carrier", "Tank")


class FakeVehicle:
    def __init__(self, vehicle_type, upgrades=()):
        self.vehicle_type = vehicle_type
        self.upgrades = list(upgrades)

    def has_upgrade(self, upgrade_id):
        return upgrade_id in self.upgrades


class FakeGame:
    """Just what the tracker reads from Game. The defaults are a plain win that earns nothing by accident: a slow run
    (not a speed run), one survivor lost, 8 survivors left, Normal difficulty and no armour on any vehicle."""
    def __init__(self, vehicles=("Pickup Truck",), recovered=0, sandbox=False, difficulty="Normal", upgrades=(), day=30):
        self.vehicles_list = list(vehicles)
        self.vehicles = [FakeVehicle(name, upgrades) for name in vehicles]   # `upgrades` go on every vehicle
        self.vehicles_recovered = recovered
        self.sandbox = sandbox
        self.difficulty = difficulty
        self.day = day
        self.survivors = 8
        self.survivors_lost = 1
        self.vehicles_wrecked = 0
        self.said = []

    def owned_vehicle_types(self):
        return list(self.vehicles_list)

    def say(self, message):
        self.said.append(message)


def _tracker():
    return AchievementTracker(os.path.join(tempfile.mkdtemp(), "sub", "achievements.json"))


def test_catalogue():
    assert len(ACHIEVEMENTS) == len(BY_ID) and set(BY_ID) == {a["id"] for a in ACHIEVEMENTS}


def test_no_achievement_is_a_placeholder_any_more():
    """Every achievement is completable: the missions of mission_data.py supply the events that used to be missing."""
    assert [a["id"] for a in ACHIEVEMENTS if a.get("placeholder")] == []


def test_win_then_second_win():
    tracker, game = _tracker(), FakeGame()
    tracker.on_victory(game)
    assert tracker.is_complete("coast_to_coast") and not tracker.is_complete("the_long_road_again")
    assert any("Coast to Coast" in line for line in game.said)
    tracker.on_victory(game)
    assert tracker.is_complete("the_long_road_again")
    count = len(game.said)
    tracker.on_victory(game)   # nothing is awarded twice
    assert len(game.said) == count


def test_collector_counts_all_runs_together():
    tracker = _tracker()
    types = [f"Type {i}" for i in range(COLLECTOR_VEHICLE_TYPES)]
    half = COLLECTOR_VEHICLE_TYPES // 2
    tracker.check(FakeGame(vehicles=types[:half]))
    assert not tracker.is_complete("convoy_collector")
    tracker.check(FakeGame(vehicles=types[half:]))   # a later run
    assert tracker.is_complete("convoy_collector")


def test_recovered_in_one_run():
    tracker, game = _tracker(), FakeGame(recovered=2)
    tracker.check(game)
    assert not tracker.is_complete("nothing_left_behind")
    game.vehicles_recovered = 3
    tracker.check(game)
    assert tracker.is_complete("nothing_left_behind")


def test_event_and_vehicle_achievements():
    """The event / vehicle conditions work: each mission event completes its achievement."""
    tracker, game = _tracker(), FakeGame()
    tracker.on_event(game, "tv_broadcast")
    assert tracker.is_complete("broadcast_from_the_end")
    tracker.on_event(game, "heavy_machinery")
    assert tracker.is_complete("heavy_machinery")
    tracker.on_event(game, None)                         # an unknown event id is harmless
    for event_id, achievement_id in (("ice_cream_van", "sweet_survival"), ("travelling_circus", "one_last_laugh"),
                                     ("presidential_escort", "presidential_protection")):
        assert not tracker.is_complete(achievement_id)
        tracker.on_event(game, event_id)
        assert tracker.is_complete(achievement_id), achievement_id


def test_the_placeholder_flag_still_blocks_an_achievement():
    """The mechanism stays for future content: a flagged achievement is listed but can never be completed."""
    tracker, game = _tracker(), FakeGame(vehicles=("Tank", "Excavator"))
    BY_ID["heavy_machinery"]["placeholder"] = True
    try:
        tracker.on_event(game, "heavy_machinery")
        assert not tracker.is_complete("heavy_machinery")
    finally:
        del BY_ID["heavy_machinery"]["placeholder"]


def test_event_achievements_are_reachable_through_a_mission():
    """Every event an achievement waits for is the "event" objective of some mission stage (so a player can reach it)."""
    from game.mission_data import MISSIONS
    mission_events = {o["event_id"] for m in MISSIONS
                      for stage in (m.get("stages") or [m]) for o in stage.get("objectives", []) if o["type"] == "event"}
    for achievement in ACHIEVEMENTS:
        if achievement["condition"]["kind"] == "event":
            for event_id in achievement["condition"]["events"]:
                assert event_id in mission_events, (achievement["id"], event_id)


def test_real_achievements_only_name_existing_content():
    """Every achievement without the placeholder flag must be completable: its events and vehicles exist."""
    from game.event_data import EVENTS
    from vehicle_data import VEHICLE_SPECS
    assert achievements.unwired({e["id"] for e in EVENTS}, set(VEHICLE_SPECS)) == []


def test_hard_road_needs_a_win_on_the_hardest_difficulty():
    from config import DIFFICULTY_ORDER
    hardest = DIFFICULTY_ORDER[-1]
    assert BY_ID["hard_road"]["condition"] == {"kind": "win_on_difficulty", "difficulty": hardest}
    for difficulty in DIFFICULTY_ORDER[:-1]:
        tracker = _tracker()
        tracker.on_victory(FakeGame(difficulty=difficulty))
        assert tracker.is_complete("coast_to_coast") and not tracker.is_complete("hard_road"), difficulty
        assert "Tank" not in tracker.unlocked_vehicles()
    tracker, game = _tracker(), FakeGame(difficulty=hardest)
    tracker.on_victory(game)
    assert tracker.is_complete("hard_road") and "Tank" in tracker.unlocked_vehicles()
    assert any("Hard Road" in line for line in game.said)


def test_hard_road_is_not_earned_by_losing_or_in_sandbox():
    tracker = _tracker()
    tracker.on_defeat(FakeGame(difficulty="Hard"))        # a defeat on Hard is not a win
    tracker.on_arrival(FakeGame(difficulty="Hard"))
    assert not tracker.is_complete("hard_road")
    tracker.on_victory(FakeGame(difficulty="Hard", sandbox=True))
    assert not tracker.is_complete("hard_road")


def test_armoured_convoy_needs_all_four_military_vehicles_all_armoured():
    condition = BY_ID["armoured_convoy"]["condition"]
    assert condition["kind"] == "win_with_convoy" and set(condition["vehicles"]) == set(ARMOURED_CONVOY)
    assert condition["upgrade"] == "armor_plating"
    # all four, every one armoured: earned (extra armoured vehicles do not matter)
    tracker, game = _tracker(), FakeGame(vehicles=ARMOURED_CONVOY + ("Pickup Truck",), upgrades=("armor_plating",))
    tracker.on_victory(game)
    assert tracker.is_complete("armoured_convoy") and "Prototype Military Vehicle" in tracker.unlocked_vehicles()
    assert "Tank" not in tracker.unlocked_vehicles()      # the Tank no longer comes from this one
    # a military vehicle missing
    tracker = _tracker()
    tracker.on_victory(FakeGame(vehicles=ARMOURED_CONVOY[:3], upgrades=("armor_plating",)))
    assert not tracker.is_complete("armoured_convoy")
    # no armour at all
    tracker = _tracker()
    tracker.on_victory(FakeGame(vehicles=ARMOURED_CONVOY))
    assert not tracker.is_complete("armoured_convoy")
    # one vehicle left without armour (a fifth, unarmoured vehicle also blocks it)
    for extra in ((), ("Pickup Truck",)):
        tracker, game = _tracker(), FakeGame(vehicles=ARMOURED_CONVOY + extra, upgrades=("armor_plating",))
        game.vehicles[-1].upgrades = []
        tracker.on_victory(game)
        assert not tracker.is_complete("armoured_convoy"), extra
    # some other upgrade is not armour plating
    tracker = _tracker()
    tracker.on_victory(FakeGame(vehicles=ARMOURED_CONVOY, upgrades=("reinforced_bumper",)))
    assert not tracker.is_complete("armoured_convoy")


def test_armoured_convoy_is_a_win_condition_only():
    """Arriving at a stop (or any other hook) with the armoured convoy does nothing: it has to reach the end."""
    tracker, game = _tracker(), FakeGame(vehicles=ARMOURED_CONVOY, upgrades=("armor_plating",))
    tracker.on_arrival(game)
    tracker.check(game)
    assert not tracker.is_complete("armoured_convoy")
    tracker.on_victory(FakeGame(vehicles=ARMOURED_CONVOY, upgrades=("armor_plating",), sandbox=True))
    assert not tracker.is_complete("armoured_convoy")


def test_unwired_checks_the_vehicles_of_a_convoy_achievement():
    from vehicle_data import VEHICLE_SPECS
    assert achievements.unwired(None, set(VEHICLE_SPECS)) == []
    missing = achievements.unwired(None, set(VEHICLE_SPECS) - {"Tank"})
    assert ("armoured_convoy", "vehicle 'Tank'") in missing


def test_saved_and_reloaded():
    tracker, game = _tracker(), FakeGame(vehicles=("A", "B"))
    tracker.on_victory(game)
    again = AchievementTracker(tracker.path)             # a new session
    assert again.is_complete("coast_to_coast") and again.counters["wins"] == 1
    assert again.vehicle_types_seen == {"A", "B"}
    again.on_victory(FakeGame())
    assert again.is_complete("the_long_road_again")      # the win counter carried over


def test_damaged_file_is_ignored():
    tracker = _tracker()
    os.makedirs(os.path.dirname(tracker.path), exist_ok=True)
    for junk in (b"not json", b"[1, 2]", b'{"completed": 5, "counters": "x"}', b"\xff\xfe"):
        with open(tracker.path, "wb") as handle:
            handle.write(junk)
        assert AchievementTracker(tracker.path).completed_count() == 0


def test_sandbox_earns_nothing():
    tracker, game = _tracker(), FakeGame(sandbox=True)
    tracker.on_victory(game)
    assert tracker.completed_count() == 0 and tracker.counters["wins"] == 0


def test_progress_and_new_unlocks():
    tracker, game = _tracker(), FakeGame(recovered=1)
    assert tracker.progress(BY_ID["nothing_left_behind"], game) == (1, 3)
    tracker.on_victory(game)
    assert tracker.pop_new_unlocks() == ["coast_to_coast"] and tracker.pop_new_unlocks() == []


def test_in_memory_tracker_writes_nothing():
    tracker = AchievementTracker(None)
    tracker.on_victory(FakeGame())
    assert tracker.is_complete("coast_to_coast")


def test_vehicle_unlocks_follow_completed_achievements():
    tracker, game = _tracker(), FakeGame(recovered=3)
    assert tracker.unlocked_vehicles() == set()
    tracker.check(game)                                   # Nothing Left Behind
    assert tracker.unlocked_vehicles() == {"Car Carrier Truck"}
    tracker.check(FakeGame(vehicles=[f"Type {i}" for i in range(COLLECTOR_VEHICLE_TYPES)]))   # Convoy Collector
    assert tracker.unlocked_vehicles() == {"Car Carrier Truck", "Limousine"}
    again = AchievementTracker(tracker.path)              # unlocks survive a new session (they come from the saved file)
    assert again.unlocked_vehicles() == {"Car Carrier Truck", "Limousine"}


def test_mission_achievements_unlock_their_bonus_vehicles():
    tracker, game = _tracker(), FakeGame()
    for event_id in ("tv_broadcast", "ice_cream_van", "travelling_circus", "presidential_escort", "heavy_machinery"):
        tracker.on_event(game, event_id)
    assert {"TV Broadcasting Van", "Ice Cream Van", "Clown Car", "Presidential Limo", "Excavator",
            "Bulldozer"} <= tracker.unlocked_vehicles()
    assert "Tank" not in tracker.unlocked_vehicles()      # the Tank is Hard Road's reward now


def test_sandbox_earns_no_vehicle_unlock():
    tracker, game = _tracker(), FakeGame(recovered=3, sandbox=True)
    tracker.check(game)
    assert tracker.unlocked_vehicles() == set()


def test_unlocks_vehicle_names_are_bonus_vehicles():
    from vehicle_data import BONUS_VEHICLES, VEHICLE_SPECS
    named = []
    for a in ACHIEVEMENTS:
        unlocked = a.get("unlocks_vehicle")
        if unlocked:
            named += [unlocked] if isinstance(unlocked, str) else list(unlocked)   # a tuple unlocks several
    assert named and len(set(named)) == len(named)
    assert all(name in VEHICLE_SPECS and name in BONUS_VEHICLES for name in named)


def _real_game(tracker=None):
    from game import Game
    from game.null_audio import NullAudio
    return Game(music=NullAudio(), sound=NullAudio(), achievements=tracker if tracker is not None else AchievementTracker(None))


def test_bonus_vehicles_hidden_until_unlocked():
    from vehicle_data import BONUS_VEHICLES, STANDARD_VEHICLES
    tracker = AchievementTracker(None)
    game = _real_game(tracker)
    assert not set(game.listed_vehicle_types()) & BONUS_VEHICLES
    assert set(STANDARD_VEHICLES) <= set(game.listed_vehicle_types())
    tracker.completed["convoy_collector"] = {"day": 1, "date": "2026-01-01"}
    assert set(game.listed_vehicle_types()) & BONUS_VEHICLES == {"Limousine"}


def test_sandbox_lists_every_bonus_vehicle():
    from vehicle_data import BONUS_VEHICLES, VEHICLE_SPECS
    game = _real_game()
    game.toggle_sandbox()
    assert set(game.listed_vehicle_types()) == set(VEHICLE_SPECS)
    assert game.unlocked_bonus_vehicles() == set(BONUS_VEHICLES)
    game.toggle_sandbox()
    assert not set(game.listed_vehicle_types()) & BONUS_VEHICLES


def test_sandbox_recovers_and_upgrades_anywhere():
    game = _real_game()
    assert not game.can_recover_here() and not game.can_upgrade_here()   # the open highway has no recovery site
    game.toggle_sandbox()
    assert game.can_recover_here() and game.can_upgrade_here()
    game.toggle_sandbox()
    assert not game.can_recover_here()


def test_sandbox_recover_all():
    from vehicle_data import VEHICLE_SPECS
    game = _real_game()
    assert game.recover_all_vehicles() == 0 and game.sandbox_recoverable_types() == []   # sandbox only
    game.toggle_sandbox()
    expected = len(VEHICLE_SPECS) - len(game.vehicles)   # every vehicle, however few survivors there are
    start = len(game.vehicles)
    assert game.recover_all_vehicles() == expected and len(game.vehicles) == start + expected
    assert len({v.vehicle_type for v in game.vehicles}) == len(game.vehicles)   # no duplicates
    assert all(v.health < v.stats["health"] for v in game.vehicles[start:])      # recovered at 70%
    assert game.adult_count() >= len(game.vehicles)                              # survivors were spawned to drive them


def test_reset_forgets_everything_and_is_saved():
    tracker, game = _tracker(), FakeGame(vehicles=("A", "B"), recovered=3)
    assert not tracker.has_progress()
    tracker.on_victory(game)                              # Coast to Coast + Nothing Left Behind, a win counted, two vehicle types seen
    assert tracker.has_progress() and tracker.unlocked_vehicles()
    tracker.reset()
    assert not tracker.has_progress() and tracker.completed_count() == 0 and tracker.unlocked_vehicles() == set()
    assert tracker.counters == {"wins": 0, "vehicles_recovered": 0} and tracker.pop_new_unlocks() == []
    again = AchievementTracker(tracker.path)              # the empty state was written to the file
    assert not again.has_progress()
    tracker.on_victory(FakeGame())                        # and achievements can be earned again afterwards
    assert tracker.is_complete("coast_to_coast") and not tracker.is_complete("the_long_road_again")


def test_reset_button_asks_first_and_no_cancels():
    tracker = AchievementTracker(None)
    tracker.on_victory(FakeGame())
    game = _real_game(tracker)
    game.achievement_page = 2
    game.ask_confirm("reset_achievements")
    assert game.confirm_popup == "reset_achievements" and tracker.is_complete("coast_to_coast")   # nothing erased yet
    game.confirm_no()
    assert game.confirm_popup is None and tracker.is_complete("coast_to_coast")
    game.ask_confirm("reset_achievements")
    game.confirm_yes()
    assert game.confirm_popup is None and not tracker.has_progress() and game.achievement_page == 0


def test_reset_keeps_the_run_going():
    tracker = AchievementTracker(None)
    game = _real_game(tracker)
    day, vehicles = game.day, len(game.vehicles)
    game.ask_confirm("reset_achievements")
    game.confirm_yes()
    assert (game.day, len(game.vehicles), game.status) == (day, vehicles, "playing")


def test_screen_layout_fits_every_window():
    """The achievements screen and the pause menu (now with ACHIEVEMENTS) fit and do not overlap (layout has no pygame)."""
    import textscale
    from layout import menu_layout, rect_inside, rects_overlap
    from layout.achievements import achievements_layout
    try:
        for width, height in ((640, 480), (1000, 680), (1920, 1080), (2560, 1440)):
            for level, _scale in textscale.TEXT_LEVELS:
                textscale.set_text_level(level)
                for g in (achievements_layout(width, height), menu_layout(width, height, True)):
                    leaves = g["leaves"]
                    assert all(rect_inside(r, (0, 0) + tuple(g["size"])) for _n, r in leaves), (width, height, level)
                    assert not any(rects_overlap(a[1], b[1]) for i, a in enumerate(leaves) for b in leaves[i + 1:])
                    assert all(rect_inside(c, p) for _n, c, p in g["inside"]), (width, height, level)
    finally:
        textscale.set_text_level("Normal")


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print("ok", name)
    print("Placeholders (COMING SOON):", [a["id"] for a in ACHIEVEMENTS if a.get("placeholder")])   # none left
