"""Screen and shared UI drawing for THE LAST CONVOY (package).

The drawing code lives in this package: common (shared helpers), convoy (convoy screen), hud (the HUD
on every run screen), map_system (the map and minimap), vehicles_screen, lists
(survivors, missions), instructions, event_ui (event / result popups), sites (SCAVENGE popup) and screens (menu, map,
title, lore, ending popup), credits (credits screen), confirm ("are you sure?" popup) and abandon ("which vehicle
to abandon?" popup), history (the full event history). This file
only re-exports their names, including the old private ones, so `from ui import ...` keeps working.
New code should import from the specific module.
"""

from .common import (
    _SCALED_CACHE, _SCALED_CACHE_LIMIT, CARD_BG, draw_paragraph, scaled_image, SCREEN_BG, whole_scale, wrap_items,
)
from .convoy import (
    _get_zombie_sprite, _ZOMBIE_SPRITE, _ZOMBIE_SPRITE_PATH, BACKGROUND_PATH,
    draw_background_zombies, draw_convoy_vehicles, draw_events, draw_info_panel, draw_lower, draw_scene,
    draw_scene_art, draw_zombie, get_background_image,
)
from .hud import draw_hud, health_color
from .vehicles_screen import (
    _draw_vehicle_table, _table_font, _TABLE_HEADERS, _TABLE_HEADERS_COMPACT, _vehicle_table_rows,
    _worst_case_cells, draw_vehicle_card, draw_vehicles_screen,
)
from .lists import (
    _no_manager, _objective_lines, _STATUS_COLORS, draw_mission_card, draw_missions_screen, draw_survivors_screen,
)
from .instructions import (
    _instructions_plan, _INSTRUCTIONS_SCROLL, _layout_instructions, _PLAN_CACHE, draw_instructions_screen,
    reset_instructions_scroll, scroll_instructions, SCROLL_STEP,
)
from .event_ui import (
    draw_event_overlay, draw_event_result_overlay, handle_event_click, handle_result_click, make_event_buttons,
    make_result_buttons,
)
from .history import clamp_history, draw_history_screen, history_max_scroll, history_page_rows
from .sites import draw_site_popup
from .credits import draw_credits_screen
from .confirm import draw_confirm_popup
from .abandon import draw_abandon_popup
from .backgrounds import draw_background_screen
from .screens import (
    draw_difficulty_screen, draw_end_overlay, draw_logo, draw_lore_screen, draw_map_screen,
    draw_menu_screen, draw_settings_screen, draw_title_screen, end_stats,
)

from widgets import draw_heading, fit_variants, text_in_rect

# Names that used to be private to ui.py (kept for old imports).
_SCREEN_BG = SCREEN_BG
_CARD_BG = CARD_BG
_draw_paragraph = draw_paragraph
_wrap_items = wrap_items
_text_in_rect = text_in_rect
_heading = draw_heading
_fit_variants = fit_variants

__all__ = [
    "BACKGROUND_PATH",
    "CARD_BG",
    "SCREEN_BG",
    "SCROLL_STEP",
    "_CARD_BG",
    "_INSTRUCTIONS_SCROLL",
    "_PLAN_CACHE",
    "_SCALED_CACHE",
    "_SCALED_CACHE_LIMIT",
    "_SCREEN_BG",
    "_STATUS_COLORS",
    "_TABLE_HEADERS",
    "_TABLE_HEADERS_COMPACT",
    "_ZOMBIE_SPRITE",
    "_ZOMBIE_SPRITE_PATH",
    "_draw_paragraph",
    "_draw_vehicle_table",
    "_fit_variants",
    "_get_zombie_sprite",
    "_heading",
    "_instructions_plan",
    "_layout_instructions",
    "_no_manager",
    "_objective_lines",
    "_table_font",
    "_text_in_rect",
    "_vehicle_table_rows",
    "_worst_case_cells",
    "_wrap_items",
    "draw_abandon_popup",
    "draw_background_screen",
    "draw_background_zombies",
    "draw_confirm_popup",
    "draw_convoy_vehicles",
    "draw_credits_screen",
    "draw_difficulty_screen",
    "draw_end_overlay",
    "draw_event_overlay",
    "draw_event_result_overlay",
    "draw_events",
    "clamp_history",
    "draw_history_screen",
    "draw_hud",
    "draw_info_panel",
    "draw_instructions_screen",
    "draw_logo",
    "draw_lore_screen",
    "draw_lower",
    "draw_map_screen",
    "draw_menu_screen",
    "draw_settings_screen",
    "draw_site_popup",
    "draw_mission_card",
    "draw_missions_screen",
    "draw_paragraph",
    "draw_scene",
    "draw_scene_art",
    "draw_survivors_screen",
    "draw_title_screen",
    "draw_vehicle_card",
    "draw_vehicles_screen",
    "draw_zombie",
    "end_stats",
    "get_background_image",
    "handle_event_click",
    "handle_result_click",
    "health_color",
    "history_max_scroll",
    "history_page_rows",
    "make_event_buttons",
    "make_result_buttons",
    "reset_instructions_scroll",
    "scaled_image",
    "scroll_instructions",
    "whole_scale",
    "wrap_items",
]
