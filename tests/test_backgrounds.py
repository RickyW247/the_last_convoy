"""Tests of the player background abilities (game/background_rules.py; the numbers are in background_data.py)."""
import random
import unittest

import background_data as bd
from game.event_data import EVENTS
from game import Game
from game.effect_handler import event_available, fitted_effects, requirements_met
from game.null_audio import NullAudio
from map_data import SITES


def make_game(background="Civilian"):
    game = Game(music=NullAudio(), sound=NullAudio())
    game.background = background
    game.reset()
    return game


def event(event_id):
    return next(e for e in EVENTS if e["id"] == event_id)


class BackgroundRulesTest(unittest.TestCase):
    def test_every_background_has_an_ability_key(self):
        for name, data in bd.BACKGROUNDS.items():
            self.assertTrue(data.get("ability_key"), name)

    def test_repair_costs(self):
        base = make_game("Police").repair_cost()   # Police has no repair discount
        for name, discount in (("Corporate", bd.CORPORATE_REPAIR_DISCOUNT), ("Civilian", 0),
                               ("Military", 0), ("Government", 0), ("Criminal", 0)):
            self.assertEqual(make_game(name).repair_cost(), max(1, base - discount), name)

    def test_recovery_prices(self):
        police, corporate, military = make_game("Police"), make_game("Corporate"), make_game("Military")
        for vehicle_type in ("Ambulance", "Military Humvee"):
            self.assertLessEqual(corporate.recovery_price(vehicle_type), police.recovery_price(vehicle_type))
        self.assertLessEqual(military.recovery_price("Military Humvee"), police.recovery_price("Military Humvee"))
        self.assertEqual(military.recovery_price("Ambulance"), police.recovery_price("Ambulance"))   # not a military vehicle

    def test_civilian_gets_scrap_back_on_every_other_repair(self):
        game = make_game("Civilian")
        game.scrap, game.food, game.water = 20, 50, 50
        for v in game.vehicles:
            v.health = 1
        cost, spent = game.repair_cost(), []
        for _ in range(4):
            before = game.scrap
            game.repair()
            spent.append(before - game.scrap)
        self.assertEqual(spent, [cost, cost - bd.CIVILIAN_REPAIR_REFUND, cost, cost - bd.CIVILIAN_REPAIR_REFUND])
        other = make_game("Police")
        other.scrap, other.food, other.water = 20, 50, 50
        for v in other.vehicles:
            v.health = 1
        before = other.scrap
        other.repair()
        other.repair()
        self.assertEqual(before - other.scrap, 2 * other.repair_cost())   # no refunds for other backgrounds

    def test_military_upgrades_are_cheaper_on_military_vehicles(self):
        from upgrade_data import get_upgrade
        upgrade = get_upgrade("armor_plating")
        military, police = make_game("Military"), make_game("Police")
        self.assertEqual(military.upgrade_price(upgrade, "Military Humvee"), upgrade["cost"] - bd.MILITARY_UPGRADE_DISCOUNT)
        self.assertEqual(military.upgrade_price(upgrade, "Pickup Truck"), upgrade["cost"])
        self.assertEqual(police.upgrade_price(upgrade, "Military Humvee"), upgrade["cost"])
        # installing really charges the discounted price
        military.scrap, military.food, military.water = 20, 50, 50
        military.selected_vehicle_type = "Military Humvee"
        military.current_stop()["sites"] = ["mixed"]   # a stop where upgrades can be installed
        before = military.scrap
        self.assertTrue(military.install_upgrade("armor_plating"))
        self.assertEqual(before - military.scrap, upgrade["cost"] - bd.MILITARY_UPGRADE_DISCOUNT)

    def test_criminal_stash_only_at_underworld_sites(self):
        random.seed(2)
        criminal, civilian = make_game("Criminal"), make_game("Civilian")
        for site in bd.CRIMINAL_STASH_SITES:
            self.assertIn(site, SITES)
        at_site = sum(1 for _ in range(400) if criminal.background_scavenge_bonus(0, {"food": 4}, "warehouse")[0] > 0)
        elsewhere = sum(1 for _ in range(400) if criminal.background_scavenge_bonus(0, {"food": 4}, "farm")[0] > 0)
        self.assertTrue(80 < at_site < 160, at_site)   # about CRIMINAL_STASH_CHANCE (30%) of 400
        self.assertEqual(elsewhere, 0)
        self.assertEqual(sum(1 for _ in range(200) if civilian.background_scavenge_bonus(0, {"food": 4}, "warehouse")[0] > 0), 0)

    def test_military_repairs_heal_military_vehicles_more(self):
        game = make_game("Military")
        humvee = next(v for v in game.vehicles if v.vehicle_type == "Military Humvee")
        self.assertEqual(game.repair_multiplier(humvee), 1 + bd.MILITARY_REPAIR_BONUS)
        civilian = make_game("Civilian")
        self.assertEqual(civilian.repair_multiplier(civilian.vehicles[0]), 1.0)

    def test_police_cut_emergency_time_penalties_only(self):
        effects = [{"type": "horde_gap", "amount": -15}, {"type": "horde_gap", "amount": 5}, {"type": "survivors", "amount": 2}]
        police, civilian = make_game("Police"), make_game("Civilian")
        cut, note = police.adjust_event_effects(event("desperate_rescue"), effects)
        self.assertEqual([e["amount"] for e in cut], [-8, 5, 2])   # -15 halved (rounded up), the gain untouched
        self.assertTrue(note)
        self.assertEqual(police.adjust_event_effects({"id": "x"}, effects), (effects, ""))        # not an emergency
        self.assertEqual(civilian.adjust_event_effects(event("desperate_rescue"), effects), (effects, ""))

    def test_government_scavenging_sometimes_yields_extra(self):
        random.seed(3)
        game = make_game("Government")
        extra = sum(1 for _ in range(400) if game.background_scavenge_bonus(0, {"food": 4})[1]["food"] > 4)
        self.assertTrue(60 < extra < 180, extra)   # about GOVERNMENT_SCAVENGE_CHANCE (30%) of 400
        other = make_game("Civilian")
        self.assertTrue(all(other.background_scavenge_bonus(0, {"food": 4}) == (0, {"food": 4}) for _ in range(100)))

    def test_criminal_recruiting_is_harder(self):
        random.seed(5)
        criminal, civilian = make_game("Criminal"), make_game("Civilian")
        self.assertEqual(civilian.willing_recruits(3), 3)
        joined = sum(criminal.willing_recruits(3) for _ in range(400))
        self.assertTrue(400 * 3 * 0.45 < joined < 400 * 3 * 0.75, joined)   # about CRIMINAL_RECRUIT_FACTOR (60%)

    def test_refusers_do_not_cost_supplies(self):
        random.seed(7)
        game = make_game("Criminal")
        choice = next(c for c in event("family_in_need")["choices"] if c["label"] == "Bring the family aboard")
        self.assertGreaterEqual(game.convoy_stats()["passengers"] - game.survivors, 3)   # room for the whole family
        seen = set()
        for _ in range(200):
            effects, _note = fitted_effects(game, choice)
            people = sum(e["amount"] for e in effects if e["type"] == "survivors")
            food = sum(e["amount"] for e in effects if e.get("resource") == "food")
            seen.add((people, food))
            self.assertLessEqual(people, 3)
            self.assertEqual(food, -2 * people)   # the food cost (-6 for 3 people) scales with the people who joined
        self.assertGreater(len(seen), 1)   # sometimes fewer than everyone joins

    def test_criminal_events_only_for_criminals(self):
        for event_id in ("underworld_fence", "smugglers_stash", "toll_gang"):
            self.assertTrue(requirements_met(make_game("Criminal"), event(event_id)["requires"]))
            self.assertFalse(requirements_met(make_game("Police"), event(event_id)["requires"]))
        self.assertFalse(event_available(make_game("Civilian"), event("underworld_fence")))

    def test_settlements_sometimes_refuse_criminals_only(self):
        random.seed(11)
        settlement = event("small_town_survivors")
        criminal, civilian = make_game("Criminal"), make_game("Civilian")
        refused = sum(1 for _ in range(400) if criminal.settlement_refuses(settlement))
        self.assertTrue(80 < refused < 240, refused)   # about CRIMINAL_SETTLEMENT_REFUSAL_CHANCE (40%)
        self.assertFalse(any(civilian.settlement_refuses(settlement) for _ in range(100)))
        self.assertFalse(any(criminal.settlement_refuses(event("roadside_cache")) for _ in range(100)))


class SmokeTest(unittest.TestCase):
    def test_a_random_run_for_every_background_never_crashes(self):
        """Scavenge, repair and drive at random with each background; every event is resolved with a random choice."""
        for name in bd.BACKGROUNDS:
            random.seed(hash(name) % 1000)
            game = make_game(name)
            game.scrap, game.fuel = 60, 60
            for _ in range(300):
                if game.status != "playing":
                    break
                if game.event_manager.active:
                    game.resolve_event_choice(random.randrange(len(game.event_manager.current_event["choices"])))
                elif game.event_result:
                    game.dismiss_event_result()
                elif game.journey:
                    game.continue_journey()
                elif game.abandon_pick_needed():
                    game.abandon_picked_vehicle()
                else:
                    action = random.choice(("scavenge", "scavenge", "repair", "travel"))
                    if action == "scavenge":
                        game.scavenge()
                    elif action == "repair":
                        game.repair()
                    else:
                        game.select_destination(game.default_destination())
                        game.travel()
                game.event_manager.clear_result()


if __name__ == "__main__":
    unittest.main()
