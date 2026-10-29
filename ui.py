"""Screen and shared UI drawing functions for THE LAST CONVOY.

Drawing only: the buttons themselves are built in buttons.py and handed to the screens that show them.
"""
import os

import pygame

from buttons import END_PANEL
from config import DIFFICULTIES, DIFFICULTY_ORDER, HORDE_BAR_MAX_KM, REPAIR_FRACTION, REPAIR_SCRAP_COST
from game import recovery_cost
import instructions_data as text
import story_data as story
from layout import (CARD, COL_NAME, COL_NUMBERS, COL_STATUS, HEIGHT, ROW_H, ROW_Y0, TABLE_W, TABLE_X, WIDTH,
                    ZOMBIE_SLOTS)
from map_system import draw_minimap
from theme import (BIG, BLUE, DARK, FONT, GREEN, HORDE_STATE_COLORS, MUTED, ORANGE, PANEL, PANEL_LIGHT, RED,
                   ROAD, SMALL, TINY, TITLE, WHITE, YELLOW)
from vehicle_rendering import get_vehicle_sprite
from vehicles import VEHICLE_LOOKS, VEHICLE_ROLES, VEHICLE_SPECS
from widgets import clamp, draw_bar, draw_text, wrap_text

BACKGROUND_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "backgrounds", "convoy_background.png"
)

_BACKGROUND_IMAGE = None


def get_background_image():
    """Load the convoy background once, preserving pixel-art edges."""
    global _BACKGROUND_IMAGE

    if _BACKGROUND_IMAGE is None:
        _BACKGROUND_IMAGE = pygame.image.load(
            BACKGROUND_PATH
        ).convert()

    return _BACKGROUND_IMAGE


# Scaled copies of the sprites, so each size is computed once instead of every frame.
_SCALED_CACHE = {}


def scaled_image(key, image, size):
    """Return `image` resized to `size`, cached by (key, size); the original when no resizing is needed.

    `key` names the source image (for example ("vehicle", "School Bus")), so equal sizes of different
    images never share an entry. Sizes come from a few fixed layouts, so the cache stays small.
    """
    if image.get_size() == size:
        return image
    cache_key = (key, size)
    scaled = _SCALED_CACHE.get(cache_key)
    if scaled is None:
        scaled = pygame.transform.scale(image, size)
        _SCALED_CACHE[cache_key] = scaled
    return scaled


def draw_convoy_vehicles(surface, game, scene):
    """Draw every owned vehicle in a left-facing line, shrinking to fit the scene."""
    vehicles = game.vehicles
    if not vehicles:
        return
    gap = 4
    sprites = [get_vehicle_sprite(v.vehicle_type) for v in vehicles]
    widths_sum = sum(s.get_width() for s in sprites)
    available = scene.w - 60 - gap * (len(sprites) - 1)
    scale = min(1.0, available / widths_sum)

    scaled = []
    for vehicle, s in zip(vehicles, sprites):
        size = (max(1, int(s.get_width() * scale)), max(1, int(s.get_height() * scale)))
        scaled.append(scaled_image(("vehicle", vehicle.vehicle_type), s, size))
    total = sum(s.get_width() for s in scaled) + gap * (len(scaled) - 1)
    x = scene.x + (scene.w - total) // 2
    baseline = 343  # y where vehicle bodies rest on the road

    for vehicle, spr in zip(vehicles, scaled):
        look = VEHICLE_LOOKS[vehicle.vehicle_type]
        # PNG sprites carry their own size, so rest the bottom edge of the image on the road baseline.
        y = baseline - spr.get_height()
        surface.blit(spr, (x, y))
        cx = x + spr.get_width() // 2
        label = TINY.render(look["label"], True, WHITE)
        surface.blit(label, label.get_rect(midtop=(cx, 356)))
        health_pct = vehicle.health / max(1, vehicle.stats["health"])
        bar_color = GREEN if health_pct >= 0.6 else (YELLOW if health_pct >= 0.3 else RED)
        bar_w = min(spr.get_width() - 10, 70)
        draw_bar(surface, cx - bar_w // 2, 375, bar_w, 5, vehicle.health, vehicle.stats["health"], bar_color)
        x += spr.get_width() + gap

# Zombie sprite asset
_ZOMBIE_SPRITE = None
_ZOMBIE_SPRITE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "zombies", "zombie.png"
)


