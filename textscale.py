"""The text-size setting and the one rule that ties fonts and layout rows together (no pygame).

k = text_k(width, height) says how much bigger than the default text a window of this size uses: 1.0 in the default
window (1000 x 680) with the Normal setting, larger in a bigger window or with a larger setting. Fonts are chosen with
text_px (widgets.scaled_font / text_ladder) and every layout row that holds text is multiplied by the same k
(layout/*.py, via tpx), so larger text always has the room it needs and nothing spills out of its box.

The setting has four levels (TEXT_LEVELS). A level above Normal only grows as far as the window allows (at the default
window size 1.5 at most, and not at all below it), so the layouts never run out of room. Changing the level calls the
registered listeners; the layout caches register theirs (layout.geometry.layout_cache) and clear themselves.

PIXEL FONT (assets/fonts/pixel.ttf, Press Start 2P). The layout always works with the same logical sizes (TEXT_PX), whatever
the font, so rows, k and the text-size setting behave exactly as they were designed. Only the font that DRAWS a logical size
changes. Press Start 2P is drawn from an 8 px grid and, without smoothing, is clean only at whole multiples of 8 (8, 16, 24,
32, 40 ...: checked glyph by glyph), so pixel_font_px() turns each logical size into one of those:
    logical 13 / 15      -> 8 px   (the small and tiny text)
    logical 17 .. 26     -> 16 px  (body text, buttons, list rows)
    logical 27 .. 33     -> 24 px  (headings)
    logical 34 .. 43     -> 32 px
    logical 44 and up    -> 40 px
The font is also 1 em wide per character (a system monospace font is about 0.55 em), so text at 16 px is about twice as
wide as the layouts were made for. The screens already choose "the largest font that fits" (widgets.pick_font /
text_ladder), so wide text falls back to 8 px where it does not fit. text_ladder's default base is LADDER_BASE (17 with this
font, so that 16 px is in the ladder at the default size).
"""
import os

PIXEL_TEXT = True   # theme.ANTIALIAS = not PIXEL_TEXT. False: smooth text and the old sizes, whatever fonts exist
PIXEL_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "pixel.ttf")
USE_PIXEL_FONT = PIXEL_TEXT and os.path.isfile(PIXEL_FONT_PATH)

# (smallest logical size, clean pixel-font size): the last row whose first number is <= the logical size is used.
PIXEL_SIZE_STEPS = ((0, 8), (17, 16), (27, 24), (34, 32), (44, 40))
TEXT_PX = (13, 15, 17, 19, 23, 26, 30, 36)    # the logical pixel sizes of the cached fonts (theme.TEXT_SIZES), smallest first
TEXT_LEVELS = (("Small", 0.87), ("Normal", 1.0), ("Large", 1.25), ("Extra large", 1.5))   # (name, scale)
BASE_PX = 15                                  # the body text size of the default window with the Normal setting
LADDER_BASE = 17 if USE_PIXEL_FONT else BASE_PX   # widgets.text_ladder's default base (17: 16 px text is in the ladder)

_state = {"level": "Normal"}
_listeners = []


def pixel_font_px(size):
    """The clean pixel-font size (8, 16, 24 ...) that draws text of `size` logical px (see PIXEL_SIZE_STEPS)."""
    best = PIXEL_SIZE_STEPS[0][1]
    for smallest, px in PIXEL_SIZE_STEPS:
        if size >= smallest:
            best = px
    return best


def on_change(callback):
    """Call `callback()` whenever the text-size level changes (used to clear caches that depend on it)."""
    _listeners.append(callback)


def text_level():
    """The name of the current level ("Small", "Normal", "Large" or "Extra large")."""
    return _state["level"]


def text_scale():
    return dict(TEXT_LEVELS)[_state["level"]]


def set_text_level(name):
    """Choose a level by name. Returns True if it changed."""
    if name not in dict(TEXT_LEVELS) or name == _state["level"]:
        return False
    _state["level"] = name
    for callback in _listeners:
        callback()
    return True


def cycle_text_level(step=1):
    """The next (+1) or previous (-1) level, wrapping round. Returns the new level's name."""
    names = [name for name, _scale in TEXT_LEVELS]
    set_text_level(names[(names.index(_state["level"]) + step) % len(names)])
    return _state["level"]


def _snap(target):
    """The largest TEXT_PX size that is at most `target` (the smallest size if none is)."""
    best = TEXT_PX[0]
    for px in TEXT_PX:
        if px <= target:
            best = px
    return best


def text_k(width, height):
    """How much the text rows grow for a window of this size: the body text size the window gets, divided by
    BASE_PX. 1.0 at the default size; a bigger window or a larger level raises it (the level only as far as the window
    has room for, see the module docstring)."""
    window = min(width / 1000, height / 680)
    scale = text_scale()
    if scale > 1.0:
        scale = min(scale, max(1.0, window * 1.5))
    return _snap(BASE_PX * scale * max(1.0, window)) / BASE_PX


def text_px(width, height, base=BASE_PX):
    """The pixel size of the font that is `base` px at the default size, for a window of this size. Never larger
    than `base` * text_k, so a font chosen with it always fits a row that was scaled by text_k."""
    return _snap(base * text_k(width, height))


def tpx(value, k):
    """`value` pixels (a row or button size made for the default text) scaled by k, at least 1."""
    return max(1, int(round(value * k)))
