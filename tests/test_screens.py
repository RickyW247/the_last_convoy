"""Tests for buttons.py and ui: title, lore, menu, instructions, convoy and ending screens, and vehicle placement."""

import itertools
import sys
import unittest
from unittest import mock

import pygame

import buttons as buttons_module  # aliased: tests often use `buttons` as a local name
import config
import instructions_data
import layout
import map_data
import ui
import vehicle_data

from tests.helpers import LayoutTestCase, make_game, needs_all_assets, needs_vehicle_assets, surface

CORE_CONVOY_BUTTONS = ("SCAVENGE", "REPAIR", "VEHICLES", "MAP [M]", "MENU [O]")


class ScreenButtonTests(LayoutTestCase):
    def setUp(self):
        super().setUp()
        self.g = make_game()

    def buttons(self, screen):
        self.g.screen = screen
        return {button.label: button for button in buttons_module.make_buttons(self.g)}

    # --- title, lore, menu
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

    def test_menu_buttons_change_the_difficulty(self):
        buttons = self.buttons("menu")
        for label in ("Easy", "Normal", "Hard", "INSTRUCTIONS", "BACK"):
            self.assertIn(label, buttons)
        buttons["Hard"].action()
        self.assertEqual(self.g.difficulty, "Hard")

    def test_menu_opens_the_instructions_and_back_returns_to_the_menu(self):
        self.buttons("menu")["INSTRUCTIONS"].action()
        self.assertEqual(self.g.screen, "instructions")
        buttons = self.buttons("instructions")
        self.assertEqual(list(buttons), ["PREVIOUS PAGE", "NEXT PAGE", "BACK"])
        self.assertFalse(buttons["PREVIOUS PAGE"].enabled)                   # first page
        self.assertTrue(buttons["NEXT PAGE"].enabled)
        for _ in range(instructions_data.PAGE_COUNT - 1):
            self.buttons("instructions")["NEXT PAGE"].action()
        buttons = self.buttons("instructions")
        self.assertTrue(buttons["PREVIOUS PAGE"].enabled)
        self.assertFalse(buttons["NEXT PAGE"].enabled)                       # last page
        buttons["BACK"].action()
        self.assertEqual(self.g.screen, "menu")

    # --- convoy screen
    def test_convoy_screen_has_its_core_buttons(self):
        buttons = self.buttons("convoy")
        for label in CORE_CONVOY_BUTTONS:
            self.assertIn(label, buttons)
        self.assertTrue(any(label.startswith("SITE:") for label in buttons))

    def test_repair_button_follows_damage_and_scrap(self):
        self.assertFalse(self.buttons("convoy")["REPAIR"].enabled)          # nothing to repair
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

    def test_convoy_screen_buttons_stay_inside_the_window_without_overlapping(self):
        rects = [b.rect for b in buttons_module.make_buttons(self.g)]
        for first, second in itertools.combinations(rects, 2):
            self.assertFalse(first.colliderect(second))
        for rect in rects:
            self.assertTrue(0 <= rect.left and rect.right <= layout.WIDTH)

    # --- map and vehicles screens
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
        self.assertTrue(self.buttons("vehicles")["ABANDON VEHICLE"].enabled)
        g.request_abandon("School Bus")
        self.assertIn("CONFIRM ABANDON", self.buttons("vehicles"))

    def test_owned_vehicles_offer_upgrades_and_the_others_offer_recovery(self):
        """NEW: written from the design notes (UPGRADE VEHICLE replaces RECOVER VEHICLE for owned vehicles)."""
        g = self.g
        g.selected_vehicle_type = "School Bus"                               # owned
        buttons = self.buttons("vehicles")
        self.assertIn("UPGRADE VEHICLE", buttons)
        self.assertNotIn("RECOVER VEHICLE", buttons)
        g.selected_vehicle_type = "Semi-Truck"                               # not owned
        buttons = self.buttons("vehicles")
        self.assertIn("RECOVER VEHICLE", buttons)
        self.assertNotIn("UPGRADE VEHICLE", buttons)

    # --- end screen
    def test_end_buttons_exist_only_after_the_run_ends(self):
        g = self.g
        self.assertEqual(buttons_module.make_end_buttons(g), [])
        g.status = "lost"
        buttons = {b.label: b for b in buttons_module.make_end_buttons(g)}
        self.assertIn("PLAY AGAIN [R]", buttons)
        self.assertIn("TITLE SCREEN", buttons)
        self.assertTrue(any(label.startswith("HISTORY") for label in buttons), "the end popup needs a HISTORY button")
        window = pygame.Rect(0, 0, layout.WIDTH, layout.HEIGHT)
        for button in buttons.values():
            self.assertTrue(window.contains(button.rect), button.label)
            self.assertTrue(button.enabled, button.label)
        for first, second in itertools.combinations(buttons.values(), 2):
            self.assertFalse(first.rect.colliderect(second.rect), f"{first.label} overlaps {second.label}")

    def test_end_buttons_restart_or_return_to_the_title(self):
        g = self.g
        g.begin_game()
        g.day, g.status = 9, "lost"
        {b.label: b for b in buttons_module.make_end_buttons(g)}["PLAY AGAIN [R]"].action()
        self.assertEqual((g.screen, g.status, g.day), ("convoy", "playing", 1))
        g.status = "won"
        {b.label: b for b in buttons_module.make_end_buttons(g)}["TITLE SCREEN"].action()
        self.assertEqual((g.screen, g.started, g.status), ("title", False, "playing"))

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


