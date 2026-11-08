"""The frame shared by the menu, vehicles, instructions, survivors, missions and map screens (no pygame).
"""
import math

from .convoy import calculate_layout
from .geometry import as_ints, clamp, inset, layout_cache, rect_bottom, tpx


@layout_cache(16)
def screen_frame(width, height):
    """The frame shared by the menu, vehicles and instructions screens.

    The convoy HUD stays at the top; below it is one big panel with a header row (title), a button row at the
    bottom and the body between them. Everything is derived from calculate_layout's margin, gap and text factor k
    (also returned as "k": the rows that hold text are scaled by it).
    """
    base = calculate_layout(width, height)
    w, h = base["width"], base["height"]
    margin, gap, k = base["margin"], base["gap"], base["k"]
    hud = as_ints(base["hud"])
    hud = (hud[0], hud[1], hud[2], int(math.ceil(base["hud"][1] + base["hud"][3])) - hud[1])
    top = rect_bottom(hud) + gap
    panel = (margin, top, w - 2 * margin, h - margin - top)
    pad = clamp(panel[2] // 60, 8, 16)
    inner = inset(panel, pad)
    title_h = clamp(int(inner[3] * 0.09), tpx(22, k), tpx(34, k))
    btn_h = clamp(int(inner[3] * 0.085), tpx(28, k), tpx(42, k))
    header = (inner[0], inner[1], inner[2], title_h)
    button_row = (inner[0], rect_bottom(inner) - btn_h, inner[2], btn_h)
    body_y = rect_bottom(header) + gap
    body = (inner[0], body_y, inner[2], button_row[1] - gap - body_y)
    return {
        "size": (w, h), "margin": margin, "gap": gap, "k": k, "hud": hud, "panel": panel, "pad": pad, "inner": inner,
        "header": header, "body": body, "button_row": button_row, "btn_h": btn_h, "title_h": title_h,
    }