def _get_zombie_sprite():
    """Load and cache the transparent zombie PNG."""
    global _ZOMBIE_SPRITE

    if _ZOMBIE_SPRITE is None:
        if not os.path.isfile(_ZOMBIE_SPRITE_PATH):
            raise FileNotFoundError(
                f"Zombie sprite not found: {_ZOMBIE_SPRITE_PATH}"
            )

        _ZOMBIE_SPRITE = pygame.image.load(
            _ZOMBIE_SPRITE_PATH
        ).convert_alpha()

    return _ZOMBIE_SPRITE


def draw_zombie(surface, x, y, s):
    """Draw a pixel-art zombie facing left toward the convoy."""
    sprite = _get_zombie_sprite()

    # Scale with scene depth while preserving the original proportions.
    target_h = max(1, int(42 * s))
    target_w = max(
        1,
        int(sprite.get_width() * target_h / sprite.get_height())
    )

    scaled = scaled_image("zombie", sprite, (target_w, target_h))

    # Anchor the zombie's feet to the ground.
    rect = scaled.get_rect(
        midbottom=(int(x - 5 * s), int(y))
    )
    surface.blit(scaled, rect)

def draw_background_zombies(surface, game):
    shown = sorted(ZOMBIE_SLOTS[:game.zombie_count()], key=lambda slot: slot[1])
    for x, y in shown:
        draw_zombie(surface, x, y, 0.8 + (y - 300) / 34 * 0.4)

def draw_scene(surface, game):
    scene = pygame.Rect(18, 125, WIDTH - 36, 270)

    # Draw the pixel-art background image.
    background = scaled_image("background", get_background_image(), (scene.w, scene.h))
    surface.blit(background, scene.topleft)

    # Zombies behind the convoy, then vehicles in front.
    draw_background_zombies(surface, game)
    draw_convoy_vehicles(surface, game, scene)

    draw_text(surface, "WEST  <---", 35, 140, WHITE, SMALL)
    draw_text(surface, "CONVOY ON THE ROAD", 740, 140, WHITE, SMALL)