class ScreenDrawingTests(LayoutTestCase):
    def setUp(self):
        super().setUp()
        self.g = make_game()

    def test_hud_menu_and_instructions_screens_draw(self):
        g = self.g
        ui.draw_hud(surface(), g)
        g.screen = "menu"
        ui.draw_menu_screen(surface(), g, buttons_module.make_buttons(g))
        g.screen = "instructions"
        for page in range(instructions_data.PAGE_COUNT):
            g.instructions_page = page
            ui.draw_instructions_screen(surface(), g, buttons_module.make_buttons(g))

    def test_hud_draws_with_an_empty_convoy(self):
        self.g.vehicles = []
        ui.draw_hud(surface(), self.g)

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

    def test_event_log_keeps_four_messages_newest_first(self):
        g = self.g
        for number in range(10):
            g.say(f"message {number}")
        self.assertEqual(g.log, ["message 9", "message 8", "message 7", "message 6"])
        ui.draw_events(surface(), g)

    @needs_all_assets
    def test_title_and_lore_screens_draw(self):
        g = self.g
        g.screen = "title"
        ui.draw_title_screen(surface(), g, buttons_module.make_buttons(g))
        g.screen = "lore"
        ui.draw_lore_screen(surface(), g, buttons_module.make_buttons(g))

    @needs_vehicle_assets
    def test_vehicle_screen_draws(self):
        for name in vehicle_data.VEHICLE_SPECS:
            self.g.selected_vehicle_type = name
            self.g.screen = "vehicles"
            ui.draw_vehicles_screen(surface(), self.g, buttons_module.make_buttons(self.g))

    @needs_all_assets
    def test_convoy_screen_draws_in_every_horde_state(self):
        for gap in (500, 120, 40, 0):
            self.g.horde = gap
            ui.draw_scene(surface(), self.g)
            ui.draw_lower(surface(), self.g, buttons_module.make_buttons(self.g))


class ConvoyDrawingTests(unittest.TestCase):
    RED = (255, 0, 0)

    @staticmethod
    def lowest_red_row(canvas, x):
        for y in range(canvas.get_height() - 1, -1, -1):
            if tuple(canvas.get_at((x, y)))[:3] == ConvoyDrawingTests.RED:
                return y
        return None

    def test_vehicles_rest_on_the_road_whatever_their_image_height(self):
        """Different image heights must share one bottom edge, above the label (which starts at y=356)."""
        heights = {"Pickup Truck": 50, "Passenger Van": 60, "School Bus": 80}
        sprites = {}
        for name, height in heights.items():
            sprite = pygame.Surface((100, height))
            sprite.fill(self.RED)
            sprites[name] = sprite
        requested = []

        def fake_sprite(name, *args, **kwargs):
            requested.append(name)
            return sprites[name]

        canvas = surface()
        canvas.fill((0, 0, 0))
        scene = pygame.Rect(18, 125, layout.WIDTH - 36, 270)
        # Patch the function in whichever module draw_convoy_vehicles lives in (ui is now a package).
        owner = sys.modules[ui.draw_convoy_vehicles.__module__]
        with mock.patch.object(owner, "get_vehicle_sprite", side_effect=fake_sprite):
            ui.draw_convoy_vehicles(canvas, make_game(), scene)

        self.assertEqual(set(requested), set(heights), "a vehicle was not drawn")
        bottoms = {self.lowest_red_row(canvas, x) for x in range(canvas.get_width())} - {None}
        self.assertEqual(len(bottoms), 1, f"vehicles have different bottom edges: {sorted(bottoms)}")
        bottom = bottoms.pop()
        self.assertGreaterEqual(bottom, 330, "vehicles float too high above the road")
        self.assertLess(bottom, 356, "vehicles overlap the label row")

    def test_no_vehicles_draws_nothing(self):
        game = make_game()
        game.vehicles = []
        ui.draw_convoy_vehicles(surface(), game, pygame.Rect(18, 125, layout.WIDTH - 36, 270))
