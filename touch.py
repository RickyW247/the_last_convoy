"""Touch input for the browser / phone version of THE LAST CONVOY (no gameplay, input translation only).

A tap on a phone arrives as a left-button MOUSEBUTTONDOWN, and the game acts on button-down. A swipe that starts on a
button would therefore press it. This module sits between pygame.event.get() and the game's event loop and fixes that
for touch events only (a real mouse is never touched):

  * a touch-down is HELD BACK until the finger lifts; if the finger stayed put (a tap) the down event is released then,
    followed by the up event, so the game sees an ordinary click;
  * if the finger moved more than SLOP pixels it is a swipe: the click is dropped and the movement becomes MOUSEWHEEL
    events (finger down = wheel up), so the screens that scroll or page with the wheel (instructions, history, credits,
    vehicles, upgrades, achievements) work by swiping with no change to them;
  * while the convoy is travelling, keeping a finger down for HOLD_MS is the same as holding SPACE (fast-forward), and
    that long press is not a click.

Usage in main.py:  for event in touch.filter(pygame.event.get(), size):   ...   and  touch.holding() for fast-forward.
"""
import pygame

SLOP = 14        # pixels a finger may wander and still be a tap
HOLD_MS = 350    # a finger down this long while travelling = fast-forward

_state = {"down": None, "start": None, "last_y": 0, "acc": 0.0, "dragging": False,
          "since": 0, "long": False, "finger_seen": False}


def _is_touch(event):
    return bool(getattr(event, "touch", False)) or _state["finger_seen"]


def _step(size):
    """Finger travel (pixels) that equals one wheel notch: a bit under 1/14 of the window height."""
    return max(32, size[1] // 14)


def _reset():
    _state.update(down=None, start=None, acc=0.0, dragging=False, long=False)


def filter(events, size):
    """Translate touch events (see the module docstring); every other event passes through unchanged."""
    out = []
    step = _step(size)
    for event in events:
        kind = event.type
        if kind in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            _state["finger_seen"] = True   # some browsers send finger events without flagging the mouse ones
            continue
        if kind == pygame.MOUSEBUTTONDOWN and event.button == 1 and _is_touch(event):
            _state.update(down=event, start=event.pos, last_y=event.pos[1], acc=0.0, dragging=False, long=False,
                          since=pygame.time.get_ticks())
            continue
        if kind == pygame.MOUSEMOTION and _state["down"] is not None and _is_touch(event):
            x, y = event.pos
            if not _state["dragging"]:
                sx, sy = _state["start"]
                if (x - sx) ** 2 + (y - sy) ** 2 > SLOP * SLOP:
                    _state["dragging"] = True
                    _state["last_y"] = y   # the slop itself does not scroll
                continue
            _state["acc"] += y - _state["last_y"]
            _state["last_y"] = y
            while abs(_state["acc"]) >= step:
                notch = 1 if _state["acc"] > 0 else -1   # finger down = wheel up = previous page / scroll up
                _state["acc"] -= notch * step
                out.append(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=notch, flipped=False, which=0,
                                               precise_x=0.0, precise_y=float(notch)))
            continue
        if kind == pygame.MOUSEBUTTONUP and event.button == 1 and _state["down"] is not None and _is_touch(event):
            if not _state["dragging"] and not _state["long"]:
                down = _state["down"]
                out.append(down)    # the tap: down, then up, at the place where the finger went down
                out.append(event)
            _reset()
            continue
        out.append(event)
    return out


def holding(on_road=False):
    """True while a finger has been held down on the road long enough to fast-forward. Call once per frame."""
    if not on_road or _state["down"] is None or _state["dragging"]:
        return False
    if _state["long"] or pygame.time.get_ticks() - _state["since"] >= HOLD_MS:
        _state["long"] = True   # from now on the release is not a click
        return True
    return False
