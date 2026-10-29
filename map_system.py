"""Map and minimap rendering for THE LAST CONVOY.

The map data and pathfinding live in map_data.py (no pygame); this module only draws them.
"""
import pygame
import os

from layout import MINI_CARD, MINI_SCALE, WIDTH
from map_data import NODES, PACIFIC, ROAD_EDGES, SITES, START
from theme import (BLUE, DARK, FONT, GREEN, HORDE_STATE_COLORS, MUTED, ORANGE, PANEL, PANEL_LIGHT, RED, SMALL,
                   TINY, TITLE, WHITE, YELLOW)
from widgets import clamp, draw_text

MAP_BG = pygame.image.load(
    os.path.join(os.path.dirname(__file__), "assets", "backgrounds", "map_background.png")
)

def draw_roads(surface, points, edges, road_color=(112, 115, 105), line_color=(220, 205, 153), main_width=22, other_width=14, center_width=2):
    """Draw the road bed and centre line for either the full map or minimap."""
    for a, b, _km, kind in edges:
        pygame.draw.line(surface, road_color, points[a], points[b], main_width if kind == "main" else other_width)
    for a, b, _km, kind in edges:
        pygame.draw.line(surface, line_color, points[a], points[b], center_width)

def danger_color(danger, selected=False):
    """Shared danger-state colour mapping for map markers."""
    if danger == "overrun":
        return RED
    if danger == "risky":
        return ORANGE
    return BLUE if selected else PANEL_LIGHT

def mini_point(x, y):
    """Convert a highway-map position to a position inside the minimap card."""
    cx, cy, cw, _ch = MINI_CARD
    return int(cx + cw / 2 + (x - 512.5) * MINI_SCALE), int(cy + 64 + (y - 332.5) * MINI_SCALE)

