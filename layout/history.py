"""Layout of the event history screen: header, a subtitle row, one list panel (the rows are drawn by ui/history.py,
which wraps long messages) with a footer, and NEWER / OLDER / BACK (no pygame)."""
from .frame import screen_frame
from .geometry import (
    LINE_H, LIST_HEAD_GAP, buttons_in_row, clamp, layout_cache, rect_bottom, tpx,
)
from .lists import _list_panel, _split_footer


@layout_cache(32)
def history_layout(width, height):
    """Rectangles of the history screen. `rows` is where the wrapped history rows go (ui/history.py counts how many
    fit); `showing` / `page` are the two halves of the footer ("Rows 1-9 of 40" and a scroll hint)."""
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)
    subtitle = (inner[0], rect_bottom(header) + 2, inner[2], lh)
    top = rect_bottom(subtitle) + gap
    list_rect, content, footer = _list_panel(inner, top, f["button_row"][1] - gap, k)
    rows = (content[0], content[1], content[2], max(0, footer[1] - LIST_HEAD_GAP - content[1]))
    showing, hint = _split_footer(footer, 0.5)

    bw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    _, right = buttons_in_row(f["button_row"], [], [bw, bw, bw], gap)

    leaves = [("header", header), ("subtitle", subtitle), ("list", list_rect),
              ("newer", right[0]), ("older", right[1]), ("back", right[2])]
    inside = [("rows", rows, list_rect), ("footer", footer, list_rect)]
    groups = [("list parts", [("rows", rows), ("footer", footer)]),
              ("footer parts", [("showing", showing), ("hint", hint)])]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "list": list_rect, "rows": rows, "footer": footer, "showing": showing, "hint": hint,
        "newer": right[0], "older": right[1], "back": right[2],
        "leaves": leaves, "inside": inside, "groups": groups,
    }
