"""Where every line of the credits screen goes (shared by the drawing, ui/credits.py, and by the buttons that make
the links clickable, buttons.py). Needs the fonts (theme) but never draws anything.

The text is laid out in two columns, and nothing is ever left out: the lines flow down the first column, then the
second, then on to the next PAGE. A section that fits in a column is kept whole (it moves to the next column / page
instead of being split); a section that is taller than a column is split between lines, and a heading never ends a
column on its own. When there is more than one page the bottom strip of the text area is reserved for the page
indicator (credits_footer).

credits_items(width, height) returns the lines of the page that is open now (the page number is kept here, like the
instructions' scroll position is kept in ui/instructions.py), so buttons.py makes buttons only for the links that are
on screen. Turn pages with turn_credits_page; reset_credits_page puts the credits back on page 1.
"""
from functools import lru_cache
from typing import NamedTuple

import credits_data
import textscale
from layout import credits_layout
from textscale import tpx
from widgets import scaled_font, wrap_pixels

HEADING_SPACE, LINE_SPACE, COLUMN_GAP = 14, 3, 30   # pixels (default text size) above a heading / a line, between the two columns
FOOTER_PAD = 4                                       # pixels between the last credits line and the page indicator


class CreditsLine(NamedTuple):
    """One drawn line: its text, kind ("heading", "text" or "link"), font, rectangle and, for a link, its address."""
    text: str
    kind: str
    font: object
    rect: tuple
    url: object


def _sections(col_w, font, k=1.0):
    """Every credits section as a list of (text, kind, spacing above, url), the heading first. The spacings are
    multiplied by k, the text-size factor, like the fonts."""
    sections = []
    for heading, lines in credits_data.CREDITS:
        section = [(heading, "heading", tpx(HEADING_SPACE, k), None)]
        for line in lines:
            url = getattr(line, "url", None)   # a credits_data.Link carries its address
            for part in wrap_pixels(line, font, col_w):
                section.append((part, "link" if url else "text", tpx(LINE_SPACE, k), url))
        sections.append(section)
    return sections


def _paginate(tx, ty, tw, th, size, k):
    """All pages (a tuple of tuples of CreditsLine) for a text area of this size, in the scaled 15 px font (the text-size
    setting and the window size, like every other screen's text)."""
    col_w = (tw - tpx(COLUMN_GAP, k)) // 2
    font = scaled_font(size, 15)
    line_h = font.get_linesize()

    pages = [[[], []]]               # pages -> two columns -> items
    pos = {"col": 0, "used": 0}      # where the next item goes: column of the last page, pixels used in it

    def need(item):
        return line_h + item[2]

    def advance():
        if pos["col"] == 0:
            pos["col"] = 1
        else:
            pages.append([[], []])
            pos["col"] = 0
        pos["used"] = 0

    def add(item):
        pages[-1][pos["col"]].append(item)
        pos["used"] += need(item)

    for section in _sections(col_w, font, k):
        total = sum(need(item) for item in section)
        if pos["used"] > 0 and pos["used"] + total > th and total <= th:
            advance()   # it fits a whole column, just not this one: keep the section together
        for index, item in enumerate(section):
            keep = need(item)
            if item[1] == "heading" and index + 1 < len(section):
                keep += need(section[index + 1])   # a heading stays with its first line
            if pos["used"] > 0 and pos["used"] + keep > th:
                advance()   # (an empty column always takes the item, so this always makes progress)
            add(item)

    result = []
    for columns in pages:
        placed = []
        for index, items in enumerate(columns):
            x = tx + index * (col_w + tpx(COLUMN_GAP, k))
            y = ty
            for text, kind, spacing, url in items:
                y += spacing
                if kind == "link":
                    w = min(col_w, font.size(text)[0])
                    rect = (x + (col_w - w) // 2, y, w, line_h)
                else:
                    rect = (x, y, col_w, line_h)
                placed.append(CreditsLine(text, kind, font, rect, url))
                y += line_h
        result.append(tuple(placed))
    return tuple(result)


@lru_cache(maxsize=8)
def credits_pages(width, height):
    """(pages, footer) for a window of this size: every page's CreditsLine tuple, and the rectangle for the page
    indicator (None when everything fits on one page)."""
    layout = credits_layout(width, height)
    tx, ty, tw, th = layout["text"]
    size, k = (width, height), layout["k"]
    pages = _paginate(tx, ty, tw, th, size, k)
    if len(pages) == 1:
        return pages, None
    footer_h = scaled_font(size, 13).get_linesize() + FOOTER_PAD
    pages = _paginate(tx, ty, tw, max(0, th - footer_h), size, k)
    return pages, (tx, ty + th - footer_h + FOOTER_PAD, tw, footer_h - FOOTER_PAD)


# ---- the page that is open (kept here, not in game.py) ----
_CREDITS_PAGE = {"page": 0}


def credits_page_count(width, height):
    return len(credits_pages(width, height)[0])


def credits_page_index(width, height):
    """The open page (0-based), kept inside the pages this window size has."""
    last = credits_page_count(width, height) - 1
    _CREDITS_PAGE["page"] = max(0, min(last, _CREDITS_PAGE["page"]))
    return _CREDITS_PAGE["page"]


def credits_footer(width, height):
    """The rectangle of the page indicator, or None when the credits fit on one page."""
    return credits_pages(width, height)[1]


def credits_items(width, height):
    """The CreditsLine tuple of the open credits page in a window of this size. Plain lines and headings span their
    column (to be drawn centred); a link's rectangle is just as wide as its text, so only the text is clickable."""
    return credits_pages(width, height)[0][credits_page_index(width, height)]


def turn_credits_page(size, step):
    """Turn the credits by `step` pages (negative = back), stopping at the first and last page; a huge step jumps to
    an end. Returns True when the page changed."""
    before = credits_page_index(*size)
    _CREDITS_PAGE["page"] = before + step
    return credits_page_index(*size) != before


def reset_credits_page():
    """Put the credits back on page 1; called whenever that screen is opened or left."""
    _CREDITS_PAGE["page"] = 0


credits_items.cache_clear = credits_pages.cache_clear   # old callers / tests that clear credits_items' cache
textscale.on_change(credits_pages.cache_clear)          # the credits layout follows the text-size setting
