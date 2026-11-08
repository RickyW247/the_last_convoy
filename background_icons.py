"""Loads and scales the player-background icons (assets/icons/<background>_icon.png, 512 x 512 PNG), e.g. military_icon.png.
Like vehicle_rendering.py it loads assets and does not draw. Nothing is loaded at import time, so headless tests are fine."""
from pathlib import Path

import pygame

ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"

_sources = {}   # background name -> full-size Surface, or None when the file is missing / unreadable
_scaled = {}    # background name -> (side, Surface): only the latest size is kept, so resizing the window does not pile up copies


def icon_path(background):
    return ICON_DIR / f"{background.lower()}_icon.png"


def _source(background):
    if background not in _sources:
        try:
            image = pygame.image.load(str(icon_path(background)))
            _sources[background] = image.convert_alpha() if pygame.display.get_surface() else image
        except (pygame.error, FileNotFoundError, OSError):
            _sources[background] = None
    return _sources[background]


def get_icon(background, side):
    """The background's icon scaled to side x side pixels (smooth, the art is far larger than it is drawn), or None."""
    src = _source(background)
    if src is None or side < 1:
        return None
    cached = _scaled.get(background)
    if cached is None or cached[0] != side:
        cached = (side, pygame.transform.smoothscale(src, (side, side)))
        _scaled[background] = cached
    return cached[1]
