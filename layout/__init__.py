"""Screen size and layout coordinates for THE LAST CONVOY (package, no pygame needed).

Every screen is laid out in real window pixels (nothing is drawn on a fixed canvas and scaled). The code is split by
screen; this file only re-exports the names, so `from layout import ...` keeps working. New code may import from the
specific module.

  geometry.py   rectangle helpers (inset, clamp, fit_ratio, buttons_in_row ...) and the shared sizes (LINE_H ...)
  convoy.py     calculate_layout(): the convoy screen (HUD, scene, events, actions, minimap), WIDTH / HEIGHT / FPS
  hud.py        hud_layout(): the HUD panel's identity block and grid of stat cells
  frame.py      screen_frame(): the shared frame (HUD above, one big panel with header, body and button row)
  menus.py      menu_layout (pause menu), difficulty_layout, settings_layout, credits_layout, instructions_layout
  vehicles.py   vehicles_layout, vehicle_card_layout, vehicle_row_at, table columns
  title.py      title_layout, lore_layout
  history.py    history_layout (the full event history screen)
  lists.py      survivors_layout, missions_layout and their per-page counts
  popups.py     popup_layout (event / result / ending), site_popup_layout (SCAVENGE), confirm_popup_layout
  map.py        map_layout, node_at, map_point

All rectangles are (x, y, width, height) tuples of ints. The layout functions are cached and return frozen
results (read-only mappings and tuples, see geometry.layout_cache), so a caller cannot corrupt a shared result. Every
layout also carries "k", the text factor of the window (textscale.py): the rows that hold text are multiplied by it. Each screen layout also carries lists for the tests:
  "leaves": [(name, rect)] - rectangles that must lie inside the window and never overlap each other,
  "inside": [(name, child_rect, parent_rect)] - rectangles that must lie inside another one,
  "groups": [(name, [(name, rect), ...])] - further sets of rectangles (the parts of a list or a card) that must
            not overlap each other.
"""
from .convoy import (
    COMPACT_LOWER_MIN_H, FPS, HEIGHT, MINI_CARD, MINI_SCALE, SCENE_BAR_Y, SCENE_BASELINE, SCENE_LABEL_Y,
    SCENE_REF_H, SCENE_REF_W, WIDTH, ZOMBIE_SLOTS, ZOMBIE_Y_MAX, ZOMBIE_Y_MIN, calculate_layout,
)
from .frame import screen_frame
from .history import history_layout
from .hud import HUD_CELLS, HUD_COLS, hud_layout
from .geometry import (
    LINE_H, LIST_HEAD_GAP, TABLE_HEADER_H, as_ints, buttons_in_row, clamp, fit_ratio, fraction_columns, inset,
    freeze, layout_cache, page_count, rect_bottom, rect_inside, rect_right, rects_overlap, text_k, tpx,
)
from .lists import (
    LIST_FOOTER_H, LIST_PAD, MISSION_CARD_GAP, MISSION_CARD_MAX_H, MISSION_CARD_MIN_H, MISSION_LINE_H,
    SURVIVOR_COLUMNS, SURVIVOR_ROW_MAX_H, SURVIVOR_ROW_MIN_H, _list_panel, _split_footer, mission_card_layout,
    missions_layout, missions_per_page, survivors_layout, survivors_per_page,
)
from .map import MAP_INFO_MAX_H, MAP_INFO_MIN_H, MAP_OLD_AREA, map_layout, map_point, map_point_in, node_at
from .menus import (
    MENU_CARD_MAX_H, MENU_CARD_MAX_W, MENU_CARD_MIN_H, MENU_ITEM_MAX_H, MENU_ITEMS, MENU_LAST_ITEMS, MENU_RUN_ITEMS,
    NOTES_H,
    credits_layout, difficulty_layout, instructions_layout, menu_card_layout, menu_layout, settings_layout,
)
from .popups import (
    END_STAT_ROWS, SITE_ROW_MAX_H, SITE_ROW_MIN_H, confirm_popup_layout, popup_layout, site_popup_layout,
)
from .title import lore_layout, title_layout
from .vehicles import (
    COMPACT_TABLE_W, MAX_ROW_H, MIN_ROW_H, TABLE_CELL_PAD, VEHICLE_ROWS, table_columns, table_pad,
    vehicle_card_layout, vehicle_row_at, vehicles_layout,
)

# Names that used to be private to layout.py (kept for old imports).
_clamp = clamp
_as_ints = as_ints
_buttons_in_row = buttons_in_row
