"""Layout of the vehicles screen: the vehicle table, the preview card and the buttons (no pygame).
"""
from functools import lru_cache

import textscale

from .frame import screen_frame
from .geometry import LINE_H, TABLE_HEADER_H, buttons_in_row, clamp, inset, layout_cache, rect_bottom, tpx


VEHICLE_ROWS = 8             # vehicle types in the table (len(vehicles.VEHICLE_SPECS))
MIN_ROW_H, MAX_ROW_H = 22, 40
COMFORT_ROW_H = 28           # rows this tall are comfortable: the layout only squeezes below it before dropping anything
MIN_PAGE_ROWS = 4            # a paged table shows at least this many vehicles per page
PAGER_H = 26                 # height of the "< PREV   Page 1/2   NEXT >" row under a paged table (scaled by k)
PAGER_BTN_W = 84             # width of the PREV / NEXT buttons (scaled by k)
COMPACT_TABLE_W = 560        # a narrower table uses shorter status text and narrower columns
BIG_TEXT_LEVELS = ("Large", "Extra large")   # only at these text sizes may the screen use shorter wording (see below)

# The convoy totals have three shapes: "grid" (4 x 2 cells above the table: the normal one), "row" (8 cells in one line
# above the table: half the height, but the cells are narrow, so the screen uses the short wording; only offered at the
# BIG_TEXT_LEVELS) and "side" (one column of 8 lines to the right of the preview card: costs no height, only width).
SUMMARY_SIDE_W = 270         # width of the "side" column (for the default text; scaled by k)
SIDE_MIN_TABLE_W = 410       # the table is never made narrower than this (scaled by k) to make room for the side column
ONE_LINE_SUB_W = 860         # at the BIG_TEXT_LEVELS the two help lines become one (short wording) when the panel is this wide (scaled by k)

# Column widths of the vehicle table as fractions of the table width: VEHICLE, STATUS, SPD, HP, PASS, CARGO,
# DEF, FCAP, FUSE. They are normalised, so the columns always fill the table exactly.
_COLUMNS_WIDE = (0.27, 0.16, 0.07, 0.12, 0.08, 0.09, 0.07, 0.07, 0.07)
# Compact columns are the narrowest widths (px, TINY font) that still hold their heading and worst-case value.
_COLUMNS_COMPACT = tuple(w / 390 for w in (84, 40, 28, 60, 36, 42, 28, 36, 36))
TABLE_CELL_PAD = (3, 2)      # horizontal padding inside a table cell: (normal, compact)
CARD_PICTURE_MIN_H = 110     # the vehicle card keeps its role text only if the picture box can stay this tall ...
CARD_PICTURE_ASPECT = 0.6    # ... but the picture box is never taller than this many times the card's inner width
ABILITY_PICTURE_MIN_H = 80   # the picture box keeps at least this many pixels while the ability block has all three lines
ABILITY_PICTURE_MIN_H_2 = 60   # ... and this many while it has two
CARD_PICTURE_FLOOR_H = 50    # (the sprite is width-limited, so a taller box is only empty space)


def table_pad(compact):
    return TABLE_CELL_PAD[1] if compact else TABLE_CELL_PAD[0]


def table_columns(table_x, table_w, compact):
    """(x, width) of each of the nine vehicle table columns, as fractions of the table width."""
    fractions = _COLUMNS_COMPACT if compact else _COLUMNS_WIDE
    total = sum(fractions)
    edge = 2
    usable = table_w - 2 * edge
    columns, acc = [], 0.0
    for fraction in fractions:
        left = table_x + edge + int(usable * acc / total)
        acc += fraction
        right = table_x + edge + int(usable * acc / total)
        columns.append((left, right - left))
    return tuple(columns)


def _card_metrics(w, k):
    p, lh = tpx(8, k), tpx(LINE_H, k)
    iw = max(0, w - 2 * p)
    stats_h = (3 if w < tpx(260, k) else 2) * lh
    # p, lh, iw, name_h, stats_h, detail_h, owned_h, ability_h (a heading line and two lines of text)
    return p, lh, iw, tpx(22, k), stats_h, 2 * lh, tpx(18, k), 3 * lh


def _picture_cap(iw):
    """The tallest the picture box needs to be: the sprite is limited by the card's width, not its height."""
    return max(CARD_PICTURE_FLOOR_H, int(iw * CARD_PICTURE_ASPECT))


