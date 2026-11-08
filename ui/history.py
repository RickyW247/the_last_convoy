"""The event history screen (drawing only): every message of the run under "Day 8 - <place>" group headers, newest
first, wrapped to the panel and scrolled by rows. The rows are planned here (they depend on the font and the width), so
this module also tells buttons.py / main.py how far the list can scroll (history_max_scroll, clamp_history)."""
import textscale
from history_log import clamp_scroll, history_rows
from layout import history_layout
from theme import MUTED, PANEL, WHITE, YELLOW
from widgets import draw_heading, draw_panel, draw_text, fit_text, scaled_font, wrap_pixels

INDENT = 14        # px (default text) a message is indented under its header
FONT_SIZE = 15     # px (default window) of the history rows (was 14, which drew as 13); a size from theme.TEXT_SIZES
SMALL_FONT_SIZE = 13  # px (default window) of the subtitle, footer and hint (as originally)
_plan_cache = {"key": None, "value": None}


def _plan(game, size):
    """(font, row_h, per_page, rows): the wrapped display rows ("header", text) / ("line", text) / ("more", text) for
    this window size and history, and how many of them fit the list. Cached until the history or the size changes."""
    g = history_layout(*size)
    history = game.history
    key = (size, textscale.text_level(), len(history), history[-1]["text"] if history else "", g["rows"], id(history))
    if _plan_cache["key"] == key:
        return _plan_cache["value"]
    font = scaled_font(size, FONT_SIZE)
    row_h = font.get_linesize() + 3
    per_page = max(1, g["rows"][3] // row_h)
    indent = max(8, int(INDENT * g["k"]))
    width = max(40, g["rows"][2] - 2 * 4)
    rows = []
    for kind, text in history_rows(history):
        if kind == "header":
            rows.append(("header", text))
            continue
        for i, part in enumerate(wrap_pixels(text, font, width - 2 * indent) or [""]):
            rows.append(("line" if i == 0 else "more", part))
    value = (font, row_h, per_page, rows)
    _plan_cache["key"], _plan_cache["value"] = key, value
    return value


def history_max_scroll(game, size):
    """The largest first-visible-row the history screen can scroll to."""
    _font, _row_h, per_page, rows = _plan(game, size)
    return max(0, len(rows) - per_page)


def history_page_rows(game, size):
    """How many rows one PageUp / PageDown (the NEWER / OLDER buttons) moves: a screenful less one row."""
    return max(1, _plan(game, size)[2] - 1)


def clamp_history(game, size):
    """Keep game.history_scroll valid (main.py calls this once per frame, like paging.clamp_pages)."""
    _font, _row_h, per_page, rows = _plan(game, size)
    game.history_scroll = clamp_scroll(game.history_scroll, len(rows), per_page)


def draw_history_screen(surface, game, buttons):
    """The history panel, its heading, the visible rows, the footer and the screen's buttons."""
    size = surface.get_size()
    g = history_layout(*size)
    font, row_h, per_page, rows = _plan(game, size)
    scroll = clamp_scroll(game.history_scroll, len(rows), per_page)

    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "EVENT HISTORY", g["header"])
    small = scaled_font(size, SMALL_FONT_SIZE)
    sx, sy, sw, sh = g["subtitle"]
    draw_text(surface, fit_text("Everything that happened this run, newest first.", small, sw), sx, sy, MUTED, small)

    draw_panel(surface, g["list"], (25, 31, 34), -1)
    rx, ry, rw, _rh = g["rows"]
    indent = max(8, int(INDENT * g["k"]))
    if not rows:
        draw_text(surface, "Nothing has happened yet.", rx + 4, ry + 2, MUTED, font)
    for i, (kind, text) in enumerate(rows[scroll:scroll + per_page]):
        y = ry + i * row_h
        if kind == "header":
            draw_text(surface, fit_text(text, font, rw - 8), rx + 4, y, YELLOW, font)
        else:
            draw_text(surface, fit_text(text, font, rw - 8 - indent), rx + 4 + indent, y,
                      WHITE if kind == "line" else MUTED, font)

    fx, fy, fw, fh = g["showing"]
    if rows:
        shown = f"Rows {scroll + 1}-{min(len(rows), scroll + per_page)} of {len(rows)}"
        draw_text(surface, fit_text(shown, small, fw), fx, fy, MUTED, small)
    hx, hy, hw, hh = g["hint"]
    hint = "Wheel / PgUp / PgDn / Home / End: scroll   H or Esc: back"
    draw_text(surface, fit_text(hint, small, hw), hx, hy, MUTED, small)

    for button in buttons:
        if button.label != "MENU":
            button.draw(surface)
