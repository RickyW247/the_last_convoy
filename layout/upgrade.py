"""Layout of the vehicle upgrade screen: the table of upgrades, the vehicle card and the buttons (no pygame).

Imported from its own module (layout/__init__.py is not edited for it), like layout/popups.py.

A vehicle can have more upgrades than fit the table (small windows, larger text): the table then shows one page of
`per_page` rows with a "PREV  Page 1 / 2  NEXT" row under it, the same way the vehicles screen pages its table.
"""
from .frame import screen_frame
from .geometry import (LINE_H, TABLE_HEADER_H, buttons_in_row, clamp, fraction_columns, layout_cache, rect_bottom,
                       tpx)

MIN_ROW_H, MAX_ROW_H = 24, 40
MIN_PAGE_ROWS = 4         # a paged table shows at least this many upgrades per page
PAGER_H = 26              # height of the "PREV  Page 1 / 2  NEXT" row under a paged table (scaled by k)
PAGER_BTN_W = 90          # width of its PREV / NEXT buttons (scaled by k)
# Column widths of the upgrade table as fractions of the table width: UPGRADE, EFFECT, COST (also the INSTALLED mark).
_COLUMNS = (0.31, 0.44, 0.25)
CELL_PAD = 4
PICTURE_MIN_H = 50       # the vehicle picture box of the card is never shorter than this (the text below is cut first)


def upgrade_card_layout(card, k=1.0):
    """Inside the card: the vehicle's name, its picture and the text under it (description, then the stat changes)."""
    x, y, w, h = card
    p, lh = tpx(8, k), tpx(LINE_H, k)
    ix, iw = x + p, max(0, w - 2 * p)
    name = (ix, y + p, iw, tpx(22, k))
    top = rect_bottom(name) + 4
    bottom = y + h - p
    room = max(0, bottom - top)
    picture_h = clamp(int(room * 0.42), min(PICTURE_MIN_H, room), max(PICTURE_MIN_H, tpx(140, k)))
    picture = (ix, top, iw, picture_h)
    text_top = rect_bottom(picture) + 4
    text = (ix, text_top, iw, max(0, bottom - text_top))
    return {"name": name, "picture": picture, "text": text, "line_h": lh}


@layout_cache(16)
def upgrade_layout(width, height, rows=1):
    """Rectangles of the upgrade screen for a vehicle with `rows` upgrades: table (with its columns and rows), vehicle card,
    status lines and the INSTALL UPGRADE / BACK buttons."""
    rows = max(1, int(rows))
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh, head_h = tpx(LINE_H, k), tpx(TABLE_HEADER_H, k)
    ix, iw = inner[0], inner[2]
    status_h = 2 * lh + 2
    status = (ix, f["button_row"][1] - gap - status_h, iw, status_h)
    y = rect_bottom(header) + gap
    space = max(0, status[1] - gap - y)

    # Paging: when the rows cannot all be at least MIN_ROW_H high, the table shows one page of as many rows as fit (at least
    # MIN_PAGE_ROWS) and a pager row under it. Otherwise everything is on one page and there is no pager.
    min_h, pager_h = tpx(MIN_ROW_H, k), tpx(PAGER_H, k)
    per_page = rows
    if (space - head_h) // rows < min_h:
        per_page = clamp((space - head_h - pager_h - gap) // min_h, min(MIN_PAGE_ROWS, rows), rows)
    paged = per_page < rows
    pages = -(-rows // per_page)
    room = space - head_h - (pager_h + gap if paged else 0)
    row_h = clamp(room // per_page, min_h, tpx(MAX_ROW_H, k))
    table_h = min(space, head_h + per_page * row_h)   # a short last page leaves the table the same height
    card_w = tpx(150, k) if iw < 700 else clamp(int(iw * 0.32), tpx(220, k), tpx(380, k))
    table_w = iw - gap - card_w
    table = (ix, y, table_w, table_h)
    card = (ix + table_w + gap, y, card_w, space)

    pager = prev_page = next_page = page_label = None
    if paged:   # under the table
        pager = (table[0], table[1] + table_h + gap, table_w, pager_h)
        btn_w = min(tpx(PAGER_BTN_W, k), max(1, (table_w - 2 * gap) // 3))
        prev_page = (pager[0], pager[1], btn_w, pager_h)
        next_page = (pager[0] + table_w - btn_w, pager[1], btn_w, pager_h)
        page_label = (prev_page[0] + btn_w + gap, pager[1], max(1, table_w - 2 * btn_w - 2 * gap), pager_h)

    aw = clamp(int(iw * 0.26), tpx(120, k), tpx(190, k))
    bw = clamp(int(iw * 0.14), tpx(80, k), tpx(120, k))
    _, right = buttons_in_row(f["button_row"], [], [aw, bw], gap)

    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "table": table,
        "table_header": (table[0], table[1], table[2], head_h), "rows_top": table[1] + head_h, "row_h": row_h,
        "rows": rows, "per_page": per_page, "pages": pages, "paged": paged, "pager": pager, "prev_page": prev_page,
        "next_page": next_page, "page_label": page_label, "columns": fraction_columns(table[0], table[2], _COLUMNS), "card": card, "status": status,
        "install": right[0], "back": right[1],
        "leaves": [("header", header), ("table", table), ("card", card), ("status", status),
                   ("install", right[0]), ("back", right[1])]
                  + ([("prev_page", prev_page), ("next_page", next_page)] if paged else []),
        "inside": [],
    }


def upgrade_row_at(width, height, pos, rows, page=0):
    """The index (in the whole list of `rows` upgrades) of the table row under a window pixel on page `page`, or None
    (shared by the drawing and main.py's clicks)."""
    g = upgrade_layout(int(width), int(height), rows)
    tx, _ty, tw, _th = g["table"]
    mx, my = pos
    first = max(0, min(page, g["pages"] - 1)) * g["per_page"]
    on_page = min(g["per_page"], g["rows"] - first)
    if not (tx <= mx < tx + tw and g["rows_top"] <= my < g["rows_top"] + g["row_h"] * on_page):
        return None
    return first + (my - g["rows_top"]) // g["row_h"]
