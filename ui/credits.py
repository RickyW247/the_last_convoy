"""The credits screen of THE LAST CONVOY. Drawing only; the lines are placed by credits_items.credits_items (one page
at a time: PgUp / PgDn or the mouse wheel turn the pages) and the links are clickable through the buttons buttons.py
builds from the same placement."""
import pygame

from widgets import PIX, draw_frame, draw_panel

import credits_data
from credits_items import credits_footer, credits_items, credits_page_count, credits_page_index
from layout import credits_layout
from theme import MUTED, PANEL, WHITE, YELLOW
from widgets import draw_heading, fit_variants, scaled_font, text_in_rect
from .common import SCREEN_BG

LINK = (120, 190, 255)         # link text; always underlined, so the colour is never the only cue
LINK_HOVER = (190, 225, 255)   # a link under the mouse pointer


def draw_credits_screen(surface, game, buttons):
    """Credits in two columns, over as many pages as the text needs: headings, plain lines and links (underlined,
    lighter under the pointer, outlined when the keyboard focus is on them), a page indicator, then BACK. Link buttons are not drawn as buttons: the text is the link."""
    size = surface.get_size()
    g = credits_layout(*size)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, credits_data.CREDITS_TITLE, g["header"])

    mouse = pygame.mouse.get_pos()
    focused = {tuple(b.rect) for b in buttons if b.focused and b.enabled}
    for line in credits_items(*size):
        rect = pygame.Rect(line.rect)
        if line.kind == "heading":
            color = YELLOW
        elif line.kind == "link":
            color = LINK_HOVER if rect.collidepoint(mouse) else LINK
        else:
            color = WHITE
        text_in_rect(surface, line.text, line.rect, color, line.font, "center")
        if line.kind == "link":
            pygame.draw.line(surface, color, (rect.x, rect.bottom - 2), (rect.right - 1, rect.bottom - 2), 1)
            if tuple(rect) in focused:
                draw_frame(surface, rect.inflate(10, 2), YELLOW, 2 * PIX)

    footer = credits_footer(*size)
    if footer:   # more than one page: which one this is, and how to turn it
        label = f"Page {credits_page_index(*size) + 1} / {credits_page_count(*size)}"
        tiny = scaled_font(size, 13)
        text = fit_variants(tiny, footer[2], (f"{label}    PgUp / PgDn: turn page", f"{label}    PgUp / PgDn", label))
        text_in_rect(surface, text, footer, MUTED, tiny, "center")

    for button in buttons:
        if getattr(button, "url", None) is None:
            button.draw(surface)
