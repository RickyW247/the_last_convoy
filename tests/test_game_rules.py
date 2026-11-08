"""Tests for the game rules (game/): flow, statistics, difficulty, horde, convoy, survival, sites and travel."""

import itertools
from unittest import mock

import config
import instructions_data
import layout
import map_data
import vehicle_data
from game.vehicle import Vehicle, recovery_cost

from tests.helpers import LayoutTestCase, make_game


class RulesTestCase(LayoutTestCase):
    """Base class: a fresh game in self.g, on the pinned map layout."""

    def setUp(self):
        super().setUp()
        self.g = make_game()


class GameFlowTests(RulesTestCase):
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
        for _ in range(instructions_data.PAGE_COUNT + 3):
            g.turn_instructions_page(1)
        self.assertEqual(g.instructions_page, instructions_data.PAGE_COUNT - 1)
        g.open_instructions()
        self.assertEqual(g.instructions_page, 0)


class RunStatisticsTests(RulesTestCase):
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
        g.advance_time(60)   # the horde now attacks every day until no survivor is left (there is no "horde caught" ending)
        self.assertEqual(g.status, "lost")
        self.assertEqual(g.end_reason, "Every survivor has left. The convoy is empty.")
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


class DifficultyTests(RulesTestCase):
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


class HordeTests(RulesTestCase):
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

    def test_horde_never_passes_the_convoy_and_eventually_catches_it(self):
        g = self.g
        g.food = g.water = 1000
        g.advance_time(60)
        self.assertLessEqual(g.horde_km, g.convoy_km)
        self.assertEqual(g.status, "lost")


class ConvoyTests(RulesTestCase):
    """Stats, cargo, fuel, repairs, abandoning and recovering vehicles, drivers and seats."""

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
        self.assertNotEqual(vehicle_data.VEHICLE_SPECS[g.vehicles[0].vehicle_type]["defense"], 999)

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
        self.assertEqual(g.scrap, 10 - recovery_cost("Semi-Truck"))
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
        g.survivor_manager.sync_count(g.survivors)             # adult_count() reads the manager's list, not g.survivors
        g.recover_vehicle("Semi-Truck")                        # nobody left to drive it
        self.assertEqual(len(g.vehicles), 3)

    def test_vehicles_can_be_recovered_in_every_city_with_a_recovery_site(self):
        g = self.g
        for index, node in enumerate(map_data.NODES):
            expected = any(key in config.RECOVERY_SITE_KEYS for key in node["sites"])
            g.position = index
            self.assertEqual(g.can_recover_here(), expected, node["name"])
        g.position = 1                                         # City 1: Gas Station, Farm, Diner
        self.assertFalse(g.can_recover_here())
        g.position = 4                                         # City 4 has a Repair Depot
        self.assertTrue(g.can_recover_here())


class SurvivalTests(RulesTestCase):
    def test_one_day_without_food_does_not_make_anyone_leave(self):
        # Hunger works in stages (conditions.py): fed -> hungry -> starving -> leaves, so nobody leaves on day one.
        g = self.g
        g.food = 0
        before = g.survivors
        g.upkeep()
        self.assertEqual(g.survivors, before)

    def test_supply_forecast_warns_when_survivors_would_leave(self):
        g = self.g
        self.assertIsNone(g.supply_forecast(3))             # a full larder
        g.food = 0
        self.assertIsNone(g.supply_forecast(1))             # hungry after one day, nobody leaves yet
        forecast = g.supply_forecast(3)                     # starving on day three: the worst case is that they leave
        self.assertEqual(forecast["short"], "food")
        self.assertGreater(forecast["leave"], 0)

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

    def test_defeat_when_no_survivors_are_left(self):
        self.g.survivors = 0
        self.g.check_defeat()
        self.assertEqual(self.g.status, "lost")

    def test_defeat_when_every_vehicle_is_destroyed(self):
        for vehicle in self.g.vehicles:
            vehicle.health = 0
        self.g.check_defeat()
        self.assertEqual(self.g.status, "lost")

    def test_ambush_damages_every_vehicle(self):
        g = self.g
        g.ambush()
        for vehicle in g.vehicles:
            self.assertLess(vehicle.health, vehicle.stats["health"])


