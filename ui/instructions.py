"""The instructions screen of THE LAST CONVOY: two pages of text that scroll when the window is too
small. The scroll position is kept here, not in game.py. Drawing only."""
import pygame

from widgets import draw_panel

import instructions_data as text
from .common import draw_paragraph, SCREEN_BG
import textscale
from layout import instructions_layout, LINE_H
from textscale import text_k, tpx
from theme import GREEN, MUTED, PANEL, WHITE, YELLOW
from widgets import draw_text, fit_text, heading_fonts, pick_font, scaled_font, text_in_rect



def _ctx(size, body):
    """(heading font, paragraph gap, k) for the page text in font `body` in a window of this size: the heading is the
    scaled 19 px font, the gap grows with the body font, and every fixed offset is multiplied by k (the text size)."""
    return scaled_font(size, 19), max(5, body.get_linesize() // 2), text_k(*size)


def _layout_instructions(surface, page, body, rect, columns,
                         secondary=True, top=None, limit=None, ctx=None):
    """Lay out one of the four instructions pages. `ctx` is _ctx(window size, body)."""
    rect = pygame.Rect(rect)
    top = rect.y if top is None else top
    limit = rect.bottom if limit is None else limit

    FONT, gap, k = ctx if ctx is not None else (body, max(5, body.get_linesize() // 2), 1.0)   # FONT: the heading
    line = body.get_linesize()
    x, width = rect.x, rect.w

    def heading(value):
        if surface is not None:
            draw_text(surface, fit_text(value, FONT, width),
                      x, top, YELLOW, FONT)

    def paragraphs(items, start_y):
        y = start_y
        for paragraph in items:
            y = draw_paragraph(
                surface, paragraph, x, y, width, WHITE, body, limit
            ) + gap
        return y

    def rows(items, start_y, label_width):
        y = start_y
        for label, description in items:
            if surface is not None and y + line <= limit:
                draw_text(
                    surface,
                    fit_text(label, body, label_width - 8),
                    x, y, GREEN, body
                )

            y = draw_paragraph(
                surface,
                description,
                x + label_width,
                y,
                width - label_width,
                WHITE,
                body,
                limit
            ) + gap

        return y

    # PAGE 1: MISSION
    if page == 0:
        heading(text.MISSION_TITLE)
        y = paragraphs(text.MISSION, top + tpx(38, k))
        return y - gap

    # PAGE 2: KEYBOARD CONTROLS (two columns)
    if page == 1:
        heading(text.CONTROLS_TITLE)

        column_gap = tpx(35, k)
        column_width = (width - column_gap) // 2
        label_width = min(tpx(105, k), column_width // 2)

        left_x = x
        right_x = x + column_width + column_gap

        def control_column(items, column_x):
            y = top + tpx(42, k)

            for label, description in items:
                if surface is not None and y + line <= limit:
                    draw_text(
                        surface,
                        fit_text(label, body, label_width - 5),
                        column_x, y, GREEN, body
                    )

                y = draw_paragraph(
                    surface,
                    description,
                    column_x + label_width,
                    y,
                    column_width - label_width,
                    WHITE,
                    body,
                    limit
                ) + gap

            return y

        left_bottom = control_column(text.CONTROLS_LEFT, left_x)
        right_bottom = control_column(text.CONTROLS_RIGHT, right_x)

        y = max(left_bottom, right_bottom)

        if secondary:
            y = draw_paragraph(
                surface,
                text.CONTROLS_NOTE,
                x, y + gap, width, MUTED, body, limit
            )

        return y

    # PAGE 3: HOW TO PLAY
    if page == 2:
        heading(text.HOW_TO_PLAY_TITLE)
        y = draw_paragraph(
            surface, text.HOW_TO_PLAY_INTRO,
            x, top + tpx(38, k), width, WHITE, body, limit
        ) + gap

        label_width = min(tpx(170, k), int(width * 0.25))
        y = rows(text.HOW_TO_PLAY, y, label_width)
        return y - gap

    # PAGE 4: SURVIVAL GUIDE
    if page == 3:
        heading(text.SURVIVAL_TITLE)

        y = draw_paragraph(
            surface, text.SURVIVAL_INTRO,
            x, top + tpx(38, k), width, WHITE, body, limit
        ) + gap

        label_width = min(tpx(170, k), int(width * 0.25))
        y = rows(text.SURVIVAL_GUIDE, y, label_width)

        return y - gap

    # PAGE 5: FINAL ADVICE
    if page == 4:
        heading(text.SURVIVAL_CONTINUED_TITLE)

        y = paragraphs(
            text.SURVIVAL_OUTRO,
            top + tpx(38, k)
        )

        return y - gap


# Scroll position of the instructions page, kept here (not in game.py): the page it belongs to and the pixels.
_INSTRUCTIONS_SCROLL = {"page": 0, "y": 0}


_PLAN_CACHE = {}
textscale.on_change(_PLAN_CACHE.clear)   # the plans depend on the text-size level


SCROLL_STEP = 3 * LINE_H


def _instructions_plan(size, page):
    """(body font, show secondary text, pixels of overflow) for an instructions page in a window of this size.

    The first of the scaled 19 / 17 / 15 / 13 px fonts, then the smallest without the grey paragraphs that fits the body is used; when even that is too
    long, TINY with everything is used and the page scrolls. Cached per window size and page.
    """
    key = (size, page)
    plan = _PLAN_CACHE.get(key)
    if plan is None:
        g = instructions_layout(*size)
        body, columns = g["body"], g["columns"]
        bottom = body[1] + body[3]
        # The body fonts follow the text-size setting: the scaled 19, 17, 15 and 13 px fonts (largest first, no repeats).
        fonts = []
        for base in (19, 17, 15, 13):
            font = scaled_font(size, base)
            if font not in fonts:
                fonts.append(font)
        tiny = fonts[-1]
        plan = (tiny, True, 0)
        for font, secondary in [(f, True) for f in fonts] + [(tiny, False)]:
            if _layout_instructions(None, page, font, body, columns, secondary, ctx=_ctx(size, font)) <= bottom:
                plan = (font, secondary, 0)
                break
        else:
            over = _layout_instructions(None, page, tiny, body, columns, True, ctx=_ctx(size, tiny)) - bottom
            plan = (tiny, True, max(0, over))
        if len(_PLAN_CACHE) > 32:
            _PLAN_CACHE.clear()
        _PLAN_CACHE[key] = plan
    return plan


def scroll_instructions(game, size, delta):
    """Scroll the instructions page by `delta` pixels (positive = down), within what overflows. Returns the offset."""
    page = game.instructions_page
    _font, _secondary, over = _instructions_plan(tuple(size), page)
    scroll = _INSTRUCTIONS_SCROLL
    if scroll["page"] != page:
        scroll["page"], scroll["y"] = page, 0
    scroll["y"] = max(0, min(over, scroll["y"] + delta))
    return scroll["y"]


def reset_instructions_scroll():
    """Put the instructions page back at its top; called whenever that screen is opened or left."""
    _INSTRUCTIONS_SCROLL.update(page=0, y=0)


def draw_instructions_screen(surface, game, buttons):
    """The player instructions: page 1 is the mission and controls, page 2 is how to play.

    Each page uses SMALL when it fits in the body rectangle, otherwise TINY, otherwise TINY without the grey
    secondary paragraphs; when even that is too long (small windows or large text) the text scrolls with the mouse
    wheel or the PageUp / PageDown / Home / End keys (Up / Down turn the pages, Left / Right move the focus). Text is never drawn outside the body.
    """
    size = tuple(surface.get_size())
    g = instructions_layout(*size)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    page, body_rect, columns = game.instructions_page, g["body"], g["columns"]
    font, secondary, over = _instructions_plan(size, page)
    offset = scroll_instructions(game, size, 0) if over else 0
    if not over:
        _INSTRUCTIONS_SCROLL.update(page=page, y=0)

    title = pygame.Rect(g["title"])
    tiny = scaled_font(size, 13)
    small = scaled_font(size, 15)
    heading_font = pick_font(heading_fonts(size), ["INSTRUCTIONS"], title.w, title.h)
    text_in_rect(surface, "INSTRUCTIONS", title, WHITE, heading_font)
    room = title.w - heading_font.size("INSTRUCTIONS")[0] - 16
    if over:
        for hint in ("Up / Down: change page    PgUp / PgDn: scroll", "PgUp / PgDn: scroll"):
            if tiny.size(hint)[0] <= room:
                text_in_rect(surface, hint, title, YELLOW, tiny, "right")
                break
    page_label = f"Page {page + 1} / {text.PAGE_COUNT}"
    text_in_rect(surface, page_label, g["page"], MUTED, pick_font((small, tiny), [page_label], g["page"][2], g["page"][3]), "right")

    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(body_rect))
    _layout_instructions(surface, page, font, body_rect, columns, secondary, top=body_rect[1] - offset,
                         ctx=_ctx(size, font),
                         limit=body_rect[1] + body_rect[3] if not over else body_rect[1] + body_rect[3] + offset + 400)
    surface.set_clip(old_clip)
    for button in buttons:
        button.draw(surface)
