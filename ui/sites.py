"""The SCAVENGE popup of THE LAST CONVOY: every site of the current stop. A click or 1-9 selects a site (its row gets
an outline); the SCAVENGE button confirms and searches it. Drawing only."""
import pygame

from widgets import PIX, draw_frame, draw_panel

from layout import site_popup_layout
from map_data import SITES
from theme import MUTED, PANEL, WHITE, YELLOW
from widgets import (draw_heading, draw_lines, fit_paragraph, fit_variants, scaled_font, text_in_rect, text_ladder,
                     wrap_pixels)


def draw_site_popup(surface, game, buttons):
    """Draw the popup straight onto the (already dimmed) window from site_popup_layout, with the given buttons
    (one per site, then SCAVENGE and CANCEL; see buttons.make_site_buttons). The selected site's row is outlined and
    its description is drawn brighter. Every description uses the same font: the largest of the window's text
    ladder in which each of them fits its row."""
    sites = game.current_sites()
    g = site_popup_layout(*surface.get_size(), len(sites))
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_frame(surface, g["panel"], YELLOW, 2 * PIX)
    draw_heading(surface, "SEARCH WHICH SITE?", g["title"], YELLOW, None, "center")

    ladder = text_ladder(surface.get_size())
    font = min((fit_paragraph(SITES[site]["detail"], ladder, rect[2], rect[3], line_gap=0)[0]
                for site, rect in zip(sites, g["details"])), key=lambda f: f.get_linesize(), default=scaled_font(surface.get_size(), 13))
    step = font.get_linesize()
    chosen = game.selected_site % len(sites) if sites else -1
    for i, (site, rect) in enumerate(zip(sites, g["details"])):
        x, y, w, h = rect
        lines = wrap_pixels(SITES[site]["detail"], font, w)[:max(1, h // step)]
        top = y + max(0, (h - len(lines) * step) // 2)
        draw_lines(surface, lines, (x, top, w, h), font, WHITE if i == chosen else MUTED, "left", 0)
        if i == chosen:
            row = pygame.Rect(g["sites"][i]).union(pygame.Rect(rect)).inflate(8, 4)
            draw_frame(surface, row, WHITE, 2 * PIX)
    for button in buttons:
        button.draw(surface)
    tiny = scaled_font(surface.get_size(), 13)
    hint = fit_variants(tiny, g["hint"][2], (
        "1-9: pick a site   |   Tab or arrows: move   |   ENTER: select / scavenge   |   ESC: cancel",
        "1-9: pick | Tab: move | ENTER: select | ESC: cancel",
        "ESC: cancel"))
    text_in_rect(surface, hint, g["hint"], MUTED, tiny, "center")
