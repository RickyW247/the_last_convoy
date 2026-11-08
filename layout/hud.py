"""The HUD's layout (no pygame): the identity block on the left and a tidy grid of stat cells beside it.

The grid is HUD_COLS columns by 2 rows. Every cell is a label line with a bar under it; the cargo cell is two columns
wide because it holds three supplies in one shared bar and their numbers. Row 1 is the state of the convoy, row 2 is
what it carries:

    FUEL           CONVOY HP        HORDE (+ its danger state)
    CARGO (two columns, food / water / scrap in one bar)       SURVIVORS (seats)
"""
from textscale import tpx

HUD_COLS = 3

# name -> (column, row, columns spanned); the order is also the order the cells are drawn in.
HUD_CELLS = {
    "fuel": (0, 0, 1),
    "convoy": (1, 0, 1),
    "horde": (2, 0, 1),
    "cargo": (0, 1, 2),
    "survivors": (2, 1, 1),
}


def hud_layout(layout):
    """Rectangles inside the HUD of a calculate_layout() result, all (x, y, width, height) tuples:

      "identity"  the title / location / day block on the left,
      "cells"     {name: {"rect": the whole cell, "label": the label line, "bar": the bar}} for every HUD_CELLS name,
      "leaves"    [(name, rect)] that must lie inside the window and not overlap (for the layout tests),
      "inside"    [(name, child, parent)] that must lie inside the HUD panel.
    """
    hx, hy, hw, hh = layout["hud"]
    mx = layout["menu"][0]
    margin, k = layout["margin"], layout["k"]

    x = hx + margin
    right = mx - 8                                    # the MENU button sits to the right of the grid
    start_x = max(x + tpx(190, k), hx + int(hw * 0.25))
    col_w = max(1, right - start_x) / HUD_COLS
    gap = 10                                          # between neighbouring cells

    label_h, bar_gap, bar_h = tpx(20, k), tpx(20, k), tpx(7, k)
    row_pitch = tpx(40, k)
    top = hy + tpx(10, k)

    cells = {}
    for name, (col, row, span) in HUD_CELLS.items():
        cx = int(start_x + col * col_w)
        cy = top + row * row_pitch
        cw = max(20, int((col + span) * col_w - col * col_w - gap))
        cells[name] = {
            "rect": (cx, cy, cw, bar_gap + bar_h),
            "label": (cx, cy, cw, label_h),
            "bar": (cx, cy + bar_gap, cw, bar_h),
        }

    identity = (x, hy + tpx(6, k), max(40, start_x - x - 10), max(1, int(hh) - tpx(12, k)))

    leaves = [("hud_identity", identity)] + [(f"hud_{name}", c["rect"]) for name, c in cells.items()]
    inside = [(name, rect, tuple(layout["hud"])) for name, rect in leaves]
    return {"identity": identity, "cells": cells, "leaves": leaves, "inside": inside}
