"""Tests for event_ui.py: choice buttons (cost notes, greyed-out choices), clicks, result screen and the hover cursor."""

import unittest
from unittest import mock

import pygame

from game import event_data
import event_ui
import main

from tests.helpers import make_game, surface

needs_cursor_function = unittest.skipUnless(
    hasattr(main, "update_mouse_cursor"), "main.update_mouse_cursor not found (moved?): update tests/test_event_ui.py")

# Window sizes the popups must work in (the layout is computed from the window, not from fixed constants).
SIZES = ((800, 600), (1280, 720), (1920, 1080), (700, 900))


def make_surface(size):
    """A window-sized surface; falls back to the helper's own surface when it ignores the size."""
    try:
        return pygame.Surface(size)
    except pygame.error:
        return surface()


def default_size():
    return surface().get_size()


def choice(label, effects=None, **extra):
    return dict({"label": label, "outcome": "Done.", "effects": effects or []}, **extra)


SCRAP_PAY = choice("Pay the mechanic", [{"type": "resource", "resource": "scrap", "amount": -5}], payment=True)
WATER_HIT = choice("Get robbed", [{"type": "resource", "resource": "water", "amount": -12}])
FREE = choice("Drive on")


def event_of(*choices, title="Test event"):
    return {"title": title, "description": "Something happened on the road.", "choices": list(choices)}


