"""Layouts of the title and lore screens, which use the whole window and have no HUD (no pygame).
"""
from .convoy import calculate_layout
from .geometry import LINE_H, clamp, inset, layout_cache, rect_bottom, tpx


@layout_cache(16)
def title_layout(width, height):
    """Rectangles of the title screen: logo + name, the convoy scene (10:3), tagline, a big PLAY and LOAD GAME, hint,
    and a MENU button in the top right corner (CREDITS and QUIT GAME live in that menu)."""
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    area_w = w - 2 * margin
    menu_w, menu_h = tpx(120, k), tpx(42, k)
    menu = (w - margin - menu_w, margin, menu_w, menu_h)
    side = menu_w + gap   # the heading gives up this much on both sides, so it stays centred and clear of MENU
    head_h = clamp(int(h * 0.12), tpx(44, k), tpx(84, k))
    tag_h = tpx(28, k)
    btn_h = clamp(int(h * 0.095), tpx(44, k), tpx(68, k))
    hint_h = tpx(LINE_H, k) + 2
    fixed = head_h + tag_h + btn_h + hint_h + 4 * gap
    scene_h = max(60, min(int(area_w * 0.28), h - 2 * margin - fixed))
    scene_w = min(area_w, int(scene_h * 10 / 3))
    y = margin + max(0, (h - 2 * margin - (fixed + scene_h)) // 2)

    head = (margin + side, y, max(1, area_w - 2 * side), head_h)
    y += head_h + gap
    scene = (margin + (area_w - scene_w) // 2, y, scene_w, scene_h)
    y += scene_h + gap
    tagline = (margin, y, area_w, tag_h)
    y += tag_h + gap
    count, btn_gap = 2, 24
    bw = min(clamp(int(area_w * 0.3), tpx(160, k), tpx(300, k)), (area_w - btn_gap * (count - 1)) // count)
    bx = margin + (area_w - (count * bw + btn_gap * (count - 1))) // 2
    play = (bx, y, bw, btn_h)
    load = (bx + bw + btn_gap, y, bw, btn_h)
    y += btn_h + gap
    hint = (margin, y, area_w, hint_h)
    leaves = [("head", head), ("scene", scene), ("tagline", tagline), ("play", play), ("load", load), ("menu", menu),
              ("hint", hint)]
    return {"size": (w, h), "k": k, "head": head, "scene": scene, "tagline": tagline, "play": play, "load": load,
            "menu": menu, "hint": hint, "leaves": leaves, "inside": []}


@layout_cache(16)
def lore_layout(width, height):
    """Rectangles of the lore screen: one panel with heading, story text and BACK / START GAME, plus a hint."""
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    hint_h = tpx(LINE_H, k) + 2
    panel = (margin, margin, w - 2 * margin, h - 2 * margin - hint_h - gap)
    inner = inset(panel, 12)
    heading_h = tpx(34, k)
    btn_h = clamp(int(h * 0.07), tpx(34, k), tpx(46, k))
    heading = (inner[0], inner[1], inner[2], heading_h)
    row = (inner[0], rect_bottom(inner) - btn_h, inner[2], btn_h)
    text_y = rect_bottom(heading) + gap
    text = (inner[0], text_y, inner[2], row[1] - gap - text_y)
    back_w = tpx(135, k)
    start_w = min(tpx(220, k), max(tpx(100, k), inner[2] - 2 * (back_w + gap)))
    back = (inner[0], row[1], back_w, btn_h)
    start = (inner[0] + (inner[2] - start_w) // 2, row[1], start_w, btn_h)
    hint = (margin, rect_bottom(panel) + gap, w - 2 * margin, hint_h)
    leaves = [("heading", heading), ("text", text), ("back", back), ("start", start), ("hint", hint)]
    return {"size": (w, h), "k": k, "panel": panel, "heading": heading, "text": text, "back": back, "start": start,
            "hint": hint, "leaves": leaves, "inside": []}
