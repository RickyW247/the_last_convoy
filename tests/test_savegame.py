"""Tests for savegame.py: saving, loading, damaged files and slot summaries.

Every test saves into its own temporary folder, never the player's own save folder.
"""
import json
import tempfile
import unittest
from unittest import mock

import savegame

from tests.helpers import LayoutTestCase, make_game


def new_game():
    """A started game with real events, standing on the convoy screen."""
    g = make_game(real_events=True)
    g.started = True
    g.status = "playing"
    g.screen = "convoy"
    return g


def state_of(game):
    """The saved state of a game, normalised the way a file round trip would (tuples become lists)."""
    return json.loads(json.dumps(savegame.to_dict(game)["state"]))


def write_slot(slot, text):
    with open(savegame.slot_path(slot), "w", encoding="utf-8") as handle:
        handle.write(text)


class SaveGameTestCase(LayoutTestCase):
    """Base class: saves go to a temporary folder that is removed after each test.

    (LayoutTestCase because loading a save can switch the map layout; it is restored afterwards.)
    """

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory(prefix="convoy-saves-")
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.object(savegame, "SAVE_DIR", folder.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        savegame.refresh_summaries()


class SaveGameTests(SaveGameTestCase):
    def test_empty_slots(self):
        self.assertEqual(savegame.slot_summaries(), [None, None, None])

    def test_round_trip(self):
        g1 = new_game()
        ok, _message = savegame.save_slot(g1, 0)
        self.assertTrue(ok)
        summary = savegame.slot_summaries()[0]
        self.assertTrue(summary)
        self.assertFalse(summary["damaged"])
        self.assertEqual(summary["day"], g1.day)
        g2 = new_game()
        ok, _message = savegame.load_slot(g2, 0)
        self.assertTrue(ok)
        self.assertEqual(state_of(g1), state_of(g2))
        self.assertEqual(g2.screen, "convoy")

    def test_deleting_a_save_empties_its_slot(self):
        savegame.save_slot(new_game(), 0)
        savegame.delete_slot(0)
        savegame.refresh_summaries()
        self.assertIsNone(savegame.slot_summaries()[0])

    def test_save_problem(self):
        not_started = make_game(real_events=True)
        not_started.started = False
        self.assertTrue(savegame.save_problem(not_started))
        self.assertFalse(savegame.save_problem(new_game()))


class DamagedSaveTests(SaveGameTestCase):
    """A bad file is reported as damaged and loading it must leave the game exactly as it was."""

    def assert_load_fails_and_changes_nothing(self, slot):
        g = new_game()
        before = state_of(g)
        ok, _message = savegame.load_slot(g, slot)
        self.assertFalse(ok)
        self.assertEqual(state_of(g), before)

    def test_unreadable_and_unknown_version_files_are_damaged(self):
        for slot, text in ((1, "not json"), (2, json.dumps({"version": 999}))):
            with self.subTest(slot=slot):
                write_slot(slot, text)
                savegame.refresh_summaries()
                self.assertTrue(savegame.slot_summaries()[slot]["damaged"])
                self.assert_load_fails_and_changes_nothing(slot)

    def test_bad_content_changes_nothing(self):
        savegame.save_slot(new_game(), 0)
        path = savegame.slot_path(0)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["state"]["vehicles"] = [{"type": "no such vehicle"}]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        savegame.refresh_summaries()
        self.assert_load_fails_and_changes_nothing(0)

    def test_loading_an_empty_slot_fails_and_changes_nothing(self):
        """NEW: written from the expected behaviour, not from savegame.py's source."""
        self.assert_load_fails_and_changes_nothing(0)
