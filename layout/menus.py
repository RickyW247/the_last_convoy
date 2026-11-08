"""Layouts of the pause menu and its pages: menu, difficulty, settings, credits and instructions (no pygame).
"""
from .frame import screen_frame
from .geometry import LINE_H, buttons_in_row, clamp, layout_cache, rect_bottom, rect_right, tpx


NOTES_H = 4 * LINE_H         # the two difficulty notes under the menu cards
MENU_CARD_MIN_H, MENU_CARD_MAX_H, MENU_CARD_MAX_W = 200, 300, 420
MENU_ITEMS = ("settings", "instructions", "saves", "mute")                # the pause menu's buttons, top to bottom ...
MENU_RUN_ITEMS = ("restart", "title")                            # ... plus these two while a run is in progress
MENU_TITLE_ITEMS = ("achievements", "credits")                   # ... or ACHIEVEMENTS and CREDITS instead, in the menu opened from the title screen
MENU_LAST_ITEMS = ("quit",)                                      # ... and always QUIT GAME at the bottom
MENU_ITEM_MAX_H = 48


# ---- Menu --------------------------------------------------------------------------------------------------------
@layout_cache(64)
def menu_card_layout(card, k=1.0):
    """Inside one difficulty card: the name, the body for the stats text and the select button."""
    x, y, w, h = card
    cp = tpx(10, k)
    name_h = tpx(34 if h >= tpx(230, k) else 26, k)
    name = (x + cp, y + cp, w - 2 * cp, name_h)
    btn_h = clamp(int(h * 0.15), tpx(26, k), tpx(40, k))
    bw = min(w - 2 * cp, tpx(220, k))
    button = (x + (w - bw) // 2, y + h - cp - btn_h, bw, btn_h)
    body_y = rect_bottom(name) + 4
    body = (x + cp, body_y, w - 2 * cp, max(0, button[1] - 6 - body_y))
    return {"name": name, "body": body, "button": button}


@layout_cache(16)
def difficulty_layout(width, height):
    """Rectangles of the difficulty screen: header, subtitle, three difficulty cards, notes and BACK."""
    f = screen_frame(width, height)
    gap, inner, header, panel, k = f["gap"], f["inner"], f["header"], f["panel"], f["k"]
    lh, notes_h = tpx(LINE_H, k), tpx(NOTES_H, k)
    subtitle = (inner[0], rect_bottom(header) + 2, inner[2], lh)
    top = rect_bottom(subtitle) + gap
    bottom = f["button_row"][1] - gap
    avail = bottom - top

    with_notes = avail - notes_h - gap >= tpx(MENU_CARD_MIN_H, k)
    card_h = min(avail - (notes_h + gap if with_notes else 0), tpx(MENU_CARD_MAX_H, k))
    card_h = max(0, card_h)
    card_w = max(1, min((inner[2] - 2 * gap) // 3, tpx(MENU_CARD_MAX_W, k)))
    x0 = inner[0] + (inner[2] - (3 * card_w + 2 * gap)) // 2
    cards = tuple((x0 + i * (card_w + gap), top, card_w, card_h) for i in range(3))
    notes = (inner[0], top + card_h + gap, inner[2], notes_h) if with_notes else None

    _, right = buttons_in_row(f["button_row"], [], [tpx(135, k)], gap)
    leaves = [("header", header), ("subtitle", subtitle)]
    leaves += [(f"card{i}", c) for i, c in enumerate(cards)]
    if notes:
        leaves.append(("notes", notes))
    leaves.append(("back", right[0]))
    difficulty_buttons = tuple(menu_card_layout(c, k)["button"] for c in cards)
    inside = [(f"card{i}_button", b, cards[i]) for i, b in enumerate(difficulty_buttons)]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "cards": cards, "difficulty_buttons": difficulty_buttons, "notes": notes,
        "back": right[0],
        "leaves": leaves, "inside": inside,
    }


@layout_cache(16)
def menu_layout(width, height, in_run=False):
    """Rectangles of the pause menu: header and a centred column of buttons in "items" order (SETTINGS,
    INSTRUCTIONS, SAVE / LOAD, MUTE MUSIC and, when `in_run` (a run has started), RESTART GAME and TITLE SCREEN, or
    ACHIEVEMENTS and CREDITS when not, then QUIT GAME), plus BACK in the button row."""
    f = screen_frame(width, height)
    gap, inner, header, body, panel, k = f["gap"], f["inner"], f["header"], f["body"], f["panel"], f["k"]
    names = MENU_ITEMS + (MENU_RUN_ITEMS if in_run else MENU_TITLE_ITEMS) + MENU_LAST_ITEMS
    count = len(names)
    item_gap = min(gap, 10)
    item_h = clamp((body[3] - (count - 1) * item_gap) // count, tpx(20, k), tpx(MENU_ITEM_MAX_H, k))
    item_w = min(body[2], clamp(int(body[2] * 0.45), tpx(200, k), tpx(340, k)))
    column_h = count * item_h + (count - 1) * item_gap
    x = body[0] + (body[2] - item_w) // 2
    y0 = body[1] + max(0, (body[3] - column_h) // 2)
    items = tuple((x, y0 + i * (item_h + item_gap), item_w, item_h) for i in range(count))
    _, right = buttons_in_row(f["button_row"], [], [tpx(135, k)], gap)
    leaves = [("header", header)] + list(zip(names, items)) + [("back", right[0])]
    inside = [(name, rect, body) for name, rect in zip(names, items)]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "body": body,
        "items": items, **dict(zip(names, items)), "back": right[0],
        "leaves": leaves, "inside": inside,
    }


SAVE_SLOTS = 3   # savegame.SLOT_COUNT (repeated here: the layout package imports nothing but geometry)


@layout_cache(16)
def saves_layout(width, height):
    """Rectangles of the SAVE / LOAD page of the pause menu: header, one card per save slot (a text area on the left,
    then SAVE, LOAD and DELETE buttons on the right), a one-line note under the cards and BACK in the button row."""
    f = screen_frame(width, height)
    gap, header, body, panel, k = f["gap"], f["header"], f["body"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)
    note = (body[0], rect_bottom(body) - lh, body[2], lh)
    card_gap = min(gap, 10)
    top = body[1]
    avail = max(0, note[1] - gap - top)
    card_h = clamp((avail - (SAVE_SLOTS - 1) * card_gap) // SAVE_SLOTS, tpx(28, k), tpx(110, k))
    pad = tpx(8, k)
    btn_h = max(1, min(tpx(40, k), card_h - 2 * pad))
    btn_w = clamp(int(body[2] * 0.14), tpx(70, k), tpx(110, k))
    slots, leaves, inside = [], [("header", header)], []
    for i in range(SAVE_SLOTS):
        card = (body[0], top + i * (card_h + card_gap), body[2], card_h)
        y = card[1] + (card_h - btn_h) // 2
        delete = (rect_right(card) - pad - btn_w, y, btn_w, btn_h)
        load = (delete[0] - gap - btn_w, y, btn_w, btn_h)
        save = (load[0] - gap - btn_w, y, btn_w, btn_h)
        info = (card[0] + pad, card[1], max(1, save[0] - gap - card[0] - pad), card_h)
        slots.append({"card": card, "info": info, "save": save, "load": load, "delete": delete})
        inside.append((f"card{i}", card, body))
        leaves += [(f"info{i}", info), (f"save{i}", save), (f"load{i}", load), (f"delete{i}", delete)]
    _, right = buttons_in_row(f["button_row"], [], [tpx(135, k)], gap)
    leaves += [("note", note), ("back", right[0])]
    inside.append(("note", note, body))
    return {"size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "body": body,
            "slots": tuple(slots), "note": note, "back": right[0], "leaves": leaves, "inside": inside}


@layout_cache(16)
def settings_layout(width, height):
    """Settings layout: music volume and sound-effect volume (each minus / bar / plus), text size and fullscreen rows, then the accessibility
    toggles. Every row is a label on the left and its button on the right; the row height shrinks (to a minimum)
    when the window is short, so that all rows fit."""

    f = screen_frame(width, height)
    gap, inner, header, body, panel, k = (
        f["gap"], f["inner"], f["header"], f["body"], f["panel"], f["k"]
    )

    lh = tpx(LINE_H, k)
    row_gap = min(gap, 8)

    # Six rows (music volume, sound-effect volume, text size, fullscreen, two accessibility toggles) share what is
    # left of the body once the one-line note, the accessibility heading and the gaps are taken off.
    fixed = 3 * gap + 4 * row_gap + 2 * lh + 8
    row_h = clamp((body[3] - fixed) // 7, tpx(20, k), tpx(40, k))

    # MUSIC VOLUME ROW
    row = (body[0], body[1], body[2], row_h)

    label_w = clamp(int(row[2] * 0.22), tpx(90, k), tpx(200, k))
    label = (row[0], row[1], label_w, row_h)

    button_w = min(tpx(35, k), max(tpx(26, k), int(row[2] * 0.08)))

    minus = (rect_right(label) + gap, row[1], button_w, row_h)
    plus = (rect_right(row) - button_w, row[1], button_w, row_h)

    bar_h = min(14, row_h - 8)
    bar_x = rect_right(minus) + gap
    bar = (bar_x, row[1] + (row_h - bar_h) // 2, max(1, plus[0] - gap - bar_x), bar_h)

    # SOUND EFFECT VOLUME ROW: the same shape as the music row (label, minus, bar, plus)
    sfx_row = (body[0], rect_bottom(row) + row_gap, body[2], row_h)
    sfx_label = (sfx_row[0], sfx_row[1], label_w, row_h)
    sfx_minus = (rect_right(sfx_label) + gap, sfx_row[1], button_w, row_h)
    sfx_plus = (rect_right(sfx_row) - button_w, sfx_row[1], button_w, row_h)
    sfx_bar_x = rect_right(sfx_minus) + gap
    sfx_bar = (sfx_bar_x, sfx_row[1] + (row_h - bar_h) // 2, max(1, sfx_plus[0] - gap - sfx_bar_x), bar_h)

    note = (body[0], rect_bottom(sfx_row) + gap, body[2], lh)   # one line: both volumes as percentages

    # TEXT SIZE ROW: label on the left, a button showing the current level on the right
    size_w = clamp(int(row[2] * 0.20), tpx(110, k), tpx(170, k))
    textsize_row = (body[0], rect_bottom(note) + gap, body[2], row_h)
    textsize_label = (textsize_row[0], textsize_row[1], textsize_row[2] - size_w - gap, row_h)
    textsize = (rect_right(textsize_row) - size_w, textsize_row[1], size_w, row_h)

    toggle_w = clamp(int(row[2] * 0.14), tpx(70, k), tpx(110, k))

    # FULLSCREEN ROW: label on the left, an ON / OFF button on the right
    fullscreen_row = (body[0], rect_bottom(textsize_row) + row_gap, body[2], row_h)
    fullscreen_label = (fullscreen_row[0], fullscreen_row[1], fullscreen_row[2] - toggle_w - gap, row_h)
    fullscreen = (rect_right(fullscreen_row) - toggle_w, fullscreen_row[1], toggle_w, row_h)

    # DIFFICULTY ROW: label on the left, a button showing the current level on the right (it opens the difficulty screen)
    difficulty_row = (body[0], rect_bottom(fullscreen_row) + row_gap, body[2], row_h)
    difficulty_label = (difficulty_row[0], difficulty_row[1], difficulty_row[2] - size_w - gap, row_h)
    difficulty = (rect_right(difficulty_row) - size_w, difficulty_row[1], size_w, row_h)

    # ACCESSIBILITY
    access = (body[0], rect_bottom(difficulty_row) + gap, body[2], lh + 4)

    rows = []
    y = rect_bottom(access) + 4

    for _ in range(2):
        rows.append((body[0], y, body[2], row_h))
        y += row_h + row_gap

    contrast_row, colorblind_row = rows

    contrast_label = (contrast_row[0], contrast_row[1], contrast_row[2] - toggle_w - gap, row_h)
    contrast = (rect_right(contrast_row) - toggle_w, contrast_row[1], toggle_w, row_h)

    colorblind_label = (colorblind_row[0], colorblind_row[1], colorblind_row[2] - toggle_w - gap, row_h)
    colorblind = (rect_right(colorblind_row) - toggle_w, colorblind_row[1], toggle_w, row_h)

    # BACK BUTTON
    _, right = buttons_in_row(f["button_row"], [], [tpx(135, k)], gap)

    leaves = [
        ("header", header),
        ("label", label),
        ("minus", minus),
        ("bar", bar),
        ("plus", plus),
        ("sfx_label", sfx_label),
        ("sfx_minus", sfx_minus),
        ("sfx_bar", sfx_bar),
        ("sfx_plus", sfx_plus),
        ("note", note),
        ("textsize_label", textsize_label),
        ("textsize", textsize),
        ("fullscreen_label", fullscreen_label),
        ("fullscreen", fullscreen),
        ("difficulty_label", difficulty_label),
        ("difficulty", difficulty),
        ("access", access),
        ("contrast_label", contrast_label),
        ("contrast", contrast),
        ("colorblind_label", colorblind_label),
        ("colorblind", colorblind),
        ("back", right[0]),
    ]

    inside = [
        ("row", row, body),
        ("sfx_row", sfx_row, body),
        ("note", note, body),
        ("textsize_row", textsize_row, body),
        ("fullscreen_row", fullscreen_row, body),
        ("difficulty_row", difficulty_row, body),
        ("access", access, body),
        ("contrast_row", contrast_row, body),
        ("colorblind_row", colorblind_row, body),
    ]

    return {
        "size": f["size"],
        "k": k,
        "hud": f["hud"],
        "panel": panel,
        "header": header,
        "body": body,
        "row": row,
        "label": label,
        "minus": minus,
        "bar": bar,
        "plus": plus,
        "sfx_row": sfx_row,
        "sfx_label": sfx_label,
        "sfx_minus": sfx_minus,
        "sfx_bar": sfx_bar,
        "sfx_plus": sfx_plus,
        "note": note,
        "textsize_row": textsize_row,
        "textsize_label": textsize_label,
        "textsize": textsize,
        "fullscreen_row": fullscreen_row,
        "fullscreen_label": fullscreen_label,
        "fullscreen": fullscreen,
        "difficulty_row": difficulty_row,
        "difficulty_label": difficulty_label,
        "difficulty": difficulty,
        "access": access,
        "contrast_row": contrast_row,
        "contrast_label": contrast_label,
        "contrast": contrast,
        "colorblind_row": colorblind_row,
        "colorblind_label": colorblind_label,
        "colorblind": colorblind,
        "back": right[0],
        "leaves": leaves,
        "inside": inside,
    }


@layout_cache(16)
def credits_layout(width, height):
    """Rectangles of the credits screen: header, the text area (centred, at most 700 px wide) and the button row:
    PREVIOUS / NEXT (they turn the credits pages, buttons.py shows them only when there is more than one page) and BACK."""
    f = screen_frame(width, height)
    inner, header, body, panel, k = f["inner"], f["header"], f["body"], f["panel"], f["k"]
    text_w = min(body[2], tpx(850, k))
    text = (body[0] + (body[2] - text_w) // 2, body[1], text_w, body[3])
    bw = clamp(int(inner[2] * 0.22), tpx(110, k), tpx(170, k))
    _, right = buttons_in_row(f["button_row"], [], [bw, bw, tpx(135, k)], f["gap"])
    leaves = [("header", header), ("text", text), ("prev", right[0]), ("next", right[1]), ("back", right[2])]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": panel, "header": header, "body": body, "text": text,
        "prev": right[0], "next": right[1], "back": right[2], "leaves": leaves, "inside": [],
    }


@layout_cache(16)
def instructions_layout(width, height):
    """Rectangles of the instructions screen: title, page indicator, text body, three buttons.

    "columns" are the (x, width) text columns of page 1 (mission | controls); page 2 uses one full-width column.
    """
    f = screen_frame(width, height)
    gap, inner, header, body, k = f["gap"], f["inner"], f["header"], f["body"], f["k"]
    page_w = tpx(110, k)
    title = (header[0], header[1], header[2] - page_w - gap, header[3])
    page = (rect_right(title) + gap, header[1], page_w, header[3])
    bw = clamp(int(inner[2] * 0.22), tpx(110, k), tpx(170, k))
    backw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    _, right = buttons_in_row(f["button_row"], [], [bw, bw, backw], gap)

    left_w = int(body[2] * 0.46)
    col_gap = 28
    columns = ((body[0], left_w), (body[0] + left_w + col_gap, body[2] - left_w - col_gap))
    leaves = [("title", title), ("page", page), ("body", body),
              ("prev", right[0]), ("next", right[1]), ("back", right[2])]
    return {
        "size": f["size"], "k": k, "hud": f["hud"], "panel": f["panel"], "title": title, "page": page, "body": body,
        "prev": right[0], "next": right[1], "back": right[2], "columns": columns,
        "leaves": leaves, "inside": [],
    }
