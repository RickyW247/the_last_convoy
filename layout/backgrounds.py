"""Layout of the background screen (shown after the lore screen). It reuses the lore screen's panel, heading, hint and
BACK / START GAME buttons, and divides the lore text area into a grid of background cards plus a details box.
The details box holds the text on the left and the background's icon (a square) on the right, and the placeholder note
in a row of its own along the bottom."""
from background_data import PLACEHOLDER_NOTE
from layout import lore_layout
from .geometry import LINE_H, layout_cache
from textscale import text_k, tpx

COLUMNS = 3

# Icon in the details box (sizes are text-scaled pixels, see textscale.tpx). The icon is as large as the box allows, but never
# wider than ICON_SHARE of the box's inner width, never larger than ICON_MAX, and it never squeezes the text column below
# TEXT_MIN. When what is left is smaller than ICON_MIN the icon is dropped and the text gets the full width.
ICON_SHARE = 0.32
ICON_MAX = 240
ICON_MIN = 56
TEXT_MIN = 240
ICON_GAP = 12
DETAIL_PAD = 10


@layout_cache(16)
def background_layout(width, height, count=6):
    g = dict(lore_layout(width, height))
    k = text_k(width, height)
    x, y, w, h = g["text"]
    gap = tpx(8, k)
    rows = -(-count // COLUMNS)
    card_h = max(tpx(30, k), min(tpx(52, k), int(h * 0.15)))
    card_w = (w - gap * (COLUMNS - 1)) // COLUMNS
    cards = []
    for i in range(count):
        r, c = divmod(i, COLUMNS)
        cards.append((x + c * (card_w + gap), y + r * (card_h + gap), card_w, card_h))
    top = y + rows * (card_h + gap)
    g["cards"] = cards
    g["detail"] = (x, top, w, max(1, y + h - top))
    g["k"] = k

    # Inside the details box: the text column (left) and the icon (right, top-aligned with the text).
    pad = tpx(DETAIL_PAD, k)
    ix, iy = x + pad, top + pad
    iw, ih = max(1, w - 2 * pad), max(1, g["detail"][3] - 2 * pad)
    # The placeholder note (if there is one) gets its own full-width row at the bottom, so neither the text nor the icon covers it.
    note_h = tpx(LINE_H, k) if PLACEHOLDER_NOTE else 0
    g["note"] = (ix, iy + ih - note_h, iw, note_h) if note_h else None
    ih = max(1, ih - note_h - (tpx(4, k) if note_h else 0))
    side = min(ih, int(iw * ICON_SHARE), tpx(ICON_MAX, k), iw - tpx(ICON_GAP, k) - tpx(TEXT_MIN, k))
    if side >= tpx(ICON_MIN, k):
        g["icon"] = (ix + iw - side, iy, side, side)
        text_w = iw - side - tpx(ICON_GAP, k)
    else:
        g["icon"] = None
        text_w = iw
    g["pad"] = pad
    g["detail_text"] = (ix, iy, text_w, ih)
    return g
