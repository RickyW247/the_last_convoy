"""Layouts of the popups: the event / result / ending popup, the SCAVENGE site picker and the "are you sure?"
confirmation popup (no pygame).
"""
from .convoy import calculate_layout
from .geometry import LINE_H, LIST_HEAD_GAP, clamp, inset, layout_cache, rect_bottom, tpx


END_STAT_ROWS = 8                          # rows of the ending popup's journey summary (ui.end_stats)


@layout_cache(32)
def popup_layout(width, height, kind, count=1):
    """The popup panel, centred in the window and sized from it, with its parts.

    kind "event":  title, body (description), hint, and `count` full-width choice buttons stacked at the bottom;
    kind "result": title, body (what you chose, the outcome, the result list) and one OK button;
    kind "end":    title, reason, "YOUR JOURNEY" heading, `count` stat rows, three buttons and a hint line.
    """
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    lh = tpx(LINE_H, k)
    pw = min(w - 2 * margin, clamp(int(w * 0.62), 520, 1000))
    if kind == "end":
        ph = min(h - 2 * margin, clamp(int(h * 0.92), 440, 800))
    else:
        ph = min(h - 2 * margin, clamp(int(h * 0.80), 380, 760))
    panel = ((w - pw) // 2, (h - ph) // 2, pw, ph)
    pad = clamp(pw // 36, 12, 24)
    inner = inset(panel, pad)
    ix, iy, iw, ih = inner
    title_h = clamp(int(ih * 0.11), tpx(30, k), tpx(52, k))
    title = (ix, iy, iw, title_h)
    body_top = iy + title_h + gap
    btn_gap = min(gap, 10)
    btn_h = clamp(int(ih * 0.10), tpx(30, k), tpx(56, k))
    out = {"size": (w, h), "k": k, "panel": panel, "inner": inner, "title": title, "hint": None, "reason": None,
           "journey": None, "stats": None, "row_h": 0, "rows": 0}
    leaves = [("title", title)]

    if kind == "event":
        count = max(1, int(count))
        while btn_h > tpx(26, k) and (iy + ih - (count * btn_h + (count - 1) * btn_gap) - gap - lh - gap
                                      - body_top) < 4 * lh:
            btn_h -= 2
        by = iy + ih - (count * btn_h + (count - 1) * btn_gap)
        buttons = tuple((ix, by + i * (btn_h + btn_gap), iw, btn_h) for i in range(count))
        hint = (ix, by - gap - lh, iw, lh)
        body = (ix, body_top, iw, max(0, hint[1] - gap - body_top))
        leaves += [("body", body), ("hint", hint)]
        out["hint"] = hint
    elif kind == "result":
        bw = clamp(int(iw * 0.30), tpx(140, k), tpx(220, k))
        buttons = ((ix + (iw - bw) // 2, iy + ih - btn_h, bw, btn_h),)
        body = (ix, body_top, iw, max(0, buttons[0][1] - gap - body_top))
        leaves.append(("body", body))
    else:
        rows = max(1, int(count))
        hint = (ix, iy + ih - lh, iw, lh)
        bw = clamp(int(iw * 0.28), tpx(130, k), tpx(200, k))
        bw = min(bw, (iw - 2 * gap) // 3)
        bx = ix + (iw - (3 * bw + 2 * gap)) // 2
        by = hint[1] - 6 - btn_h
        buttons = tuple((bx + i * (bw + gap), by, bw, btn_h) for i in range(3))   # PLAY AGAIN, HISTORY, TITLE SCREEN
        body = (ix, body_top, iw, max(0, by - gap - body_top))
        journey_h = lh + 2
        row_h, stats_h, reason_h = tpx(20, k), rows * tpx(20, k), 0
        for row_h in [tpx(v, k) for v in (36, 32, 28, 24, 20)]:
            stats_h = rows * row_h
            reason_h = body[3] - journey_h - LIST_HEAD_GAP - stats_h - gap
            if reason_h >= 3 * lh + 2:
                break
        reason = (ix, body[1], iw, max(0, reason_h))
        journey = (ix, rect_bottom(reason) + gap, iw, journey_h)
        stats = (ix, rect_bottom(journey) + LIST_HEAD_GAP, iw, stats_h)
        leaves += [("reason", reason), ("journey", journey), ("stats", stats), ("hint", hint)]
        out.update(hint=hint, reason=reason, journey=journey, stats=stats, row_h=row_h, rows=rows)
    leaves += [(f"button{i}", b) for i, b in enumerate(buttons)]
    out.update(body=body, buttons=buttons, leaves=leaves,
               inside=[("panel", panel, (0, 0, w, h)), ("inner", inner, panel)], groups=[])
    return out


SITE_ROW_MIN_H, SITE_ROW_MAX_H = 30, 60


@layout_cache(32)
def site_popup_layout(width, height, count):
    """The SCAVENGE popup: a title, one row per site of the stop (a button on the left, what the site offers on
    the right), a SCAVENGE (confirm) and a CANCEL button side by side, and a hint line, in a panel centred in the
    window. "buttons" are the site buttons, then SCAVENGE, then CANCEL, in order; "details" are the text rectangles
    beside the site buttons."""
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    count = max(1, int(count))
    pw = min(w - 2 * margin, clamp(int(w * 0.55), 440, 820))
    pad = clamp(pw // 32, 12, 20)
    title_h, cancel_h, hint_h, row_gap = tpx(28, k), tpx(32, k), tpx(LINE_H, k), 6
    fixed = 2 * pad + title_h + 3 * gap + cancel_h + hint_h
    room = h - 2 * margin - fixed
    row_h = clamp((room - (count - 1) * row_gap) // count, tpx(SITE_ROW_MIN_H, k), tpx(SITE_ROW_MAX_H, k))
    ph = min(h - 2 * margin, fixed + count * row_h + (count - 1) * row_gap)
    panel = ((w - pw) // 2, (h - ph) // 2, pw, ph)
    inner = inset(panel, pad)
    ix, iy, iw, ih = inner
    title = (ix, iy, iw, title_h)
    top = iy + title_h + gap
    btn_w = min(clamp(int(iw * 0.40), tpx(150, k), tpx(240, k)), iw // 2)
    sites = tuple((ix, top + i * (row_h + row_gap), btn_w, row_h) for i in range(count))
    details = tuple((ix + btn_w + gap, r[1], iw - btn_w - gap, row_h) for r in sites)
    rows_end = top + count * row_h + (count - 1) * row_gap
    cancel_w = clamp(int(iw * 0.30), tpx(110, k), tpx(180, k))
    pair_x = ix + (iw - (2 * cancel_w + gap)) // 2
    scavenge = (pair_x, rows_end + gap, cancel_w, cancel_h)
    cancel = (pair_x + cancel_w + gap, rows_end + gap, cancel_w, cancel_h)
    hint = (ix, iy + ih - hint_h, iw, hint_h)
    leaves = [("title", title)]
    leaves += [(f"site{i}", r) for i, r in enumerate(sites)] + [(f"detail{i}", r) for i, r in enumerate(details)]
    leaves += [("scavenge", scavenge), ("cancel", cancel), ("hint", hint)]
    return {"size": (w, h), "k": k, "panel": panel, "inner": inner, "title": title, "sites": sites, "details": details,
            "scavenge": scavenge, "cancel": cancel, "hint": hint, "buttons": sites + (scavenge, cancel),
            "leaves": leaves,
            "inside": [("panel", panel, (0, 0, w, h)), ("inner", inner, panel)], "groups": []}


CONFIRM_BODY_LINES = 3                      # lines of message in the "are you sure?" popup
CONFIRM_BODY_LINES_LONG = {"daycost": 5, "uninstall": 5, "reset_achievements": 5}    # popups with a longer, changing message (a repair / recovery that costs a survivor)


def confirm_body_lines(action):
    """How many message lines the "are you sure?" popup for `action` has room for (the drawing and buttons.py both ask)."""
    return CONFIRM_BODY_LINES_LONG.get(action, CONFIRM_BODY_LINES)


@layout_cache(32)
def confirm_popup_layout(width, height, body_lines=CONFIRM_BODY_LINES):
    """The "are you sure?" popup (RESTART GAME / TITLE SCREEN / QUIT GAME): a title, a message, YES and NO side by
    side and a hint line, in a small panel centred in the window. "buttons" are YES, then NO, in order."""
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    lh = tpx(LINE_H, k)
    pw = min(w - 2 * margin, clamp(int(w * 0.42), 340, 560))
    pad = clamp(pw // 28, 12, 20)
    title_h, btn_h = tpx(32, k), tpx(40, k)
    fixed = 2 * pad + title_h + btn_h + lh + 4 * gap
    body_h = max(lh, min(max(1, int(body_lines)) * lh, h - 2 * margin - fixed))
    ph = min(h - 2 * margin, fixed + body_h)
    panel = ((w - pw) // 2, (h - ph) // 2, pw, ph)
    inner = inset(panel, pad)
    ix, iy, iw, ih = inner
    title = (ix, iy, iw, title_h)
    body = (ix, rect_bottom(title) + gap, iw, body_h)
    btn_w = min(clamp(int(iw * 0.38), tpx(110, k), tpx(200, k)), (iw - gap) // 2)
    pair_x = ix + (iw - (2 * btn_w + gap)) // 2
    by = rect_bottom(body) + gap
    yes = (pair_x, by, btn_w, btn_h)
    no = (pair_x + btn_w + gap, by, btn_w, btn_h)
    hint = (ix, iy + ih - lh, iw, lh)
    leaves = [("title", title), ("body", body), ("yes", yes), ("no", no), ("hint", hint)]
    return {"size": (w, h), "k": k, "panel": panel, "inner": inner, "title": title, "body": body, "yes": yes, "no": no,
            "hint": hint, "buttons": (yes, no), "leaves": leaves,
            "inside": [("panel", panel, (0, 0, w, h)), ("inner", inner, panel)], "groups": []}


ABANDON_ROW_MIN_H, ABANDON_ROW_MAX_H = 22, 48   # the convoy can hold eight vehicles: the rows may be low in a small window


@layout_cache(32)
def abandon_popup_layout(width, height, count):
    """The "which vehicle to abandon?" popup (a convoy with more vehicles than adult drivers): a title, a two-line
    message, one row per vehicle (a button on the left, the vehicle's figures on the right), an ABANDON (confirm)
    button and a hint line, in a panel centred in the window. "buttons" are the `count` vehicle buttons, then
    ABANDON; "details" are the text rectangles beside the vehicle buttons. There is no CANCEL: the choice is forced."""
    base = calculate_layout(width, height)
    w, h, margin, gap, k = base["width"], base["height"], base["margin"], base["gap"], base["k"]
    count = max(1, int(count))
    lh = tpx(LINE_H, k)
    pw = min(w - 2 * margin, clamp(int(w * 0.60), 460, 880))
    pad = clamp(pw // 32, 12, 20)
    title_h, confirm_h, hint_h, message_h, row_gap = tpx(28, k), tpx(32, k), lh, 2 * lh, 4
    fixed = 2 * pad + title_h + message_h + confirm_h + hint_h + 4 * gap
    room = h - 2 * margin - fixed
    row_h = clamp((room - (count - 1) * row_gap) // count, tpx(ABANDON_ROW_MIN_H, k), tpx(ABANDON_ROW_MAX_H, k))
    ph = min(h - 2 * margin, fixed + count * row_h + (count - 1) * row_gap)
    panel = ((w - pw) // 2, (h - ph) // 2, pw, ph)
    inner = inset(panel, pad)
    ix, iy, iw, ih = inner
    title = (ix, iy, iw, title_h)
    message = (ix, iy + title_h + gap, iw, message_h)
    top = message[1] + message_h + gap
    btn_w = min(clamp(int(iw * 0.40), tpx(150, k), tpx(240, k)), iw // 2)
    rows = tuple((ix, top + i * (row_h + row_gap), btn_w, row_h) for i in range(count))
    details = tuple((ix + btn_w + gap, r[1], iw - btn_w - gap, row_h) for r in rows)
    rows_end = top + count * row_h + (count - 1) * row_gap
    confirm_w = clamp(int(iw * 0.36), tpx(140, k), tpx(240, k))
    confirm = (ix + (iw - confirm_w) // 2, rows_end + gap, confirm_w, confirm_h)
    hint = (ix, iy + ih - hint_h, iw, hint_h)
    leaves = [("title", title), ("message", message)]
    leaves += [(f"vehicle{i}", r) for i, r in enumerate(rows)] + [(f"detail{i}", r) for i, r in enumerate(details)]
    leaves += [("confirm", confirm), ("hint", hint)]
    return {"size": (w, h), "k": k, "panel": panel, "inner": inner, "title": title, "message": message,
            "rows": rows, "details": details, "confirm": confirm, "hint": hint, "buttons": rows + (confirm,),
            "leaves": leaves,
            "inside": [("panel", panel, (0, 0, w, h)), ("inner", inner, panel)], "groups": []}
