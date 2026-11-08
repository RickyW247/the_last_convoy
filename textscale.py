"""The text-size setting and the one rule that ties fonts and layout rows together (no pygame).

k = text_k(width, height) says how much bigger than the default text a window of this size uses: 1.0 in the default
window (1000 x 680) with the Normal setting, larger in a bigger window or with a larger setting. Fonts are chosen with
text_px (widgets.scaled_font / text_ladder) and every layout row that holds text is multiplied by the same k
(layout/*.py, via tpx), so larger text always has the room it needs and nothing spills out of its box.

The setting has four levels (TEXT_LEVELS). A level above Normal only grows as far as the window allows (at the default
window size 1.5 at most, and not at all below it), so the layouts never run out of room. Changing the level calls the
registered listeners; the layout caches register theirs (layout.geometry.layout_cache) and clear themselves.
"""

TEXT_PX = (13, 15, 17, 19, 23, 26, 30, 36)   # the pixel sizes of the cached fonts (theme.TEXT_SIZES), smallest first
TEXT_LEVELS = (("Small", 0.87), ("Normal", 1.0), ("Large", 1.25), ("Extra large", 1.5))   # (name, scale)
BASE_PX = 15                                  # the body text size of the default window with the Normal setting

_state = {"level": "Normal"}
_listeners = []


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