def vehicle_card_height(w, k, max_h):
    """The height the preview card needs for width `w`: its rows plus a picture box capped by the width (at most
    `max_h`, the height of the table beside it)."""
    p, lh, iw, name_h, stats_h, detail_h, owned_h, ability_h = _card_metrics(w, k)
    chrome = p + name_h + 4 + 4 + owned_h + 2 + detail_h + 4 + stats_h + p   # the card is sized for a vehicle without an ability;
    # one with an ability uses its block's rows from the picture / role text instead (see vehicle_card_layout)
    cap = _picture_cap(iw)
    with_role = chrome + (2 * lh + 4) + cap
    return with_role if with_role <= max_h else min(max_h, chrome + cap)


@lru_cache(maxsize=128)   # not layout_cache: that decorator only passes (card, k) on
def _card_layout(card, k, ability_lines):
    """Inside the vehicle preview card: name, optional role text, picture, special ability (only when `ability_lines` > 0), status, detail and stats rows.
    `ability_lines` is how many lines of effect text the ability needs at this width (1 or 2); the block is never bigger than that."""
    x, y, w, h = card
    p, lh, iw, name_h, stats_h, detail_h, owned_h, ability_h = _card_metrics(w, k)
    ix = x + p
    name = (ix, y + p, iw, name_h)
    top = rect_bottom(name) + 4
    bottom = y + h - p
    stats = (ix, bottom - stats_h, iw, stats_h)
    detail = (ix, stats[1] - 4 - detail_h, iw, detail_h)
    owned = (ix, detail[1] - 2 - owned_h, iw, owned_h)
    cap = _picture_cap(iw)
    ability = None
    room_bottom = owned[1] - 4
    if ability_lines:   # the special ability sits under the picture; vehicles without one get no empty block
        # The full ability text matters more than a tall picture: the block has a heading and two text lines as long as the
        # picture box keeps ABILITY_PICTURE_MIN_H pixels (or its cap, if smaller; the role text is dropped before that),
        # else a heading and one line (the picture needs the lower ABILITY_PICTURE_MIN_H_2 for that), else a single line
        # ("Name: short effect"). The drawing code reads how many lines it got from the block's height.
        lines = 1
        for candidate, need in ((1 + min(2, ability_lines), ABILITY_PICTURE_MIN_H), (2, ABILITY_PICTURE_MIN_H_2)):
            if owned[1] - 2 - candidate * lh - 4 - top >= min(need, cap):
                lines = candidate
                break
        ability = (ix, owned[1] - 2 - lines * lh, iw, lines * lh)
        room_bottom = ability[1] - 4
    role = None
    role_h = 2 * lh
    # The picture comes first: the role text is only shown when the picture box still keeps CARD_PICTURE_MIN_H pixels
    # (or its cap, if that is smaller; a fixed size, not scaled by k: the sprite is pixel art and does not grow with the
    # text size, but the text rows around it do).
    if room_bottom - top - (role_h + 4) >= min(CARD_PICTURE_MIN_H, cap):
        role = (ix, top, iw, role_h)
        top = rect_bottom(role) + 4
    # The card can be taller than its content needs (it reaches down to the bottom of the status text), so the picture
    # box takes all the room that is left instead of being capped by the card's width.
    picture = (ix, top, iw, max(0, room_bottom - top))
    return {"name": name, "role": role, "picture": picture, "ability": ability, "owned": owned, "detail": detail,
            "stats": stats}


def vehicle_card_layout(card, k=1.0, ability_lines=0):
    """Inside the vehicle preview card (see _card_layout): `ability_lines` (0 = no ability, else the lines of effect text it needs) adds the special-ability block under the picture."""
    return _card_layout(tuple(card), k, int(ability_lines))


