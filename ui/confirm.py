"""The "are you sure?" popup of THE LAST CONVOY (RESTART GAME, TITLE SCREEN and QUIT GAME). Drawing only."""
import pygame

from widgets import PIX, draw_frame, draw_panel

from layout import confirm_popup_layout
from layout.popups import confirm_body_lines
from textscale import text_k
from theme import HEAD_FONTS, MUTED, PANEL, WHITE, YELLOW
from widgets import draw_heading, draw_lines, fit_paragraph, fit_variants, screen_fonts, text_in_rect

MESSAGE = "Are you sure? Progress will not be saved."
CONFIRM_TITLES = {   # game.confirm_popup -> the popup's heading
    "restart": "RESTART GAME?",
    "title": "GO TO TITLE SCREEN?",
    "quit": "QUIT GAME?",
    "difficulty": "RESTART REQUIRED",       # changing the difficulty of a run in progress
    "uninstall": "UNINSTALL UPGRADE?",     # taking an upgrade off a vehicle (free; may lose seats / supplies)
    "reset_achievements": "RESET ACHIEVEMENTS?",   # achievements screen: erase every achievement and counter
    "daycost": "A SURVIVOR WILL LEAVE",   # a repair / recovery that takes a day with too little food or water
}


def draw_confirm_popup(surface, game, buttons):
    """The popup that asks before a run is thrown away, drawn straight onto the (already dimmed) window from
    confirm_popup_layout; `buttons` are YES and NO. Nothing is drawn while no confirmation is pending."""
    action = game.confirm_popup
    if action is None:
        return
    size = surface.get_size()
    g = confirm_popup_layout(*size, confirm_body_lines(action))
    medium, body, small, tiny = screen_fonts(size)   # follow the text-size setting, like the layout's rows
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_frame(surface, g["panel"], YELLOW, 2 * PIX)

    draw_heading(surface, CONFIRM_TITLES.get(action, "ARE YOU SURE?"), g["title"], YELLOW,
                 HEAD_FONTS if text_k(*size) <= 1.0 else None, "center")

    bx, by, bw, bh = g["body"]
    message = MESSAGE
    if action == "difficulty":   # buttons.choose_difficulty keeps the chosen level in game.pending_difficulty
        level = getattr(game, "pending_difficulty", None)
        message = (f"Changing to {level} restarts the game. Progress will not be saved. Continue?" if level
                   else "Changing the difficulty restarts the game. Progress will not be saved.")
    if action == "reset_achievements":   # not a run: it erases achievements.json progress, so say that instead of "progress will not be saved"
        message = ("Erase every achievement and counter? Bonus vehicles they unlocked lock again. "
                   "This cannot be undone.")
    if action == "uninstall":   # the text says what would be left behind (Game.uninstall_text)
        message = game.uninstall_text()
    if action == "daycost":   # the text depends on what is short (see SurvivalMixin.confirm_day_cost)
        message = (getattr(game, "day_cost_pending", None) or {}).get("text", "This takes a day. Go ahead anyway?")
    font, lines = fit_paragraph(message, (body, medium, small, tiny), bw, bh, line_gap=4)
    block = len(lines) * (font.get_linesize() + 4)
    draw_lines(surface, lines, (bx, by + max(0, (bh - block) // 2), bw, bh), font, WHITE, "center", 4)

    for button in buttons:
        button.draw(surface)
    text_in_rect(surface, fit_variants(tiny, g["hint"][2], ("Y: yes   |   N or ESC: cancel   |   Tab / arrows: move   |   ENTER: select",
                                                               "Y: yes | N / ESC: cancel | ENTER: select",
                                                               "Y: yes | N: cancel")),
                 g["hint"], MUTED, tiny, "center")