class SiteTests(RulesTestCase):
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

    def test_arrow_keys_cycle_through_the_stops_west_and_east(self):
        g = self.g
        g.position = 3
        convoy_x = map_data.NODES[3]["pos"][0]
        west = [i for i, n in enumerate(map_data.NODES) if n["pos"][0] < convoy_x]
        east = [i for i, n in enumerate(map_data.NODES) if n["pos"][0] > convoy_x]
        near = g.neighbours()
        for direction, ids in ((-1, west), (+1, east)):
            seen = []
            for _ in ids:
                g.cycle_destination(direction)
                seen.append(g.selected)
            self.assertEqual(sorted(seen), sorted(ids), "every stop that way is visited once")
            first = len([i for i in ids if i in near])
            self.assertTrue(all(i in near for i in seen[:first]), "stops one road away come first")
            for part in (seen[:first], seen[first:]):           # then each group runs nearest first
                xs = [map_data.NODES[i]["pos"][0] for i in part]
                self.assertEqual(xs, sorted(xs, reverse=(direction < 0)), "nearest first")
            g.cycle_destination(direction)
            self.assertEqual(g.selected, seen[0], "wraps around")

    def test_an_arrow_key_with_no_stops_that_way_changes_nothing(self):
        g = self.g
        g.position = map_data.START                         # the easternmost stop
        g.selected = 4
        g.cycle_destination(+1)
        self.assertEqual(g.selected, 4)


