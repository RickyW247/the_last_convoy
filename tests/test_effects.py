"""Tests for game/effect_handler.py: every effect type, losses, payments, requirements, rescues that do not fit and
the data validators.

Event DATA rules (every event is valid, has a choice that is never locked, ...) live in test_events.py.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from game.effect_handler import (
    affordable_flags, apply_effects, choice_available, defended_loss, event_available, fitted_effects, free_seats,
    gain_vehicle, is_payment, requirement_text, requirements_met, resource_costs, shortfalls,
    unmet_requirement_notes, unowned_vehicle_types, validate_effect, validate_events, validate_requires,
    vehicle_to_lose, check_events,
)
from game.vehicle import Vehicle

from tests.helpers import FakeResourceGame, make_game

RESOURCES = ("fuel", "food", "water", "scrap")


class StatsGame:
    """Just enough of Game for requirements_met / free_seats / fitted_effects, with every stat settable."""

    def __init__(self, vehicles=("Pickup Truck",), adults=1, health=100, passengers=8, **values):
        self.fuel = self.food = self.water = self.scrap = 10
        self.survivors, self.horde = 5, 50
        self.vehicles = [SimpleNamespace(vehicle_type=name) for name in vehicles]
        self._adults, self._health, self._passengers = adults, health, passengers
        self.__dict__.update(values)

    def adult_count(self):
        return self._adults

    def convoy_health_pct(self):
        return self._health

    def convoy_stats(self):
        return {"passengers": self._passengers, "fuel_capacity": 15}


def fake_vehicle(name, health, maximum=100):
    return SimpleNamespace(vehicle_type=name, health=health, stats={"health": maximum})


class ApplyEffectsTests(unittest.TestCase):
    """Every effect type, applied to a real game."""

    def setUp(self):
        self.g = make_game()

    def apply(self, *effects):
        return apply_effects(self.g, list(effects))

    def test_no_effects(self):
        self.assertEqual(apply_effects(self.g, []), [])
        self.assertEqual(apply_effects(self.g, None), [])

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
        g = self.g
        before = (g.food, g.water, g.scrap, g.fuel, g.survivors)
        notes = self.apply({"type": "resource", "resource": "gold", "amount": 5}, {"type": "teleport", "amount": 5})
        self.assertEqual(notes, [])
        self.assertEqual(before, (g.food, g.water, g.scrap, g.fuel, g.survivors))

    # --- survivors
    def test_survivors_are_limited_by_seats_and_zero(self):
        g = self.g
        seats = g.convoy_stats()["passengers"]
        g.survivors = seats - 1
        self.assertEqual(self.apply({"type": "survivors", "amount": 5}), ["Survivors +1"])
        self.assertEqual(g.survivors, seats)
        self.apply({"type": "survivors", "amount": -10 ** 6})
        self.assertEqual(g.survivors, 0)

    def test_defense_cuts_a_survivors_loss_only_when_asked(self):
        g = self.g
        with mock.patch.object(g, "defense_reduction", return_value=50):
            g.survivors = 4
            self.apply({"type": "survivors", "amount": -4, "defense": True})
            self.assertEqual(g.survivors, 2)           # half of the loss absorbed
            g.survivors = 4
            self.apply({"type": "survivors", "amount": -4})
            self.assertEqual(g.survivors, 0)           # no "defense": no reduction

    # --- injuries
    def test_injury_hurts_and_treatment_heals(self):
        g = self.g
        self.assertGreaterEqual(g.survivors, 1, "the fresh game needs a healthy survivor for this test")
        self.assertEqual(g.injured_count(), 0)
        notes = self.apply({"type": "injury", "amount": 1})
        self.assertEqual(notes, ["Survivors injured +1"])
        self.assertEqual(g.injured_count(), 1)
        notes = self.apply({"type": "injury", "amount": -5})
        self.assertEqual(notes, ["Survivors treated 1"])
        self.assertEqual(g.injured_count(), 0)

    def test_treating_nobody_gives_no_note(self):
        self.assertEqual(self.apply({"type": "injury", "amount": -3}), [])

    def test_defense_can_spare_everyone_from_injury(self):
        g = self.g
        with mock.patch.object(g, "defense_reduction", return_value=100):
            self.assertEqual(self.apply({"type": "injury", "amount": 2, "defense": True}), [])
        self.assertEqual(g.injured_count(), 0)

    # --- vehicle damage and repair
    def test_vehicle_damage_pct_hurts_every_vehicle(self):
        g = self.g
        before = [v.health for v in g.vehicles]
        notes = self.apply({"type": "vehicle_damage_pct", "amount": 5})
        self.assertEqual(notes, ["Convoy took 5% damage"])
        for vehicle, health in zip(g.vehicles, before):
            self.assertLess(vehicle.health, health)
        self.assertEqual(g.status, "playing")

    def test_defense_reduces_vehicle_damage_only_when_asked(self):
        g = self.g
        with mock.patch.object(g, "defense_reduction", return_value=50):
            plain = self.apply({"type": "vehicle_damage_pct", "amount": 20})
            defended = self.apply({"type": "vehicle_damage_pct", "amount": 20, "defense": True})
        self.assertEqual(plain, ["Convoy took 20% damage"])
        self.assertEqual(defended, ["Convoy took 10% damage"])

    def test_old_vehicle_damage_is_a_percentage_with_defense_always_on(self):
        g = self.g
        with mock.patch.object(g, "defense_reduction", return_value=50):
            notes = self.apply({"type": "vehicle_damage", "amount": 20})
        self.assertEqual(notes, ["Convoy took 10% damage"])

    def test_a_hit_always_does_at_least_one_percent(self):
        g = self.g
        with mock.patch.object(g, "defense_reduction", return_value=60):
            notes = self.apply({"type": "vehicle_damage_pct", "amount": 1, "defense": True})
        self.assertEqual(notes, ["Convoy took 1% damage"])

    def test_lethal_vehicle_damage_ends_the_game(self):
        self.apply({"type": "vehicle_damage_pct", "amount": 10 ** 6})
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

    def test_repair_goes_to_the_most_damaged_vehicle_first(self):
        game = SimpleNamespace(vehicles=[fake_vehicle("Pickup Truck", 90), fake_vehicle("Ambulance", 20)])
        notes = apply_effects(game, [{"type": "vehicle_repair", "amount": 15}])
        self.assertEqual([v.health for v in game.vehicles], [90, 35])
        self.assertEqual(notes, ["Vehicle repairs +15 health"])

    def test_repair_spills_over_to_the_next_vehicle(self):
        game = SimpleNamespace(vehicles=[fake_vehicle("Pickup Truck", 90), fake_vehicle("Ambulance", 95)])
        apply_effects(game, [{"type": "vehicle_repair", "amount": 12}])
        # the truck (90 %) is repaired first and is full after 10 points; the other 2 go to the ambulance (95 %)
        self.assertEqual([v.health for v in game.vehicles], [100, 97])

    def test_repair_shares_are_by_percentage_not_by_points(self):
        big = fake_vehicle("Semi-Truck", 150, maximum=200)     # 75 %
        small = fake_vehicle("Pickup Truck", 60, maximum=100)  # 60 %: the more damaged one
        apply_effects(SimpleNamespace(vehicles=[big, small]), [{"type": "vehicle_repair", "amount": 5}])
        self.assertEqual((big.health, small.health), (150, 65))

    # --- horde gap
    def test_horde_gap_changes_and_never_goes_below_zero(self):
        g = self.g
        g.horde = 100
        self.assertEqual(self.apply({"type": "horde_gap", "amount": -30}), ["Horde gap -30 km"])
        self.assertEqual(g.horde, 70)
        self.apply({"type": "horde_gap", "amount": 10})
        self.assertEqual(g.horde, 80)
        self.apply({"type": "horde_gap", "amount": -10 ** 6})
        self.assertEqual(g.horde, 0)

    # --- vehicles gained and lost
    def test_no_spare_driver_for_a_new_vehicle_is_reported(self):
        game = SimpleNamespace(vehicles=[SimpleNamespace(vehicle_type="Pickup Truck")], adult_count=lambda: 1)
        self.assertEqual(apply_effects(game, [{"type": "vehicle_gain"}]), ["No driver free for the new vehicle"])
        self.assertEqual(len(game.vehicles), 1)

    def test_a_new_vehicle_joins_when_there_is_a_driver(self):
        g = self.g
        kind = unowned_vehicle_types(g)[0]
        gained = getattr(g, "vehicles_gained", 0)
        with mock.patch.object(g, "adult_count", return_value=50):
            notes = self.apply({"type": "vehicle_gain", "vehicle": kind.upper()})   # any capitalisation
        self.assertEqual(notes, [f"New vehicle: {kind}"])
        self.assertIn(kind, [v.vehicle_type for v in g.vehicles])
        self.assertEqual(g.vehicles_gained, gained + 1)

    def test_a_random_new_vehicle_is_one_the_convoy_lacks(self):
        g = self.g
        owned = {v.vehicle_type for v in g.vehicles}
        with mock.patch.object(g, "adult_count", return_value=50):
            self.apply({"type": "vehicle_gain"})
        newest = g.vehicles[-1].vehicle_type
        self.assertNotIn(newest, owned)

    def test_a_new_vehicle_comes_at_the_given_share_of_its_health(self):
        g = self.g
        kind = unowned_vehicle_types(g)[0]
        with mock.patch.object(g, "adult_count", return_value=50):
            vehicle = gain_vehicle(g, kind, 0.7)
        self.assertEqual(vehicle.health, max(1, int(vehicle.stats["health"] * 0.7)))

    def test_a_vehicle_type_the_convoy_owns_cannot_join_twice(self):
        g = self.g
        owned = g.vehicles[0].vehicle_type
        count = len(g.vehicles)
        with mock.patch.object(g, "adult_count", return_value=50):
            notes = self.apply({"type": "vehicle_gain", "vehicle": owned})
        self.assertEqual(notes, ["No new vehicle could join the convoy"])
        self.assertEqual(len(g.vehicles), count)

    def test_the_last_vehicle_is_never_given_up(self):
        g = self.g
        del g.vehicles[1:]
        self.assertEqual(self.apply({"type": "vehicle_loss"}), [])
        self.assertEqual(len(g.vehicles), 1)

    def test_vehicle_loss_gives_up_the_most_damaged_vehicle(self):
        g = self.g
        extra = Vehicle(unowned_vehicle_types(g)[0])
        g.vehicles.append(extra)
        extra.health = 1
        count = len(g.vehicles)
        notes = self.apply({"type": "vehicle_loss"})
        self.assertEqual(len(g.vehicles), count - 1)
        self.assertNotIn(extra, g.vehicles)
        self.assertTrue(notes and notes[0].startswith("Vehicle abandoned"), notes)


class VehicleToLoseTests(unittest.TestCase):
    def test_nothing_to_lose_with_one_vehicle_or_no_game(self):
        self.assertIsNone(vehicle_to_lose(None))
        self.assertIsNone(vehicle_to_lose(SimpleNamespace(vehicles=[fake_vehicle("A", 10)])))
        self.assertIsNone(vehicle_to_lose(SimpleNamespace(vehicles=[])))

    def test_the_lowest_share_of_maximum_health_goes(self):
        sturdy = fake_vehicle("Semi-Truck", 150, maximum=200)    # 75 %
        wreck = fake_vehicle("Pickup Truck", 40, maximum=100)    # 40 %
        self.assertIs(vehicle_to_lose(SimpleNamespace(vehicles=[sturdy, wreck])), wreck)

    def test_on_a_tie_the_least_valuable_goes(self):
        cheap, dear = fake_vehicle("Pickup Truck", 50), fake_vehicle("Ambulance", 50)
        value = {"Pickup Truck": 1, "Ambulance": 9}
        game = SimpleNamespace(vehicles=[dear, cheap], _vehicle_value=lambda v: value[v.vehicle_type])
        self.assertIs(vehicle_to_lose(game), cheap)


class ResourceLossTests(unittest.TestCase):
    """A loss never goes below 0, never takes more than it asks, and never touches another resource."""

    def lose(self, field, amount, have):
        game = FakeResourceGame(**{field: have})
        others = {name: getattr(game, name) for name in RESOURCES if name != field}
        notes = apply_effects(game, [{"type": "resource", "resource": field, "amount": amount}])
        for name, value in others.items():
            self.assertEqual(getattr(game, name), value, f"a {field} loss touched {name}")
        return getattr(game, field), notes

    def test_a_loss_takes_only_what_there_is(self):
        for field in RESOURCES:
            with self.subTest(resource=field):
                self.assertEqual(self.lose(field, -12, 1), (0, [f"{field.title()} -1"]))
                self.assertEqual(self.lose(field, -12, 0), (0, []))        # nothing to take: no change, no note

    def test_a_normal_loss_is_unchanged(self):
        for field in RESOURCES:
            with self.subTest(resource=field):
                self.assertEqual(self.lose(field, -3, 10)[0], 7)
                self.assertEqual(self.lose(field, -5, 5)[0], 0)            # exactly all of it

    def test_fuel_above_capacity(self):
        self.assertEqual(self.lose("fuel", -2, 20)[0], 18)    # a loss still takes only what it asks
        self.assertEqual(self.lose("fuel", 4, 20)[0], 20)     # a gain never lowers it
        self.assertEqual(self.lose("fuel", 10, 10)[0], 15)    # a gain is still capped by the fuel capacity

    def test_two_losses_in_one_choice_each_stop_at_their_own_zero(self):
        game = FakeResourceGame(water=2, food=3)
        apply_effects(game, [{"type": "resource", "resource": "water", "amount": -12},
                             {"type": "resource", "resource": "food", "amount": -12}])
        self.assertEqual((game.water, game.food, game.scrap, game.fuel), (0, 0, 10, 10))


class CostTests(unittest.TestCase):
    def test_resource_costs_add_up_the_negative_resource_effects(self):
        choice = {"effects": [{"type": "resource", "resource": "scrap", "amount": -3},
                              {"type": "resource", "resource": "scrap", "amount": -2},
                              {"type": "resource", "resource": "fuel", "amount": -1},
                              {"type": "resource", "resource": "food", "amount": 4},       # a gain is no cost
                              {"type": "resource", "resource": "gold", "amount": -9},      # unknown resource
                              {"type": "horde_gap", "amount": -7}]}                         # not a supply
        self.assertEqual(resource_costs(choice), {"scrap": 5, "fuel": 1})

    def test_a_free_choice_costs_nothing(self):
        self.assertEqual(resource_costs({"effects": []}), {})
        self.assertEqual(resource_costs({}), {})
        self.assertEqual(resource_costs({"effects": None}), {})


class PaymentTests(unittest.TestCase):
    """Payment choices (a service the player pays for) are greyed out when unaffordable; penalties are always pickable."""
    PAY = {"label": "Pay", "payment": True, "effects": [{"type": "resource", "resource": "scrap", "amount": -5}]}
    HIT = {"label": "Robbed", "effects": [{"type": "resource", "resource": "water", "amount": -12}]}

    def setUp(self):
        self.poor = FakeResourceGame(scrap=1, water=1)

    def test_is_payment(self):
        self.assertTrue(is_payment(self.PAY))
        self.assertFalse(is_payment(self.HIT))

    def test_shortfalls(self):
        self.assertEqual(shortfalls(self.poor, self.PAY), [("scrap", 5, 1)])
        self.assertEqual(shortfalls(self.poor, self.HIT), [])

    def test_unaffordable_payments_are_greyed_out(self):
        self.assertEqual(affordable_flags(self.poor, [self.PAY, self.HIT]), [False, True])

    def test_when_nothing_is_payable_nobody_is_stuck(self):
        self.assertEqual(affordable_flags(self.poor, [self.PAY, dict(self.PAY)]), [True, True])

    def test_a_penalty_takes_what_is_left_and_nothing_else(self):
        game = FakeResourceGame(water=1)
        apply_effects(game, self.HIT["effects"])
        self.assertEqual((game.water, game.food), (0, 10))


class RequirementTests(unittest.TestCase):
    """"requires" dicts: every key, its boundaries, and what an unknown key does."""

    def test_empty_requirements_always_hold(self):
        game = StatsGame()
        for requires in (None, {}):
            self.assertTrue(requirements_met(game, requires))

    def test_below_is_strict_and_at_least_is_inclusive(self):
        game = StatsGame(fuel=3)
        self.assertTrue(requirements_met(game, {"fuel_below": 4}))
        self.assertFalse(requirements_met(game, {"fuel_below": 3}))
        self.assertTrue(requirements_met(game, {"fuel_at_least": 3}))
        self.assertFalse(requirements_met(game, {"fuel_at_least": 4}))

    def test_every_stat_can_be_tested(self):
        game = StatsGame(vehicles=("Pickup Truck", "Ambulance"), health=40, passengers=8, survivors=5, horde=12,
                         food=2, water=3, scrap=9)
        for key, value in {"food_below": 3, "water_below": 4, "scrap_at_least": 9, "survivors_at_least": 5,
                           "horde_below": 15, "health_below": 50, "vehicles_at_least": 2,
                           "free_seats_at_least": 3}.items():
            with self.subTest(requirement=key):
                self.assertTrue(requirements_met(game, {key: value}))
        for key, value in {"food_at_least": 3, "horde_at_least": 13, "health_at_least": 41, "vehicles_below": 2,
                           "free_seats_at_least": 4}.items():
            with self.subTest(requirement=key):
                self.assertFalse(requirements_met(game, {key: value}))

    def test_every_entry_must_hold(self):
        game = StatsGame(fuel=2, scrap=0)
        self.assertTrue(requirements_met(game, {"fuel_below": 3, "scrap_below": 1}))
        self.assertFalse(requirements_met(game, {"fuel_below": 3, "scrap_at_least": 1}))

    def test_vehicle_requirement_ignores_case_and_accepts_a_list(self):
        game = StatsGame(vehicles=("Pickup Truck", "Ambulance"))
        self.assertTrue(requirements_met(game, {"vehicle": "ambulance"}))
        self.assertTrue(requirements_met(game, {"vehicle": ["School Bus", "AMBULANCE"]}))
        self.assertFalse(requirements_met(game, {"vehicle": "School Bus"}))
        self.assertFalse(requirements_met(game, {"vehicle": ["School Bus", "Semi-Truck"]}))

    def test_vehicle_slot_needs_a_spare_driver(self):
        self.assertTrue(requirements_met(StatsGame(adults=2), {"vehicle_slot": True}))
        self.assertFalse(requirements_met(StatsGame(adults=1), {"vehicle_slot": True}))
        self.assertTrue(requirements_met(StatsGame(adults=1), {"vehicle_slot": False}))

    def test_free_seats(self):
        self.assertEqual(free_seats(StatsGame(passengers=8, survivors=5)), 3)
        self.assertEqual(free_seats(StatsGame(passengers=8, survivors=20)), 0)   # never negative

    def test_an_unknown_key_is_never_met(self):
        game = StatsGame()
        for key in ("fuel_belowe", "gold_below", "fuel", "fuel_exactly", "teleport"):
            with self.subTest(key=key):
                self.assertFalse(requirements_met(game, {key: 1}))

    def test_choice_available_needs_requirements_and_payment(self):
        game = StatsGame(scrap=2)
        pay = {"payment": True, "effects": [{"type": "resource", "resource": "scrap", "amount": -5}]}
        locked = {"requires": {"vehicles_at_least": 3}, "effects": []}
        free = {"effects": []}
        self.assertFalse(choice_available(game, pay))
        self.assertFalse(choice_available(game, locked))
        self.assertTrue(choice_available(game, free))
        game.scrap = 5
        self.assertTrue(choice_available(game, pay))

    def test_affordable_flags_lock_a_choice_whose_requirement_is_not_met(self):
        game = StatsGame()
        locked = {"requires": {"vehicles_at_least": 3}, "effects": []}
        free = {"effects": []}
        self.assertEqual(affordable_flags(game, [locked, free]), [False, True])
        self.assertEqual(affordable_flags(game, [locked, dict(locked)]), [True, True])   # nobody is stuck

    def test_event_available_needs_its_requirements_and_a_pickable_choice(self):
        game = StatsGame(fuel=20, scrap=0)
        pay = {"payment": True, "effects": [{"type": "resource", "resource": "scrap", "amount": -5}]}
        free = {"effects": []}
        self.assertTrue(event_available(game, {"choices": [pay, free]}))
        self.assertFalse(event_available(game, {"choices": [pay, dict(pay)]}))               # nothing payable
        self.assertFalse(event_available(game, {"requires": {"fuel_below": 3}, "choices": [free]}))
        self.assertTrue(event_available(game, {"requires": {"fuel_at_least": 3}, "choices": [free]}))
        self.assertFalse(event_available(game, {"choices": []}))

    def test_requirement_text(self):
        cases = {
            ("vehicle", "Ambulance"): "needs Ambulance",
            ("vehicle", ("Ambulance", "School Bus")): "needs Ambulance or School Bus",   # a tuple: a list cannot be a dict key
            ("background", "Military"): "only for Military backgrounds",
            ("vehicle_slot", True): "needs a spare driver",
            ("free_seats_at_least", 1): "needs a free seat",
            ("free_seats_at_least", 3): "needs 3+ free seats",
            ("vehicles_at_least", 2): "needs 2+ vehicles",
            ("fuel_below", 3): "only if fuel is under 3",
            ("fuel_belowe", 3): "not available",
        }
        for (key, value), text in cases.items():
            with self.subTest(key=key):
                self.assertEqual(requirement_text(key, value), text)

    def test_unmet_requirement_notes_list_only_what_is_missing(self):
        game = StatsGame(vehicles=("Pickup Truck",), fuel=20)
        choice = {"requires": {"fuel_at_least": 5, "vehicles_at_least": 2, "vehicle": "Ambulance"}}
        self.assertEqual(unmet_requirement_notes(game, choice), ["needs 2+ vehicles", "needs Ambulance"])
        self.assertEqual(unmet_requirement_notes(game, {}), [])


class FittedEffectsTests(unittest.TestCase):
    """A rescue that offers more people than there are free seats only takes (and charges for) those who fit."""

    def rescue(self, offered, cost):
        return {"effects": [{"type": "resource", "resource": "scrap", "amount": -cost},
                            {"type": "survivors", "amount": offered},
                            {"type": "horde_gap", "amount": -6}]}

    def test_everyone_fits_nothing_changes(self):
        choice = self.rescue(3, 8)                                   # 3 free seats (8 - 5)
        effects, note = fitted_effects(StatsGame(), choice)
        self.assertEqual(effects, choice["effects"])
        self.assertEqual(note, "")

    def test_a_choice_without_a_rescue_is_not_touched(self):
        choice = {"effects": [{"type": "resource", "resource": "scrap", "amount": -4}]}
        effects, note = fitted_effects(StatsGame(survivors=8), choice)
        self.assertEqual((effects, note), (choice["effects"], ""))

    def test_the_cost_is_scaled_to_the_people_who_fit(self):
        effects, note = fitted_effects(StatsGame(), self.rescue(4, 8))   # 3 of 4 fit: 8 * 3/4 = 6
        self.assertEqual(effects[0]["amount"], -6)
        self.assertEqual(note, "Only 3 of 4 could fit aboard, so the cost was scaled down.")

    def test_the_scaled_cost_is_rounded_up(self):
        effects, _note = fitted_effects(StatsGame(), self.rescue(4, 5))  # 5 * 3/4 = 3.75 -> 4
        self.assertEqual(effects[0]["amount"], -4)

    def test_time_and_danger_are_not_scaled(self):
        effects, _note = fitted_effects(StatsGame(), self.rescue(4, 8))
        self.assertEqual(effects[2], {"type": "horde_gap", "amount": -6})
        self.assertEqual(effects[1], {"type": "survivors", "amount": 4})

    def test_with_no_free_seat_the_rescue_costs_nothing(self):
        effects, note = fitted_effects(StatsGame(survivors=8), self.rescue(2, 8))
        self.assertEqual(effects[0]["amount"], 0)
        self.assertIn("Only 0 of 2", note)

    def test_the_original_choice_is_not_changed(self):
        choice = self.rescue(4, 8)
        fitted_effects(StatsGame(), choice)
        self.assertEqual(choice["effects"][0]["amount"], -8)

    def test_gains_are_not_scaled(self):
        choice = {"effects": [{"type": "resource", "resource": "food", "amount": 4},
                              {"type": "survivors", "amount": 4}]}
        effects, _note = fitted_effects(StatsGame(), choice)
        self.assertEqual(effects[0]["amount"], 4)


class DefendedLossTests(unittest.TestCase):
    def test_defense_only_counts_when_the_effect_asks_for_it(self):
        game = SimpleNamespace(defense_reduction=lambda: 50)
        self.assertEqual(defended_loss(game, 4, {"defense": True}), 2)
        self.assertEqual(defended_loss(game, 4, {}), 4)

    def test_rounds_half_up(self):
        game = SimpleNamespace(defense_reduction=lambda: 50)
        self.assertEqual(defended_loss(game, 3, {"defense": True}), 2)
        self.assertEqual(defended_loss(game, 1, {"defense": True}), 1)

    def test_a_game_without_defense_changes_nothing(self):
        self.assertEqual(defended_loss(None, 5, {"defense": True}), 5)
        self.assertEqual(defended_loss(SimpleNamespace(), 5, {"defense": True}), 5)


class ValidatorTests(unittest.TestCase):
    """The validators catch typos in event and mission data before they silently do nothing in play."""

    def test_the_validator_finds_typos(self):
        bad_effects = [
            {"type": "resource", "resource": "fuell", "amount": -3},     # unknown resource
            {"type": "resource", "resource": "fuel", "amount": "3"},     # int("3") would work, "three" would crash
            {"type": "resource", "resource": "fuel"},                    # amount missing: silently 0
            {"type": "survivor", "amount": 1},                           # unknown type: silently ignored
            {"type": "vehicle_gain", "vehicle": "Hovercraft"},
            {"type": "vehicle_gain", "health": 2},
            {"type": "horde_gap", "amount": 1.5},
            {"type": "injury", "amount": "2"},                           # injury needs an integer amount
            {"type": "injury"},
            {"type": "vehicle_damage_pct"},
            {"type": "vehicle_damage_pct", "amount": 2.5},
            {"type": "resource", "resource": "fuel", "amount": True},    # a bool is not an amount
            "not a dict",
        ]
        for effect in bad_effects:
            self.assertTrue(validate_effect(effect), f"not caught: {effect}")

    def test_the_validator_accepts_good_effects(self):
        for effect in ({"type": "resource", "resource": "scrap", "amount": -2}, {"type": "vehicle_loss"},
                       {"type": "survivors", "amount": 2, "defense": True}, {"type": "vehicle_gain"},
                       {"type": "vehicle_gain", "vehicle": "ambulance", "health": 0.7},
                       {"type": "injury", "amount": 2, "defense": True}, {"type": "injury", "amount": -1},
                       {"type": "vehicle_damage_pct", "amount": 10, "defense": True},
                       {"type": "vehicle_damage", "amount": 5}, {"type": "vehicle_repair", "amount": 4}):
            self.assertEqual(validate_effect(effect), [], effect)

    def test_requires_are_validated(self):
        for bad in ({"fuel_belowe": 3}, {"vehicle": "Hovercraft"}, {"vehicle": []}, {"vehicle_slot": "yes"},
                    {"fuel_below": "3"}, {"gold_at_least": 1}, "not a dict"):
            self.assertTrue(validate_requires(bad), f"not caught: {bad}")
        for good in (None, {}, {"fuel_below": 3, "vehicle_slot": True, "vehicle": ["Ambulance"]},
                     {"vehicles_at_least": 2}, {"free_seats_at_least": 1}, {"health_below": 50},
                     {"horde_below": 15}, {"scrap_at_least": 8}):
            self.assertEqual(validate_requires(good), [], good)

    def test_bad_events_are_reported_by_id(self):
        events = [{"id": "oops", "choices": [{"effects": [{"type": "resource", "resource": "fuel"}]}]}]
        self.assertIn("oops", validate_events(events)[0])
        with self.assertRaises(ValueError):
            check_events(events)

    def test_a_bad_requires_on_a_choice_or_an_event_is_reported(self):
        choice_bad = [{"id": "a", "choices": [{"requires": {"fuell_below": 1}, "effects": []}]}]
        event_bad = [{"id": "b", "requires": {"vehicle": "Hovercraft"}, "choices": [{"effects": []}]}]
        self.assertTrue(validate_events(choice_bad))
        self.assertTrue(validate_events(event_bad))

    def test_an_event_without_choices_is_reported(self):
        self.assertTrue(validate_events([{"id": "empty", "choices": []}]))
        self.assertTrue(validate_events([{"id": "none"}]))
        self.assertTrue(validate_events(["not a dict"]))

    def test_good_events_pass(self):
        events = [{"id": "fine", "requires": {"fuel_below": 3},
                   "choices": [{"requires": {"vehicles_at_least": 2}, "effects": [{"type": "vehicle_loss"}]}]}]
        self.assertEqual(validate_events(events), [])
        check_events(events)


if __name__ == "__main__":
    unittest.main()
