"""Screen rendering coordination: selects and coordinates the drawing of each
game screen. Actual screen drawing is handled by the ui/ package."""

from ui import (
    draw_history_screen,
    draw_hud,
    draw_title_screen,
    draw_lore_screen,
    draw_background_screen,
    draw_vehicles_screen,
    draw_menu_screen,
    draw_difficulty_screen,
    draw_settings_screen,
    draw_credits_screen,
    draw_instructions_screen,
    draw_map_screen,
    draw_missions_screen,
    draw_survivors_screen,
    draw_scene,
    draw_lower,
)
from ui.achievements_screen import draw_achievements_screen   # imported from its module: ui/__init__.py is not edited for it
from ui.upgrade_screen import draw_upgrade_screen   # imported from its module: ui/__init__.py is not edited for it

# Every screen is laid out in real window pixels (layout.py) and drawn straight onto the window; mouse positions
# are raw window coordinates. These are drawn by draw_window_screen, the convoy screen by draw_convoy_screen.
WINDOW_SCREENS = (
    "title",
    "lore",
    "background",
    "menu",
    "difficulty",
    "settings",
    "credits",
    "vehicles",
    "upgrade",
    "instructions",
    "map",
    "missions",
    "survivors",
    "history",
    "achievements",
)


def draw_window_screen(surface, game, layout, screen_buttons):
    """Draw a screen other than the convoy screen in window pixels.

    screen_buttons is the frame's button list, built from the same live layout the screen is drawn with. The HUD
    is drawn after the screen so that it stays on top; the screens' panels start below it.
    """
    menu_button = next(
        (b for b in screen_buttons if b.label == "MENU"),
        None
    )

    if game.screen == "title":
        draw_title_screen(surface, game, screen_buttons)

    elif game.screen == "lore":
        draw_lore_screen(surface, game, screen_buttons)

    elif game.screen == "background":
        draw_background_screen(surface, game, screen_buttons)

    elif game.screen == "vehicles":
        draw_vehicles_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "upgrade":
        draw_upgrade_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "menu":
        draw_menu_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "difficulty":
        draw_difficulty_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "settings":
        draw_settings_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "credits":
        draw_credits_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "instructions":
        draw_instructions_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "map":
        draw_map_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "missions":
        draw_missions_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "survivors":
        draw_survivors_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "history":
        draw_history_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)

    elif game.screen == "achievements":
        draw_achievements_screen(surface, game, screen_buttons)
        draw_hud(surface, game, layout, menu_button)


def draw_convoy_screen(surface, game, layout, screen_buttons):
    """Draw the main convoy screen using the responsive layout."""
    menu_button = next(
        (b for b in screen_buttons if b.label == "MENU"),
        None
    )

    draw_hud(surface, game, layout, menu_button)
    draw_scene(surface, game, layout["scene"])
    draw_lower(surface, game, screen_buttons, layout)