class TravelTests(RulesTestCase):
    def setUp(self):
        super().setUp()
        self.g.fuel = 10 ** 6
        # No time passes and no random road incident happens, so only the travel rules are tested.
        self.g.advance_time = lambda amount=1: None
        patcher = mock.patch("random.random", return_value=0.99)
        patcher.start()
        self.addCleanup(patcher.stop)

    def go_to_the_coast(self):
        """Put the convoy at City 4, the stop one road from the Pacific Coast in every layout, and set off."""
        g = self.g
        g.position, g.current_location = 4, "City 4"
        g.selected = map_data.PACIFIC
        g.travel()

    def test_reaching_the_coast_wins_at_once_when_the_evacuation_is_off(self):
        with mock.patch("game.evacuation.EVACUATION_ENABLED", False):   # evacuation.py imported the value itself
            self.go_to_the_coast()
        self.assertEqual(self.g.status, "won")
        self.assertIn("Pacific Coast", self.g.end_reason)

    def test_reaching_the_coast_starts_the_evacuation_and_victory_waits_for_it(self):
        g = make_game(real_events=True)          # the scripted evacuation events need the real event manager
        g.fuel = 10 ** 6
        g.advance_time = lambda amount=1: None
        g.position, g.current_location = 4, "City 4"
        g.selected = map_data.PACIFIC
        g.travel()
        self.assertEqual(g.status, "playing")
        self.assertIsNotNone(g.evacuation)
        self.assertEqual(g.event_manager.current_event["id"], "evac_gate")
        for expected in ("evac_gate", "evac_quota", "evac_boarding"):
            self.assertEqual(g.event_manager.current_event["id"], expected)
            last = len(g.event_manager.current_event["choices"]) - 1     # the last choice of each costs nothing
            g.resolve_event_choice(last)
            self.assertEqual(g.status, "playing")                        # the result screen comes first
            self.assertIsNotNone(g.event_result)
            g.dismiss_event_result()
        self.assertEqual(g.status, "won")
        self.assertIsNone(g.evacuation)
        self.assertIn("last ship", g.end_reason)

    def test_a_day_on_the_road_can_open_a_real_event_and_a_choice_resolves_it(self):
        g = make_game(real_events=True)
        g.fuel = 10 ** 6
        g.advance_time = lambda amount=1: None
        g.selected = 1
        # Day 1: the ambush roll misses, the event roll hits; every later roll misses.
        rolls = itertools.chain([0.99, 0.0], itertools.repeat(0.99))
        with mock.patch("random.random", side_effect=rolls):
            g.travel()
            self.assertTrue(g.event_manager.active)
            self.assertEqual((g.status, g.position), ("playing", 0))   # the journey waits for the player
            self.assertIsNotNone(g.journey)
            self.assertIsNone(g.event_result)
            g.resolve_event_choice(0)
            self.assertFalse(g.event_manager.active)
            self.assertIsNotNone(g.event_result)            # kept until the player clicks OK
            g.dismiss_event_result()                         # the journey goes on to the arrival
        self.assertIsNone(g.event_result)
        self.assertEqual((g.position, g.journey), (1, None))

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
        g.selected = 1
        g.travel()
        self.assertEqual(g.position, map_data.START)
        self.assertIsNone(g.journey)
        self.assertIn("Not enough fuel", g.log[0])
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
        g.selected = 2                       # back east, one road away: the horde would catch the convoy
        g.travel()
        self.assertEqual(g.position, 3)
        self.assertIn("Too dangerous", g.log[0])

    def test_plan_trip_values(self):
        g = self.g
        g.selected = 1
        trip = g.plan_trip()
        self.assertEqual(trip["path"], [0, 1])
        self.assertEqual(trip["km"], 100)
        self.assertEqual(trip["delta"], 90)
        self.assertEqual(trip["through"], [])
        self.assertEqual(trip["wear"], 0)
        km_per_day = max(1, int(g.convoy_stats()["speed"] * config.KM_PER_SPEED_DAY))
        self.assertEqual(trip["days"], max(config.MIN_TRIP_DAYS, -(-100 // km_per_day) * config.TRAVEL_DAY_SCALE))


class JourneyTests(RulesTestCase):
    """Animated journeys (main.py turns animate_travel on): TRAVELLING..., one day per delay, pauses for popups."""

    def setUp(self):
        super().setUp()
        g = self.g
        g.fuel = 10 ** 6
        g.screen = "convoy"                    # on_road() only counts on the convoy screen
        g.animate_travel = True
        g.advance_time = lambda amount=1: None
        patcher = mock.patch("random.random", return_value=0.99)   # no incident, no event on the road
        patcher.start()
        self.addCleanup(patcher.stop)
        g.selected = 1
        g.travel()

    def test_setting_off_starts_the_travelling_state(self):
        g = self.g
        self.assertEqual((g.position, g.journey["dest"], g.journey["day"]), (0, 1, 0))
        self.assertTrue(g.on_road())
        self.assertTrue(g.travelling())
        self.assertEqual(g.travel_delay, config.TRAVEL_START_DELAY)
        self.assertFalse(g.can_travel_now())

    def test_one_day_passes_per_delay(self):
        g = self.g
        g.update_travel(config.TRAVEL_START_DELAY - 0.1)
        self.assertEqual(g.journey["day"], 0)
        g.update_travel(0.2)
        self.assertEqual(g.journey["day"], 1)
        self.assertEqual(g.travel_delay, config.TRAVEL_DAY_DELAY)

    def test_the_journey_ends_with_the_arrival(self):
        g = self.g
        steps = g.journey["days"] + 1          # every day on the road, then the arrival
        for _ in range(steps):
            g.update_travel(1000)
        self.assertEqual((g.position, g.journey), (1, None))
        self.assertFalse(g.on_road())

    def test_the_clock_stops_while_a_result_is_open(self):
        g = self.g
        g.event_manager.result = {"title": "Event", "choice": "", "outcome": "Something happened.", "changes": []}
        self.assertFalse(g.travelling())
        g.update_travel(1000)
        self.assertEqual(g.journey["day"], 0)

    def test_after_an_event_the_journey_waits_before_the_next_day(self):
        g = self.g
        g.travel_delay = 0
        g.continue_journey()
        self.assertEqual(g.travel_delay, config.TRAVEL_EVENT_DELAY)

    def test_nothing_that_takes_a_day_can_be_done_on_the_road(self):
        g = self.g
        g.scrap = 50
        g.vehicles[0].health = 1
        g.repair()
        self.assertIn("on the road", g.log[0])
        g.recover_vehicle("Semi-Truck")
        self.assertIn("on the road", g.log[0])

    def test_rough_roads_wear_vehicles_and_the_coast_does_not(self):
        g = self.g
        pass_id = next(i for i, n in enumerate(map_data.NODES) if n["kind"] == "pass")
        self.assertEqual(g.route_wear([0, pass_id]), config.ROUTE_WEAR["pass"])
        self.assertEqual(g.route_wear([0, 1]), 0)


class SandboxTests(RulesTestCase):
    def test_sandbox_tops_supplies_up_and_never_lowers_them(self):
        g = self.g
        g.toggle_sandbox()
        self.assertEqual((g.fuel, g.food, g.water, g.scrap), (999, 300, 300, 300))
        g.upkeep()
        g.fuel -= 50
        self.assertEqual((g.fuel, g.food, g.water), (999, 300, 300))

    def test_turning_sandbox_off_trims_supplies_to_the_convoy_capacity(self):
        g = self.g
        g.toggle_sandbox()
        g.toggle_sandbox()
        caps = g.convoy_stats()
        self.assertEqual(g.fuel, caps["fuel_capacity"])
        self.assertLessEqual(g.cargo_used(), caps["cargo"])

    def test_sandbox_survives_a_restart(self):
        g = self.g
        g.toggle_sandbox()
        g.reset()
        self.assertTrue(g.sandbox)
        self.assertEqual((g.fuel, g.food), (999, 300))


class ConditionTests(RulesTestCase):
    """Hunger, thirst and injury (conditions.py). random.random returning 0.0 makes every roll hit, 0.99 every roll miss."""

    def test_a_short_day_moves_everyone_one_stage_on(self):
        g = self.g
        with mock.patch("random.random", return_value=0.0):
            g.update_conditions(True, False)
            self.assertEqual((g.conditions["hungry"], g.conditions["starving"]), (8, 0))
            g.update_conditions(True, False)
            self.assertEqual((g.conditions["hungry"], g.conditions["starving"]), (0, 8))
            self.assertEqual(g.survivors, 8)                  # nobody leaves before the third short day

    def test_starving_survivors_leave_and_an_empty_convoy_is_lost(self):
        g = self.g
        with mock.patch("random.random", return_value=0.0):
            for _ in range(3):
                g.update_conditions(True, False)
        self.assertEqual(g.condition_losses["hunger"], 8)
        self.assertEqual((g.survivors, g.status), (0, "lost"))

    def test_nothing_changes_when_every_roll_misses(self):
        g = self.g
        with mock.patch("random.random", return_value=0.99):
            g.update_conditions(True, True)
        self.assertEqual(g.conditions, {key: 0 for key in g.conditions})

    def test_a_fed_day_puts_everyone_back_to_normal(self):
        g = self.g
        g.conditions.update(hungry=3, starving=2, thirsty=4, dehydrated=1)
        with mock.patch("random.random", return_value=0.99):
            g.update_conditions(False, False)
        self.assertEqual((g.conditions["hungry"], g.conditions["starving"]), (0, 0))
        self.assertEqual((g.conditions["thirsty"], g.conditions["dehydrated"]), (0, 0))

    def test_thirst_runs_on_its_own_track(self):
        g = self.g
        with mock.patch("random.random", return_value=0.0):
            g.update_conditions(False, True)
        self.assertEqual((g.conditions["thirsty"], g.conditions["hungry"]), (8, 0))

    def test_injuries_only_hit_healthy_survivors(self):
        g = self.g
        self.assertEqual(g.injure(3), 3)
        self.assertEqual(g.injured_count(), 3)
        self.assertEqual(g.injure(100), 5)
        self.assertEqual(g.injured_count(), 8)

    def test_treatment_heals_the_critical_first(self):
        g = self.g
        g.conditions.update(injured=3, critical=2)
        self.assertEqual(g.heal_injuries(3), 3)
        self.assertEqual((g.conditions["critical"], g.conditions["injured"]), (0, 2))

    def test_counts_never_exceed_the_survivors_and_the_worse_stage_keeps_its_people(self):
        g = self.g
        g.conditions.update(hungry=6, starving=6)
        g.sync_conditions()
        self.assertEqual((g.conditions["starving"], g.conditions["hungry"]), (6, 2))

    def test_critical_survivors_can_die(self):
        g = self.g
        g.conditions["critical"] = 2
        with mock.patch("random.random", return_value=0.0):
            g.update_conditions(False, False)
        self.assertEqual((g.survivors, g.condition_losses["injury"]), (6, 2))
        self.assertTrue(any("died of their injuries" in line for line in g.log))

    def test_only_an_ambulance_counts_as_medical_care(self):
        g = self.g
        self.assertFalse(g.has_medical_care())
        g.vehicles.append(Vehicle("Ambulance"))
        self.assertTrue(g.has_medical_care())


class HordeAttackTests(RulesTestCase):
    def test_an_attack_kills_at_least_the_minimum_share_and_builds_a_streak(self):
        g = self.g
        g.horde = 0
        g.horde_attack()
        self.assertLessEqual(g.survivors, 8 - 3)               # at least 30% of 8, rounded up
        self.assertEqual(g.horde_attack_streak, 1)
        g.horde_attack()
        self.assertEqual(g.horde_attack_streak, 2)

    def test_the_last_vehicle_is_never_wrecked_by_the_horde(self):
        g = self.g
        for vehicle in g.vehicles:
            vehicle.health = 1
        g.horde = 0
        g.horde_attack()
        self.assertEqual((len(g.vehicles), g.vehicles[0].health, g.status), (1, 1, "playing"))

    def test_the_convoy_moves_along_the_line_during_a_journey(self):
        g = self.g
        g.journey = {"axis_to": 200, "days": 4, "day": 2}      # halfway between the start (0 km) and 200 km
        self.assertEqual(g.convoy_km, 100)


class EvacuationTests(RulesTestCase):
    def board(self, berths, survivors=8):
        g = self.g
        g.evacuation = {"stage": 3, "berths": berths}
        g.survivors = survivors
        g.survivor_manager.sync_count(survivors)
        g.complete_evacuation()
        return g

    def test_no_berths_outside_the_evacuation(self):
        g = self.g
        self.assertEqual((g.berths(), g.add_berths(5)), (0, 0))
        self.assertFalse(g.evacuating())

    def test_berths_change_but_never_go_below_zero(self):
        g = self.g
        g.evacuation = {"stage": 1, "berths": 2}
        self.assertEqual(g.add_berths(-5), -2)
        self.assertEqual(g.berths(), 0)

    def test_the_evacuation_starts_with_the_port_gate(self):
        g = make_game(real_events=True)
        g.begin_evacuation()
        self.assertEqual(g.evacuation, {"stage": 1, "berths": config.EVAC_BASE_BERTHS})
        self.assertEqual(g.event_manager.current_event["id"], "evac_gate")
        self.assertTrue(g.evacuating())

    def test_everyone_escapes_when_there_are_enough_berths(self):
        g = self.board(berths=16)
        self.assertEqual((g.status, g.survivors, g.survivors_left_behind), ("won", 8, 0))
        self.assertIn("Nobody was left behind", g.end_reason)

    def test_survivors_without_a_berth_are_left_on_the_dock(self):
        g = self.board(berths=5)
        self.assertEqual((g.status, g.survivors, g.survivors_left_behind), ("won", 5, 3))
        self.assertIn("3 survivors left behind", g.end_reason)

    def test_the_run_is_lost_when_nobody_gets_aboard(self):
        g = self.board(berths=0)
        self.assertEqual(g.status, "lost")
        self.assertIn("The ship sailed without you", g.end_reason)


class ScavengeResultTests(RulesTestCase):
    def setUp(self):
        super().setUp()
        self.g = make_game(real_events=True)
        patcher = mock.patch("random.random", return_value=0.99)     # no survivors, no rare fuel
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_several_sites_open_the_picker_and_a_pick_searches_that_site(self):
        g = self.g
        g.position = 1                                              # City 1: Gas Station, Farm, Diner
        g.start_scavenge()
        self.assertTrue(g.site_picker)
        self.assertEqual(g.day, 1)                                  # nothing is searched until a site is chosen
        g.scavenge_site(1)
        self.assertFalse(g.site_picker)
        self.assertEqual((g.selected_site, g.day), (1, 2))
        self.assertEqual(g.event_result["title"], "Scavenged: Farm")

    def test_a_stop_with_one_site_is_searched_at_once(self):
        g = self.g
        g.start_scavenge()                                          # the starting highway has one site
        self.assertFalse(g.site_picker)
        self.assertEqual(g.day, 2)

    def test_an_unknown_site_index_searches_nothing(self):
        g = self.g
        g.position = 1
        g.scavenge_site(9)
        self.assertEqual((g.site_picker, g.day), (False, 1))

    def test_a_site_without_data_fails_loudly(self):
        with self.assertRaises(ValueError):
            self.g._search_site("no_such_site")

    def test_a_full_convoy_leaves_finds_behind_and_says_so(self):
        g = self.g
        g.position = 1
        g.selected_site = g.current_sites().index("farm")
        g.food, g.water, g.scrap = 60, 45, 0                        # exactly the 105 cargo of pickup + van + bus
        g.scavenge()
        self.assertIn("Convoy is full", g.event_result["outcome"])
