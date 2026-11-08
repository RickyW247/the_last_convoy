"""Tests for the history log and the history rules of the screen navigation (on a bare mixin, no game needed)."""

import unittest

from game.navigation import NavigationMixin

from tests.helpers import import_first

history_log = import_first("game.history_log", "history_log")


class HistoryLogTests(unittest.TestCase):
    def test_header_names_the_day_and_place(self):
        self.assertEqual(history_log.header(8, "City 4"), "Day 8 - City 4")

    def test_rows_are_grouped_by_day_and_place_newest_first(self):
        entries = []
        history_log.add_entry(entries, 8, "City 4", "A")
        history_log.add_entry(entries, 8, "City 4", "B")
        history_log.add_entry(entries, 9, "On the road", "C")
        history_log.add_entry(entries, 9, "City 5", "D")
        history_log.add_entry(entries, 9, "City 5", "E")
        self.assertEqual(history_log.history_rows(entries), [
            ("header", "Day 9 - City 5"), ("line", "E"), ("line", "D"),
            ("header", "Day 9 - On the road"), ("line", "C"),
            ("header", "Day 8 - City 4"), ("line", "B"), ("line", "A")])

    def test_empty_history_has_no_rows(self):
        self.assertEqual(history_log.history_rows([]), [])

    def test_history_is_capped_and_keeps_the_newest_entries(self):
        entries = []
        limit = history_log.HISTORY_LIMIT
        for i in range(limit + 50):
            history_log.add_entry(entries, 1, "X", str(i))
        self.assertEqual(len(entries), limit)
        self.assertEqual(entries[-1]["text"], str(limit + 49))

    def test_scroll_is_clamped_to_the_rows(self):
        clamp = history_log.clamp_scroll
        self.assertEqual(clamp(-3, 10, 4), 0)
        self.assertEqual(clamp(99, 10, 4), 6)
        self.assertEqual(clamp(5, 3, 4), 0)       # fewer rows than fit: no scrolling


class EventManagerStub:
    active = False
    result = None


class Navigator(NavigationMixin):
    """The mixin on a bare object, standing on the vehicles screen."""
    status = "playing"
    site_picker = False
    abandon_confirm = None
    history_scroll = 5
    history_return = "convoy"

    def __init__(self, screen="vehicles"):
        self._screen = screen
        self.event_manager = EventManagerStub()


class HistoryNavigationTests(unittest.TestCase):
    def test_opening_history_remembers_where_it_came_from(self):
        g = Navigator()
        g.toggle_history()
        self.assertEqual(g.screen, "history")
        self.assertEqual(g.history_return, "vehicles")
        self.assertEqual(g.history_scroll, 0)

    def test_toggling_again_returns_to_that_screen(self):
        g = Navigator()
        g.toggle_history()
        g.toggle_history()
        self.assertEqual(g.screen, "vehicles")

    def test_history_never_opens_over_an_event_popup(self):
        g = Navigator()
        g.event_manager.active = True
        g.toggle_history()
        self.assertEqual(g.screen, "vehicles")

    def test_history_does_not_open_from_the_menu(self):
        g = Navigator(screen="menu")
        g.toggle_history()
        self.assertEqual(g.screen, "menu")

    def test_scrolling_never_goes_above_the_first_row(self):
        g = Navigator(screen="history")
        g.scroll_history(-9)
        self.assertEqual(g.history_scroll, 0)
