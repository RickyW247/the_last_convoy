"""Layouts of the survivors and missions screens: list panels, rows / cards per page and footers (no pygame).

The sizes below are for the default text; every function multiplies the rows that hold text by the frame's k.
"""
from .frame import screen_frame
from .geometry import (
    LINE_H, LIST_HEAD_GAP, TABLE_HEADER_H, buttons_in_row, clamp, fraction_columns, inset, layout_cache, page_count,
    rect_bottom, tpx,
)


LIST_PAD = 6                               # padding inside a list panel
LIST_FOOTER_H = 20                         # the "Showing 1-8 of 12" / "PAGE 1/2" row at the bottom of a list
SURVIVOR_ROW_MIN_H, SURVIVOR_ROW_MAX_H = 30, 36
SURVIVOR_COLUMNS = (0.34, 0.16, 0.10, 0.40)   # NAME, GENDER, AGE, VEHICLE as fractions of the list width
MISSION_CARD_MIN_H, MISSION_CARD_MAX_H = 114, 144   # the pitch (card height + gap) of the mission cards
MISSION_CARD_GAP = 6
MISSION_LINE_H = 22                        # one objective line in a mission card


def _list_panel(inner, top, bottom, k=1.0):
    """A list panel between `top` and `bottom` (full inner width): (panel, content, footer)."""
    panel = (inner[0], top, inner[2], max(0, bottom - top))
    content = inset(panel, LIST_PAD)
    footer_h = tpx(LIST_FOOTER_H, k)
    footer = (content[0], max(content[1], rect_bottom(content) - footer_h), content[2],
              min(footer_h, content[3]))
    return panel, content, footer


def _split_footer(footer, left_fraction):
    """The footer's left and right halves, as (left, right) rectangles."""
    fx, fy, fw, fh = footer
    left_w = int(fw * left_fraction)
    return (fx, fy, left_w, fh), (fx + left_w, fy, fw - left_w, fh)


