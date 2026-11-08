"""Tests for vehicles: vehicle_data, sprites (vehicle_rendering) and the upgrade rules (upgrade_data, game.convoy)."""

import unittest

import pygame

import vehicle_data
import vehicle_rendering
from game.convoy import ConvoyMixin
from game.vehicle import Vehicle, recovery_cost
from upgrade_data import ALL_TYPES, UPGRADES, describe_effects, look_for, upgrades_for
from vehicle_data import VEHICLE_SPECS

from tests.helpers import make_game, needs_vehicle_assets

STAT_KEYS = {"speed", "health", "passengers", "cargo", "defense", "fuel_capacity", "fuel_consumption"}


class VehicleDataTests(unittest.TestCase):
    def test_all_vehicle_tables_cover_the_same_types(self):
        types = set(VEHICLE_SPECS)
        self.assertEqual(len(types), 8)
        self.assertEqual(set(vehicle_data.VEHICLE_ROLES), types)
        self.assertTrue(types <= set(vehicle_data.VEHICLE_LOOKS))
        self.assertTrue(types <= set(vehicle_rendering._SPRITE_FILES))

    def test_specs_have_positive_whole_number_stats(self):
        for name, stats in VEHICLE_SPECS.items():
            with self.subTest(vehicle=name):
                self.assertEqual(set(stats), STAT_KEYS)
                for key, value in stats.items():
                    self.assertIsInstance(value, int, key)
                    self.assertGreater(value, 0, key)

    def test_recovery_costs(self):
        for name, cost in vehicle_data.RECOVERY_COSTS.items():
            self.assertIn(name, VEHICLE_SPECS)
            self.assertGreater(cost, 0)
        for name in VEHICLE_SPECS:
            self.assertGreater(recovery_cost(name), 0)
        self.assertEqual(recovery_cost("Unlisted Vehicle"), 3)

    def test_looks_and_sprite_files(self):
        for name, look in vehicle_data.VEHICLE_LOOKS.items():
            self.assertTrue(look["label"], name)
        files = list(vehicle_rendering._SPRITE_FILES.values())
        self.assertEqual(len(files), len(set(files)), "two vehicles share one sprite file")
        for filename in files:
            self.assertTrue(filename.endswith(".png"))

    def test_every_look_an_upgrade_can_give_has_a_sprite_file(self):
        for upgrade in UPGRADES:
            for vehicle_type in upgrade["types"]:
                look = look_for(vehicle_type, [upgrade["id"]])
                self.assertIn(look, vehicle_rendering._SPRITE_FILES, f"{upgrade['id']} on {vehicle_type}")

    def test_the_starting_convoy_is_playable(self):
        g = make_game()
        for vehicle in g.vehicles:
            self.assertIn(vehicle.vehicle_type, VEHICLE_SPECS)
        self.assertGreaterEqual(g.survivors, len(g.vehicles))                    # a driver for each vehicle
        self.assertLessEqual(g.survivors, g.convoy_stats()["passengers"])        # a seat for each survivor
        self.assertLessEqual(g.cargo_used(), g.convoy_stats()["cargo"])
        self.assertLessEqual(g.fuel, g.convoy_stats()["fuel_capacity"])

    def test_unknown_vehicle_sprite_is_an_error(self):
        with self.assertRaises(KeyError):
            vehicle_rendering.get_vehicle_sprite("Hovercraft")


