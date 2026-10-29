"""Automated tests for THE LAST CONVOY.

How to run (keep this file in the game folder, next to main.py and the assets/ folder):
    python test_convoy.py
    python -m unittest test_convoy -v
    python -m unittest test_convoy.EffectHandlerTests -v      (one group only)

The tests run headless (SDL's dummy video driver), so no game window opens. Random events and random
rolls are replaced by controlled stand-ins wherever a result must be repeatable.

Coverage:
- GameRulesTests, TravelTests ......... game.py: resources, horde, repair, vehicles, sites, screens, run
                                        statistics, travel, victory
- EffectHandlerTests .................. effect_handler.py: every effect type
- EventDataTests, EventManagerTests ... event_data.py and event_manager.py (including the event result)
- EventUiTests ........................ event_ui.py: choice buttons, clicks, result screen, hover cursor (main.py)
- MapSystemTests, SiteDataTests ....... map_data.py and map_system.py: map data, sites, roads, pathfinding, drawing
- VehicleDataTests, VehicleSpriteTests  vehicles.py and vehicle_rendering.py
- HelperTests, ScreenTests ............ widgets.py, layout.py, config.py helpers; buttons.py and ui.py screens
                                        (title, lore, menu, instructions, convoy, ending)
- TextDataTests ....................... instructions_data.py and story_data.py
- ConvoyDrawingTests .................. vehicle placement on the convoy screen
- StructureTests ...................... no star imports; game rules import without pygame
- VersionTests ........................ README version has a history entry
Tests that need the PNG files in assets/ are skipped automatically when that folder is missing.
"""
import ast
import os
import random
import re
import subprocess
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import buttons as buttons_module  # noqa: E402  (aliased: tests often use `buttons` as a local name)
import config  # noqa: E402
import effect_handler  # noqa: E402
import event_data  # noqa: E402
import event_manager  # noqa: E402
import event_ui  # noqa: E402
import game as game_rules  # noqa: E402  (aliased: tests use `game` as a local name)
import instructions_data  # noqa: E402
import layout  # noqa: E402
import main  # noqa: E402
import map_data  # noqa: E402
import map_system  # noqa: E402
import story_data  # noqa: E402
import theme  # noqa: E402
import ui  # noqa: E402
import vehicle_rendering  # noqa: E402
import vehicles  # noqa: E402
import widgets  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HAVE_VEHICLE_ASSETS = os.path.isdir(os.path.join(HERE, "assets", "vehicles"))
HAVE_ALL_ASSETS = (
    HAVE_VEHICLE_ASSETS
    and os.path.isfile(os.path.join(HERE, "assets", "backgrounds", "convoy_background.png"))
    and os.path.isfile(os.path.join(HERE, "assets", "zombies", "zombie.png"))
)
needs_vehicle_assets = unittest.skipUnless(HAVE_VEHICLE_ASSETS, "assets/vehicles folder not found")
needs_all_assets = unittest.skipUnless(HAVE_ALL_ASSETS, "assets folder not found or incomplete")


class FakeEvents:
    """Stand-in for EventManager so travel tests don't depend on random events."""

    def __init__(self, opens_event=False):
        self.opens_event = opens_event
        self.active = False
        self.current_event = None
        self.result = None

    def start_for_arrival(self, game):
        if self.opens_event:
            self.active = True
            self.current_event = {"title": "Test", "description": "", "choices": [{"label": "OK"}]}

    def resolve_choice(self, game, choice_index):
        self.active = False
        self.result = {"title": "Test", "choice": "OK", "outcome": "Event resolved.", "changes": []}
        return "Event resolved."

    def clear_result(self):
        self.result = None


def make_game(opens_event=False):
    """A new game whose random events are replaced by FakeEvents."""
    game = game_rules.Game()
    game.event_manager = FakeEvents(opens_event)
    return game


def surface():
    return pygame.Surface((layout.WIDTH, layout.HEIGHT))