@layout_cache(16)
def vehicles_layout(width, height, rows=VEHICLE_ROWS):
    """Rectangles of the vehicles screen: table (with its columns and rows), preview card, convoy summary,
    help text, status lines and the three buttons.

    Nothing is dropped as long as it can be made to fit. When the window is short for its text size the layout gives
    way in this order (the first step that fits wins; see `tiers` below): comfortable rows, rows squeezed to their
    minimum, smaller gaps, the summary in one line (Large / Extra large text only: the screen then uses its short
    wording), the summary in a column beside the card (when the window is wide); then the two help lines become one
    (Large / Extra large text and a wide window only); and only then the help text, and finally the summary, are left
    out. "subtitle_lines" (2, 1 or 0) and "summary_shape" ("grid", "row", "side" or None) say what was chosen.
    """
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh, head_h = tpx(LINE_H, k), tpx(TABLE_HEADER_H, k)
    ix, iw = inner[0], inner[2]
    status_h = 2 * lh + 2
    status = (ix, f["button_row"][1] - gap - status_h, iw, status_h)
    y0 = rect_bottom(header)
    cell_h = tpx(24, k)
    stacked_h = {"grid": 2 * cell_h, "row": cell_h}   # height of the summary above the table, by shape
    min_h, max_h, comfy_h = tpx(MIN_ROW_H, k), tpx(MAX_ROW_H, k), tpx(COMFORT_ROW_H, k)
    tight = max(2, gap // 2)

    card_w = tpx(150, k) if iw < 700 else clamp(int(iw * 0.30), tpx(200, k), tpx(360, k))
    side_w = tpx(SUMMARY_SIDE_W, k)
    side_ok = iw - 2 * gap - card_w - side_w >= tpx(SIDE_MIN_TABLE_W, k)
    big = textscale.text_level() in BIG_TEXT_LEVELS

    pager_h = tpx(PAGER_H, k)

    def room(sub, shape, g):
        """The height left for the table's rows (without its heading) with `sub` subtitle lines, this summary shape and gap `g`."""
        remaining = (status[1] - gap - (y0 + g) - (sub * lh + g if sub else 0)
                     - (stacked_h[shape] + g if shape in stacked_h else 0))
        return remaining - head_h

    # Paging: when all the rows cannot be comfortable (comfy_h) at the roomiest arrangement, the table shows one page of
    # as many comfortable rows as fit (at least MIN_PAGE_ROWS), and a pager row under it. Otherwise everything is on one page.
    per_page = rows
    if room(2, "grid", gap) // max(1, rows) < comfy_h:
        per_page = clamp((room(2, "grid", gap) - pager_h - gap) // comfy_h, min(MIN_PAGE_ROWS, rows), rows)
    paged = per_page < rows
    pages = -(-rows // per_page) if rows else 1
    shown = per_page   # rows drawn on a page (a short last page leaves the table the same height)

    def rows_fit(sub, shape, g):
        """The row height that is left for the table with `sub` subtitle lines, this summary shape and gap `g`."""
        return (room(sub, shape, g) - (pager_h + g if paged else 0)) // max(1, shown)

    # (subtitle lines, summary shape, gap between the blocks, smallest row height accepted), best first.
    shapes = ("grid", "row") if big else ("grid",)
    sub_options = [2] + ([1] if big and iw >= tpx(ONE_LINE_SUB_W, k) else []) + [0]
    tiers = []
    for sub in sub_options:
        for need, g in ((comfy_h, gap), (min_h, gap), (min_h, tight)):
            tiers += [(sub, shape, g, need) for shape in shapes]
        if side_ok:
            tiers += [(sub, "side", gap, min_h), (sub, "side", tight, min_h)]
    tiers.append((0, None, gap, 0))   # nothing else fits: no subtitle, no summary (the rows stay at their minimum)
    want_sub, shape, g, _need = next((t for t in tiers if rows_fit(*t[:3]) >= t[3]), tiers[-1])
    row_h = clamp(rows_fit(want_sub, shape, g), min_h, max_h)

    y = y0 + g
    subtitle = summary = None
    if want_sub:
        subtitle = (ix, y, iw, want_sub * lh)
        y += want_sub * lh + g
    if shape in stacked_h:
        summary = (ix, y, iw, stacked_h[shape])
        y += stacked_h[shape] + g
    table_h = head_h + shown * row_h
    table_w = iw - gap - card_w - (gap + side_w if shape == "side" else 0)
    table = (ix, y, table_w, table_h)
    card_x = ix + table_w + gap
    # The status text sits under the table only (it is as wide as the table), and the preview card reaches down to the
    # bottom of that text, so the card's bottom lines up with the last status line and the card has more height.
    status = (ix, status[1], table_w, status_h)
    card_h = max(table_h, rect_bottom(status) - y)
    card = (card_x, y, card_w, card_h)
    if shape == "side":
        # inset by the 5 / 2 px that the drawing code's frame around the summary sticks out by, so the frame is the column
        summary = inset((card_x + card_w + gap, y, side_w, table_h), 5, 2)
    compact = table_w < tpx(COMPACT_TABLE_W, k)
    summary_grid = {"grid": (4, 2), "row": (8, 1), "side": (1, 8)}.get(shape, (4, 2))

    pager = prev_page = next_page = page_label = None
    if paged:   # centred under the table
        pager = (table[0], table[1] + table_h + g, table_w, pager_h)
        btn_w = min(tpx(PAGER_BTN_W, k), max(1, (table_w - 2 * gap) // 3))
        prev_page = (pager[0], pager[1], btn_w, pager_h)
        next_page = (pager[0] + table_w - btn_w, pager[1], btn_w, pager_h)
        page_label = (prev_page[0] + btn_w + gap, pager[1], max(1, table_w - 2 * btn_w - 2 * gap), pager_h)

    aw = clamp(int(iw * 0.26), tpx(120, k), tpx(190, k))
    bw = clamp(int(iw * 0.14), tpx(80, k), tpx(120, k))
    _, right = buttons_in_row(f["button_row"], [], [aw, aw, bw], gap)

    leaves = [("header", header)]
    if subtitle:
        leaves.append(("subtitle", subtitle))
    if summary:
        leaves.append(("summary", summary))
    if paged:
        leaves += [("prev_page", prev_page), ("next_page", next_page)]
    leaves += [("table", table), ("card", card), ("status", status),
               ("abandon", right[0]), ("recover", right[1]), ("back", right[2])]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "subtitle_lines": want_sub, "summary": summary, "summary_grid": summary_grid, "summary_shape": shape,
        "table": table, "table_header": (table[0], table[1], table[2], head_h),
        "rows_top": table[1] + head_h, "row_h": row_h, "rows": rows,
        "per_page": per_page, "pages": pages, "paged": paged, "pager": pager,
        "prev_page": prev_page, "next_page": next_page, "page_label": page_label,
        "columns": table_columns(table[0], table[2], compact), "compact": compact, "card": card,
        "status": status, "abandon": right[0], "recover": right[1], "back": right[2],
        "leaves": leaves, "inside": [],
    }


def vehicles_buttons(width, height, recover_all=False):
    """The vehicles screen's button row as {name: rect}. ABANDON, RECOVER and BACK stay right-aligned exactly as in
    vehicles_layout; with `recover_all` (SANDBOX MODE only) RECOVER ALL is added at the far left of the row. If the
    window is too narrow for it to fit beside the other three, they are all shrunk together."""
    f = screen_frame(width, height)
    k, gap = f["k"], f["gap"]
    iw = f["inner"][2]
    aw = clamp(int(iw * 0.26), tpx(120, k), tpx(190, k))
    bw = clamp(int(iw * 0.14), tpx(80, k), tpx(120, k))
    x, y, w, h = f["button_row"]

    def right_aligned(names, widths):
        room = w - gap * (len(widths) - 1)
        total = sum(widths)
        if total > room:   # a narrow window: every button gets its share of what there is
            widths = [max(1, value * room // total) for value in widths]
        left = x + w - (sum(widths) + gap * (len(widths) - 1))
        rects = {}
        for name, value in zip(names, widths):
            rects[name] = (left, y, value, h)
            left += value + gap
        return rects

    rects = right_aligned(["abandon", "recover", "back"], [aw, aw, bw])
    if recover_all:
        room = rects["abandon"][0] - gap - x   # the space left of ABANDON
        if room >= tpx(80, k):
            rects = {"recover_all": (x, y, min(aw, room), h), **rects}
        else:   # too narrow for a left-hand button: share the row
            rects = right_aligned(["recover_all", "abandon", "recover", "back"], [aw, aw, aw, bw])
    return rects


def vehicle_row_at(width, height, pos, rows=VEHICLE_ROWS, page=0):
    """The index (into all `rows` vehicles, not just the page) of the vehicle table row under a window pixel, or None.
    `page` is the page the table is showing. Shared by the drawing code's geometry (vehicles_layout) and the click
    handling in main.py so the two cannot drift apart."""
    g = vehicles_layout(int(width), int(height), rows)
    per_page = g["per_page"]
    page = max(0, min(page, g["pages"] - 1))
    first = page * per_page
    on_page = min(per_page, rows - first)
    tx, ty, tw, _th = g["table"]
    mx, my = pos
    if not (tx <= mx < tx + tw and g["rows_top"] <= my < g["rows_top"] + g["row_h"] * on_page):
        return None
    return first + (my - g["rows_top"]) // g["row_h"]