@needs_vehicle_assets
class VehicleSpriteTests(unittest.TestCase):
    """Every sprite, including the upgraded looks."""

    def test_every_vehicle_sprite_loads_with_transparency_and_is_cached(self):
        for name in vehicle_rendering._SPRITE_FILES:
            with self.subTest(vehicle=name):
                sprite = vehicle_rendering.get_vehicle_sprite(name)
                self.assertGreater(sprite.get_width(), 0)
                self.assertGreater(sprite.get_height(), 0)
                self.assertTrue(sprite.get_flags() & pygame.SRCALPHA, "sprite has no transparency")
                self.assertIs(vehicle_rendering.get_vehicle_sprite(name), sprite)

    def test_sprites_have_no_empty_rows_under_the_wheels(self):
        """Vehicles are placed by the bottom edge of their image; empty rows there make them float.

        The PNG files have transparent padding, so get_vehicle_sprite trims it; this checks what it returns."""
        for name in vehicle_rendering._SPRITE_FILES:
            with self.subTest(vehicle=name):
                sprite = vehicle_rendering.get_vehicle_sprite(name)
                empty_rows = sprite.get_height() - sprite.get_bounding_rect().bottom
                self.assertEqual(empty_rows, 0,
                                 f"{empty_rows} transparent row(s) under the {name}; it will float above the road")


# ---------------------------------------------------------------------------------------------------- upgrades
class FakeSurvivors:
    def get_survivors(self):
        return [{"id": i, "age": 30} for i in range(8)]


class UpgradeGame(ConvoyMixin):
    """Just enough of Game for the convoy mixin's upgrade rules."""

    def __init__(self, site="Truck Stop", scrap=20):
        self.vehicles = [Vehicle("Pickup Truck"), Vehicle("Semi-Truck")]
        self.scrap, self.status, self.survivors = scrap, "playing", 8
        self.selected_vehicle_type, self.vehicle_upgrades, self.selected_upgrade = "Semi-Truck", {}, None
        self.site, self.log, self.survivor_manager = site, [], FakeSurvivors()
        self.journey, self.vehicles_recovered, self.current_location = None, 0, "Test"
        self.advanced = 0

    def current_sites(self):
        return ["truck" if self.site == "Truck Stop" else "farm"]

    def say(self, message):
        self.log.append(message)

    def assign_survivors_to_vehicles(self):
        pass

    def advance_time(self, days):
        self.advanced += days

    def confirm_day_cost(self, *args, **kwargs):
        return True

    def check_defeat(self):
        pass

    def enforce_limits(self):
        pass


class UpgradeCatalogueTests(unittest.TestCase):
    def test_ids_are_unique_and_entries_complete(self):
        ids = [u["id"] for u in UPGRADES]
        self.assertEqual(len(ids), len(set(ids)))
        for upgrade in UPGRADES:
            with self.subTest(upgrade=upgrade["id"]):
                self.assertTrue(set(upgrade["types"]) <= set(ALL_TYPES))
                self.assertGreater(upgrade["cost"], 0)
                self.assertTrue(upgrade["effects"])

    def test_upgrade_types_are_real_vehicles(self):
        self.assertTrue(set(ALL_TYPES) <= set(VEHICLE_SPECS))

    def test_every_vehicle_type_has_an_upgrade_and_the_trailer_fits_only_the_semi(self):
        self.assertTrue(all(upgrades_for(t) for t in ALL_TYPES))
        semi_cargo = [u["id"] for u in UPGRADES if "Semi-Truck" in u["types"] and u["category"] == "Cargo"]
        self.assertEqual(semi_cargo, ["semi_trailer"])

    def test_effects_are_described(self):
        self.assertEqual(describe_effects({"health": 25, "defense": 1}), "+25 HP  +1 DEF")