@layout_cache(32)
def survivors_layout(width, height):
    """Rectangles of the survivors screen: header, subtitle + total, a row of three condition cells (hunger, thirst,
    injury), a list panel (column headings, rows, footer) and PREVIOUS / NEXT / BACK. `per_page` is how many survivor
    rows fit the available height."""
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)
    info_y = rect_bottom(header) + 2
    sub_w = int(inner[2] * 0.62)
    subtitle = (inner[0], info_y, sub_w, lh)
    total = (inner[0] + sub_w + gap, info_y, inner[2] - sub_w - gap, lh)
    cond_y = rect_bottom(subtitle) + 2
    cond_w = inner[2] // 3
    widths = (cond_w - gap, cond_w - gap, inner[2] - 2 * cond_w)   # the last cell takes what is left of the width
    conditions = tuple((inner[0] + i * cond_w, cond_y, widths[i], lh) for i in range(3))   # hunger, thirst, injury
    top = rect_bottom(subtitle) + 2 + lh + gap
    list_rect, content, footer = _list_panel(inner, top, f["button_row"][1] - gap, k)

    heading = (content[0], content[1], content[2], tpx(TABLE_HEADER_H, k))
    rows_top = rect_bottom(heading) + LIST_HEAD_GAP
    area_h = max(0, footer[1] - LIST_HEAD_GAP - rows_top)
    row_min, row_max = tpx(SURVIVOR_ROW_MIN_H, k), tpx(SURVIVOR_ROW_MAX_H, k)
    per_page = max(1, area_h // row_min)
    row_h = clamp(area_h // per_page, row_min, row_max)
    row_h = max(1, min(row_h, area_h)) if area_h else 1
    rows = (content[0], rows_top, content[2], per_page * row_h)
    showing, page = _split_footer(footer, 0.6)
    columns = fraction_columns(content[0], content[2], SURVIVOR_COLUMNS)

    pw = clamp(int(inner[2] * 0.15), tpx(90, k), tpx(130, k))
    bw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    _, right = buttons_in_row(f["button_row"], [], [pw, pw, bw], gap)

    leaves = [("header", header), ("subtitle", subtitle), ("total", total), ("list", list_rect),
              ("prev", right[0]), ("next", right[1]), ("back", right[2])]
    leaves += [(f"condition{i}", c) for i, c in enumerate(conditions)]
    inside = [("heading", heading, list_rect), ("rows", rows, list_rect), ("footer", footer, list_rect)]
    inside += [(f"column{i}", (x, heading[1], w, heading[3]), heading) for i, (x, w) in enumerate(columns)]
    groups = [("list parts", [("heading", heading), ("rows", rows), ("footer", footer)]),
              ("columns", [(f"column{i}", (x, heading[1], w, heading[3])) for i, (x, w) in enumerate(columns)]),
              ("footer parts", [("showing", showing), ("page", page)])]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "total": total, "conditions": conditions,
        "list": list_rect, "heading": heading, "columns": columns, "rows_top": rows_top, "row_h": row_h,
        "per_page": per_page, "rows": rows, "footer": footer, "showing": showing, "page": page,
        "prev": right[0], "next": right[1], "back": right[2],
        "leaves": leaves, "inside": inside, "groups": groups,
    }


def survivors_per_page(width, height):
    """How many survivor rows fit one page of the survivors screen (at least 1). The one function the drawing code
    and buttons.py both use, so the page numbers always agree with what is on screen."""
    return survivors_layout(int(width), int(height))["per_page"]


@layout_cache(64)
def mission_card_layout(card, k=1.0):
    """Inside one mission card: title and status on the top row, the objectives below them, "Objectives: a/b" at
    the bottom left and the ACCEPT / ABANDON button at the bottom right. `lines` is how many objective lines fit.
    `k` is the text factor of the window (rows are scaled by it)."""
    x, y, w, h = card
    p, row_h, lh = tpx(8, k), tpx(22, k), tpx(MISSION_LINE_H, k)   # lh: a row of the larger card text
    status_w = tpx(112 if w >= 330 else 92, k)
    title = (x + p, y + p, max(1, w - 2 * p - status_w - 8), row_h)
    status = (x + w - p - status_w, y + p, status_w, row_h)
    btn_w = clamp(int(w * 0.22), tpx(90, k), tpx(130, k))
    btn_h = clamp(int(h * 0.30), tpx(24, k), tpx(32, k))
    button = (x + w - p - btn_w, y + h - p - btn_h, btn_w, btn_h)
    text_w = max(1, button[0] - 8 - (x + p))
    footer = (x + p, y + h - p - lh, text_w, lh)
    obj_top = rect_bottom(title) + 4
    obj_h = max(0, footer[1] - 2 - obj_top)
    objectives = (x + p, obj_top, text_w, obj_h)
    return {"title": title, "status": status, "objectives": objectives, "footer": footer, "button": button,
            "lines": obj_h // tpx(MISSION_LINE_H, k)}


@layout_cache(32)
def missions_layout(width, height):
    """Rectangles of the missions screen: header with the ACTIVE / COMPLETED filter buttons, subtitle, a list
    panel holding `per_page` mission cards and a "PAGE x/y" footer, and PREVIOUS / NEXT / BACK."""
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)
    fw = clamp(int(inner[2] * 0.17), tpx(90, k), tpx(150, k))
    _, filters = buttons_in_row(header, [], [fw, fw], gap)
    title = (header[0], header[1], max(1, filters[0][0] - gap - header[0]), header[3])
    subtitle = (inner[0], rect_bottom(header) + 2, inner[2], lh)
    top = rect_bottom(subtitle) + gap
    list_rect, content, footer = _list_panel(inner, top, f["button_row"][1] - gap, k)

    cards_top = content[1]
    area_h = max(0, footer[1] - LIST_HEAD_GAP - cards_top)
    card_min, card_max = tpx(MISSION_CARD_MIN_H, k), tpx(MISSION_CARD_MAX_H, k)
    per_page = max(1, area_h // card_min)
    pitch = clamp(area_h // per_page, card_min, card_max)
    pitch = max(1, min(pitch, area_h)) if area_h else 1
    cards = tuple((content[0], cards_top + i * pitch, content[2], max(1, pitch - MISSION_CARD_GAP))
                  for i in range(per_page))
    card_parts = tuple(mission_card_layout(c, k) for c in cards)

    pw = clamp(int(inner[2] * 0.15), tpx(90, k), tpx(130, k))
    bw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    _, right = buttons_in_row(f["button_row"], [], [pw, pw, bw], gap)

    leaves = [("title", title), ("active", filters[0]), ("completed", filters[1]), ("subtitle", subtitle),
              ("list", list_rect), ("prev", right[0]), ("next", right[1]), ("back", right[2])]
    inside = [(f"card{i}", c, list_rect) for i, c in enumerate(cards)] + [("footer", footer, list_rect)]
    for i, (card, parts) in enumerate(zip(cards, card_parts)):
        inside += [(f"card{i}_{name}", parts[name], card)
                   for name in ("title", "status", "objectives", "footer", "button")]
    groups = [("list parts", [(f"card{i}", c) for i, c in enumerate(cards)] + [("footer", footer)])]
    groups += [(f"card{i} parts", [(name, parts[name])
                                   for name in ("title", "status", "objectives", "footer", "button")])
               for i, parts in enumerate(card_parts)]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "title": title,
        "active": filters[0], "completed": filters[1], "subtitle": subtitle, "list": list_rect,
        "cards": cards, "card_parts": card_parts, "per_page": per_page, "footer": footer,
        "prev": right[0], "next": right[1], "back": right[2],
        "leaves": leaves, "inside": inside, "groups": groups,
    }


def missions_per_page(width, height):
    """How many mission cards fit one page of the missions screen (at least 1); shared by drawing and buttons."""
    return missions_layout(int(width), int(height))["per_page"]
