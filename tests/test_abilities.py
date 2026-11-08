"""Tests of the vehicle special abilities (design doc section 6): Reinforced Protection, Recovery Support, and the
ability text shown on the vehicles screen. Headless: no pygame display, sound device or settings file."""
import unittest

from config import (DEFENSE_REDUCTION_CAP, RECOVERY_SUPPORT_RECOVERY_DISCOUNT, RECOVERY_SUPPORT_REPAIR_DISCOUNT,
                    REINFORCED_PROTECTION_BONUS, REPAIR_SCRAP_COST)
from game import Game, Vehicle, recovery_cost
from game.null_audio import NullAudio
from vehicle_data import ABILITY_INFO, VEHICLE_ABILITIES, VEHICLE_SPECS, ability_info


def new_game():
    return Game(music=NullAudio(), sound=NullAudio())


class AbilityDataTests(unittest.TestCase):
    def test_every_ability_key_has_display_text(self):
        for vehicle_type, key in VEHICLE_ABILITIES.items():
            self.assertIn(vehicle_type, VEHICLE_SPECS)
            self.assertIn(key, ABILITY_INFO)
            info = ability_info(vehicle_type)
            self.assertTrue(info["name"] and info["text"] and info["short"])

    def test_vehicle_without_ability_has_no_info(self):
        self.assertIsNone(ability_info("Pickup Truck"))


class ReinforcedProtectionTests(unittest.TestCase):
    def test_humvee_adds_its_bonus_to_the_convoy_defense(self):
        game = new_game()
        plain = game.total_defense()
        self.assertEqual(plain, game.convoy_stats()["defense"])
        game.vehicles.append(Vehicle("Military Humvee"))
        self.assertEqual(game.total_defense(),
                         plain + VEHICLE_SPECS["Military Humvee"]["defense"] + REINFORCED_PROTECTION_BONUS)

    def test_reduction_stays_under_the_cap(self):
        game = new_game()
        game.vehicles.append(Vehicle("Military Humvee"))
        self.assertLessEqual(game.defense_reduction(), DEFENSE_REDUCTION_CAP)


class RecoverySupportTests(unittest.TestCase):
    def test_repair_costs_less_with_a_tow_truck(self):
        game = new_game()
        self.assertEqual(game.repair_cost(), REPAIR_SCRAP_COST)
        game.vehicles.append(Vehicle("Tow/Recovery Truck"))
        self.assertEqual(game.repair_cost(), max(1, REPAIR_SCRAP_COST - RECOVERY_SUPPORT_REPAIR_DISCOUNT))

    def test_recovery_costs_less_with_a_tow_truck_but_never_below_one(self):
        game = new_game()
        self.assertEqual(game.recovery_price("Semi-Truck"), recovery_cost("Semi-Truck"))
        game.vehicles.append(Vehicle("Tow/Recovery Truck"))
        self.assertEqual(game.recovery_price("Semi-Truck"),
                         max(1, recovery_cost("Semi-Truck") - RECOVERY_SUPPORT_RECOVERY_DISCOUNT))
        self.assertGreaterEqual(game.recovery_price("Pickup Truck"), 1)

    def test_repair_charges_the_discounted_price(self):
        game = new_game()
        game.vehicles.append(Vehicle("Tow/Recovery Truck"))
        game.vehicles[0].health = 1
        game.scrap = 10
        game.food = game.water = 100   # no survivor would leave during the day the repair takes
        game.repair()
        self.assertEqual(game.scrap, 10 - game.repair_cost())


if __name__ == "__main__":
    unittest.main()
