"""Colours and fonts for THE LAST CONVOY."""
import os

import pygame

import textscale

pygame.font.init()


class Colour(list):
    """An RGB colour that can be changed in place. pygame accepts it anywhere it accepts a colour, and because every
    module imports the same object, set_accessibility() recolours the whole game at once. It compares and hashes
    like the equivalent tuple, so old code that compares colours or uses them as keys keeps working."""

    def __eq__(self, other):
        try:
            return tuple(self) == tuple(other)
        except TypeError:
            return False

    def __ne__(self, other):
        return not self == other

    __hash__ = lambda self: hash(tuple(self))   # noqa: E731  (a list is unhashable by default)


# The normal palette. Everything the screens draw with a name from this table is recoloured by set_accessibility.
_NORMAL = {
    "BG": (22, 27, 31),
    "PANEL": (35, 43, 48),
    "PANEL_LIGHT": (48, 58, 63),
    "WHITE": (235, 235, 222),
    "MUTED": (165, 176, 174),
    "GREEN": (116, 178, 105),
    "YELLOW": (226, 190, 93),
    "RED": (205, 91, 82),
    "ROAD": (61, 65, 65),
    "ROAD_LINE": (197, 185, 142),
    "DARK": (15, 18, 20),
    "BLUE": (100, 155, 190),
    "ORANGE": (211, 132, 74),
    "SCREEN_BG": (24, 34, 35),     # the full-window screens
    "CARD_BG": (29, 38, 40),
    "BORDER": (94, 108, 111),      # button and bar outlines
    "DISABLED_BG": (55, 59, 59),
    "DISABLED_TEXT": (112, 119, 116),
}

# Colour-blind safe: the Okabe-Ito colours. Good / warning / bad / danger no longer rely on red against green: they
# are blue, yellow, orange and reddish purple, which differ in brightness as well as hue. (The screens also add words
# and symbols, so colour is never the only signal.)
_COLORBLIND = {
    "GREEN": (86, 180, 233),
    "YELLOW": (240, 228, 66),
    "ORANGE": (230, 159, 0),
    "RED": (204, 121, 167),
    "BLUE": (0, 114, 178),
}

# High contrast: black backgrounds, bright text, stronger outlines, readable disabled buttons.
_HIGH_CONTRAST = {
    "BG": (0, 0, 0),
    "PANEL": (14, 17, 19),
    "PANEL_LIGHT": (52, 62, 68),
    "WHITE": (255, 255, 255),
    "MUTED": (222, 229, 227),
    "DARK": (0, 0, 0),
    "SCREEN_BG": (0, 0, 0),
    "CARD_BG": (12, 15, 17),
    "BORDER": (200, 210, 208),
    "DISABLED_BG": (30, 33, 33),
    "DISABLED_TEXT": (170, 176, 174),
}

_PALETTE = {name: Colour(rgb) for name, rgb in _NORMAL.items()}
BG, PANEL, PANEL_LIGHT, WHITE, MUTED = (_PALETTE[n] for n in ("BG", "PANEL", "PANEL_LIGHT", "WHITE", "MUTED"))
GREEN, YELLOW, RED, ROAD, ROAD_LINE = (_PALETTE[n] for n in ("GREEN", "YELLOW", "RED", "ROAD", "ROAD_LINE"))
DARK, BLUE, ORANGE = (_PALETTE[n] for n in ("DARK", "BLUE", "ORANGE"))
SCREEN_BG, CARD_BG, BORDER = (_PALETTE[n] for n in ("SCREEN_BG", "CARD_BG", "BORDER"))
DISABLED_BG, DISABLED_TEXT = _PALETTE["DISABLED_BG"], _PALETTE["DISABLED_TEXT"]

HORDE_STATE_COLORS = {"Distant": GREEN, "Approaching": YELLOW, "Close": ORANGE, "Overrun": RED}

ACCESS = {"high_contrast": False, "colorblind": False}   # the accessibility options currently on


def set_accessibility(high_contrast=None, colorblind=None):
    """Turn the high-contrast and colour-blind palettes on or off (None leaves an option as it is) and recolour the
    shared colour objects in place. Returns ACCESS."""
    if high_contrast is not None:
        ACCESS["high_contrast"] = bool(high_contrast)
    if colorblind is not None:
        ACCESS["colorblind"] = bool(colorblind)
    colours = dict(_NORMAL)
    if ACCESS["colorblind"]:
        colours.update(_COLORBLIND)
    if ACCESS["high_contrast"]:
        colours.update({k: v for k, v in _HIGH_CONTRAST.items() if not (ACCESS["colorblind"] and k in _COLORBLIND)})
    for name, rgb in colours.items():
        _PALETTE[name][:] = rgb
    return ACCESS


