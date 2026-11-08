"""Shared test helpers: folder paths, asset checks, fakes, map-layout pinning and the game/surface factories.

Everything here imports without pygame (the rule tests run headless); pygame is only imported inside surface().
"""
import importlib
import os
import unittest

import game as game_rules  # aliased: tests use `game` as a local name
import map_data
from game.null_audio import NullAudio

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(TESTS_DIR)

HAVE_VEHICLE_ASSETS = os.path.isdir(os.path.join(GAME_DIR, "assets", "vehicles"))
HAVE_ALL_ASSETS = (
    HAVE_VEHICLE_ASSETS
    and os.path.isfile(os.path.join(GAME_DIR, "assets", "backgrounds", "convoy_background.png"))
    and os.path.isfile(os.path.join(GAME_DIR, "assets", "zombies", "zombie.png"))
)
needs_vehicle_assets = unittest.skipUnless(HAVE_VEHICLE_ASSETS, "assets/vehicles folder not found")
needs_all_assets = unittest.skipUnless(HAVE_ALL_ASSETS, "assets folder not found or incomplete")

# Tests that name stops or distances of the map ("City 3", "100 km to City 1") run on this layout (1-based, as in
# map_data.choose_layout). Change it here if your default map is a different one.
PINNED_LAYOUT = 1

_IGNORED_FOLDERS = {"__pycache__", "venv", "env", "build", "dist", "site-packages"}


# ---------------------------------------------------------------------------------------------- project files
def project_python_files(include_tests=False):
    """Relative paths (with "/") of every .py file of the game, packages included. Tests only when asked for."""
    found = []
    for folder, subfolders, filenames in os.walk(GAME_DIR):
        subfolders[:] = [name for name in subfolders
                         if name not in _IGNORED_FOLDERS and not name.startswith(".")
                         and (include_tests or os.path.join(folder, name) != TESTS_DIR)]
        for filename in filenames:
            if filename.endswith(".py"):
                found.append(os.path.relpath(os.path.join(folder, filename), GAME_DIR).replace(os.sep, "/"))
    return sorted(found)


def read_sources():
    """The text of every game source file (tests excluded) joined together."""
    texts = []
    for relative in project_python_files():
        with open(os.path.join(GAME_DIR, relative), encoding="utf-8") as source:
            texts.append(source.read())
    return "\n".join(texts)


def import_first(*names):
    """Import and return the first module of `names` that exists.

    Some modules moved into the game/ package while others did not; this keeps the tests working with either
    layout. Once you know where a module lives, replace the call with a plain import.
    """
    for name in names:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError as error:
            if error.name != name:      # the module exists but one of ITS imports is missing: a real error
                raise
    raise ModuleNotFoundError(f"none of these modules exists: {', '.join(names)}")


# ------------------------------------------------------------------------------------------------------ fakes
class FakeEvents:
    """Stand-in for EventManager so travel tests don't depend on random events."""

    def __init__(self, opens_event=False):
        self.opens_event = opens_event
        self.active = False
        self.current_event = None
        self.result = None

    def start_for_arrival(self, game, trigger=None):
        """Ordinary travel events only (an ambush asks for trigger="ambush": none is shown, the automatic damage applies)."""
        if self.opens_event and trigger is None:
            self.active = True
            self.current_event = {"title": "Test", "description": "", "choices": [{"label": "OK"}]}
            return self.current_event
        return None

    def start_event(self, game, event_id, announce="Evacuation"):
        """The scripted evacuation events are not part of this fake: none opens (the evacuation then skips them)."""
        return None

    def show_result(self, title, choice, outcome, change_lines):
        """Used by scavenge(): the result popup."""
        self.result = {"title": title, "choice": choice, "outcome": outcome, "changes": change_lines}

    def resolve_choice(self, game, choice_index):
        self.active = False
        self.result = {"title": "Test", "choice": "OK", "outcome": "Event resolved.", "changes": []}
        return "Event resolved."

    def clear_result(self):
        self.result = None


class FakeResourceGame:
    """Just enough of Game for effect_handler's resource rules: four supplies, survivors and the horde gap."""

    def __init__(self, **values):
        self.fuel = self.food = self.water = self.scrap = 10
        self.survivors, self.horde, self.vehicles = 5, 20, []
        self.__dict__.update(values)

    def convoy_stats(self):
        return {"fuel_capacity": 15, "passengers": 8}


# ----------------------------------------------------------------------------------------------- factories
def make_game(opens_event=False, real_events=False):
    """A new game with silent audio. Its random events are replaced by FakeEvents unless real_events is True."""
    game = game_rules.Game(music=NullAudio(), sound=NullAudio())
    if not real_events:
        game.event_manager = FakeEvents(opens_event)
    return game


def surface():
    import pygame
    import layout
    return pygame.Surface((layout.WIDTH, layout.HEIGHT))


# -------------------------------------------------------------------------------------------- map layouts
class LayoutTestCase(unittest.TestCase):
    """Base class for tests that depend on the map: pins the layout for each test and restores it afterwards.

    The game can switch between several map layouts; without pinning, a test that names "City 3" would pass or
    fail depending on which layout an earlier test left active.
    """
    pinned_layout = PINNED_LAYOUT

    def setUp(self):
        super().setUp()
        saved = map_data.CURRENT_LAYOUT
        self.addCleanup(map_data.load_layout, saved)
        map_data.choose_layout(self.pinned_layout)

    def for_each_layout(self, check):
        """Activate every layout choose_layout() can pick (numbers are 1-based) and run check() on each one."""
        for number in range(1, len(map_data.LAYOUTS) + 1):
            map_data.choose_layout(number)
            with self.subTest(layout=map_data.layout_name()):
                check()
