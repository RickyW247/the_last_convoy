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
# assets/fonts/pixel.ttf (for example Silkscreen, Pixelify Sans or Press Start 2P: any .ttf, drop it in and rename it) every
# size uses it; otherwise the monospace system font is used, un-smoothed. Set PIXEL_TEXT = False for smooth text again.
PIXEL_TEXT = True
ANTIALIAS = not PIXEL_TEXT   # widgets.text_surface and the other render() calls use this
PIXEL_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "pixel.ttf")


def _mono(size, bold=False):
    if PIXEL_TEXT and os.path.isfile(PIXEL_FONT_PATH):
        try:
            return pygame.font.Font(PIXEL_FONT_PATH, size)   # a pixel font has no bold: the heading sizes are just larger
        except (pygame.error, OSError):
            pass   # an unreadable font file: fall back to the system font
    return pygame.font.SysFont(MONO_FONTS, size, bold=bold)


# Every size is created once here and never scaled: screens pick the largest one that fits their space
# (widgets.pick_font), so text stays sharp at any window size.
FONT = _mono(19)
SMALL = _mono(15)
TINY = _mono(13)
TITLE = _mono(27, bold=True)
BIG = _mono(34, bold=True)
# Extra cached sizes for large windows (1.18): between SMALL and FONT, above FONT, and a large heading.
MEDIUM = _mono(17)
LARGE = _mono(23)
HUGE = _mono(44, bold=True)

# Bigger sizes for big windows (1.27). TEXT_SIZES lists (pixel size, font) from the smallest up; widgets.scaled_font /
# text_ladder choose from it by window size (15 px text in the default 1000 x 680 window, larger above that).
LARGER = _mono(26)
XLARGE = _mono(30)
XXLARGE = _mono(36)
TEXT_SIZES = ((13, TINY), (15, SMALL), (17, MEDIUM), (19, FONT), (23, LARGE), (26, LARGER), (30, XLARGE),
              (36, XXLARGE))
# textscale.TEXT_PX (which text_k / text_px snap to) must list exactly the sizes cached here, or a snapped size would
# have no cached font. Fail loudly at import if one list is changed without the other.
if tuple(px for px, _font in TEXT_SIZES) != textscale.TEXT_PX:
    raise ValueError(f"theme.TEXT_SIZES {tuple(px for px, _font in TEXT_SIZES)} and textscale.TEXT_PX "
                     f"{textscale.TEXT_PX} must list the same pixel sizes")
TEXT_FONTS = tuple(font for _px, font in reversed(TEXT_SIZES))   # largest first, for pick_font / fit_paragraph

# Font ladders, largest first, for pick_font.
BODY_FONTS = (LARGE, FONT, MEDIUM, SMALL, TINY)
HEAD_FONTS = (HUGE, BIG, TITLE, FONT, SMALL)