# Consolas only ships with Windows and Office. pygame's SysFont takes a comma-separated list and uses the first one
# that is installed: Consolas (Windows), DejaVu Sans Mono (most Linux), Menlo (macOS), Liberation Mono and Courier New
# as last resorts. If none is installed pygame falls back to its default font, which is not monospaced.
MONO_FONTS = "consolas,dejavusansmono,menlo,liberationmono,couriernew"


# Pixel-art look. PIXEL_TEXT draws text without smoothing (hard-edged letters). If a pixel font file exists at
# assets/fonts/pixel.ttf (Press Start 2P) every size uses it; otherwise the monospace system font is used, un-smoothed.
# Set textscale.PIXEL_TEXT = False for smooth text again.
#
# Press Start 2P is drawn from an 8 px grid, and without smoothing it is only clean at 8, 16, 24, 32 ... px (whole
# multiples of 8; see textscale.py). So the pixel font is never asked for another size: _mono(size) draws a "logical" size
# (the sizes the layout works with, textscale.TEXT_PX) at the clean size textscale.pixel_font_px gives for it.
PIXEL_TEXT = textscale.PIXEL_TEXT
ANTIALIAS = not PIXEL_TEXT   # widgets.text_surface and the other render() calls use this
PIXEL_FONT_PATH = textscale.PIXEL_FONT_PATH

_FONT_CACHE = {}


def _mono(size, bold=False):
    """The monospace font for a logical `size`. With the pixel font: the clean size for it (8 / 16 / 24 / 32 / 40), no bold (a pixel
    font has none: the heading sizes are just larger). Fonts are cached, so sizes that share a clean size share a font."""
    if textscale.USE_PIXEL_FONT:
        shown, bold = textscale.pixel_font_px(size), False
    else:
        shown = size
    key = (shown, bold)
    font = _FONT_CACHE.get(key)
    if font is None:
        if textscale.USE_PIXEL_FONT:
            try:
                font = pygame.font.Font(PIXEL_FONT_PATH, shown)
            except (pygame.error, OSError):
                font = None   # an unreadable font file: fall back to the system font at the logical size
        if font is None:
            font = pygame.font.SysFont(MONO_FONTS, size, bold=bold)
        _FONT_CACHE[key] = font
    return font


# Every size is created once here and never scaled: screens pick the largest one that fits their space
# (widgets.pick_font), so text stays sharp at any window size.
# With the pixel font these names map to: TINY, SMALL = 8 px; MEDIUM, FONT, LARGE, LARGER = 16 px; TITLE, XLARGE = 24 px;
# BIG, XXLARGE = 32 px; HUGE = 40 px.
FONT = _mono(19)
SMALL = _mono(15)
TINY = _mono(13)
TITLE = _mono(27, bold=True)
BIG = _mono(34, bold=True)
# Extra cached sizes for large windows (1.18): between SMALL and FONT, above FONT, and a large heading.
MEDIUM = _mono(17)
LARGE = _mono(23)
HUGE = _mono(44, bold=True)

# Bigger sizes for big windows (1.27).
LARGER = _mono(26)
XLARGE = _mono(30)
XXLARGE = _mono(36)

# TEXT_SIZES lists (logical pixel size, font) from the smallest up; widgets.scaled_font / text_ladder choose from it by
# window size (15 px text in the default 1000 x 680 window, larger above that). The logical sizes are textscale.TEXT_PX
# (the sizes the layout scales its rows by); with the pixel font several of them share one clean font.
TEXT_SIZES = tuple((px, _mono(px)) for px in textscale.TEXT_PX)
# textscale.TEXT_PX (which text_k / text_px snap to) must list exactly the sizes cached here, or a snapped size would
# have no cached font. Fail loudly at import if one list is changed without the other.
if tuple(px for px, _font in TEXT_SIZES) != textscale.TEXT_PX:
    raise ValueError(f"theme.TEXT_SIZES {tuple(px for px, _font in TEXT_SIZES)} and textscale.TEXT_PX "
                     f"{textscale.TEXT_PX} must list the same pixel sizes")


def _distinct_largest_first(fonts):
    """`fonts` without repeats (the same font object), order kept."""
    seen = []
    for font in fonts:
        if not any(font is other for other in seen):
            seen.append(font)
    return tuple(seen)


TEXT_FONTS = _distinct_largest_first(font for _px, font in reversed(TEXT_SIZES))   # largest first, for pick_font / fit_paragraph

# Font ladders, largest first, for pick_font.
BODY_FONTS = _distinct_largest_first((LARGE, FONT, MEDIUM, SMALL, TINY))
HEAD_FONTS = _distinct_largest_first((HUGE, BIG, TITLE, FONT, SMALL))