def draw_hud(surface, game):
    totals = game.convoy_stats()
    pygame.draw.rect(surface, PANEL, (18, 16, WIDTH - 36, 96), border_radius=8)
    draw_text(surface, "THE LAST CONVOY", 32, 24, WHITE, TITLE)
    draw_text(surface, f"LOCATION: {game.current_location}", 33, 63, MUTED, SMALL)
    # DAY sits under the location (it used to overlap the survivor count on the right).
    draw_text(surface, f"DAY {game.day}", 33, 84, YELLOW, FONT)

    # Fuel: against the convoy's fuel capacity.
    draw_text(surface, f"FUEL {game.fuel}/{totals['fuel_capacity']}", 330, 27, YELLOW, SMALL)
    draw_bar(surface, 330, 51, 105, 9, game.fuel, totals["fuel_capacity"], YELLOW)

    # Cargo: food, water and scrap share one pool, so they share one stacked bar. Its full length is the
    # convoy's total cargo space; the dark part at the end is the free space.
    cargo_cap = max(1, totals["cargo"])
    draw_text(surface, f"FOOD {game.food}", 456, 27, GREEN, SMALL)
    draw_text(surface, f"WATER {game.water}", 576, 27, BLUE, SMALL)
    draw_text(surface, f"SCRAP {game.scrap}", 696, 27, ORANGE, SMALL)
    bar_x, bar_w = 456, 363
    pygame.draw.rect(surface, DARK, (bar_x, 51, bar_w, 9), border_radius=3)
    used_before = 0
    for amount, color in ((game.food, GREEN), (game.water, BLUE), (game.scrap, ORANGE)):
        start = int(bar_w * clamp(used_before / cargo_cap, 0, 1))
        used_before += amount
        end = int(bar_w * clamp(used_before / cargo_cap, 0, 1))
        if end > start:
            pygame.draw.rect(surface, color, (bar_x + start, 51, end - start, 9))
    pygame.draw.rect(surface, (90, 100, 102), (bar_x, 51, bar_w, 9), 1, border_radius=3)
    draw_text(surface, f"CARGO {game.cargo_used()}/{totals['cargo']}  free {game.cargo_free()}", 456, 63, MUTED, TINY)

    draw_text(surface, f"SURVIVORS {game.survivors}/{totals['passengers']}", 834, 27, WHITE, SMALL)
    draw_bar(surface, 834, 51, 105, 9, game.survivors, totals["passengers"], WHITE)

    # Convoy health is the combined health of the vehicles.
    draw_text(surface, f"CONVOY {game.convoy_health_pct()}%", 330, 75, WHITE, SMALL)
    draw_bar(surface, 465, 78, 125, 9, totals["health"], totals["max_health"], GREEN)
    state = game.horde_state()
    state_color = HORDE_STATE_COLORS[state]
    draw_text(surface, f"HORDE GAP {game.horde} km", 620, 75, state_color, SMALL)
    draw_bar(surface, 805, 78, 150, 9, game.horde, HORDE_BAR_MAX_KM, state_color)
    draw_text(surface, state.upper(), 805, 92, state_color, TINY)

def draw_events(surface, game):
    """The recent events box: newest message first, long messages wrap, as many as fit."""
    box = (32, 520, 508, 128)
    pygame.draw.rect(surface, (25, 31, 34), box, border_radius=4)
    draw_text(surface, "RECENT EVENTS", 43, 526, YELLOW, TINY)
    y = 546
    for i, message in enumerate(game.log):
        for line in wrap_text(message, 66):
            if y + 13 > box[1] + box[3] - 4:
                return
            draw_text(surface, line, 43, y, WHITE if i == 0 else MUTED, TINY)
            y += 15

def draw_lower(surface, game, buttons):
    # Top: title and notes. Middle: a row of action buttons with their costs. Bottom: events (left), minimap (right).
    pygame.draw.rect(surface, PANEL, (18, 410, WIDTH - 36, 246), border_radius=8)
    draw_text(surface, f"CONVOY ACTIONS ({game.difficulty})", 32, 420, WHITE, FONT)
    food_use, water_use = game.daily_use()
    draw_text(surface, f"Each day: {food_use} food, {water_use} water.", 340, 424, MUTED, SMALL)
    draw_text(surface, "Travel and scavenging take time.", 600, 424, YELLOW, SMALL)
    for button in buttons:
        button.draw(surface)

    # What the actions cost, just below their buttons.
    low, high = game.horde_daily_range()
    draw_text(surface, "1 day", 32, 489, MUTED, TINY)
    draw_text(surface, f"horde +{low} to {high} km closer", 32, 503, MUTED, TINY)
    site_count = len(game.current_sites())
    if site_count > 1:
        draw_text(surface, f"{site_count} sites here", 180, 489, MUTED, TINY)
        draw_text(surface, "click SITE or press Tab", 180, 503, MUTED, TINY)
    can_pay = game.scrap >= REPAIR_SCRAP_COST
    draw_text(surface, f"{REPAIR_SCRAP_COST} scrap", 418, 489, MUTED if can_pay else RED, TINY)
    if game.needs_repair():
        draw_text(surface, f"+{int(REPAIR_FRACTION * 100)}% health", 418, 503, MUTED, TINY)
    else:
        draw_text(surface, "No damage to repair", 418, 503, RED, TINY)

    draw_events(surface, game)
    draw_minimap(surface, game)

