"""Tests for instructions_data.py and story_data.py."""

import re
import unittest

import instructions_data
import story_data

from tests.helpers import read_sources


class InstructionsTextTests(unittest.TestCase):
    def test_instructions_text_is_complete(self):
        self.assertGreaterEqual(instructions_data.PAGE_COUNT, 2)
        self.assertTrue(all(instructions_data.MISSION))
        for key, action in instructions_data.CONTROLS:
            self.assertTrue(key and action)
        for label, description in instructions_data.HOW_TO_PLAY:
            self.assertTrue(label and description)
        self.assertTrue(instructions_data.HOW_TO_PLAY_OUTRO)

    def test_instructions_do_not_mention_removed_controls(self):
        text = " ".join(key + action for key, action in instructions_data.CONTROLS)
        self.assertNotIn("0–5", text)
        self.assertNotIn("settings", text.lower())

    def test_every_documented_key_is_handled_somewhere_in_the_game(self):
        code = read_sources()
        for name in ("K_RETURN", "K_m", "K_s", "K_r", "K_o", "K_ESCAPE", "K_TAB", "K_LEFT", "K_RIGHT", "K_1"):
            self.assertTrue(re.search(rf"\b{name}\b", code), f"no source file handles {name}")


class StoryTextTests(unittest.TestCase):
    def test_story_text(self):
        self.assertTrue(story_data.GAME_TITLE)
        self.assertTrue(story_data.TAGLINE)
        self.assertTrue(story_data.LORE_TITLE)
        self.assertGreaterEqual(len(story_data.LORE), 3)
        self.assertTrue(all(story_data.LORE))
        self.assertIn("west", " ".join(story_data.LORE).lower())
        self.assertIn("coast", " ".join(story_data.LORE).lower())
