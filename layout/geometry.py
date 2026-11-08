"""Rectangle helpers and the sizes shared by every layout module of THE LAST CONVOY (no pygame).

All rectangles are (x, y, width, height) tuples of ints.

Text sizes: the constants below (LINE_H, TABLE_HEADER_H ...) are the sizes for the default text. A layout function
gets k = text_k(width, height) (1.0 by default, larger in a big window or with a larger text-size setting, see
textscale.py) and multiplies every row that holds text by it with tpx(value, k), so text and rows always grow together.

Every layout function is wrapped in @layout_cache: the result is cached and frozen (dicts become read-only mappings,
lists become tuples), so a caller can never corrupt the shared result, and the cache clears itself when the text size
changes.
"""
import functools
from types import MappingProxyType

import textscale
from textscale import text_k, tpx  # noqa: F401  (re-exported for the layout modules)


LINE_H = 16                  # height reserved for one line of TINY text
TABLE_HEADER_H = 22          # the heading row of the vehicle table and of the survivors list
LIST_HEAD_GAP = 4            # space under the heading row and above the footer of a list (also used by popups)


def freeze(value):
    """A read-only copy: dicts become mappings that cannot be changed, lists and tuples become tuples."""
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def layout_cache(maxsize=32):
    """Decorator for layout functions: cache the result, freeze it (see freeze) and clear the cache when the
    text-size setting changes."""
    def decorate(func):
        @functools.wraps(func)
        def frozen(*args, **kwargs):
            return freeze(func(*args, **kwargs))
        cached = functools.lru_cache(maxsize=maxsize)(frozen)
        textscale.on_change(cached.cache_clear)
        return cached
    return decorate


def clamp(value, low, high):
    return max(low, min(high, value))


def inset(rect, dx, dy=None):
    """`rect` shrunk by dx on the left and right and dy (default dx) on the top and bottom."""
    dy = dx if dy is None else dy
    x, y, w, h = rect
    return (x + dx, y + dy, max(0, w - 2 * dx), max(0, h - 2 * dy))


def rect_right(rect):
    return rect[0] + rect[2]


def rect_bottom(rect):
    return rect[1] + rect[3]


def rects_overlap(a, b):
    """True if two (x, y, w, h) rectangles share any area (touching edges do not count)."""
    return (a[2] > 0 and a[3] > 0 and b[2] > 0 and b[3] > 0
            and a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
            and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


def rect_inside(inner, outer):
    """True if `inner` lies completely inside `outer`."""
    return (inner[0] >= outer[0] and inner[1] >= outer[1]
            and rect_right(inner) <= rect_right(outer) and rect_bottom(inner) <= rect_bottom(outer))


def as_ints(rect):
    return tuple(int(round(v)) for v in rect)


def fit_ratio(rect, ratio_w, ratio_h):
    """The largest ratio_w : ratio_h rectangle that fits inside rect = (x, y, w, h), centred in it."""
    x, y, w, h = rect
    fit_w = w
    fit_h = int(w * ratio_h / ratio_w)
    if fit_h > h:
        fit_h = h
        fit_w = int(h * ratio_w / ratio_h)
    return (x + (w - fit_w) // 2, y + (h - fit_h) // 2, fit_w, fit_h)


def buttons_in_row(row, left_widths, right_widths, gap):
    """Button rectangles in `row`: the left group starts at the left edge, the right group ends at the right
    edge (in the given order, so the last one is rightmost). Widths shrink together if the row is too narrow."""
    x, y, w, h = row
    count = len(left_widths) + len(right_widths)
    widths_sum = sum(left_widths) + sum(right_widths)
    room = w - gap * max(0, count - 1)
    k = min(1.0, room / widths_sum) if widths_sum else 1.0
    left = []
    cx = x
    for bw in left_widths:
        bw = max(1, int(bw * k))
        left.append((cx, y, bw, h))
        cx += bw + gap
    right = []
    cx = x + w
    for bw in reversed(right_widths):
        bw = max(1, int(bw * k))
        cx -= bw
        right.append((cx, y, bw, h))
        cx -= gap
    right.reverse()
    return left, right


def page_count(total, per_page):
    """Number of pages (at least 1) for `total` items at `per_page` per page."""
    return max(1, -(-max(0, int(total)) // max(1, int(per_page))))


def fraction_columns(x, width, fractions):
    """(x, width) of columns whose widths are `fractions` of `width` (normalised, so they fill it exactly)."""
    total = sum(fractions)
    columns, acc = [], 0.0
    for fraction in fractions:
        left = x + int(width * acc / total)
        acc += fraction
        right = x + int(width * acc / total)
        columns.append((left, right - left))
    return tuple(columns)
