"""Tests for the small helpers in widgets.py, layout.py and config.py."""

import unittest

import config
import layout
import theme
import widgets

from tests.helpers import surface


class HelperTests(unittest.TestCase):
    def test_wrap_text(self):
        self.assertEqual(widgets.wrap_text("", 10), [])
        self.assertEqual(widgets.wrap_text("a b c", 3), ["a b", "c"])
        text = "the quick brown fox jumps over the lazy dog " * 5
        lines = widgets.wrap_text(text, 20)
        self.assertEqual(" ".join(lines).split(), text.split())            # no words lost or changed
        self.assertTrue(all(len(line) <= 20 for line in lines))

    def test_people(self):
        self.assertEqual(config.people(1), "1 survivor")
        self.assertEqual(config.people(2), "2 survivors")

    def test_clamp(self):
        self.assertEqual((widgets.clamp(5, 0, 3), widgets.clamp(-1, 0, 3), widgets.clamp(2, 0, 3)), (3, 0, 2))

    def test_zombie_slots(self):
        slots = layout.ZOMBIE_SLOTS   # (x, y) as fractions of the convoy scene rectangle (964 x 270 reference, drawn at 18, 125)
        self.assertEqual(len(slots), 18)
        x_lo, x_hi = (690 - 18) / 964, (960 - 18) / 964
        y_lo, y_hi = (300 - 125) / 270, (334 - 125) / 270
        self.assertTrue(all(x_lo - 1e-9 <= x <= x_hi + 1e-9 and y_lo - 1e-9 <= y <= y_hi + 1e-9 for x, y in slots))
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