def draw_minimap(surface, game):
    """Display-only copy of the map: east (start) on the right, Pacific Coast on the left."""
    cx0, cy0, cw, ch = MINI_CARD
    pygame.draw.rect(surface, (35, 48, 43), MINI_CARD, border_radius=8)
    pygame.draw.rect(surface, (94, 108, 111), MINI_CARD, 1, border_radius=8)
    # The same scattered trees as the map screen, scaled down (only those that fall inside the card).
    for i in range(18):
        tx, ty = mini_point(45 + (i * 53) % 900, 210 + (i * 71) % 330)
        if cx0 + 8 <= tx <= cx0 + cw - 8 and cy0 + 8 <= ty <= cy0 + ch - 8:
            pygame.draw.circle(surface, (47, 72, 55), (tx, ty), 4)
    points = [mini_point(*node["pos"]) for node in NODES]
    draw_roads(surface, points, ROAD_EDGES, main_width=8, other_width=5, center_width=1)

    pos = game.position
    dangers = set()
    for i, (x, y) in enumerate(points):
        danger = game.travel_danger(i)
        if danger:
            dangers.add(danger)
        if danger == "overrun":
            fill = RED
        elif danger == "risky":
            fill = ORANGE
        elif i == pos:
            fill = YELLOW
        elif i == START or NODES[i]["axis"] < NODES[pos]["axis"]:
            fill = GREEN          # stops behind the convoy that are safe to return to
        else:
            fill = PANEL_LIGHT
        pygame.draw.circle(surface, fill, (x, y), 8)
        pygame.draw.circle(surface, WHITE, (x, y), 8, 1)
        text = "X" if danger == "overrun" else ("!" if danger == "risky" else NODES[i]["tag"])
        draw_text(surface, text, x - TINY.size(text)[0] // 2, y - 7, DARK if fill == YELLOW else WHITE, TINY)
        if i == pos:
            pygame.draw.circle(surface, YELLOW, (x, y), 13, 2)
            label_w = TINY.size("CONVOY")[0]
            lx = int(clamp(x - label_w // 2, cx0 + 4, cx0 + cw - 4 - label_w))
            ly = y - 30 if y - 30 >= cy0 + 2 else y + 16
            draw_text(surface, "CONVOY", lx, ly, YELLOW, TINY)

    legend = []
    if "overrun" in dangers:
        legend.append("X overrun")
    if "risky" in dangers:
        legend.append("! risky")
    if legend:
        text = "  ".join(legend)
        draw_text(surface, text, cx0 + cw - 10 - TINY.size(text)[0], cy0 + ch - 18, RED if "overrun" in dangers else ORANGE, TINY)

def route_point_for_axis(axis):
    """Where a position on the straight Start-to-Pacific line is along the map's main road."""
    main = [NODES[i] for i in range(PACIFIC + 1)]
    if axis <= 0:
        sx, sy = main[0]["pos"]
        return int(sx + min(45, -axis * 0.25)), sy
    for a, b in zip(main, main[1:]):
        if axis <= b["axis"]:
            t = (axis - a["axis"]) / (b["axis"] - a["axis"])
            return (int(a["pos"][0] + (b["pos"][0] - a["pos"][0]) * t),
                    int(a["pos"][1] + (b["pos"][1] - a["pos"][1]) * t))
    return main[-1]["pos"]

def draw_map(surface, game):
    # Exact area where the terrain should appear
    map_rect = pygame.Rect(18, 195, WIDTH - 36, 345)

    bg_w, bg_h = MAP_BG.get_size()

    # Scale to FILL the rectangle, not fit inside it
    scale = max(
        map_rect.width / bg_w,
        map_rect.height / bg_h
    )

    scaled_size = (
        round(bg_w * scale),
        round(bg_h * scale)
    )

    scaled_bg = pygame.transform.smoothscale(
        MAP_BG, scaled_size
    )

    # Crop the center of the scaled image
    crop_x = (scaled_size[0] - map_rect.width) // 2
    crop_y = (scaled_size[1] - map_rect.height) // 2

    cropped_bg = scaled_bg.subsurface(
        pygame.Rect(
            crop_x,
            crop_y,
            map_rect.width,
            map_rect.height
        )
    )

    # Draw only the cropped image in the map area
    surface.blit(cropped_bg, map_rect.topleft)

    # Map heading and instructions.
    draw_text(surface, "HIGHWAY MAP", 32, 137, WHITE, TITLE)
    draw_text(
        surface,
        "Travel west across the country. Click a stop to inspect it. "
        "Costs are measured from where you are now.",
        34, 174, MUTED, TINY
    )

    # East is on the right; the Pacific Coast / western destination is on the left.
    draw_roads(surface, [node["pos"] for node in NODES], ROAD_EDGES)

    for i, node in enumerate(NODES):
        x, y = node["pos"]
        selected = i == game.selected
        danger = game.travel_danger(i)
        color = GREEN if i == START and danger not in ("overrun", "risky") else danger_color(danger, selected)
        pygame.draw.circle(surface, color, (x, y), 17)
        pygame.draw.circle(surface, WHITE, (x, y), 17, 2)
        if selected and danger:
            pygame.draw.circle(surface, BLUE, (x, y), 21, 2)   # keep the selection visible on red / orange stops
        draw_text(surface, node["tag"], x - 4, y - 9, WHITE, SMALL)
        label = TINY.render(node["label"], True, WHITE)
        surface.blit(label, label.get_rect(center=(x, y + 29)))
        if danger:
            tag = TINY.render("OVERRUN" if danger == "overrun" else "RISKY", True, RED if danger == "overrun" else ORANGE)
            surface.blit(tag, tag.get_rect(center=(x, y + 45)))
        if i == game.position:
            # Mark where the convoy currently is.
            pygame.draw.circle(surface, YELLOW, (x, y), 25, 3)
            here = TINY.render("CONVOY", True, YELLOW)
            surface.blit(here, here.get_rect(center=(x, y - 36)))

    # The horde, placed on the main road at its real position on the Start-to-Pacific line.
    state = game.horde_state()
    hx, hy = route_point_for_axis(game.horde_km)
    for i in range(6):
        pygame.draw.circle(surface, (111, 143, 79), (hx + (i % 3) * 8 - 8, hy + (i // 3) * 8 - 4), 5)
    horde_label = TINY.render(f"HORDE: {state.upper()}", True, HORDE_STATE_COLORS[state])
    surface.blit(horde_label, horde_label.get_rect(center=(int(clamp(hx, 70, 925)), hy + 66)))

    dest = NODES[game.selected]
    trip = game.plan_trip()
    danger = game.travel_danger()
    info = pygame.Rect(32, 548, 600, 100)
    pygame.draw.rect(surface, PANEL, info, border_radius=7)
    pygame.draw.rect(surface, RED if danger == "overrun" else (ORANGE if danger == "risky" else BLUE), info, 1, border_radius=7)
    draw_text(surface, f"SELECTED: {dest['name']}", 45, 552, WHITE, FONT)
    if trip["km"] == 0:
        draw_text(surface, "The convoy is already here.", 45, 576, YELLOW, SMALL)
    else:
        direction = "WEST" if trip["delta"] > 0 else ("EAST (backwards)" if trip["delta"] < 0 else "DETOUR")
        draw_text(surface, f"Fuel required: {trip['fuel']}  |  {trip['km']} km {direction}  |  {trip['days']} day(s)", 45, 576, YELLOW, SMALL)
        route = "direct road" if not trip["through"] else "via " + ", ".join(trip["through"])
        draw_text(surface, f"Route: {route} ({trip['km']} km)", 45, 596, MUTED, TINY)
    sites = dest.get("sites", [])
    if dest["kind"] == "coast":
        detail = "Final destination: reach the coast to escape by ship."
    elif len(sites) == 1:
        detail = SITES[sites[0]]["detail"]
    elif sites:
        detail = "Sites: " + ", ".join(SITES[site]["name"] for site in sites) + ". Scavenge one at a time."
    else:
        detail = "Explore this location."
    draw_text(surface, detail, 45, 614, MUTED, TINY)
    if trip["km"] > 0:
        if danger == "overrun":
            draw_text(surface, "BLOCKED: this trip would let the horde overrun the convoy.", 45, 632, RED, TINY)
        elif danger == "risky":
            draw_text(surface, "RISKY: the horde may overrun the convoy on this trip.", 45, 632, ORANGE, TINY)
        elif trip["delta"] > 0:
            draw_text(surface, f"Horde gap grows by {trip['delta']} km (before time passes).", 45, 632, GREEN, TINY)
        elif trip["delta"] < 0:
            draw_text(surface, f"Horde gap shrinks by {-trip['delta']} km (before time passes).", 45, 632, RED, TINY)
        else:
            draw_text(surface, "Detour: the gap doesn't change, but time passes and the horde closes in.", 45, 632, ORANGE, TINY)
    short_of_fuel = trip["km"] > 0 and game.fuel < trip["fuel"]
    draw_text(surface, f"Fuel available: {game.fuel}" + (f" (need {trip['fuel']})" if short_of_fuel else ""), 660, 556, RED if short_of_fuel else WHITE, SMALL)
    draw_text(surface, f"Horde gap: {game.horde} km ({state})", 660, 578, HORDE_STATE_COLORS[state], SMALL)