class EventUiTests(unittest.TestCase):
    EVENT = {
        "title": "Test event",
        "description": "Something happened on the road.",
        "choices": [{"label": "First"}, {"label": "Second"}, {"label": "Third"}],
    }
    RESULT = {"title": "Test event", "choice": "First", "outcome": "It went fine.",
              "changes": [("Food +3", True), ("Survivors -1", False)]}

    def setUp(self):
        self.size = default_size()

    def cursor_when_hovering(self, buttons, position):
        """The cursor main.update_mouse_cursor picks with the mouse at `position`."""
        with mock.patch("pygame.mouse.get_pos", return_value=position), \
                mock.patch("pygame.mouse.set_cursor") as set_cursor:
            main.update_mouse_cursor(buttons)
        self.assertTrue(set_cursor.called, "the cursor was never set")
        return set_cursor.call_args[0][0]

    # --- choice buttons
    def test_one_button_per_choice(self):
        buttons = event_ui.make_event_buttons(self.EVENT, self.size)
        self.assertEqual(len(buttons), 3)
        for number, (button, c) in enumerate(zip(buttons, self.EVENT["choices"]), start=1):
            self.assertTrue(button.label.startswith(f"{number}."))
            self.assertIn(c["label"], button.label)

    def test_click_returns_the_choice_index(self):
        for index, button in enumerate(event_ui.make_event_buttons(self.EVENT, self.size)):
            self.assertEqual(event_ui.handle_event_click(button.rect.center, self.EVENT, self.size), index)

    def test_click_outside_returns_none(self):
        self.assertIsNone(event_ui.handle_event_click((0, 0), self.EVENT, self.size))

    def test_buttons_do_not_overlap_and_stay_on_screen_at_every_window_size(self):
        for count in (1, 2, 3, 4):
            event = event_of(*[choice(str(i)) for i in range(count)])
            for size in SIZES:
                with self.subTest(choices=count, size=size):
                    rects = [b.rect for b in event_ui.make_event_buttons(event, size)]
                    self.assertEqual(len(rects), count)
                    for i, first in enumerate(rects):
                        self.assertTrue(0 <= first.left and first.right <= size[0]
                                        and 0 <= first.top and first.bottom <= size[1], (first, size))
                        for second in rects[i + 1:]:
                            self.assertFalse(first.colliderect(second))

    def test_event_without_choices(self):
        event = {"title": "Empty", "choices": []}
        self.assertEqual(event_ui.make_event_buttons(event, self.size), [])
        self.assertIsNone(event_ui.handle_event_click((500, 400), event, self.size))

    def test_overlay_draws_without_error(self):
        event_ui.draw_event_overlay(surface(), self.EVENT)
        for event in event_data.EVENTS:
            with self.subTest(event=event["id"]):
                event_ui.draw_event_overlay(surface(), event)

    def test_overlay_draws_for_a_real_game_and_at_every_window_size(self):
        game = make_game()
        for size in SIZES:
            for event in event_data.EVENTS:
                with self.subTest(event=event["id"], size=size):
                    event_ui.draw_event_overlay(make_surface(size), event, game=game)

    def test_overlay_uses_the_buttons_it_is_given(self):
        game = make_game()
        buttons = event_ui.make_event_buttons(self.EVENT, self.size, game)
        event_ui.draw_event_overlay(surface(), self.EVENT, buttons, game)

    # --- cost and effect notes on the buttons
    def test_a_payment_shows_its_cost(self):
        game = make_game()
        game.scrap = 20
        label = event_ui.make_event_buttons(event_of(SCRAP_PAY, FREE), self.size, game)[0].label
        self.assertIn("-5 scrap", label)

    def test_a_penalty_shows_lose_up_to(self):
        game = make_game()
        label = event_ui.make_event_buttons(event_of(WATER_HIT, FREE), self.size, game)[0].label
        self.assertIn("lose up to 12 water", label)

    def test_effect_notes_without_a_game(self):
        notes = {
            "-13% HP": {"type": "vehicle_damage_pct", "amount": 13},
            "-2 survivors": {"type": "survivors", "amount": -2},
            "-1 survivor": {"type": "survivors", "amount": -1},
            "lose a vehicle": {"type": "vehicle_loss"},
            "new vehicle": {"type": "vehicle_gain"},
        }
        for text, effect in notes.items():
            with self.subTest(note=text):
                label = event_ui.make_event_buttons(event_of(choice("Act", [effect]), FREE), self.size)[0].label
                self.assertIn(text, label)

    def test_gains_and_no_effects_add_no_note(self):
        label = event_ui.make_event_buttons(
            event_of(choice("Search", [{"type": "resource", "resource": "food", "amount": 3}]), FREE), self.size)[0].label
        self.assertNotIn("[", label)

    # --- greyed-out choices
    def test_an_unaffordable_payment_cannot_be_clicked(self):
        game = make_game()
        game.scrap = 1
        event = event_of(SCRAP_PAY, FREE)
        buttons = event_ui.make_event_buttons(event, self.size, game)
        self.assertIsNone(event_ui.handle_event_click(buttons[0].rect.center, event, self.size, game))
        self.assertEqual(event_ui.handle_event_click(buttons[1].rect.center, event, self.size, game), 1)

    def test_an_unaffordable_payment_says_what_is_missing(self):
        game = make_game()
        game.scrap = 1
        label = event_ui.make_event_buttons(event_of(SCRAP_PAY, FREE), self.size, game)[0].label
        self.assertIn("need 5 scrap, have 1", label)
        self.assertNotIn("-5 scrap", label)

    def test_without_a_game_every_choice_can_be_clicked(self):
        event = event_of(SCRAP_PAY, FREE)
        for index, button in enumerate(event_ui.make_event_buttons(event, self.size)):
            self.assertEqual(event_ui.handle_event_click(button.rect.center, event, self.size), index)

    def test_a_choice_with_an_unmet_requirement_is_locked_and_explained(self):
        game = make_game()
        locked = choice("Sacrifice a vehicle", [{"type": "vehicle_loss"}], requires={"vehicles_at_least": 99})
        event = event_of(locked, FREE)
        buttons = event_ui.make_event_buttons(event, self.size, game)
        self.assertIn("needs 99+ vehicles", buttons[0].label)
        self.assertIsNone(event_ui.handle_event_click(buttons[0].rect.center, event, self.size, game))

    def test_when_nothing_can_be_picked_nobody_is_stuck(self):
        game = make_game()
        game.scrap = 0
        event = event_of(SCRAP_PAY, dict(SCRAP_PAY, label="Pay double"))
        for index, button in enumerate(event_ui.make_event_buttons(event, self.size, game)):
            self.assertEqual(event_ui.handle_event_click(button.rect.center, event, self.size, game), index)

    def test_a_long_label_keeps_the_cost_note(self):
        game = make_game()
        game.scrap = 20
        long_pay = dict(SCRAP_PAY, label="Pay the mechanic a very long explanation of why this costs so much " * 3)
        label = event_ui.make_event_buttons(event_of(long_pay, FREE), (800, 600), game)[0].label
        self.assertTrue(label.endswith("[-5 scrap]"), label)

    # --- result screen
    def test_result_screen_has_one_ok_button_inside_the_window(self):
        for size in SIZES:
            with self.subTest(size=size):
                buttons = event_ui.make_result_buttons(self.RESULT, size)
                self.assertEqual(len(buttons), 1)
                self.assertTrue(buttons[0].label.startswith("OK"))
                self.assertTrue(0 <= buttons[0].rect.left and buttons[0].rect.right <= size[0])
                self.assertTrue(0 <= buttons[0].rect.top and buttons[0].rect.bottom <= size[1])

    def test_result_screen_click(self):
        button = event_ui.make_result_buttons(self.RESULT, self.size)[0]
        self.assertTrue(event_ui.handle_result_click(button.rect.center, self.RESULT, self.size))
        self.assertFalse(event_ui.handle_result_click((0, 0), self.RESULT, self.size))

    def test_result_screen_draws_with_any_amount_of_content(self):
        long_result = {"title": "T", "choice": "C", "outcome": "A long outcome. " * 30,
                       "changes": [(f"Thing {i} +{i}", i % 2 == 0) for i in range(12)]}
        for size in SIZES:
            with self.subTest(size=size):
                event_ui.draw_event_result_overlay(make_surface(size), self.RESULT)
                event_ui.draw_event_result_overlay(make_surface(size), {"title": "T", "changes": []})
                event_ui.draw_event_result_overlay(make_surface(size), long_result)

    def test_result_screen_uses_the_buttons_it_is_given(self):
        buttons = event_ui.make_result_buttons(self.RESULT, self.size)
        event_ui.draw_event_result_overlay(surface(), self.RESULT, buttons)

    # --- how the result text is planned (event_ui._plan_result)
    def plan(self, result, width=400, height=300):
        font, plan = event_ui._plan_result(result, width, height)
        return plan

    def test_plan_lists_choice_outcome_heading_and_changes(self):
        plan = self.plan(self.RESULT)
        kinds = [kind for _text, _colour, kind in plan]
        self.assertEqual(plan[0][0], "You chose: First")
        self.assertIn("outcome", kinds)
        self.assertEqual(kinds.count("heading"), 1)
        self.assertEqual([text for text, _c, kind in plan if kind == "change"], ["Food +3", "Survivors -1"])
        self.assertNotIn("more", kinds)

    def test_plan_without_changes_says_no_lasting_effect(self):
        plan = self.plan({"title": "T", "outcome": "Nothing.", "changes": []})
        self.assertIn("No lasting effect.", [text for text, _c, _k in plan])

    def test_plan_without_a_choice_has_no_you_chose_line(self):
        plan = self.plan({"title": "T", "choice": "", "outcome": "Nothing.", "changes": []})
        self.assertNotIn("chosen", [kind for _t, _c, kind in plan])

    def test_plan_without_an_outcome_uses_the_default(self):
        plan = self.plan({"title": "T", "changes": []})
        self.assertIn("The convoy moves on.", " ".join(text for text, _c, kind in plan if kind == "outcome"))

    def test_plan_shortens_a_long_result_list_and_says_so(self):
        result = {"title": "T", "outcome": "Short.", "changes": [(f"Thing {i} +1", True) for i in range(30)]}
        plan = self.plan(result, 300, 110)
        more = [text for text, _c, kind in plan if kind == "more"]
        shown = [text for text, _c, kind in plan if kind == "change"]
        self.assertEqual(len(more), 1)
        self.assertRegex(more[0], r"^\+\d+ more$")
        self.assertEqual(int(more[0][1:].split()[0]) + len(shown), 30)   # nothing silently dropped

    def test_plan_cuts_a_long_outcome_visibly(self):
        result = {"title": "T", "outcome": "A very long outcome sentence. " * 40, "changes": [("Food +1", True)]}
        plan = self.plan(result, 300, 110)
        outcome_lines = [text for text, _c, kind in plan if kind == "outcome"]
        self.assertTrue(outcome_lines[-1].endswith("..."), outcome_lines[-1])

    def test_plan_colours_good_and_bad_changes(self):
        colours = {text: colour for text, colour, kind in self.plan(self.RESULT) if kind == "change"}
        self.assertNotEqual(colours["Food +3"], colours["Survivors -1"])

    # --- hover cursor
    @needs_cursor_function
    def test_result_screen_buttons_get_the_hand_cursor(self):
        buttons = event_ui.make_result_buttons(self.RESULT, self.size)
        self.assertEqual(self.cursor_when_hovering(buttons, buttons[0].rect.center), pygame.SYSTEM_CURSOR_HAND)

    @needs_cursor_function
    def test_hand_cursor_over_event_buttons_only(self):
        buttons = event_ui.make_event_buttons(self.EVENT, self.size)
        self.assertEqual(self.cursor_when_hovering(buttons, buttons[1].rect.center), pygame.SYSTEM_CURSOR_HAND)
        self.assertEqual(self.cursor_when_hovering(buttons, (0, 0)), pygame.SYSTEM_CURSOR_ARROW)