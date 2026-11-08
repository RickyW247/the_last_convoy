"""Automated tests for THE LAST CONVOY, split by area (one test_*.py file per area).

Run everything from the game folder (the folder that contains tests/):

    python -m unittest                      # all tests
    python -m unittest tests.test_effects   # one file
    python -m unittest tests.test_effects.PaymentTests.test_is_payment   # one test
    python -m pytest tests                  # pytest works too, if it is installed

Importing this package prepares the environment for every test file: the game folder (the parent of this
folder) is put on the import path, and SDL is switched to its dummy drivers so no window or sound opens.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _GAME_DIR not in sys.path:
    sys.path.insert(0, _GAME_DIR)
