"""Runs ALL automated tests for THE LAST CONVOY. Keep this file in the game folder, next to main.py.

How to run:
    python test_convoy.py                                         (everything)
    python -m unittest test_convoy -v                             (everything, same thing)
    python -m unittest tests.test_events -v                       (one file only)
    python -m unittest tests.test_events.EventManagerTests -v     (one group only)

The tests themselves live in the tests/ folder, one test_*.py file per area, and are found automatically:
a new tests/test_something.py is picked up without editing this file. Shared helpers are in tests/helpers.py.

The tests run headless (SDL's dummy video driver and silent audio), so no game window opens. Random events and
random rolls are replaced by controlled stand-ins wherever a result must be repeatable. Tests that name stops or
distances of the map run on a pinned map layout (PINNED_LAYOUT in tests/helpers.py), and the save tests write to
a temporary folder, never the player's own saves.

Coverage:
- tests/test_game_rules.py ..... the game rules: flow, statistics, difficulty, horde, convoy, survival, sites,
                                 travel, victory (GameFlowTests, RunStatisticsTests, DifficultyTests, HordeTests,
                                 ConvoyTests, SurvivalTests, SiteTests, TravelTests)
- tests/test_effects.py ........ effect_handler.py: every effect type, losses, payments, data validators
                                 (ApplyEffectsTests, ResourceLossTests, PaymentTests, ValidatorTests)
- tests/test_events.py ......... event_data.py and the event manager: data, selection, results, requirements
                                 (EventDataTests, EventManagerTests, EventEligibilityTests)
- tests/test_event_ui.py ....... event_ui.py: choice buttons, clicks, result screen, hover cursor (EventUiTests)
- tests/test_map.py ............ map_data.py and map_system.py: map data, sites, roads, pathfinding, drawing
                                 (MapSystemTests, SiteDataTests)
- tests/test_missions.py ....... missions: every destination reachable on every layout, prerequisites, rewards
                                 (DestinationMissionTests, MissionDataTests)
- tests/test_vehicles.py ....... vehicle_data.py, vehicle_rendering.py and the upgrade rules (VehicleDataTests,
                                 VehicleSpriteTests, UpgradeCatalogueTests, VehicleUpgradeTests, GameUpgradeTests)
- tests/test_layouts.py ........ window-pixel layouts of every screen and popup at many window sizes
                                 (ScreenLayoutTests, ListScreenLayoutTests)
- tests/test_screens.py ........ buttons.py and ui screens: title, lore, menu, instructions, convoy, ending,
                                 vehicle placement (ScreenButtonTests, ScreenDrawingTests, ConvoyDrawingTests)
- tests/test_history.py ........ the history log and its screen navigation (HistoryLogTests,
                                 HistoryNavigationTests)
- tests/test_savegame.py ....... savegame.py: slots, round trip, damaged files (SaveGameTests, DamagedSaveTests)
- tests/test_helpers.py ........ widgets.py, layout.py, config.py helpers (HelperTests)
- tests/test_text_data.py ...... instructions_data.py and story_data.py (InstructionsTextTests, StoryTextTests)
- tests/test_headless_game.py .. the game rules work without pygame or settings (HeadlessGameTests)
- tests/test_abilities.py ...... vehicle special abilities (AbilityDataTests, ReinforcedProtectionTests,
                                 RecoverySupportTests)
- tests/test_achievements.py ... achievement tracker, saved progress, screen layout (function tests)
- tests/test_backgrounds.py .... player background abilities (BackgroundRulesTest, SmokeTest)
- tests/test_background_icons.py background icons: files and layout (function tests)
- tests/test_scenery.py ........ desert / highway scenery on every map layout (function test)
- tests/test_structure.py ...... no star imports, README version and file list (StructureTests, ReadmeTests)
Tests that need the PNG files in assets/ are skipped automatically when that folder is missing.
"""
import importlib
import os
import types
import unittest

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.join(GAME_DIR, "tests")


def _function_tests():
    """Module-level test_* functions (pytest style), which unittest discovery ignores."""
    suite = unittest.TestSuite()
    for filename in sorted(os.listdir(TESTS_DIR)):
        if not (filename.startswith("test_") and filename.endswith(".py")):
            continue
        name = "tests." + filename[:-3]
        try:
            module = importlib.import_module(name)
        except Exception:
            continue   # discover() already reports this import failure
        for attr in sorted(dir(module)):
            func = getattr(module, attr)
            if (attr.startswith("test_") and isinstance(func, types.FunctionType)
                    and func.__module__ == module.__name__):
                suite.addTest(unittest.FunctionTestCase(func, description=f"{name}.{attr}"))
    return suite


def load_tests(loader, standard_tests, pattern):
    """Collect every tests/test_*.py file (this is what makes `python -m unittest test_convoy` run them all).

    Test classes are found by discovery; plain module-level test_* functions are added by _function_tests().
    """
    suite = loader.discover(TESTS_DIR, pattern="test_*.py", top_level_dir=GAME_DIR)
    suite.addTests(_function_tests())
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
