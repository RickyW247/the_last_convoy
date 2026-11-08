"""The game rules must work without pygame, a display or settings.json (what the README promises).

Each check runs in a fresh interpreter in which pygame (and, where stated, settings_store) cannot be imported.
"""
import subprocess
import sys
import unittest

from tests.helpers import GAME_DIR

BLOCK_PYGAME = (
    "import importlib.abc, sys\n"
    "class Block(importlib.abc.MetaPathFinder):\n"
    "    def find_spec(self, name, path, target=None):\n"
    "        if name == 'pygame' or name.startswith('pygame.'):\n"
    "            raise ImportError('pygame is blocked')\n"
    "sys.meta_path.insert(0, Block())\n"
)
BLOCK_SETTINGS = "sys.modules['settings_store'] = None\n"


def run_python(code, block_settings=False):
    prelude = BLOCK_PYGAME + (BLOCK_SETTINGS if block_settings else "")
    return subprocess.run([sys.executable, "-c", prelude + code], cwd=GAME_DIR, capture_output=True, text=True)


class HeadlessGameTests(unittest.TestCase):
    def test_rule_and_data_modules_import_without_pygame(self):
        result = run_python(
            "import game, game.effect_handler, game.mission_manager\n"
            "import config, map_data, instructions_data, event_data, vehicle_data, upgrade_data\n"
            "assert 'pygame' not in sys.modules\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_game_can_be_created_without_pygame(self):
        result = run_python("import game\ngame.Game()\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_game_runs_with_null_audio_and_no_settings_file_module(self):
        code = ("from game import Game\n"
                "from game.null_audio import NullAudio\n"
                "game = Game(music=NullAudio(), sound=NullAudio())\n"
                "assert game.status == 'playing' and not game.music_muted\n"
                "assert ('play_music', ('menu',)) in game.music_manager.calls\n")
        result = run_python(code, block_settings=True)
        self.assertEqual(result.returncode, 0, result.stderr)
