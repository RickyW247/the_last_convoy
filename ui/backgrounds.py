"""The background screen of THE LAST CONVOY (after the lore screen): choose who you were before the outbreak.
Drawing only. The choice gives the starting vehicles; the rest is placeholder (see background_data.py). The selected background's
icon (background_icons.py) is drawn on the right of the details box, the text on the left."""
import pygame

from background_icons import get_icon
from background_data import BACKGROUNDS, BACKGROUND_ORDER, PLACEHOLDER_NOTE
from layout.backgrounds import background_layout
from platform_web import IS_WEB
from textscale import tpx
from theme import GREEN, MUTED, PANEL, WHITE, YELLOW
from widgets import (PIX, draw_frame, draw_heading, draw_panel, draw_text, fit_text, scaled_font, screen_fonts,
                     text_in_rect, wrap_pixels)
from .common import CARD_BG, SCREEN_BG, draw_paragraph


def _airy_paragraph(surface, text, x, y, width, color, font, limit, spacing):
    """Like draw_paragraph, with `spacing` extra pixels between the lines (desktop build). Returns the y below the text."""
    step = font.get_linesize() + spacing
    for line in wrap_pixels(text, font, width):
        if y + font.get_linesize() > limit:
            break
        draw_text(surface, fit_text(line, font, width), x, y, color, font)
        y += step
    return y


def draw_background_screen(surface, game, buttons):
    """Heading, the six background cards (they are the buttons) and the details of the selected background."""
    size = surface.get_size()
    g = background_layout(*size, len(BACKGROUND_ORDER))
    _medium, _body, _small, hint_font = screen_fonts(size)
    # Name 19 px; description text and labels share one size, 15 px (at the default size).
    body, small = scaled_font(size, 19), scaled_font(size, 15)
    tiny = small
    k = g["k"]
    # Desktop build: more room between the lines, the labels and the sections (the browser build keeps its compact text).
    line_extra, label_gap, block_gap = (0, 2, tpx(6, k)) if IS_WEB else (tpx(6, k), tpx(8, k), tpx(16, k))

    def paragraph(text, x, y, width, color, font, limit):
        if IS_WEB:
            return draw_paragraph(surface, text, x, y, width, color, font, limit=limit)
        return _airy_paragraph(surface, text, x, y, width, color, font, limit, line_extra)

    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "CHOOSE YOUR BACKGROUND", g["heading"], YELLOW, None, "center")

    chosen = BACKGROUNDS[game.background]
    box = pygame.Rect(g["detail"])
    draw_panel(surface, box, CARD_BG, -1)
    draw_frame(surface, box, (70, 82, 86), 1 * PIX)
    # The layout reserves the text column (left) and the icon square (right); no icon file means the text takes the full width.
    x, y, w, text_h = g["detail_text"]
    bottom = y + text_h
    icon = get_icon(game.background, g["icon"][2]) if g["icon"] else None
    if icon is not None:
        surface.blit(icon, g["icon"][:2])
    else:
        w = box.w - 2 * g["pad"]

    def block(label, text, color=WHITE):
        """A muted label followed by wrapped text, in the largest font that still fits the box."""
        nonlocal y
        if y + tiny.get_linesize() > bottom:
            return
        draw_text(surface, label, x, y, MUTED, tiny)
        y += tiny.get_linesize() + label_gap
        font = small if y + small.get_linesize() * 2 <= bottom else tiny
        y = paragraph(text, x, y, w, color, font, bottom) + block_gap

    draw_text(surface, fit_text(game.background.upper(), body, w), x, y, GREEN, body)
    y += body.get_linesize() + (4 if IS_WEB else tpx(10, k))
    blurb_font = small if y + small.get_linesize() * 2 <= bottom else tiny
    y = paragraph(chosen["blurb"], x, y, w, WHITE, blurb_font, bottom) + block_gap
    block("STARTING VEHICLES", ", ".join(chosen["vehicles"]))
    block(f"ABILITY: {chosen['ability'].upper()}", chosen["ability_text"])
    if chosen["trait"]:
        block(f"TRAIT: {chosen['trait'][0].upper()}", chosen["trait"][1])
    block("PLAYSTYLE", chosen["playstyle"])
    if g["note"]:   # its own row along the bottom of the box (layout), under the text and the icon
        text_in_rect(surface, PLACEHOLDER_NOTE, g["note"], YELLOW, hint_font)

    for button in buttons:
        button.draw(surface, selected=button.label == game.background.upper())
    text_in_rect(surface, "Arrows or Tab: choose   |   ENTER: select   |   ESC: back", g["hint"], MUTED, hint_font, "center")
