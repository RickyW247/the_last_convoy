"""Layout of the achievements screen: header, a subtitle row, a list panel of achievement cards (as many per page as
fit) with a "PAGE x/y" footer, RESET (left) and PREVIOUS / NEXT / BACK (right) (no pygame). Built like the missions screen (layout/lists.py)."""
from .frame import screen_frame
from .geometry import LINE_H, LIST_HEAD_GAP, buttons_in_row, clamp, layout_cache, rect_bottom, tpx
from .lists import _list_panel

ACH_CARD_MIN_H, ACH_CARD_MAX_H = 84, 112   # the pitch (card height + gap) of the achievement cards, for the default text
ACH_CARD_GAP = 6


@layout_cache(64)
def achievement_card_layout(card, k=1.0):
    """Inside one card: name and status on the top row, the description under them, then the reward (left) and the
    date it was earned (right) on the bottom row."""
    x, y, w, h = card
    p, row_h, lh = tpx(8, k), tpx(22, k), tpx(LINE_H, k)
    status_w = tpx(112 if w >= 330 else 92, k)
    title = (x + p, y + p, max(1, w - 2 * p - status_w - 8), row_h)
    status = (x + w - p - status_w, y + p, status_w, row_h)
    inner_w = max(1, w - 2 * p)
    bottom = (x + p, y + h - p - lh, inner_w, lh)
    reward_w = int(inner_w * 0.64)
    reward = (bottom[0], bottom[1], reward_w, lh)
    earned = (bottom[0] + reward_w, bottom[1], inner_w - reward_w, lh)
    desc_top = title[1] + title[3] + 2
    description = (x + p, desc_top, inner_w, max(1, bottom[1] - 2 - desc_top))
    return {"title": title, "status": status, "description": description, "reward": reward, "earned": earned}


@layout_cache(32)
def achievements_layout(width, height):
    """Rectangles of the achievements screen. `per_page` is how many cards fit the list (the one number the drawing
    code, buttons.py and paging.py all use, so the page numbers always match what is on screen)."""
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)
    subtitle = (inner[0], rect_bottom(header) + 2, inner[2], lh)
    top = rect_bottom(subtitle) + gap
    list_rect, content, footer = _list_panel(inner, top, f["button_row"][1] - gap, k)

    cards_top = content[1]
    area_h = max(0, footer[1] - LIST_HEAD_GAP - cards_top)
    card_min, card_max = tpx(ACH_CARD_MIN_H, k), tpx(ACH_CARD_MAX_H, k)
    per_page = max(1, area_h // card_min)
    pitch = clamp(area_h // per_page, card_min, card_max)
    pitch = max(1, min(pitch, area_h)) if area_h else 1
    cards = tuple((content[0], cards_top + i * pitch, content[2], max(1, pitch - ACH_CARD_GAP)) for i in range(per_page))
    card_parts = tuple(achievement_card_layout(c, k) for c in cards)

    pw = clamp(int(inner[2] * 0.15), tpx(90, k), tpx(130, k))
    bw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    rw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    left, right = buttons_in_row(f["button_row"], [rw], [pw, pw, bw], gap)   # RESET sits at the left end

    names = ("title", "status", "description", "reward", "earned")
    leaves = [("header", header), ("subtitle", subtitle), ("list", list_rect),
              ("reset", left[0]), ("prev", right[0]), ("next", right[1]), ("back", right[2])]
    inside = [(f"card{i}", c, list_rect) for i, c in enumerate(cards)] + [("footer", footer, list_rect)]
    for i, (card, parts) in enumerate(zip(cards, card_parts)):
        inside += [(f"card{i}_{name}", parts[name], card) for name in names]
    groups = [("list parts", [(f"card{i}", c) for i, c in enumerate(cards)] + [("footer", footer)])]
    groups += [(f"card{i} parts", [(name, parts[name]) for name in names]) for i, parts in enumerate(card_parts)]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "list": list_rect, "cards": cards, "card_parts": card_parts, "per_page": per_page, "footer": footer,
        "reset": left[0], "prev": right[0], "next": right[1], "back": right[2],
        "leaves": leaves, "inside": inside, "groups": groups,
    }