def draw_vehicle_card(surface, game):
    """Preview card for the selected vehicle: picture, status, health or recovery cost, key stats."""
    x, y, w, h = CARD
    name = game.selected_vehicle_type
    stats = VEHICLE_SPECS[name]
    owned_vehicle = next((v for v in game.vehicles if v.vehicle_type == name), None)
    pygame.draw.rect(surface, (29, 38, 40), CARD, border_radius=8)
    pygame.draw.rect(surface, BLUE, CARD, 1, border_radius=8)
    draw_text(surface, name, x + 12, y + 10, WHITE, FONT)
    for i, line in enumerate(wrap_text(VEHICLE_ROLES.get(name, ""), 38)[:2]):
        draw_text(surface, line, x + 12, y + 36 + i * 16, MUTED, TINY)

    # Picture: the same side-view drawing as the convoy screen (facing west / left), a bit larger.
    px, py, pw, ph = x + 12, y + 78, w - 24, 120
    pygame.draw.rect(surface, (70, 99, 102), (px, py, pw, ph), border_radius=6)
    pygame.draw.rect(surface, ROAD, (px, py + ph - 30, pw, 30))
    sprite = get_vehicle_sprite(name)
    scale = min((pw - 20) / sprite.get_width(), (ph - 20) / sprite.get_height(), 1.5)
    new_w, new_h = max(1, int(sprite.get_width() * scale)), max(1, int(sprite.get_height() * scale))
    picture = scaled_image(("vehicle", name), sprite, (new_w, new_h))
    surface.blit(picture, (px + (pw - new_w) // 2, py + ph - 10 - new_h))

    draw_text(surface, "OWNED" if owned_vehicle else "NOT OWNED", x + 12, y + 210, GREEN if owned_vehicle else MUTED, SMALL)
    if owned_vehicle:
        hp_color = GREEN if owned_vehicle.health >= 0.6 * stats["health"] else (YELLOW if owned_vehicle.health >= 0.3 * stats["health"] else RED)
        draw_text(surface, f"Health {owned_vehicle.health}/{stats['health']}", x + 12, y + 234, WHITE, TINY)
        draw_bar(surface, x + 12, y + 254, w - 24, 10, owned_vehicle.health, stats["health"], hp_color)
    else:
        draw_text(surface, f"Recovery: {recovery_cost(name)} scrap + 1 day", x + 12, y + 234, WHITE, TINY)
        draw_text(surface, "Starts at 70% health once recovered.", x + 12, y + 254, MUTED, TINY)
    draw_text(surface, f"Seats {stats['passengers']}   Cargo {stats['cargo']}   Defense {stats['defense']}", x + 12, y + 284, MUTED, TINY)
    draw_text(surface, f"Speed {stats['speed']}   Fuel {stats['fuel_capacity']}   Fuel use {stats['fuel_consumption']}", x + 12, y + 304, MUTED, TINY)

def _draw_vehicle_table_row(surface, index, vehicle_name, stats, owned_vehicle, selected):
    """Render one vehicle catalogue row, keeping row styling and stat colours consistent."""
    y = ROW_Y0 + index * ROW_H
    is_owned = owned_vehicle is not None
    if selected:
        pygame.draw.rect(surface, (46, 68, 74), (TABLE_X, y - 2, TABLE_W, 35), border_radius=3)
        pygame.draw.rect(surface, BLUE, (TABLE_X, y - 2, TABLE_W, 35), 1, border_radius=3)
    elif index % 2 == 0:
        pygame.draw.rect(surface, (29, 38, 40), (TABLE_X, y - 2, TABLE_W, 35), border_radius=3)
    draw_text(surface, vehicle_name, COL_NAME, y + 5, WHITE, TINY)
    draw_text(surface, "OWNED" if is_owned else "NOT OWNED", COL_STATUS, y + 5, GREEN if is_owned else MUTED, TINY)
    hp_text = f"{owned_vehicle.health}/{stats['health']}" if is_owned else stats["health"]
    values = [stats["speed"], hp_text, stats["passengers"], stats["cargo"], stats["defense"], stats["fuel_capacity"], stats["fuel_consumption"]]
    for column, (x, value) in enumerate(zip(COL_NUMBERS, values)):
        color = WHITE if is_owned else MUTED
        if column == 1 and is_owned and owned_vehicle.health < stats["health"]:
            color = YELLOW
        draw_text(surface, value, x, y + 5, color, TINY)


def draw_vehicles_screen(surface, game, buttons):
    """Show the vehicle catalogue, ownership, specifications, and convoy totals, with the given buttons."""
    surface.fill((24, 34, 35))
    pygame.draw.rect(surface, PANEL, (18, 125, WIDTH - 36, 535), border_radius=8)
    draw_text(surface, "VEHICLE MANAGEMENT", 32, 137, WHITE, TITLE)
    draw_text(surface, "Select a vehicle to recover it (needs a Truck Stop, Repair Depot or Military Installation) or abandon it. Each needs one driver.", 34, 174, MUTED, TINY)
    draw_text(surface, "SPD speed  HP health  PASS seats  CARGO storage  DEF defense  FCAP fuel capacity  FUSE fuel use", 34, 190, MUTED, TINY)

    totals = game.convoy_stats()
    summary = [
        f"OWNED {len(game.vehicles)} / {len(VEHICLE_SPECS)} (drivers: {game.survivors})",
        f"SPEED {totals['speed']} (slowest vehicle)",
        f"HEALTH {totals['health']}/{totals['max_health']}",
        f"PASSENGERS {game.survivors}/{totals['passengers']}",
        f"CARGO {game.cargo_used()}/{totals['cargo']}",
        f"DEFENSE {totals['defense']} (-{game.defense_reduction()}% ambush)",
        f"FUEL {game.fuel}/{totals['fuel_capacity']}",
        f"FUEL USE {totals['fuel_consumption']}/travel unit",
    ]
    for i, item in enumerate(summary):
        col = i % 4
        row = i // 4
        x = 34 + col * 235
        y = 212 + row * 28
        draw_text(surface, item, x, y, YELLOW if i == 1 else WHITE, SMALL)

    header_y = 274
    pygame.draw.rect(surface, PANEL_LIGHT, (TABLE_X, header_y, TABLE_W, 27), border_radius=4)
    headers = [(COL_NAME, "VEHICLE"), (COL_STATUS, "STATUS")] + list(zip(COL_NUMBERS, ["SPD", "HP", "PASS", "CARGO", "DEF", "FCAP", "FUSE"]))
    for x, label in headers:
        draw_text(surface, label, x, header_y + 6, WHITE, TINY)

    owned_by_type = {vehicle.vehicle_type: vehicle for vehicle in game.vehicles}
    for index, (vehicle_name, stats) in enumerate(VEHICLE_SPECS.items()):
        owned_vehicle = owned_by_type.get(vehicle_name)
        _draw_vehicle_table_row(
            surface, index, vehicle_name, stats, owned_vehicle,
            vehicle_name == game.selected_vehicle_type,
        )

    draw_vehicle_card(surface, game)

    # The convoy travels as one, so the location is not shown here.
    selected = game.selected_vehicle_type
    draw_text(surface, f"Selected: {selected} | Scrap: {game.scrap}", 34, 618, YELLOW, TINY)
    if selected in owned_by_type:
        if game.abandon_confirm == selected:
            draw_text(surface, f"Click CONFIRM ABANDON to give up the {selected}. No refund.", 34, 637, RED, TINY)
        elif len(game.vehicles) <= 1:
            draw_text(surface, "Your last vehicle can't be abandoned.", 34, 637, MUTED, TINY)
        else:
            draw_text(surface, "Abandoned vehicles can be recovered later (no refund).", 34, 637, MUTED, TINY)
    elif game.survivors <= len(game.vehicles):
        draw_text(surface, "No spare survivor to drive another vehicle.", 34, 637, RED, TINY)
    elif game.can_recover_here():
        cost = recovery_cost(selected)
        draw_text(surface, f"Recovery: {cost} scrap + 1 day; vehicle starts at 70% health.", 34, 637, MUTED, TINY)
    else:
        draw_text(surface, "Recover vehicles in a stop with a Truck Stop, Depot or Military Installation.", 34, 637, MUTED, TINY)
    for button in buttons:
        button.draw(surface, selected=(button.label == "CONFIRM ABANDON"))

def draw_menu_screen(surface, game, buttons):
    """The menu: difficulty selection and the way to the instructions, with the given buttons. Only resource use, horde speed and scavenge yield change."""
    surface.fill((24, 34, 35))
    pygame.draw.rect(surface, PANEL, (18, 125, WIDTH - 36, 535), border_radius=8)
    draw_text(surface, "MENU", 32, 137, WHITE, TITLE)
    draw_text(surface, "Difficulty changes how fast supplies run out, how fast the horde closes in, and how much scavenging finds.", 34, 174, MUTED, TINY)

    for i, name in enumerate(DIFFICULTY_ORDER):
        level = DIFFICULTIES[name]
        x = 40 + i * 310
        card = pygame.Rect(x, 205, 290, 270)
        is_current = name == game.difficulty
        pygame.draw.rect(surface, (46, 68, 74) if is_current else (29, 38, 40), card, border_radius=8)
        pygame.draw.rect(surface, BLUE if is_current else (70, 82, 86), card, 2 if is_current else 1, border_radius=8)
        draw_text(surface, name.upper(), x + 18, 218, GREEN if is_current else WHITE, TITLE)
        draw_text(surface, f"Food & water use  x{level['consumption']:g}", x + 18, 268, WHITE, SMALL)
        draw_text(surface, f"Horde speed       x{level['horde']:g}", x + 18, 296, WHITE, SMALL)
        draw_text(surface, f"Scavenge yield    x{level['scavenge']:g}", x + 18, 324, WHITE, SMALL)
        draw_text(surface, level["blurb"], x + 18, 372, MUTED, TINY)
        if is_current:
            draw_text(surface, "CURRENT", x + 18, 396, YELLOW, TINY)

    draw_text(surface, "Not affected by difficulty: vehicle stats, repair cost, distances, fuel costs, recovery costs.", 34, 500, MUTED, TINY)
    draw_text(surface, "Changes apply immediately and stay when you restart a run (R), but are not saved when you close the game.", 34, 520, MUTED, TINY)
    for button in buttons:
        button.draw(surface, selected=(button.label == game.difficulty))

def wrap_pixels(string, font, max_width):
    """Split text into lines that fit `max_width` pixels in `font`."""
    lines, current = [], ""
    for word in string.split():
        trial = (current + " " + word).strip()
        if current and font.size(trial)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _draw_paragraph(surface, string, x, y, width, color=WHITE, font=SMALL):
    """Draw wrapped text (just measure it when surface is None); returns the y below it."""
    for line in wrap_pixels(string, font, width):
        if surface is not None:
            draw_text(surface, line, x, y, color, font)
        y += font.get_linesize()
    return y


def _layout_instructions(surface, page, body):
    """Lay out one instructions page with the font `body`; draws it unless surface is None. Returns the bottom y."""
    top = 182
    gap = 8 if body is SMALL else 5
    if page == 0:
        left_x, left_w = 34, 380
        right_x = left_x + left_w + 30
        right_w = WIDTH - 34 - right_x
        if surface is not None:
            draw_text(surface, text.MISSION_TITLE, left_x, top, YELLOW, FONT)
        y = top + 30
        for paragraph in text.MISSION:
            y = _draw_paragraph(surface, paragraph, left_x, y, left_w, WHITE, body) + gap
        left_bottom = y
        if surface is not None:
            draw_text(surface, text.CONTROLS_TITLE, right_x, top, YELLOW, FONT)
        y = top + 30
        key_w = 110
        for key, action in text.CONTROLS:
            if surface is not None:
                draw_text(surface, key, right_x, y, GREEN, body)
            y = _draw_paragraph(surface, action, right_x + key_w, y, right_w - key_w, WHITE, body) + gap // 2
        y = _draw_paragraph(surface, text.CONTROLS_NOTE, right_x, y + gap, right_w, MUTED, TINY)
        return max(left_bottom, y)
    x, width = 34, WIDTH - 68
    if surface is not None:
        draw_text(surface, text.HOW_TO_PLAY_TITLE, x, top, YELLOW, FONT)
    y = _draw_paragraph(surface, text.HOW_TO_PLAY_INTRO, x, top + 30, width, WHITE, body) + gap
    label_w = 170
    for label, description in text.HOW_TO_PLAY:
        if surface is not None:
            draw_text(surface, label, x, y, GREEN, body)
        y = _draw_paragraph(surface, description, x + label_w, y, width - label_w, WHITE, body) + gap // 2
    y += gap
    for paragraph in text.HOW_TO_PLAY_OUTRO:
        y = _draw_paragraph(surface, paragraph, x, y, width, MUTED, body) + gap
    return y


def draw_instructions_screen(surface, game, buttons):
    """The player instructions: page 1 is the mission and controls, page 2 is how to play.

    Each page uses the larger font when it fits above the buttons, otherwise the smaller one.
    """
    surface.fill((24, 34, 35))
    pygame.draw.rect(surface, PANEL, (18, 125, WIDTH - 36, 535), border_radius=8)
    draw_text(surface, "INSTRUCTIONS", 32, 137, WHITE, TITLE)
    draw_text(surface, f"Page {game.instructions_page + 1} / {text.PAGE_COUNT}", WIDTH - 130, 145, MUTED, SMALL)
    body = SMALL if _layout_instructions(None, game.instructions_page, SMALL) <= 605 else TINY
    _layout_instructions(surface, game.instructions_page, body)
    for button in buttons:
        button.draw(surface)


def draw_logo(surface, cx, cy, r):
    """The game's emblem: a badge with a west-pointing arrow and a small convoy of three headlights."""
    pygame.draw.circle(surface, DARK, (cx, cy), r)
    pygame.draw.circle(surface, YELLOW, (cx, cy), r, 3)
    pygame.draw.circle(surface, (90, 100, 102), (cx, cy), r - 7, 1)
    arrow = [(-0.62, 0), (-0.12, -0.38), (-0.12, -0.14), (0.62, -0.14), (0.62, 0.14), (-0.12, 0.14), (-0.12, 0.38)]
    pygame.draw.polygon(surface, YELLOW, [(cx + int(px * r), cy - int(r * 0.12) + int(py * r)) for px, py in arrow])
    for i in range(3):
        pygame.draw.circle(surface, WHITE, (cx - int(r * 0.32) + int(i * r * 0.32), cy + int(r * 0.52)), max(2, r // 14))


def draw_title_screen(surface, game, buttons):
    """Title screen: logo and name above the convoy scene, with PLAY and MENU."""
    surface.fill((24, 34, 35))
    title = BIG.render(story.GAME_TITLE, True, WHITE)
    title_rect = title.get_rect(center=(WIDTH // 2 + 40, 66))
    surface.blit(title, title_rect)
    draw_logo(surface, title_rect.left - 52, 66, 38)

    scene = pygame.Rect(18, 125, WIDTH - 36, 270)
    background = scaled_image("background", get_background_image(), (scene.w, scene.h))
    surface.blit(background, scene.topleft)
    for x, y in sorted(ZOMBIE_SLOTS[:8], key=lambda slot: slot[1]):
        draw_zombie(surface, x, y, 0.8 + (y - 300) / 34 * 0.4)
    draw_convoy_vehicles(surface, game, scene)

    tagline = FONT.render(story.TAGLINE, True, YELLOW)
    surface.blit(tagline, tagline.get_rect(center=(WIDTH // 2, 430)))
    for button in buttons:
        button.draw(surface)
    hint = TINY.render("Press ENTER to play", True, MUTED)
    surface.blit(hint, hint.get_rect(center=(WIDTH // 2, 555)))


def draw_lore_screen(surface, game, buttons):
    """The story: why the convoy must reach the Pacific Coast."""
    surface.fill((24, 34, 35))
    pygame.draw.rect(surface, PANEL, (18, 60, WIDTH - 36, 520), border_radius=8)
    heading = TITLE.render(story.LORE_TITLE, True, YELLOW)
    surface.blit(heading, heading.get_rect(center=(WIDTH // 2, 100)))
    width = min(WIDTH - 100, 820)
    x = (WIDTH - width) // 2
    for font, gap in ((FONT, 18), (SMALL, 14)):   # the larger font unless the story would not fit
        bottom = 150
        for paragraph in story.LORE:
            bottom = _draw_paragraph(None, paragraph, x, bottom, width, WHITE, font) + gap
        if bottom <= 575:
            break
    y = 150
    for paragraph in story.LORE:
        y = _draw_paragraph(surface, paragraph, x, y, width, WHITE, font) + gap
    for button in buttons:
        button.draw(surface)
    hint = TINY.render("Press ENTER to start", True, MUTED)
    surface.blit(hint, hint.get_rect(center=(WIDTH // 2, 658)))


def end_stats(game):
    """The (label, value, colour) rows summarising the finished run."""
    lost = game.vehicles_lost()
    return [
        ("Days survived", game.day, WHITE),
        ("Survivors left", game.survivors, WHITE if game.survivors else RED),
        ("Stops visited", f"{game.stops_visited()} of {game.stops_total()}", WHITE),
        ("Vehicles lost", lost, RED if lost else WHITE),
        ("Distance travelled", f"{game.km_traveled} km", WHITE),
        ("Difficulty", game.difficulty, MUTED),
    ]


def draw_end_overlay(surface, game, buttons):
    """Victory / game over screen: how the run ended, a summary of it, and the buttons to go on."""
    if game.status == "playing":
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 205))
    surface.blit(overlay, (0, 0))
    won = game.status == "won"
    color = GREEN if won else RED
    x, y, w, h = END_PANEL
    pygame.draw.rect(surface, PANEL, END_PANEL, border_radius=10)
    pygame.draw.rect(surface, color, END_PANEL, 2, border_radius=10)

    title = BIG.render("YOU ESCAPED!" if won else "CONVOY LOST", True, color)
    surface.blit(title, title.get_rect(center=(x + w // 2, y + 55)))
    reason = game.end_reason or game.log[0]
    ly = y + 105
    for line in wrap_pixels(reason, SMALL, w - 80):
        label = SMALL.render(line, True, WHITE)
        surface.blit(label, label.get_rect(center=(x + w // 2, ly + 9)))
        ly += 24

    draw_text(surface, "YOUR JOURNEY", x + 40, y + 170, MUTED, TINY)
    row_y = y + 196
    for i, (name, value, value_color) in enumerate(end_stats(game)):
        pygame.draw.line(surface, (70, 82, 86), (x + 40, row_y - 4), (x + w - 40, row_y - 4), 1)
        draw_text(surface, name, x + 44, row_y + 6, MUTED, SMALL)
        value_text = SMALL.render(str(value), True, value_color)
        surface.blit(value_text, value_text.get_rect(topright=(x + w - 44, row_y + 6)))
        row_y += 40
    pygame.draw.line(surface, (70, 82, 86), (x + 40, row_y - 4), (x + w - 40, row_y - 4), 1)

    for button in buttons:
        button.draw(surface)
    hint = TINY.render("R or ENTER: play again   |   ESC: quit", True, MUTED)
    surface.blit(hint, hint.get_rect(center=(x + w // 2, y + h - 18)))