# ---------------------------------------------------------------------------------------------------------
# game.py
# ---------------------------------------------------------------------------------------------------------
class GameRulesTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()

    def test_initial_state(self):
        g = self.g
        self.assertEqual([v.vehicle_type for v in g.vehicles], ["Pickup Truck", "Passenger Van", "School Bus"])
        self.assertEqual(g.survivors, 8)
        self.assertEqual(g.day, 1)
        self.assertEqual(g.status, "playing")

    def test_game_starts_on_the_title_screen(self):
        g = self.g
        self.assertEqual((g.screen, g.started), ("title", False))
        g.show_lore()
        self.assertEqual(g.screen, "lore")
        g.begin_game()
        self.assertEqual((g.screen, g.started), ("convoy", True))

    def test_restart_goes_straight_back_to_the_convoy_screen(self):
        g = self.g
        g.begin_game()
        g.status = "lost"
        g.reset()
        self.assertEqual((g.screen, g.started, g.status), ("convoy", True, "playing"))

    def test_return_to_title_starts_a_fresh_run_on_the_title_screen(self):
        g = self.g
        g.begin_game()
        g.set_difficulty("Hard")
        g.day, g.status = 9, "lost"
        g.return_to_title()
        self.assertEqual((g.screen, g.started, g.status, g.day), ("title", False, "playing", 1))
        self.assertEqual(g.difficulty, "Hard")

    def test_menu_returns_to_where_it_was_opened(self):
        g = self.g
        g.open_menu()
        self.assertEqual((g.screen, g.menu_return), ("menu", "title"))
        g.close_menu()
        self.assertEqual(g.screen, "title")
        g.begin_game()
        g.open_menu()
        self.assertEqual(g.menu_return, "convoy")
        g.close_menu()
        self.assertEqual(g.screen, "convoy")

    def test_instructions_pages_stay_in_range(self):
        g = self.g
        g.open_instructions()
        self.assertEqual((g.screen, g.instructions_page), ("instructions", 0))
        g.turn_instructions_page(-1)
        self.assertEqual(g.instructions_page, 0)
        for _ in range(5):
            g.turn_instructions_page(1)
        self.assertEqual(g.instructions_page, instructions_data.PAGE_COUNT - 1)
        g.open_instructions()
        self.assertEqual(g.instructions_page, 0)

    def test_run_statistics_start_empty(self):
        g = self.g
        self.assertEqual((g.stops_visited(), g.vehicles_lost(), g.km_traveled, g.end_reason), (0, 0, 0, ""))
        self.assertEqual(g.stops_total(), len(map_data.NODES) - 1)

    def test_vehicles_lost_counts_every_way_of_losing_one(self):
        g = self.g
        g.survivors = 2                      # fewer survivors than vehicles: the rearmost is abandoned
        g.enforce_limits()
        self.assertEqual(g.vehicles_lost(), 1)
        g.vehicles.pop()                     # removed some other way (an event, say)
        self.assertEqual(g.vehicles_lost(), 2)

    def test_recovering_a_vehicle_does_not_hide_earlier_losses(self):
        g = self.g
        g.abandon_vehicle("School Bus")
        g.position, g.current_location = 3, "City 3"
        g.scrap = 10
        g.food = g.water = 1000
        g.recover_vehicle("Semi-Truck")
        self.assertEqual(len(g.vehicles), 3)
        self.assertEqual(g.vehicles_lost(), 1)

    def test_end_reasons_are_recorded(self):
        g = self.g
        g.survivors = 0
        g.check_defeat()
        self.assertEqual(g.status, "lost")
        self.assertEqual(g.end_reason, "Every survivor has left. The convoy is empty.")
        g = make_game()
        g.food = g.water = 1000
        g.advance_time(60)
        self.assertEqual(g.end_reason, "The horde caught the convoy.")
        self.assertEqual(g.log[0], g.end_reason)

    def test_reset_restores_the_start_but_keeps_difficulty(self):
        g = self.g
        g.set_difficulty("Hard")
        g.food = 0
        g.day = 9
        g.status = "lost"
        g.reset()
        self.assertEqual((g.food, g.day, g.status), (24, 1, "playing"))
        self.assertEqual(g.difficulty, "Hard")

    def test_reset_clears_the_run_statistics(self):
        g = self.g
        g.visited.add(3)
        g.km_traveled = 500
        g.vehicles_recovered = 2
        g.end_reason = "Something."
        g.reset()
        self.assertEqual((g.stops_visited(), g.km_traveled, g.vehicles_lost(), g.end_reason), (0, 0, 0, ""))

    def test_daily_use_rounds_up(self):
        g = self.g
        g.difficulty = "Normal"
        for survivors, expected in ((1, (1, 1)), (8, (2, 2)), (21, (5, 6))):
            g.survivors = survivors
            self.assertEqual(g.daily_use(), expected, f"{survivors} survivors")

    def test_difficulty_scales_daily_use(self):
        g = self.g
        g.survivors = 20
        use = {}
        for name in ("Easy", "Normal", "Hard"):
            g.difficulty = name
            use[name] = g.daily_use()
        for index in (0, 1):
            self.assertLessEqual(use["Easy"][index], use["Normal"][index])
            self.assertLessEqual(use["Normal"][index], use["Hard"][index])

    def test_difficulty_scales_horde_speed_and_scavenge_yield(self):
        g = self.g
        ranges, yields = {}, {}
        for name in ("Easy", "Normal", "Hard"):
            g.difficulty = name
            ranges[name] = g.horde_daily_range()
            yields[name] = g.scaled_yield(10)
        self.assertLess(ranges["Easy"][1], ranges["Normal"][1])
        self.assertLess(ranges["Normal"][1], ranges["Hard"][1])
        self.assertGreater(yields["Easy"], yields["Normal"])
        self.assertGreater(yields["Normal"], yields["Hard"])
        self.assertEqual(g.scaled_yield(0), 0)
        self.assertGreaterEqual(g.scaled_yield(1), 1)  # a real find is never rounded down to nothing

    def test_unknown_difficulty_is_ignored(self):
        self.g.set_difficulty("Impossible")
        self.assertEqual(self.g.difficulty, "Normal")

    def test_horde_state_thresholds(self):
        g = self.g
        self.assertEqual(g.horde_state(0), "Overrun")
        self.assertEqual(g.horde_state(config.APPROACHING_MIN_KM - 1), "Close")
        self.assertEqual(g.horde_state(config.APPROACHING_MIN_KM), "Approaching")
        self.assertEqual(g.horde_state(config.DISTANT_MIN_KM - 1), "Approaching")
        self.assertEqual(g.horde_state(config.DISTANT_MIN_KM), "Distant")

    def test_horde_gap_setter_and_getter_agree(self):
        g = self.g
        g.position = 3
        g.horde = 30
        self.assertEqual(g.horde, 30)
        self.assertEqual(g.horde_km, g.convoy_km - 30)

    def test_zombie_count_follows_the_gap(self):
        g = self.g
        counts = []
        for gap in (config.DISTANT_MIN_KM + 50, config.DISTANT_MIN_KM - 1, config.APPROACHING_MIN_KM - 1, 0):
            g.horde = gap
            counts.append(g.zombie_count())
        self.assertEqual(counts[0], 0)
        self.assertEqual(counts[-1], 18)
        self.assertEqual(counts, sorted(counts))
        self.assertLessEqual(max(counts), len(layout.ZOMBIE_SLOTS))

    def test_horde_warning_is_logged_when_the_state_changes(self):
        g = self.g
        g.horde = 100  # Approaching
        g.check_horde_state()
        self.assertIn("Approaching", g.log[0])
        g.check_horde_state()  # no change, no new message
        self.assertEqual(sum("Approaching" in line for line in g.log), 1)

    def test_convoy_stats_totals(self):
        g = self.g
        stats = g.convoy_stats()
        self.assertEqual(stats["speed"], min(v.stats["speed"] for v in g.vehicles))
        self.assertEqual(stats["health"], sum(v.health for v in g.vehicles))
        self.assertEqual(stats["cargo"], sum(v.stats["cargo"] for v in g.vehicles))
        self.assertEqual(stats["passengers"], sum(v.stats["passengers"] for v in g.vehicles))
        self.assertEqual(g.convoy_health_pct(), 100)

    def test_vehicles_use_their_own_copy_of_the_stats(self):
        g = self.g
        g.vehicles[0].stats["defense"] = 999
        self.assertNotEqual(vehicles.VEHICLE_SPECS[g.vehicles[0].vehicle_type]["defense"], 999)

    def test_defense_reduction_is_capped(self):
        for vehicle in self.g.vehicles:
            vehicle.stats["defense"] = 100
        self.assertEqual(self.g.defense_reduction(), config.DEFENSE_REDUCTION_CAP)

    def test_fuel_never_exceeds_capacity(self):
        g = self.g
        g.fuel = 0
        capacity = g.convoy_stats()["fuel_capacity"]
        left = g.gain("fuel", 10 ** 6)
        self.assertEqual(g.fuel, capacity)
        self.assertEqual(left, 10 ** 6 - capacity)

    def test_cargo_never_exceeds_capacity_and_is_shared(self):
        g = self.g
        g.food = g.water = g.scrap = 0
        free = g.cargo_free()
        self.assertGreaterEqual(free, 3, "test needs at least 3 free cargo units")
        left = g.gain_cargo({"food": free, "water": free, "scrap": free})
        self.assertEqual(g.cargo_used(), free)
        self.assertEqual(left, 2 * free)
        self.assertGreater(g.food, 0)
        self.assertGreater(g.water, 0)
        self.assertGreater(g.scrap, 0)

    def test_losing_a_vehicle_leaves_behind_what_no_longer_fits(self):
        g = self.g
        g.food = g.convoy_stats()["cargo"] - g.water - g.scrap  # cargo exactly full
        g.vehicles.pop(0)
        g.trim_supplies()
        self.assertLessEqual(g.cargo_used(), g.convoy_stats()["cargo"])
        self.assertLessEqual(g.fuel, g.convoy_stats()["fuel_capacity"])

    def test_repair_restores_a_fraction_of_each_vehicle(self):
        g = self.g
        for vehicle in g.vehicles:
            vehicle.health = 1
        g.scrap = config.REPAIR_SCRAP_COST
        g.repair()
        for vehicle in g.vehicles:
            maximum = vehicle.stats["health"]
            self.assertEqual(vehicle.health, min(maximum, 1 + int(maximum * config.REPAIR_FRACTION + 0.5)))
        self.assertEqual(g.scrap, 0)

    def test_repair_needs_scrap(self):
        g = self.g
        g.vehicles[0].health = 1
        g.scrap = 0
        g.repair()
        self.assertEqual(g.vehicles[0].health, 1)

    def test_repair_not_needed_keeps_scrap(self):
        g = self.g
        g.scrap = 5
        g.repair()
        self.assertEqual(g.scrap, 5)

    def test_abandon_needs_a_second_click(self):
        g = self.g
        g.request_abandon("School Bus")
        self.assertEqual(len(g.vehicles), 3)
        g.request_abandon("School Bus")
        self.assertEqual(len(g.vehicles), 2)
        self.assertNotIn("School Bus", g.owned_vehicle_types())

    def test_cannot_abandon_last_vehicle(self):
        g = self.g
        g.vehicles = g.vehicles[:1]
        g.abandon_vehicle(g.vehicles[0].vehicle_type)
        self.assertEqual(len(g.vehicles), 1)

    def test_every_vehicle_needs_a_driver(self):
        g = self.g
        g.survivors = 2
        g.enforce_limits()
        self.assertLessEqual(len(g.vehicles), g.survivors)
        self.assertNotIn("School Bus", g.owned_vehicle_types())  # the rearmost vehicle goes first

    def test_survivors_without_a_seat_leave(self):
        g = self.g
        g.survivors = g.convoy_stats()["passengers"] + 5
        g.enforce_limits()
        self.assertLessEqual(g.survivors, g.convoy_stats()["passengers"])

    def test_recover_vehicle_at_a_recovery_site(self):
        g = self.g
        g.position, g.current_location = 3, "City 3"      # City 3 has a Truck Stop
        g.scrap = 10
        g.food = g.water = 1000  # a day passes during recovery
        g.recover_vehicle("Semi-Truck")
        self.assertIn("Semi-Truck", g.owned_vehicle_types())
        self.assertEqual(g.scrap, 10 - game_rules.recovery_cost("Semi-Truck"))
        recovered = g.vehicles[-1]
        self.assertEqual(recovered.health, int(recovered.stats["health"] * 0.7))
        self.assertEqual(g.day, 2)

    def test_recover_vehicle_refused_in_the_wrong_place_or_state(self):
        g = self.g
        g.scrap = 50
        g.recover_vehicle("Semi-Truck")                       # at the starting highway
        self.assertEqual(len(g.vehicles), 3)
        g.position, g.current_location = 3, "City 3"
        g.recover_vehicle("Pickup Truck")                      # already owned
        self.assertEqual(len(g.vehicles), 3)
        g.scrap = 1
        g.recover_vehicle("Semi-Truck")                        # not enough scrap
        self.assertEqual(len(g.vehicles), 3)
        g.scrap = 50
        g.survivors = len(g.vehicles)
        g.recover_vehicle("Semi-Truck")                        # nobody left to drive it
        self.assertEqual(len(g.vehicles), 3)

    def test_vehicles_can_be_recovered_in_every_city_with_a_recovery_site(self):
        g = self.g
        for index, node in enumerate(map_data.NODES):
            expected = any(map_data.SITES[key]["name"] in config.RECOVERY_SITES for key in node["sites"])
            g.position = index
            self.assertEqual(g.can_recover_here(), expected, node["name"])
        g.position = 1                                         # City 1: Gas Station, Farm, Diner
        self.assertFalse(g.can_recover_here())
        g.position = 4                                         # City 4 has a Repair Depot
        self.assertTrue(g.can_recover_here())

    def test_starvation_removes_one_survivor(self):
        g = self.g
        g.food = 0
        before = g.survivors
        g.upkeep()
        self.assertEqual(g.survivors, before - 1)

    def test_daily_upkeep_uses_food_and_water(self):
        g = self.g
        food, water = g.food, g.water
        used_food, used_water = g.daily_use()
        g.upkeep()
        self.assertEqual((g.food, g.water), (food - used_food, water - used_water))

    def test_day_counter_advances(self):
        g = self.g
        g.food = g.water = 1000
        g.advance_time(3)
        self.assertEqual(g.day, 4)
        self.assertEqual(g.status, "playing")

    def test_horde_never_passes_the_convoy_and_eventually_catches_it(self):
        g = self.g
        g.food = g.water = 1000
        g.advance_time(60)
        self.assertLessEqual(g.horde_km, g.convoy_km)
        self.assertEqual(g.status, "lost")

    def test_defeat_conditions(self):
        g = self.g
        g.survivors = 0
        g.check_defeat()
        self.assertEqual(g.status, "lost")
        g = make_game()
        for vehicle in g.vehicles:
            vehicle.health = 0
        g.check_defeat()
        self.assertEqual(g.status, "lost")

    def test_ambush_damages_every_vehicle(self):
        g = self.g
        g.ambush()
        for vehicle in g.vehicles:
            self.assertLess(vehicle.health, vehicle.stats["health"])

    def test_scavenge_takes_a_day_and_uses_the_current_stop(self):
        g = self.g
        g.position, g.current_location = 2, "City 2"        # the convoy is here, even if another stop is selected
        g.selected = 0                                      # City 2's first site is the Supermarket
        g.food = g.water = 5
        g.scrap = 0
        with mock.patch("random.random", return_value=0.99):  # no survivors join
            g.scavenge()
        self.assertEqual(g.day, 2)
        self.assertGreater(g.food, 5 - g.daily_use()[0])      # supermarket yields food

    def test_sites_are_chosen_one_at_a_time_and_wrap_around(self):
        g = self.g
        g.position = 1                                      # City 1: Gas Station, Farm, Diner
        self.assertEqual(g.current_sites(), ["fuel", "farm", "diner"])
        self.assertEqual(g.current_site(), "fuel")
        g.cycle_site()
        self.assertEqual(g.current_site(), "farm")
        g.cycle_site()
        g.cycle_site()
        self.assertEqual(g.current_site(), "fuel")

    def test_a_stop_with_one_site_or_none_has_nothing_to_choose(self):
        g = self.g
        g.cycle_site()                                      # the starting highway has one site
        self.assertEqual(g.current_site(), "start")
        g.position = map_data.PACIFIC
        self.assertEqual(g.current_sites(), [])
        self.assertIsNone(g.current_site())
        g.cycle_site()

    def test_scavenging_searches_the_chosen_site_and_can_be_repeated(self):
        g = self.g
        g.position = 1
        g.selected_site = g.current_sites().index("farm")
        g.food = g.water = 5
        with mock.patch("random.random", return_value=0.99):
            g.scavenge()
            g.scavenge()
        self.assertEqual(g.day, 3)                          # one day per search
        self.assertGreater(g.food, 5)                       # the farm gives plenty of food

    def test_nothing_to_scavenge_where_there_are_no_sites(self):
        g = self.g
        g.position = map_data.PACIFIC
        g.scavenge()
        self.assertEqual(g.day, 1)
        self.assertIn("nothing to scavenge", g.log[0])

    def test_every_site_can_be_scavenged(self):
        for key in map_data.SITES:
            with self.subTest(site=key):
                g = make_game()
                g.position = next(i for i, n in enumerate(map_data.NODES) if key in n["sites"])
                g.selected_site = map_data.NODES[g.position]["sites"].index(key)
                g.food = g.water = 100
                with mock.patch("random.random", return_value=0.99):
                    g.scavenge()
                self.assertEqual((g.day, g.status), (2, "playing"))

    def test_arrow_keys_cycle_through_the_stops_west_and_east(self):
        g = self.g
        g.position = 3
        convoy_x = map_data.NODES[3]["pos"][0]
        west = [i for i, n in enumerate(map_data.NODES) if n["pos"][0] < convoy_x]
        east = [i for i, n in enumerate(map_data.NODES) if n["pos"][0] > convoy_x]
        for direction, ids in ((-1, west), (+1, east)):
            seen = []
            for _ in ids:
                g.cycle_destination(direction)
                seen.append(g.selected)
            self.assertEqual(sorted(seen), sorted(ids), "every stop that way is visited once")
            xs = [map_data.NODES[i]["pos"][0] for i in seen]
            self.assertEqual(xs, sorted(xs, reverse=(direction < 0)), "nearest first")
            g.cycle_destination(direction)
            self.assertEqual(g.selected, seen[0], "wraps around")

    def test_an_arrow_key_with_no_stops_that_way_changes_nothing(self):
        g = self.g
        g.position = map_data.START                         # the easternmost stop
        g.selected = 4
        g.cycle_destination(+1)
        self.assertEqual(g.selected, 4)

    def test_scavenging_the_starting_highway_finds_only_survivors(self):
        g = self.g
        food, scrap = g.food, g.scrap
        with mock.patch("random.random", return_value=0.99):
            g.scavenge()
        self.assertEqual(g.scrap, scrap)
        self.assertLessEqual(g.food, food)

    def test_found_survivors_are_limited_by_free_seats(self):
        g = self.g
        g.survivors = g.convoy_stats()["passengers"] - 1
        with mock.patch("random.random", return_value=0.0), mock.patch("random.randint", return_value=4):
            self.assertTrue(g.find_survivors(1.0, 4, 4))
        self.assertEqual(g.survivors, g.convoy_stats()["passengers"])


class TravelTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()
        self.g.fuel = 10 ** 6
        # No time passes and no random road incident happens, so only the travel rules are tested.
        self.g.advance_time = lambda amount=1: None
        patcher = mock.patch("random.random", return_value=0.99)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_victory_when_no_event_opens(self):
        g = self.g
        g.selected = map_data.PACIFIC
        g.travel()
        self.assertEqual(g.status, "won")
        self.assertFalse(g.pending_victory)
        self.assertIn("Pacific Coast", g.end_reason)

    def test_victory_waits_for_the_event_to_be_resolved(self):
        g = make_game(opens_event=True)
        g.fuel = 10 ** 6
        g.advance_time = lambda amount=1: None
        g.selected = map_data.PACIFIC
        g.travel()
        self.assertEqual(g.status, "playing")
        self.assertTrue(g.pending_victory)
        self.assertTrue(g.event_manager.active)
        g.resolve_event_choice(0)
        self.assertEqual(g.status, "playing")           # the result screen comes first
        self.assertIsNotNone(g.event_result)
        g.dismiss_event_result()
        self.assertIsNone(g.event_result)
        self.assertEqual(g.status, "won")

    def test_arrival_opens_a_real_event_and_a_choice_resolves_it(self):
        g = game_rules.Game()                       # real EventManager
        g.fuel = 10 ** 6
        g.advance_time = lambda amount=1: None
        g.selected = 1
        g.travel()
        self.assertTrue(g.event_manager.active)
        self.assertEqual(g.status, "playing")
        self.assertIsNone(g.event_result)
        g.resolve_event_choice(0)
        self.assertFalse(g.event_manager.active)
        self.assertEqual(g.status, "playing")
        self.assertIsNotNone(g.event_result)            # kept until the player clicks OK
        g.dismiss_event_result()
        self.assertIsNone(g.event_result)

    def test_travel_moves_the_convoy_and_uses_fuel(self):
        g = self.g
        g.selected = 1
        trip = g.plan_trip()
        fuel = g.fuel
        g.travel()
        self.assertEqual(g.position, 1)
        self.assertEqual(g.current_location, "City 1")
        self.assertEqual(g.fuel, fuel - trip["fuel"])

    def test_arriving_in_a_city_selects_its_first_site(self):
        g = self.g
        g.selected_site = 2
        g.selected = 1
        g.travel()
        self.assertEqual(g.selected_site, 0)

    def test_travel_records_stops_visited_and_distance(self):
        g = self.g
        g.selected = 1
        g.travel()
        g.selected = 2
        g.travel()
        self.assertEqual(g.stops_visited(), 2)
        self.assertEqual(g.km_traveled, 100 + 120)
        g.selected = 1                                  # back east: a stop already visited
        g.travel()
        self.assertEqual(g.stops_visited(), 2)
        self.assertEqual(g.km_traveled, 100 + 120 + 120)

    def test_not_enough_fuel_blocks_travel(self):
        g = self.g
        g.fuel = 0
        g.selected = map_data.PACIFIC
        g.travel()
        self.assertEqual(g.position, map_data.START)
        self.assertEqual(g.status, "playing")

    def test_travelling_to_the_current_stop_does_nothing(self):
        g = self.g
        g.selected = g.position
        fuel = g.fuel
        g.travel()
        self.assertEqual(g.fuel, fuel)

    def test_overrun_trips_are_blocked(self):
        g = self.g
        g.position, g.current_location = 3, "City 3"
        g.horde = 10
        g.selected = 1                       # back east: the horde would catch the convoy
        g.travel()
        self.assertEqual(g.position, 3)

    def test_plan_trip_values(self):
        g = self.g
        g.selected = 1
        trip = g.plan_trip()
        self.assertEqual(trip["path"], [0, 1])
        self.assertEqual(trip["km"], 100)
        self.assertEqual(trip["delta"], 90)
        self.assertEqual(trip["through"], [])
        self.assertEqual(trip["days"], max(1, -(-100 // int(g.convoy_stats()["speed"] * config.KM_PER_SPEED_DAY))))


# ---------------------------------------------------------------------------------------------------------
# effect_handler.py
# ---------------------------------------------------------------------------------------------------------
class EffectHandlerTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()

    def apply(self, *effects):
        return effect_handler.apply_effects(self.g, list(effects))

    def test_no_effects(self):
        self.assertEqual(effect_handler.apply_effects(self.g, []), [])
        self.assertEqual(effect_handler.apply_effects(self.g, None), [])

    def test_gaining_cargo(self):
        g = self.g
        food = g.food
        notes = self.apply({"type": "resource", "resource": "food", "amount": 3})
        self.assertEqual(g.food, food + 3)
        self.assertEqual(notes, ["Food +3"])

    def test_gaining_cargo_when_full(self):
        g = self.g
        g.food = g.convoy_stats()["cargo"] - g.water - g.scrap   # no free cargo space
        food = g.food
        notes = self.apply({"type": "resource", "resource": "food", "amount": 3})
        self.assertEqual(g.food, food)
        self.assertTrue(any("Cargo full" in note for note in notes), notes)

    def test_spending_cargo_never_goes_below_zero(self):
        g = self.g
        g.scrap = 5
        self.assertEqual(self.apply({"type": "resource", "resource": "scrap", "amount": -2}), ["Scrap -2"])
        self.assertEqual(g.scrap, 3)
        self.apply({"type": "resource", "resource": "scrap", "amount": -99})
        self.assertEqual(g.scrap, 0)

    def test_fuel_is_limited_by_capacity_and_zero(self):
        g = self.g
        capacity = g.convoy_stats()["fuel_capacity"]
        g.fuel = capacity - 1
        self.assertEqual(self.apply({"type": "resource", "resource": "fuel", "amount": 10}), ["Fuel +1"])
        self.assertEqual(g.fuel, capacity)
        self.apply({"type": "resource", "resource": "fuel", "amount": -10 ** 6})
        self.assertEqual(g.fuel, 0)

    def test_unknown_resource_and_effect_types_are_ignored(self):
        before = (self.g.food, self.g.water, self.g.scrap, self.g.fuel, self.g.survivors)
        notes = self.apply({"type": "resource", "resource": "gold", "amount": 5}, {"type": "teleport", "amount": 5})
        self.assertEqual(notes, [])
        self.assertEqual(before, (self.g.food, self.g.water, self.g.scrap, self.g.fuel, self.g.survivors))

    def test_survivors_are_limited_by_seats_and_zero(self):
        g = self.g
        seats = g.convoy_stats()["passengers"]
        g.survivors = seats - 1
        self.assertEqual(self.apply({"type": "survivors", "amount": 5}), ["Survivors +1"])
        self.assertEqual(g.survivors, seats)
        self.apply({"type": "survivors", "amount": -10 ** 6})
        self.assertEqual(g.survivors, 0)

    def test_vehicle_damage_hits_every_vehicle(self):
        g = self.g
        before = [v.health for v in g.vehicles]
        notes = self.apply({"type": "vehicle_damage", "amount": 5})
        self.assertEqual([v.health for v in g.vehicles], [h - 5 for h in before])
        self.assertEqual(notes, ["Each vehicle took 5 damage"])
        self.assertEqual(g.status, "playing")

    def test_lethal_vehicle_damage_ends_the_game(self):
        self.apply({"type": "vehicle_damage", "amount": 10 ** 6})
        self.assertEqual(self.g.status, "lost")

    def test_vehicle_repair_is_capped_by_each_vehicles_maximum(self):
        g = self.g
        g.vehicles[0].health = g.vehicles[0].stats["health"] - 3
        notes = self.apply({"type": "vehicle_repair", "amount": 100})
        self.assertEqual(g.vehicles[0].health, g.vehicles[0].stats["health"])
        for vehicle in g.vehicles:
            self.assertLessEqual(vehicle.health, vehicle.stats["health"])
        self.assertEqual(notes, ["Vehicle repairs +3 health"])   # only 3 points of damage existed

    def test_vehicle_repair_never_repairs_more_than_the_amount(self):
        g = self.g
        first, second = g.vehicles[0], g.vehicles[1]
        first.health = first.stats["health"] - 3
        second.health = second.stats["health"] - 20
        before = first.health + second.health
        self.apply({"type": "vehicle_repair", "amount": 8})
        repaired = first.health + second.health - before
        self.assertLessEqual(repaired, 8, f"repaired {repaired} health for an effect worth 8")

    def test_horde_gap_changes_and_never_goes_below_zero(self):
        g = self.g
        g.horde = 100
        self.assertEqual(self.apply({"type": "horde_gap", "amount": -30}), ["Horde gap -30 km"])
        self.assertEqual(g.horde, 70)
        self.apply({"type": "horde_gap", "amount": 10})
        self.assertEqual(g.horde, 80)
        self.apply({"type": "horde_gap", "amount": -10 ** 6})
        self.assertEqual(g.horde, 0)


# ---------------------------------------------------------------------------------------------------------
# event_data.py and event_manager.py
# ---------------------------------------------------------------------------------------------------------
SUPPORTED_EFFECTS = {"resource", "survivors", "vehicle_repair", "vehicle_damage", "horde_gap"}


class EventDataTests(unittest.TestCase):
    def test_there_are_events_with_unique_ids(self):
        ids = [event["id"] for event in event_data.EVENTS]
        self.assertGreater(len(ids), 0)
        self.assertEqual(len(ids), len(set(ids)), "duplicate event ids")

    def test_every_event_is_complete(self):
        for event in event_data.EVENTS:
            with self.subTest(event=event.get("id")):
                self.assertIsInstance(event.get("weight"), int)
                self.assertGreater(event["weight"], 0)
                self.assertTrue(event.get("title"))
                self.assertTrue(event.get("description"))
                # Number keys 1-4 select a choice, and a single choice is not a decision.
                self.assertTrue(2 <= len(event["choices"]) <= 4, "events need 2-4 choices")
                lines = widgets.wrap_text(event["description"], 76)
                self.assertLessEqual(len(lines), 3, "description is too long for the overlay")

    def test_every_choice_and_effect_is_valid(self):
        for event in event_data.EVENTS:
            for choice in event["choices"]:
                with self.subTest(event=event["id"], choice=choice.get("label")):
                    self.assertTrue(choice.get("label"))
                    self.assertLessEqual(len(choice["label"]), 60)
                    self.assertTrue(choice.get("outcome"))
                    self.assertIsInstance(choice.get("effects"), list)
                    for effect in choice["effects"]:
                        self.assertIn(effect.get("type"), SUPPORTED_EFFECTS)
                        self.assertIsInstance(effect.get("amount"), int)
                        if effect["type"] == "resource":
                            self.assertIn(effect.get("resource"), effect_handler.RESOURCE_FIELDS)

    def test_every_choice_can_be_played_on_a_fresh_game(self):
        for event in event_data.EVENTS:
            for index, choice in enumerate(event["choices"]):
                with self.subTest(event=event["id"], choice=choice["label"]):
                    game = make_game()
                    manager = event_manager.EventManager()
                    manager.current_event = event
                    outcome = manager.resolve_choice(game, index)
                    self.assertIsInstance(outcome, str)
                    self.assertFalse(manager.active)
                    self.assertEqual(game.status, "playing")


class EventManagerTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()
        self.em = event_manager.EventManager()

    def test_starts_inactive(self):
        self.assertFalse(self.em.active)
        self.assertIsNone(self.em.current_event)

    def test_start_selects_an_event_and_logs_it(self):
        event = self.em.start_for_arrival(self.g)
        self.assertIn(event, event_data.EVENTS)
        self.assertTrue(self.em.active)
        self.assertTrue(self.g.log[0].startswith("Unexpected situation"))

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

    def test_zero_weight_events_are_never_chosen(self):
        events = [
            {"id": "never", "weight": 0, "title": "Never", "choices": []},
            {"id": "always", "weight": 1, "title": "Always", "choices": []},
        ]
        with mock.patch.object(event_manager, "EVENTS", events):
            for _ in range(20):
                self.assertEqual(self.em.start_for_arrival(self.g)["id"], "always")
                self.em.current_event = None

    def test_no_events_defined(self):
        with mock.patch.object(event_manager, "EVENTS", []):
            self.assertIsNone(self.em.start_for_arrival(self.g))

    def test_resolving_applies_effects_and_ends_the_event(self):
        g = self.g
        g.horde = 200
        g.scrap = 5
        self.em.current_event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        outcome = self.em.resolve_choice(g, 1)         # "Take only the scrap": +2 scrap, -1 km gap
        self.assertIn("Scrap +2", outcome)
        self.assertEqual(g.scrap, 7)
        self.assertEqual(g.horde, 199)
        self.assertFalse(self.em.active)

    def test_resolving_with_no_effects_still_gives_the_outcome(self):
        self.em.current_event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        event = self.em.current_event
        outcome = self.em.resolve_choice(self.g, 2)    # "Leave it alone": no effects
        self.assertEqual(outcome, event["choices"][2]["outcome"])

    def test_resolving_records_the_result_for_the_result_screen(self):
        g = self.g
        g.horde = 200
        g.scrap = 5
        event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        self.em.current_event = event
        self.assertIsNone(self.em.result)
        outcome = self.em.resolve_choice(g, 1)                       # "Take only the scrap"
        result = self.em.result
        self.assertEqual(result["title"], event["title"])
        self.assertEqual(result["choice"], event["choices"][1]["label"])
        self.assertEqual(result["outcome"], event["choices"][1]["outcome"])   # plain text, no effect notes
        self.assertIn(("Scrap +2", True), result["changes"])
        self.assertIn("Scrap +2", outcome)                           # the event log keeps the notes
        self.em.clear_result()
        self.assertIsNone(self.em.result)

    def test_a_choice_without_effects_has_no_changes(self):
        self.em.current_event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        self.em.resolve_choice(self.g, 2)                            # "Leave it alone"
        self.assertEqual(self.em.result["changes"], [])

    def test_changes_are_listed_as_good_or_bad(self):
        g = self.g
        before = self.em  # (the manager itself is stateless between events)
        self.em.current_event = {"title": "T", "choices": [{"label": "L", "outcome": "O", "effects": [
            {"type": "resource", "resource": "scrap", "amount": 2},
            {"type": "survivors", "amount": -1},
        ]}]}
        self.em.resolve_choice(g, 0)
        self.assertEqual(dict(self.em.result["changes"]), {"Scrap +2": True, "Survivors -1": False})

    def test_invalid_choices_leave_no_result(self):
        self.em.current_event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        self.em.resolve_choice(self.g, 99)
        self.assertIsNone(self.em.result)

    def test_invalid_choices_are_ignored(self):
        self.em.current_event = next(e for e in event_data.EVENTS if e["id"] == "roadside_cache")
        for bad in (-1, 99, "1", None, 1.0):
            self.assertIsNone(self.em.resolve_choice(self.g, bad), repr(bad))
            self.assertTrue(self.em.active)

    def test_resolving_without_an_event_does_nothing(self):
        self.assertIsNone(self.em.resolve_choice(self.g, 0))


# ---------------------------------------------------------------------------------------------------------
# event_ui.py
# ---------------------------------------------------------------------------------------------------------
class EventUiTests(unittest.TestCase):
    EVENT = {
        "title": "Test event",
        "description": "Something happened on the road.",
        "choices": [{"label": "First"}, {"label": "Second"}, {"label": "Third"}],
    }

    def test_one_button_per_choice(self):
        buttons = event_ui.make_event_buttons(self.EVENT)
        self.assertEqual(len(buttons), 3)
        for number, (button, choice) in enumerate(zip(buttons, self.EVENT["choices"]), start=1):
            self.assertTrue(button.label.startswith(f"{number}."))
            self.assertIn(choice["label"], button.label)

    def test_click_returns_the_choice_index(self):
        for index, button in enumerate(event_ui.make_event_buttons(self.EVENT)):
            self.assertEqual(event_ui.handle_event_click(button.rect.center, self.EVENT), index)

    def test_click_outside_returns_none(self):
        self.assertIsNone(event_ui.handle_event_click((0, 0), self.EVENT))

    def test_buttons_do_not_overlap_and_stay_on_screen(self):
        rects = [b.rect for b in event_ui.make_event_buttons(self.EVENT)]
        for i, first in enumerate(rects):
            self.assertTrue(0 <= first.left and first.right <= layout.WIDTH and 0 <= first.top and first.bottom <= layout.HEIGHT)
            for second in rects[i + 1:]:
                self.assertFalse(first.colliderect(second))

    def test_four_choices_still_fit(self):
        event = {"title": "T", "choices": [{"label": str(i)} for i in range(4)]}
        for button in event_ui.make_event_buttons(event):
            self.assertLessEqual(button.rect.bottom, layout.HEIGHT)

    def test_event_without_choices(self):
        event = {"title": "Empty", "choices": []}
        self.assertEqual(event_ui.make_event_buttons(event), [])
        self.assertIsNone(event_ui.handle_event_click((500, 400), event))

    def test_overlay_draws_without_error(self):
        event_ui.draw_event_overlay(surface(), self.EVENT)
        for event in event_data.EVENTS:
            event_ui.draw_event_overlay(surface(), event)

    RESULT = {"title": "Test event", "choice": "First", "outcome": "It went fine.",
              "changes": [("Food +3", True), ("Survivors -1", False)]}

    def test_result_screen_has_one_ok_button_inside_the_window(self):
        buttons = event_ui.make_result_buttons(self.RESULT)
        self.assertEqual(len(buttons), 1)
        self.assertTrue(buttons[0].label.startswith("OK"))
        self.assertTrue(0 <= buttons[0].rect.left and buttons[0].rect.right <= layout.WIDTH)
        self.assertLessEqual(buttons[0].rect.bottom, layout.HEIGHT)

    def test_result_screen_click(self):
        button = event_ui.make_result_buttons(self.RESULT)[0]
        self.assertTrue(event_ui.handle_result_click(button.rect.center, self.RESULT))
        self.assertFalse(event_ui.handle_result_click((0, 0), self.RESULT))

    def test_result_screen_draws_with_any_amount_of_content(self):
        event_ui.draw_event_result_overlay(surface(), self.RESULT)
        event_ui.draw_event_result_overlay(surface(), {"title": "T", "changes": []})
        long_result = {"title": "T", "choice": "C", "outcome": "A long outcome. " * 30,
                       "changes": [(f"Thing {i} +{i}", i % 2 == 0) for i in range(12)]}
        event_ui.draw_event_result_overlay(surface(), long_result)

    def test_result_screen_buttons_get_the_hand_cursor(self):
        buttons = event_ui.make_result_buttons(self.RESULT)
        with mock.patch("pygame.mouse.get_pos", return_value=buttons[0].rect.center), \
                mock.patch("pygame.mouse.set_cursor") as set_cursor:
            main.update_mouse_cursor(buttons)
        set_cursor.assert_called_with(pygame.SYSTEM_CURSOR_HAND)

    def test_hand_cursor_over_event_buttons_only(self):
        buttons = event_ui.make_event_buttons(self.EVENT)
        with mock.patch("pygame.mouse.get_pos", return_value=buttons[1].rect.center), \
                mock.patch("pygame.mouse.set_cursor") as set_cursor:
            main.update_mouse_cursor(buttons)
        set_cursor.assert_called_with(pygame.SYSTEM_CURSOR_HAND)
        with mock.patch("pygame.mouse.get_pos", return_value=(0, 0)), \
                mock.patch("pygame.mouse.set_cursor") as set_cursor:
            main.update_mouse_cursor(buttons)
        set_cursor.assert_called_with(pygame.SYSTEM_CURSOR_ARROW)


# ---------------------------------------------------------------------------------------------------------
# map_data.py and map_system.py
# ---------------------------------------------------------------------------------------------------------
class MapSystemTests(unittest.TestCase):
    NODES = map_data.NODES

    def test_start_and_destination(self):
        self.assertEqual(self.NODES[map_data.START]["kind"], "start")
        self.assertEqual(self.NODES[map_data.PACIFIC]["kind"], "coast")
        self.assertEqual(self.NODES[map_data.START]["axis"], 0)
        self.assertEqual(max(n["axis"] for n in self.NODES), self.NODES[map_data.PACIFIC]["axis"])

    def test_nodes_are_complete_and_unique(self):
        for node in self.NODES:
            for key in ("name", "kind", "axis", "pos", "tag", "label", "sites"):
                self.assertIn(key, node)
        for key in ("name", "tag"):
            values = [n[key] for n in self.NODES]
            self.assertEqual(len(values), len(set(values)), f"duplicate {key}")

    def test_map_labels_are_consistent(self):
        """Cities are numbered 1-8; the other stops have a letter: S start, C coast, P pass."""
        for node in self.NODES:
            self.assertEqual(len(node["tag"]), 1, node["name"])            # fits inside the marker
            if node["kind"] == "city":
                self.assertTrue(node["tag"].isdigit(), node["name"])
                self.assertEqual(node["name"], f"City {node['tag']}")
        city_tags = sorted(n["tag"] for n in self.NODES if n["kind"] == "city")
        self.assertEqual(city_tags, [str(number) for number in range(1, 9)])
        self.assertEqual(self.NODES[map_data.START]["tag"], "S")
        self.assertEqual(self.NODES[map_data.PACIFIC]["tag"], "C")
        self.assertEqual(next(n["tag"] for n in self.NODES if n["kind"] == "pass"), "P")

    def test_recovery_sites_exist_on_the_map(self):
        names = {map_data.SITES[key]["name"] for node in self.NODES for key in node["sites"]}
        for site in config.RECOVERY_SITES:
            self.assertIn(site, names)

    def test_roads_connect_real_stops_and_are_never_shorter_than_the_straight_line(self):
        for a, b, km, kind in map_data.ROAD_EDGES:
            self.assertIn(a, range(len(self.NODES)))
            self.assertIn(b, range(len(self.NODES)))
            self.assertGreaterEqual(km, abs(self.NODES[a]["axis"] - self.NODES[b]["axis"]), f"road {a}-{b}")
            self.assertIn(kind, ("main", "spur", "alt"))

    def test_adjacency_is_symmetric(self):
        for a, neighbours in map_data.ADJACENT.items():
            for b, km in neighbours:
                self.assertIn((a, km), map_data.ADJACENT[b])

    def test_every_stop_is_reachable_from_every_other(self):
        ids = range(len(self.NODES))
        for a in ids:
            for b in ids:
                path, km = map_data.shortest_path(a, b)
                self.assertEqual((path[0], path[-1]), (a, b), f"{a} -> {b}")
                self.assertEqual(km == 0, a == b)

    def test_shortest_path_is_symmetric_and_adds_up(self):
        ids = range(len(self.NODES))
        for a in ids:
            for b in ids:
                path, km = map_data.shortest_path(a, b)
                _back_path, back_km = map_data.shortest_path(b, a)
                self.assertEqual(km, back_km)      # (equally long alternative routes may differ, so only km is compared)
                total = 0
                for x, y in zip(path, path[1:]):
                    total += dict(map_data.ADJACENT[x])[y]
                self.assertEqual(total, km)

    def test_mountain_pass_bypasses_the_truck_stop(self):
        path, km = map_data.shortest_path(map_data.START, map_data.PACIFIC)
        truck_stop = next(i for i, n in enumerate(self.NODES) if n["name"] == "City 3")   # the bypassed city
        mountain_pass = next(i for i, n in enumerate(self.NODES) if n["name"] == "Mountain Pass")
        self.assertIn(mountain_pass, path)
        self.assertNotIn(truck_stop, path)
        main_road_km = sum(km for a, b, km, kind in map_data.ROAD_EDGES if kind == "main" and a < 5 and b <= 5)
        self.assertLess(km, main_road_km)

    def test_survivor_finds_are_valid(self):
        for kind, (chance, smallest, largest) in map_data.SURVIVOR_FINDS.items():
            self.assertIn(kind, map_data.SITES)
            self.assertTrue(0 < chance <= 1)
            self.assertTrue(1 <= smallest <= largest)
        self.assertIn("start", map_data.SURVIVOR_FINDS)

    def test_route_point_runs_along_the_main_road(self):
        self.assertEqual(map_system.route_point_for_axis(0), self.NODES[map_data.START]["pos"])
        self.assertEqual(map_system.route_point_for_axis(560), self.NODES[map_data.PACIFIC]["pos"])
        self.assertEqual(map_system.route_point_for_axis(9999), self.NODES[map_data.PACIFIC]["pos"])
        xs = [map_system.route_point_for_axis(axis)[0] for axis in range(0, 561, 20)]
        self.assertEqual(xs, sorted(xs, reverse=True))             # west is to the left
        self.assertGreaterEqual(map_system.route_point_for_axis(-200)[0], self.NODES[0]["pos"][0])

    def test_minimap_points_stay_inside_the_card(self):
        x0, y0, width, height = layout.MINI_CARD
        for node in self.NODES:
            x, y = map_system.mini_point(*node["pos"])
            self.assertTrue(x0 <= x <= x0 + width and y0 <= y <= y0 + height, node["name"])

    def test_danger_markers(self):
        g = make_game()
        g.position, g.current_location = 3, "City 3"
        g.horde = 30
        self.assertIsNone(g.travel_danger(3))                         # already here
        self.assertIsNone(g.travel_danger(5))                         # heading west is always safe
        self.assertEqual(g.travel_danger(1), "overrun")               # back east with the horde 30 km behind
        self.assertEqual(g.travel_danger(8), "risky")                 # sideways detour: the horde might arrive
        g.horde = 10
        self.assertEqual(g.travel_danger(8), "overrun")
        g.horde = 40
        self.assertIsNone(g.travel_danger(8))

    def test_map_info_names_the_sites_of_the_selected_city(self):
        """The info panel text for every stop is built from SITES; drawing each must not fail."""
        g = make_game()
        for selected in range(len(self.NODES)):
            g.selected = selected
            map_system.draw_map(surface(), g)

    def test_map_and_minimap_draw_for_every_selection(self):
        g = make_game()
        for position in range(len(self.NODES)):
            g.position, g.current_location = position, self.NODES[position]["name"]
            for selected in range(len(self.NODES)):
                g.selected = selected
                map_system.draw_map(surface(), g)
                map_system.draw_minimap(surface(), g)


class SiteDataTests(unittest.TestCase):
    NODES = map_data.NODES

    def test_every_site_is_complete(self):
        for key, site in map_data.SITES.items():
            with self.subTest(site=key):
                self.assertTrue(site["name"])
                self.assertTrue(site["short"])
                self.assertLessEqual(len(site["short"]), 15, "too long for the SITE button")
                self.assertTrue(site["detail"])

    def test_every_stop_lists_known_sites_without_duplicates(self):
        for node in self.NODES:
            self.assertEqual(len(node["sites"]), len(set(node["sites"])), node["name"])
            for key in node["sites"]:
                self.assertIn(key, map_data.SITES, node["name"])

    def test_cities_have_three_sites_and_the_other_stops_follow_their_role(self):
        for node in self.NODES:
            if node["kind"] == "city":
                self.assertEqual(len(node["sites"]), 3, node["name"])
        self.assertEqual(self.NODES[map_data.START]["sites"], ["start"])
        self.assertEqual(self.NODES[map_data.PACIFIC]["sites"], [])
        self.assertEqual(next(n["sites"] for n in self.NODES if n["kind"] == "pass"), ["pass"])

    def test_every_site_is_used_somewhere(self):
        used = {key for node in self.NODES for key in node["sites"]}
        self.assertEqual(used, set(map_data.SITES))

    def test_some_sites_exist_in_several_cities(self):
        counts = {}
        for node in self.NODES:
            for key in node["sites"]:
                counts[key] = counts.get(key, 0) + 1
        self.assertTrue(any(count > 1 for count in counts.values()))

    def test_site_names_are_unique(self):
        names = [site["name"] for site in map_data.SITES.values()]
        self.assertEqual(len(names), len(set(names)))


# ---------------------------------------------------------------------------------------------------------
# vehicles.py and vehicle_rendering.py
# ---------------------------------------------------------------------------------------------------------
STAT_KEYS = {"speed", "health", "passengers", "cargo", "defense", "fuel_capacity", "fuel_consumption"}


class VehicleDataTests(unittest.TestCase):
    def test_all_vehicle_tables_cover_the_same_types(self):
        types = set(vehicles.VEHICLE_SPECS)
        self.assertEqual(len(types), 8)
        self.assertEqual(set(vehicles.VEHICLE_ROLES), types)
        self.assertEqual(set(vehicles.VEHICLE_LOOKS), types)
        self.assertEqual(set(vehicle_rendering._SPRITE_FILES), types)

    def test_specs_have_positive_whole_number_stats(self):
        for name, stats in vehicles.VEHICLE_SPECS.items():
            with self.subTest(vehicle=name):
                self.assertEqual(set(stats), STAT_KEYS)
                for key, value in stats.items():
                    self.assertIsInstance(value, int, key)
                    self.assertGreater(value, 0, key)

    def test_recovery_costs(self):
        for name, cost in vehicles.RECOVERY_COSTS.items():
            self.assertIn(name, vehicles.VEHICLE_SPECS)
            self.assertGreater(cost, 0)
        for name in vehicles.VEHICLE_SPECS:
            self.assertGreater(game_rules.recovery_cost(name), 0)
        self.assertEqual(game_rules.recovery_cost("Unlisted Vehicle"), 3)

    def test_looks_and_sprite_files(self):
        for name, look in vehicles.VEHICLE_LOOKS.items():
            self.assertTrue(look["label"], name)
        files = list(vehicle_rendering._SPRITE_FILES.values())
        self.assertEqual(len(files), len(set(files)), "two vehicles share one sprite file")
        for filename in files:
            self.assertTrue(filename.endswith(".png"))

    def test_the_starting_convoy_is_playable(self):
        g = make_game()
        for vehicle in g.vehicles:
            self.assertIn(vehicle.vehicle_type, vehicles.VEHICLE_SPECS)
        self.assertGreaterEqual(g.survivors, len(g.vehicles))                    # a driver for each vehicle
        self.assertLessEqual(g.survivors, g.convoy_stats()["passengers"])        # a seat for each survivor
        self.assertLessEqual(g.cargo_used(), g.convoy_stats()["cargo"])
        self.assertLessEqual(g.fuel, g.convoy_stats()["fuel_capacity"])

    def test_unknown_vehicle_sprite_is_an_error(self):
        with self.assertRaises(KeyError):
            vehicle_rendering.get_vehicle_sprite("Hovercraft")


@needs_vehicle_assets
class VehicleSpriteTests(unittest.TestCase):
    def test_every_vehicle_sprite_loads_with_transparency_and_is_cached(self):
        for name in vehicles.VEHICLE_SPECS:
            with self.subTest(vehicle=name):
                sprite = vehicle_rendering.get_vehicle_sprite(name)
                self.assertGreater(sprite.get_width(), 0)
                self.assertGreater(sprite.get_height(), 0)
                self.assertTrue(sprite.get_flags() & pygame.SRCALPHA, "sprite has no transparency")
                self.assertIs(vehicle_rendering.get_vehicle_sprite(name), sprite)

    def test_sprites_have_no_empty_rows_under_the_wheels(self):
        """Vehicles are placed by the bottom edge of their image; empty rows there make them float.

        The PNG files have transparent padding, so get_vehicle_sprite trims it; this checks what it returns."""
        for name in vehicles.VEHICLE_SPECS:
            with self.subTest(vehicle=name):
                sprite = vehicle_rendering.get_vehicle_sprite(name)
                empty_rows = sprite.get_height() - sprite.get_bounding_rect().bottom
                self.assertEqual(empty_rows, 0, f"{empty_rows} transparent row(s) under the {name}; it will float above the road")


# ---------------------------------------------------------------------------------------------------------
# widgets.py, layout.py, config.py, buttons.py, ui.py
# ---------------------------------------------------------------------------------------------------------
class HelperTests(unittest.TestCase):
    def test_wrap_text(self):
        self.assertEqual(widgets.wrap_text("", 10), [])
        self.assertEqual(widgets.wrap_text("a b c", 3), ["a b", "c"])
        text = "the quick brown fox jumps over the lazy dog " * 5
        lines = widgets.wrap_text(text, 20)
        self.assertEqual(" ".join(lines).split(), text.split())            # no words lost or changed
        self.assertTrue(all(len(line) <= 20 for line in lines))

    def test_small_helpers(self):
        self.assertEqual(config.people(1), "1 survivor")
        self.assertEqual(config.people(2), "2 survivors")
        self.assertEqual((widgets.clamp(5, 0, 3), widgets.clamp(-1, 0, 3), widgets.clamp(2, 0, 3)), (3, 0, 2))

    def test_zombie_slots(self):
        slots = layout.ZOMBIE_SLOTS
        self.assertEqual(len(slots), 18)
        self.assertTrue(all(690 <= x <= 960 and 300 <= y <= 334 for x, y in slots))
        self.assertEqual([x for x, _ in slots], sorted((x for x, _ in slots), reverse=True))

    def test_disabled_buttons_cannot_be_clicked(self):
        enabled = widgets.Button((10, 10, 50, 20), "ON", lambda: None)
        disabled = widgets.Button((10, 10, 50, 20), "OFF", lambda: None, enabled=False)
        self.assertTrue(enabled.clicked((20, 20)))
        self.assertFalse(enabled.clicked((200, 200)))
        self.assertFalse(disabled.clicked((20, 20)))

    def test_buttons_and_bars_draw(self):
        canvas = surface()
        widgets.Button((10, 10, 100, 30), "OK", lambda: None).draw(canvas)
        widgets.Button((10, 50, 100, 30), "OK", lambda: None, enabled=False).draw(canvas, selected=True)
        widgets.draw_bar(canvas, 10, 100, 100, 8, 5, 10, theme.GREEN)
        widgets.draw_bar(canvas, 10, 120, 100, 8, 0, 0, theme.GREEN)      # zero maximum must not crash


class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()

    def buttons(self, screen):
        self.g.screen = screen
        return {button.label: button for button in buttons_module.make_buttons(self.g)}

    def test_title_and_lore_screen_buttons(self):
        buttons = self.buttons("title")
        self.assertEqual(list(buttons), ["PLAY", "MENU"])
        buttons["PLAY"].action()
        self.assertEqual(self.g.screen, "lore")
        buttons = self.buttons("lore")
        self.assertEqual(list(buttons), ["BACK", "START GAME"])
        buttons["BACK"].action()
        self.assertEqual(self.g.screen, "title")
        self.buttons("lore")["START GAME"].action()
        self.assertEqual((self.g.screen, self.g.started), ("convoy", True))

    def test_title_menu_button_opens_the_menu_and_back_returns_to_the_title(self):
        self.buttons("title")["MENU"].action()
        self.assertEqual(self.g.screen, "menu")
        self.buttons("menu")["BACK"].action()
        self.assertEqual(self.g.screen, "title")

    def test_convoy_screen_buttons(self):
        buttons = self.buttons("convoy")
        self.assertEqual(list(buttons), ["SCAVENGE", "SITE: Open Highway", "REPAIR", "VEHICLES", "MAP [M]", "MENU [O]"])
        self.assertFalse(buttons["REPAIR"].enabled)                         # nothing to repair
        self.g.vehicles[0].health = 1
        self.g.scrap = config.REPAIR_SCRAP_COST
        self.assertTrue(self.buttons("convoy")["REPAIR"].enabled)
        self.g.scrap = 0
        self.assertFalse(self.buttons("convoy")["REPAIR"].enabled)          # cannot pay

    def test_site_button_shows_and_cycles_the_site(self):
        g = self.g
        g.position = 2                                                      # City 2: Supermarket, Hospital, Pharmacy
        button = self.buttons("convoy")["SITE: Supermarket"]
        self.assertTrue(button.enabled)
        button.action()
        self.assertIn("SITE: Hospital", self.buttons("convoy"))
        g.position = map_data.START                                         # one site: nothing to choose
        g.selected_site = 0
        self.assertFalse(self.buttons("convoy")["SITE: Open Highway"].enabled)

    def test_no_sites_means_nothing_to_scavenge(self):
        self.g.position = map_data.PACIFIC
        buttons = self.buttons("convoy")
        self.assertFalse(buttons["SCAVENGE"].enabled)
        self.assertFalse(buttons["NO SITES HERE"].enabled)

    def test_convoy_buttons_do_their_job(self):
        self.buttons("convoy")["SCAVENGE"].action()
        self.assertEqual(self.g.day, 2)
        self.buttons("convoy")["MAP [M]"].action()
        self.assertEqual(self.g.screen, "map")
        self.buttons("map")["BACK"].action()
        self.assertEqual(self.g.screen, "convoy")

    def test_buttons_are_disabled_after_the_game_ends(self):
        self.g.status = "lost"
        for button in self.buttons("convoy").values():
            self.assertFalse(button.enabled, button.label)

    def test_travel_button(self):
        self.assertTrue(self.buttons("map")["TRAVEL"].enabled)               # a stop is selected and fuel is available
        self.g.selected = self.g.position
        self.assertFalse(self.buttons("map")["TRAVEL"].enabled)              # already there
        self.g.selected = 1
        self.g.fuel = 0
        self.assertFalse(self.buttons("map")["TRAVEL"].enabled)              # no fuel

    def test_vehicle_screen_buttons(self):
        g = self.g
        g.selected_vehicle_type = "Semi-Truck"                               # not owned
        buttons = self.buttons("vehicles")
        self.assertFalse(buttons["ABANDON VEHICLE"].enabled)
        self.assertFalse(buttons["RECOVER VEHICLE"].enabled)                 # not at a recovery site
        g.position, g.current_location = 3, "City 3"
        g.scrap = 10
        self.assertTrue(self.buttons("vehicles")["RECOVER VEHICLE"].enabled)
        g.selected_vehicle_type = "School Bus"                               # owned
        buttons = self.buttons("vehicles")
        self.assertTrue(buttons["ABANDON VEHICLE"].enabled)
        g.request_abandon("School Bus")
        self.assertIn("CONFIRM ABANDON", self.buttons("vehicles"))

    def test_menu_buttons_change_the_difficulty(self):
        buttons = self.buttons("menu")
        self.assertEqual(list(buttons), ["Easy", "Normal", "Hard", "INSTRUCTIONS", "BACK"])
        buttons["Hard"].action()
        self.assertEqual(self.g.difficulty, "Hard")

    def test_menu_opens_the_instructions_and_back_returns_to_the_menu(self):
        self.buttons("menu")["INSTRUCTIONS"].action()
        self.assertEqual(self.g.screen, "instructions")
        buttons = self.buttons("instructions")
        self.assertEqual(list(buttons), ["PREVIOUS PAGE", "NEXT PAGE", "BACK"])
        self.assertFalse(buttons["PREVIOUS PAGE"].enabled)                   # first page
        self.assertTrue(buttons["NEXT PAGE"].enabled)
        buttons["NEXT PAGE"].action()
        buttons = self.buttons("instructions")
        self.assertTrue(buttons["PREVIOUS PAGE"].enabled)
        self.assertFalse(buttons["NEXT PAGE"].enabled)                       # last page
        buttons["BACK"].action()
        self.assertEqual(self.g.screen, "menu")

    def test_end_buttons_exist_only_after_the_run_ends(self):
        g = self.g
        self.assertEqual(buttons_module.make_end_buttons(g), [])
        g.status = "lost"
        buttons = {b.label: b for b in buttons_module.make_end_buttons(g)}
        self.assertEqual(list(buttons), ["PLAY AGAIN [R]", "TITLE SCREEN"])
        panel = pygame.Rect(buttons_module.END_PANEL)
        for button in buttons.values():
            self.assertTrue(panel.contains(button.rect), button.label)
            self.assertTrue(button.enabled)

    def test_end_buttons_restart_or_return_to_the_title(self):
        g = self.g
        g.begin_game()
        g.day, g.status = 9, "lost"
        {b.label: b for b in buttons_module.make_end_buttons(g)}["PLAY AGAIN [R]"].action()
        self.assertEqual((g.screen, g.status, g.day), ("convoy", "playing", 1))
        g.status = "won"
        {b.label: b for b in buttons_module.make_end_buttons(g)}["TITLE SCREEN"].action()
        self.assertEqual((g.screen, g.started, g.status), ("title", False, "playing"))

    def test_hud_menu_and_instructions_screens_draw(self):
        g = self.g
        ui.draw_hud(surface(), g)
        g.screen = "menu"
        ui.draw_menu_screen(surface(), g, buttons_module.make_buttons(g))
        g.screen = "instructions"
        for page in range(instructions_data.PAGE_COUNT):
            g.instructions_page = page
            ui.draw_instructions_screen(surface(), g, buttons_module.make_buttons(g))

    def test_instruction_pages_fit_above_the_buttons(self):
        """Each page must end above the button row (y=615), in the larger font or else the smaller one."""
        for page in range(instructions_data.PAGE_COUNT):
            bottom = ui._layout_instructions(None, page, theme.TINY)
            self.assertLessEqual(bottom, 610, f"page {page + 1} does not fit even in the small font")

    @needs_all_assets
    def test_title_and_lore_screens_draw(self):
        g = self.g
        g.screen = "title"
        ui.draw_title_screen(surface(), g, buttons_module.make_buttons(g))
        g.screen = "lore"
        ui.draw_lore_screen(surface(), g, buttons_module.make_buttons(g))

    def test_logo_draws(self):
        for radius in (20, 38, 80):
            ui.draw_logo(surface(), 200, 200, radius)

    def test_end_screen_draws_for_a_win_and_every_kind_of_loss(self):
        g = self.g
        g.vehicles_recovered = 1
        g.visited.update({1, 2, 3})
        for status, reason in (("won", "You reached the Pacific Coast. The survivors escape by ship!"),
                               ("lost", "The horde caught the convoy."), ("lost", "")):
            g.status, g.end_reason = status, reason
            ui.draw_end_overlay(surface(), g, buttons_module.make_end_buttons(g))
        g.status = "playing"
        ui.draw_end_overlay(surface(), g, [])                                # nothing drawn while playing

    def test_end_stats_summarise_the_run(self):
        g = self.g
        g.day, g.survivors, g.km_traveled = 12, 5, 640
        g.visited.update({1, 2, 3})
        g.vehicles.pop()
        rows = {label: value for label, value, _colour in ui.end_stats(g)}
        self.assertEqual(rows["Days survived"], 12)
        self.assertEqual(rows["Survivors left"], 5)
        self.assertEqual(rows["Stops visited"], f"3 of {len(map_data.NODES) - 1}")
        self.assertEqual(rows["Vehicles lost"], 1)
        self.assertEqual(rows["Distance travelled"], "640 km")
        self.assertEqual(rows["Difficulty"], "Normal")

    def test_end_screen_summary_fits_the_panel(self):
        x, y, w, h = buttons_module.END_PANEL
        self.assertGreaterEqual(x, 0)
        self.assertLessEqual(x + w, layout.WIDTH)
        self.assertLessEqual(y + h, layout.HEIGHT)
        stats_bottom = y + 196 + 40 * len(ui.end_stats(self.g))
        self.assertLessEqual(stats_bottom, y + h - 80, "the summary would run into the buttons")

    def test_hud_draws_with_an_empty_convoy(self):
        self.g.vehicles = []
        ui.draw_hud(surface(), self.g)

    def test_event_log_keeps_four_messages_newest_first(self):
        g = self.g
        for number in range(10):
            g.say(f"message {number}")
        self.assertEqual(g.log, ["message 9", "message 8", "message 7", "message 6"])
        ui.draw_events(surface(), g)

    @needs_vehicle_assets
    def test_vehicle_screen_draws(self):
        for name in vehicles.VEHICLE_SPECS:
            self.g.selected_vehicle_type = name
            self.g.screen = "vehicles"
            ui.draw_vehicles_screen(surface(), self.g, buttons_module.make_buttons(self.g))

    def test_convoy_screen_buttons_stay_inside_the_window_without_overlapping(self):
        rects = [b.rect for b in buttons_module.make_buttons(self.g)]
        for i, first in enumerate(rects):
            self.assertTrue(0 <= first.left and first.right <= layout.WIDTH)
            for second in rects[i + 1:]:
                self.assertFalse(first.colliderect(second))

    @needs_all_assets
    def test_convoy_screen_draws_in_every_horde_state(self):
        for gap in (500, 120, 40, 0):
            self.g.horde = gap
            ui.draw_scene(surface(), self.g)
            ui.draw_lower(surface(), self.g, buttons_module.make_buttons(self.g))


class TextDataTests(unittest.TestCase):
    def test_instructions_text_is_complete(self):
        self.assertEqual(instructions_data.PAGE_COUNT, 2)
        self.assertTrue(all(instructions_data.MISSION))
        for key, action in instructions_data.CONTROLS:
            self.assertTrue(key and action)
        for label, description in instructions_data.HOW_TO_PLAY:
            self.assertTrue(label and description)
        self.assertTrue(instructions_data.HOW_TO_PLAY_OUTRO)

    def test_instructions_do_not_mention_removed_controls(self):
        text = " ".join(key + action for key, action in instructions_data.CONTROLS)
        self.assertNotIn("0–5", text)
        self.assertNotIn("settings", text.lower())

    def test_every_documented_key_is_handled_by_main(self):
        with open(os.path.join(HERE, "main.py"), encoding="utf-8") as source:
            code = source.read()
        for name in ("K_RETURN", "K_m", "K_s", "K_r", "K_o", "K_ESCAPE", "K_TAB", "K_LEFT", "K_RIGHT", "K_1"):
            self.assertIn(f"pygame.{name}", code, f"main.py does not handle {name}")

    def test_story_text(self):
        self.assertTrue(story_data.GAME_TITLE)
        self.assertTrue(story_data.TAGLINE)
        self.assertTrue(story_data.LORE_TITLE)
        self.assertGreaterEqual(len(story_data.LORE), 3)
        self.assertTrue(all(story_data.LORE))
        self.assertIn("west", " ".join(story_data.LORE).lower())
        self.assertIn("coast", " ".join(story_data.LORE).lower())


class ConvoyDrawingTests(unittest.TestCase):
    RED = (255, 0, 0)

    @staticmethod
    def lowest_red_row(canvas, x):
        for y in range(canvas.get_height() - 1, -1, -1):
            if tuple(canvas.get_at((x, y)))[:3] == ConvoyDrawingTests.RED:
                return y
        return None

    def test_vehicles_rest_on_the_road_whatever_their_image_height(self):
        """Different PNG heights must share one bottom edge, above the label (which starts at y=356)."""
        heights = {"Pickup Truck": 50, "Passenger Van": 60, "School Bus": 80}
        sprites = {}
        for name, height in heights.items():
            sprite = pygame.Surface((100, height))
            sprite.fill(self.RED)
            sprites[name] = sprite

        canvas = surface()
        canvas.fill((0, 0, 0))
        game = make_game()
        scene = pygame.Rect(18, 125, layout.WIDTH - 36, 270)
        with mock.patch.object(ui, "get_vehicle_sprite", side_effect=lambda name: sprites[name]):
            ui.draw_convoy_vehicles(canvas, game, scene)

        gap = 4
        total = 3 * 100 + 2 * gap
        x0 = scene.x + (scene.w - total) // 2
        bottoms = [self.lowest_red_row(canvas, x0 + i * (100 + gap) + 50) for i in range(3)]

        self.assertNotIn(None, bottoms, "a vehicle was not drawn")
        self.assertEqual(len(set(bottoms)), 1, f"vehicles have different bottom edges: {bottoms}")
        self.assertGreaterEqual(bottoms[0], 330, "vehicles float too high above the road")
        self.assertLess(bottoms[0], 356, "vehicles overlap the label row")

    def test_no_vehicles_draws_nothing(self):
        game = make_game()
        game.vehicles = []
        ui.draw_convoy_vehicles(surface(), game, pygame.Rect(18, 125, layout.WIDTH - 36, 270))


class StructureTests(unittest.TestCase):
    def test_no_module_uses_a_star_import(self):
        for filename in sorted(f for f in os.listdir(HERE) if f.endswith(".py")):
            with open(os.path.join(HERE, filename), encoding="utf-8") as source:
                tree = ast.parse(source.read(), filename)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("*", [alias.name for alias in node.names], f"{filename}: from {node.module} import *")

    def test_game_rules_import_without_pygame(self):
        """game.py, config.py and map_data.py (and what they import) must work with no pygame installed."""
        code = (
            "import importlib.abc, sys\n"
            "class Block(importlib.abc.MetaPathFinder):\n"
            "    def find_spec(self, name, path, target=None):\n"
            "        if name == 'pygame' or name.startswith('pygame.'):\n"
            "            raise ImportError('pygame is blocked')\n"
            "sys.meta_path.insert(0, Block())\n"
            "import game, config, map_data, instructions_data\n"
            "assert 'pygame' not in sys.modules\n"
            "game.Game()\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class VersionTests(unittest.TestCase):
    def test_readme_version_has_a_history_entry(self):
        doc = main.__doc__
        version = re.search(r"Version: (\d+\.\d+)", doc).group(1)
        self.assertIn(f"- {version}:", doc, f"no version-history entry for {version}")

    def test_readme_has_the_standing_instructions(self):
        doc = main.__doc__
        self.assertIn("zip", doc.lower())
        self.assertIn("without being asked", doc)

    def test_every_python_file_in_the_folder_is_in_the_readme(self):
        doc = main.__doc__
        for filename in sorted(f for f in os.listdir(HERE) if f.endswith(".py")):
            self.assertIn(f"{filename}:", doc, f"{filename} is not listed in the README project files")

    def test_readme_lists_every_python_file(self):
        doc = main.__doc__
        modules = (main, game_rules, config, theme, layout, widgets, buttons_module, map_data, map_system,
                   vehicles, vehicle_rendering, ui, event_data, effect_handler, event_manager, event_ui,
                   instructions_data, story_data)
        for filename in [os.path.basename(m.__file__) for m in modules] + ["test_convoy.py"]:
            self.assertIn(f"{filename}:", doc, f"{filename} is missing from the README project files")


if __name__ == "__main__":
    unittest.main(verbosity=2)
