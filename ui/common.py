"""Helpers shared by the UI modules of THE LAST CONVOY: colours of the full-window screens, the scaled-image
cache and wrapped-paragraph drawing. Drawing only."""
import pygame

from .pixel_art import whole_scale   # noqa: F401  (lives in pixel_art.py; also importable from here)
from theme import CARD_BG, SCREEN_BG, SMALL, WHITE   # CARD_BG / SCREEN_BG live in theme (they change with the palette)
from widgets import draw_text, wrap_pixels


# Scaled copies of the sprites, so each size is computed once instead of every frame.
_SCALED_CACHE = {}


_SCALED_CACHE_LIMIT = 96   # dragging the window edge produces many sizes; the least recently used are dropped


def scaled_image(key, image, size):
    """Return `image` resized to `size`, cached by (key, size); the original when no resizing is needed.

    `key` names the source image (for example ("vehicle", "School Bus")), so equal sizes of different
    images never share an entry. The cache keeps the most recently used copies, up to a fixed limit.
    """
    if image.get_size() == size:
        return image
    cache_key = (key, size)
    scaled = _SCALED_CACHE.pop(cache_key, None)
    if scaled is None:
        scaled = pygame.transform.scale(image, size)
    _SCALED_CACHE[cache_key] = scaled   # (re)inserted last, so the oldest entries come first
    while len(_SCALED_CACHE) > _SCALED_CACHE_LIMIT:
        del _SCALED_CACHE[next(iter(_SCALED_CACHE))]
    return scaled


def draw_paragraph(surface, string, x, y, width, color=WHITE, font=SMALL, limit=None):
    """Draw wrapped text (just measure it when surface is None); returns the y below it.

    With `limit`, lines that would end below that y are not drawn (the returned y is still the full height).
    """
    for line in wrap_pixels(string, font, width):
        if surface is not None and (limit is None or y + font.get_linesize() <= limit):
            draw_text(surface, line, x, y, color, font)
        y += font.get_linesize()
    return y


def wrap_items(items, font, width, separator=" "):
    """Join short items (such as "Seats 4") into lines no wider than `width`, never splitting an item."""
    lines, current = [], ""
    for item in items:
        trial = current + separator + item if current else item
        if current and font.size(trial)[0] > width:
            lines.append(current)
            current = item
        else:
            current = trial
    if current:
        lines.append(current)
    return lines