class VehicleUpgradeTests(unittest.TestCase):
    """Upgrades on a single Vehicle."""

    def test_stats_and_look_change_but_the_baseline_does_not(self):
        v = Vehicle("Semi-Truck")
        base = dict(VEHICLE_SPECS["Semi-Truck"])
        self.assertEqual((v.sprite_type, v.upgrades), ("Semi-Truck", []))
        self.assertTrue(v.install_upgrade("semi_trailer"))
        self.assertEqual(v.stats["cargo"], base["cargo"] + 100)
        self.assertEqual(v.stats["speed"], base["speed"] - 5)
        self.assertEqual(v.stats["fuel_consumption"], base["fuel_consumption"] + 4)
        self.assertEqual(v.sprite_type, "Semi-Truck Trailer")
        self.assertEqual(look_for("Semi-Truck", v.upgrades), "Semi-Truck Trailer")
        self.assertEqual(VEHICLE_SPECS["Semi-Truck"], base)       # the baseline is never changed
        self.assertEqual(Vehicle("Pickup Truck").sprite_type, "Pickup Truck")

    def test_bad_installs_are_refused(self):
        v = Vehicle("Semi-Truck")
        self.assertTrue(v.install_upgrade("semi_trailer"))
        self.assertFalse(v.install_upgrade("semi_trailer"))       # once only
        self.assertFalse(v.install_upgrade("cargo_racks"))        # does not fit a semi
        self.assertFalse(v.install_upgrade("nonsense"))

    def test_armour_adds_current_health(self):
        v = Vehicle("Pickup Truck")
        v.health = 40
        v.install_upgrade("armor_plating")
        self.assertEqual((v.stats["health"], v.health), (105, 65))

    def test_stats_keep_their_floors(self):
        v = Vehicle("Pickup Truck")
        v.install_upgrade("fuel_injectors")
        self.assertEqual(v.stats["fuel_consumption"], 6)
        self.assertGreaterEqual(v.stats["speed"], 1)


class GameUpgradeTests(unittest.TestCase):
    """Installing upgrades through the convoy rules (place, scrap, selection, time)."""

    def test_upgrades_are_only_installed_at_recovery_stops(self):
        g = UpgradeGame(site="Farm")
        self.assertEqual(g.upgrade_problem("semi_trailer"), g.UPGRADE_PLACE_MESSAGE)
        self.assertFalse(g.install_upgrade("semi_trailer"))
        self.assertEqual(g.scrap, 20)

    def test_upgrades_cost_scrap(self):
        g = UpgradeGame(scrap=3)
        self.assertIn("Need 8 scrap", g.upgrade_problem("semi_trailer"))

    def test_the_first_row_is_selected_until_another_is_picked(self):
        g = UpgradeGame()
        self.assertEqual(g.selected_upgrade_id(), "armor_plating")
        g.select_upgrade("semi_trailer")
        self.assertEqual(g.selected_upgrade_id(), "semi_trailer")
        self.assertEqual(g.upgrade_problem(), "")
        g.select_upgrade("cargo_racks")                           # does not fit the semi: ignored
        self.assertEqual(g.selected_upgrade_id(), "semi_trailer")

    def test_installing_changes_the_convoy_and_takes_a_day(self):
        g = UpgradeGame()
        g.select_upgrade("semi_trailer")
        before = g.convoy_stats()
        self.assertTrue(g.install_upgrade())
        after = g.convoy_stats()
        self.assertEqual(g.scrap, 12)
        self.assertEqual(after["cargo"], before["cargo"] + 100)
        self.assertLess(after["speed"], before["speed"])
        self.assertEqual(g.owned_vehicle("Semi-Truck").sprite_type, "Semi-Truck Trailer")
        self.assertEqual(g.upgrade_problem("semi_trailer"), "Already installed.")
        self.assertEqual(g.advanced, 1)   # CHANGED: installing now takes a day (this used to assert 0)

    def test_upgrades_survive_abandon_and_recover(self):
        g = UpgradeGame()
        g.select_upgrade("armor_plating")
        g.install_upgrade()
        g.vehicles = [v for v in g.vehicles if v.vehicle_type != "Semi-Truck"]   # lost some way or other
        g.selected_vehicle_type = "Pickup Truck"
        g.select_upgrade("armor_plating")
        g.install_upgrade()
        g.vehicles.remove(g.owned_vehicle("Pickup Truck"))
        g.vehicles.append(Vehicle("Semi-Truck"))
        g.scrap = 20
        g.survivor_manager = FakeSurvivors()
        g.recover_vehicle("Pickup Truck")
        back = g.owned_vehicle("Pickup Truck")
        self.assertEqual(back.upgrades, ["armor_plating"])
        self.assertEqual(back.stats["health"], 105)
        self.assertEqual(back.health, int(105 * 0.7))             # recovered at 70% of the upgraded maximum
