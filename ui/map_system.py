"""Map and minimap rendering for THE LAST CONVOY. Drawing only.

The map data and pathfinding live in map_data.py (no pygame); this module only draws them.

The map screen is drawn straight onto the window from map_layout (the layout/ package): the terrain fills the map rectangle,
the stops sit where map_layout puts them (the same positions layout.node_at uses for clicks) and circles, labels,
the CONVOY / HORDE markers and the info panel follow the size of the map rectangle.
"""
import random

import pygame

from widgets import PIX, draw_frame, draw_panel
import os

import map_data
from config import MAP_BG_PIXEL_ART
from layout import calculate_layout, map_point_in
from map_data import NODES, PACIFIC, ROAD_EDGES, SITES, START
from .pixel_art import ART_BLOCK, pixelate
from theme import (ACCESS, BLUE, DARK, DISABLED_BG, DISABLED_TEXT, FONT, GREEN, HORDE_STATE_COLORS, LARGE, MEDIUM, MUTED, ORANGE, PANEL, PANEL_LIGHT,
                   RED, SMALL, TINY, WHITE, YELLOW)
from widgets import (clamp, draw_text, ellipsize, fit_variants, pick_font, scaled_font, screen_fonts, text_in_rect,
                     text_surface, wrap_pixels)

_MAP_BG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "backgrounds", "map_background.png")
_MAP_BG = None
_MAP_TERRAIN = {}   # the finished terrain picture for each map size
_MINI_TERRAIN = {}  # the same picture for each minimap size


def _map_bg():
    """The low-resolution map background, loaded once (after the window exists)."""
    global _MAP_BG
    if _MAP_BG is None:
        image = pygame.image.load(_MAP_BG_PATH).convert()
        # MAP_BG_PIXEL_ART (config.py): True = chunky low-resolution pixel art; False = the PNG as drawn, scaled smoothly
        _MAP_BG = pixelate(image, ART_BLOCK["map"]) if MAP_BG_PIXEL_ART else image
    return _MAP_BG


def _mini_terrain(size):
    """The map background fitted to the minimap card: scaled (not by a whole number) so the whole picture is
    seen, cropped at the centre to the card's shape. Built once per size."""
    terrain = _MINI_TERRAIN.get(size)
    if terrain is None:
        bg = _map_bg()
        width, height = size
        bg_w, bg_h = bg.get_size()
        scale = max(width / bg_w, height / bg_h)
        new_size = (max(width, round(bg_w * scale)), max(height, round(bg_h * scale)))
        try:
            scaled = (pygame.transform.smoothscale if scale < 1 else pygame.transform.scale)(bg, new_size)
        except ValueError:   # smoothscale needs a 24 / 32-bit surface
            scaled = pygame.transform.scale(bg, new_size)
        crop = pygame.Rect((new_size[0] - width) // 2, (new_size[1] - height) // 2, width, height)
        terrain = scaled.subsurface(crop).copy()
        if len(_MINI_TERRAIN) > 4:
            _MINI_TERRAIN.clear()
        _MINI_TERRAIN[size] = terrain
    return terrain


# ---- The horde: a crowd of zombies filling the land east of its front --------------------------------------------
_HORDE_COLORS = ((111, 143, 79), (86, 114, 63), (139, 166, 98), (64, 86, 52), (96, 120, 70), (122, 52, 46))
_HORDE_FIELDS = {}


def _horde_field(size, grain):
    """A transparent picture of a dense crowd of dots (with a dark tint underneath) covering `size`. Built once per
    size; each frame only the part east of the horde's front is drawn (_draw_horde)."""
    key = (size, grain)
    field = _HORDE_FIELDS.get(key)
    if field is None:
        width, height = size
        field = pygame.Surface(size, pygame.SRCALPHA)
        field.fill((24, 38, 22, 125))
        rng = random.Random(1307)   # fixed seed: the crowd looks the same every frame and every run
        spacing = max(2, int(grain * 1.5))
        for gy in range(-1, height // spacing + 2):
            for gx in range(-1, width // spacing + 2):
                x = int(gx * spacing + rng.uniform(-0.6, 0.6) * spacing)
                y = int(gy * spacing + rng.uniform(-0.6, 0.6) * spacing)
                pygame.draw.circle(field, rng.choice(_HORDE_COLORS), (x, y), rng.randint(max(1, grain - 1), grain + 1))
        if len(_HORDE_FIELDS) > 6:
            _HORDE_FIELDS.clear()
        _HORDE_FIELDS[key] = field
    return field


def _draw_horde(surface, rect, front_x, grain, strip, jag):
    """Draw the crowd over `rect` from the horde's front (an x position) to the east edge. The front is ragged:
    each horizontal strip starts a little further east or west, the same way every frame."""
    field = _horde_field(rect.size, grain)
    for k, y in enumerate(range(0, rect.h, strip)):
        offset = int((((k * 2654435761) >> 7) % 1000) / 1000 * 2 * jag - jag)
        x = int(clamp(front_x + offset - rect.x, 0, rect.w))
        if x < rect.w:
            surface.blit(field, (rect.x + x, rect.y + y), pygame.Rect(x, y, rect.w - x, min(strip, rect.h - y)))


def _backing(surface, rect, alpha=150):
    """A dark see-through box behind text so it can be read over the horde."""
    box = pygame.Surface(rect.size, pygame.SRCALPHA)
    box.fill((10, 14, 10, alpha))
    surface.blit(box, rect.topleft)


def _map_terrain(size):
    """The map terrain filling `size`, with NO zoom: the whole low-resolution picture is shown, trimmed only as much as
    needed to match the map rectangle's shape (the same fractions at every size, centred), then enlarged to exactly
    the rectangle. The stops are placed as fractions of that same rectangle (layout.map_layout), so the picture and
    the stops keep the same relationship at every window size. Built once per size, not every frame."""
    terrain = _MAP_TERRAIN.get(size)
    if terrain is None:
        bg = _map_bg()   # after the window exists
        width, height = size
        bg_w, bg_h = bg.get_size()
        if bg_w * height > bg_h * width:     # picture wider than the map: trim the sides
            crop_w, crop_h = max(1, round(bg_h * width / height)), bg_h
        else:                                # picture taller than the map: trim top and bottom
            crop_w, crop_h = bg_w, max(1, round(bg_w * height / width))
        crop = pygame.Rect((bg_w - crop_w) // 2, (bg_h - crop_h) // 2, crop_w, crop_h)
        part = bg.subsurface(crop)
        if MAP_BG_PIXEL_ART:
            terrain = pygame.transform.scale(part, size)   # nearest neighbour: crisp art pixels, no smoothing blur
        else:
            try:
                terrain = pygame.transform.smoothscale(part, size)   # fine detail, no chunky pixels
            except ValueError:   # smoothscale needs a 24 / 32-bit surface
                terrain = pygame.transform.scale(part, size)
        _MAP_TERRAIN.clear()   # only one map size is ever on screen
        _MAP_TERRAIN[size] = terrain
    return terrain


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

def _mix(base, other, amount):
    """`base` colour moved `amount` (0-1) of the way towards `other`."""
    return tuple(int(b + (o - b) * amount) for b, o in zip(base[:3], other[:3]))


# Colours of a stop that is not one road away (disabled): (fill, outline). Still clearly dimmer than a reachable stop,
# but overrun is a dark red, risky a dark orange and a visited stop a grey-green. Danger beats "visited".
_DISABLED_TINTS = {
    "overrun": ((104, 30, 30), (178, 74, 74)),
    "risky": ((150, 84, 22), (211, 132, 74)),
    "visited": ((52, 80, 58), (110, 150, 116)),
}


def _visited(game, i):
    """Whether the convoy has been at stop i (the starting highway counts from day one)."""
    return i == START or i in game.visited


def _mini_bounds():
    """The box (left, top, right, bottom) in map space that the minimap has to show: every stop, plus the strip east of
    the start where the horde walks in from."""
    xs = [node["pos"][0] for node in NODES]
    ys = [node["pos"][1] for node in NODES]
    return min(xs), min(ys), max(xs) + 45, max(ys)


def mini_point(x, y, card):
    """Map-space coordinates -> minimap pixels. The stops' bounding box is stretched to fill the card (a small margin
    only), so the minimap uses its whole box; `card` is the minimap rectangle."""
    cx, cy, cw, ch = card
    x0, y0, x1, y1 = _mini_bounds()
    pad_x, pad_y = max(10, cw // 28), max(14, ch // 9)   # room for the circles and the CONVOY label
    sx = (cw - 2 * pad_x) / max(1, x1 - x0)
    sy = min((ch - 2 * pad_y) / max(1, y1 - y0), sx * 1.6)   # stretch vertically, but not too much
    ox = cx + (cw - (x1 - x0) * sx) / 2
    oy = cy + (ch - (y1 - y0) * sy) / 2
    return int(ox + (x - x0) * sx), int(oy + (y - y0) * sy)


def draw_minimap(surface, game, card=None):
    """Draw the minimap: the map screen's background, the horde, the roads and the stops, filling the card."""
    if card is None:
        card = calculate_layout(*surface.get_size())["minimap"]
    card = pygame.Rect(card)

    cx0, cy0, cw, ch = card
    surface.blit(_mini_terrain(card.size), card.topleft)
    draw_frame(surface, card, (94, 108, 111), 1 * PIX)

    # Clip drawing to the minimap card.
    old_clip = surface.get_clip()
    surface.set_clip(card)

    # The horde: everything east of its front on the main road.
    state = game.horde_state()
    hx, hy = mini_point(*route_point_for_axis(game.horde_km), card)
    _draw_horde(surface, card, hx, max(1, cw // 160), 3, max(3, cw // 70))

    points = [mini_point(*node["pos"], card) for node in NODES]
    draw_roads(
        surface, points, ROAD_EDGES,
        main_width=max(2, cw // 50),
        other_width=max(1, cw // 75),
        center_width=1
    )

    pos = game.position
    dangers = set()

    for i, (x, y) in enumerate(points):
        danger = game.travel_danger(i)
        if danger:
            dangers.add(danger)

        # Danger beats visited and "here". A stop that is not one road away is drawn disabled, as on the full map:
        # dark red when overrun, dark orange when risky, grey-green when only visited.
        disabled = i != pos and not game.can_travel_to(i)
        outline = WHITE
        if disabled and (danger or _visited(game, i)):
            fill, outline = _DISABLED_TINTS.get(danger) or _DISABLED_TINTS["visited"]
        elif danger == "overrun":
            fill = RED
        elif danger == "risky":
            fill = ORANGE
        elif i == pos:
            fill = YELLOW
        elif _visited(game, i):
            fill = GREEN
        else:
            fill = PANEL_LIGHT

        radius = max(3, min(7, cw // 55))
        pygame.draw.circle(surface, fill, (x, y), radius)
        pygame.draw.circle(surface, outline, (x, y), radius, 1)

        label = (
            "X" if danger == "overrun"
            else "!" if danger == "risky"
            else NODES[i]["tag"]
        )
        label_img = text_surface(label, TINY, DARK if fill == YELLOW else WHITE)
        surface.blit(label_img, label_img.get_rect(center=(x, y)))

        if i == pos:
            pygame.draw.circle(surface, YELLOW, (x, y), radius + 4, 2)
            convoy_label = text_surface("CONVOY", TINY, YELLOW)
            lx = max(
                cx0 + 3,
                min(x - convoy_label.get_width() // 2,
                    cx0 + cw - convoy_label.get_width() - 3)
            )
            ly = y - 19 if y - 19 >= cy0 + 2 else y + 10
            _backing(surface, pygame.Rect(lx - 2, ly, convoy_label.get_width() + 4, convoy_label.get_height()), 110)
            surface.blit(convoy_label, (lx, ly))

    # A small HORDE tag at its front, when there is room east of the front for it.
    horde_label = text_surface("HORDE", TINY, HORDE_STATE_COLORS[state])
    lw, lh = horde_label.get_size()
    if cx0 + cw - hx >= lw + 8:
        spot = pygame.Rect(hx + 5, int(clamp(hy - lh // 2, cy0 + 2, cy0 + ch - lh - 2)), lw, lh)
        _backing(surface, spot.inflate(4, 2))
        surface.blit(horde_label, spot.topleft)

    legend = []
    if "overrun" in dangers:
        legend.append("X overrun")
    if "risky" in dangers:
        legend.append("! risky")

    if legend:
        text = "  ".join(legend)
        image = text_surface(text, TINY, RED if "overrun" in dangers else ORANGE)
        spot = pygame.Rect(cx0 + 4, cy0 + ch - image.get_height() - 3, *image.get_size())
        _backing(surface, spot.inflate(4, 2))
        surface.blit(image, spot.topleft)

    surface.set_clip(old_clip)


def route_point_for_axis(axis):
    """Where a position on the straight Start-to-Pacific line is along the map's main road, in the old
    1000 x 680 map space of the NODES "pos" values (layout.map_point_in converts it to window pixels)."""
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


# ---- The map screen ----------------------------------------------------------------------------------------------
def _label_font(unit):
    """The stop-label font for a map drawn at `unit` times the old size (1.0 = the old 964 px wide map)."""
    if unit >= 1.7:
        return FONT
    if unit >= 1.35:
        return MEDIUM
    if unit >= 1.0:
        return SMALL
    return TINY


_LABEL_CACHE = {}


def _static_labels(g, font):
    """Where each stop's name goes (a Rect, or None when it would not fit without touching something).

    Candidates are below, above, right and left of the circle; a label is kept inside the map, away from the other
    stops' circles and from the labels already placed. Cached per window size, font and map layout.
    """
    key = (g["size"], font, map_data.LAYOUT_VERSION)   # the stops move with each run's map layout
    cached = _LABEL_CACHE.get(key)
    if cached is not None:
        return cached
    map_rect = pygame.Rect(g["map"])
    r, positions = g["radius"], g["positions"]
    circles = [pygame.Rect(x - r - 2, y - r - 2, 2 * r + 4, 2 * r + 4) for x, y in positions]
    placed, result = [], []
    for i, node in enumerate(NODES):
        x, y = positions[i]
        w, h = font.size(node["label"])
        chosen = None
        for sx, sy in ((x - w // 2, y + r + 3), (x - w // 2, y - r - 3 - h),
                       (x + r + 4, y - h // 2), (x - r - 4 - w, y - h // 2)):
            rect = pygame.Rect(int(clamp(sx, map_rect.x + 2, map_rect.right - w - 2)), sy, w, h)
            if not map_rect.contains(rect):
                continue
            if any(rect.colliderect(c) for j, c in enumerate(circles) if j != i):
                continue
            if any(rect.colliderect(p) for p in placed):
                continue
            chosen = rect
            break
        if chosen is not None:
            placed.append(chosen)
        result.append(chosen)
    if len(_LABEL_CACHE) > 8:
        _LABEL_CACHE.clear()
    _LABEL_CACHE[key] = result
    return result


def _place_text(images, centre, outer, map_rect, avoid):
    """Find room for a marker's text next to a marker centred at `centre` whose outline reaches `outer` pixels.

    `images` are the text surfaces to try, longest first. Each is tried above, below, right, left and diagonally
    from the marker (then one text line further out), kept inside the map; the first spot clear of every rectangle
    in `avoid` wins. Returns (image, rect), or None when there is no clear spot: the caller then leaves the text
    out (the marker itself is still drawn, and the info panel gives the same facts).
    """
    x, y = centre
    for image in images:
        w, h = image.get_size()
        for extra in (0, h + 2):
            o = outer + extra
            d = int(o * 0.75)
            spots = ((x - w // 2, y - o - h - 1), (x - w // 2, y + o + 1), (x + o + 3, y - h // 2),
                     (x - o - 3 - w, y - h // 2), (x + d, y - d - h), (x - d - w, y - d - h),
                     (x + d, y + d), (x - d - w, y + d))
            for sx, sy in spots:
                rect = pygame.Rect(int(clamp(sx, map_rect.x + 2, map_rect.right - w - 2)),
                                   int(clamp(sy, map_rect.y + 2, map_rect.bottom - h - 2)), w, h)
                if not any(rect.colliderect(a) for a in avoid):
                    return image, rect
    return None


def draw_map(surface, game, g):
    """The map itself (terrain, roads, stops, CONVOY and HORDE markers) in the rectangles of map_layout `g`."""
    map_rect = pygame.Rect(g["map"])
    # The terrain fills the rectangle (cropped, not squashed) and is cached, so it is not rescaled every frame.
    surface.blit(_map_terrain(map_rect.size), map_rect.topleft)

    unit, radius, ring, positions = g["unit"], g["radius"], g["ring"], g["positions"]
    old_clip = surface.get_clip()
    surface.set_clip(map_rect)
    line = max(1, int(round(2 * unit)))

    # The horde fills the land east of its front, drawn under the roads and stops. Its front sits on the main road at
    # the horde's real position on the Start-to-Pacific line.
    state = game.horde_state()
    hx, hy = map_point_in(g["node_area"], route_point_for_axis(game.horde_km))
    grain = max(3, int(round(5 * unit)))
    step = max(5, int(round(8 * unit)))
    hx = int(clamp(hx, map_rect.x + step + grain + 1, map_rect.right - step - grain - 1))
    hy = int(clamp(hy, map_rect.y + step + grain + 1, map_rect.bottom - step - grain - 1))
    jag = max(6, int(round(16 * unit)))
    _draw_horde(surface, map_rect, hx, grain, max(4, int(round(6 * unit))), jag)

    draw_roads(surface, positions, ROAD_EDGES, main_width=max(4, int(round(22 * unit))),
               other_width=max(3, int(round(14 * unit))), center_width=line)

    symbols = radius < 12            # small map: X / ! inside the circle instead of OVERRUN / RISKY text
    label_font = _label_font(unit)
    labels = _static_labels(g, label_font)
    circles = [pygame.Rect(x - radius - 2, y - radius - 2, 2 * radius + 4, 2 * radius + 4) for x, y in positions]
    taken = [lab for lab in labels if lab is not None]   # rectangles later text must keep clear of
    dangers = set()

    for i, node in enumerate(NODES):
        x, y = positions[i]
        selected = i == game.selected
        danger = game.travel_danger(i)
        if danger:
            dangers.add(danger)
        visited = _visited(game, i)
        # danger (red / orange) beats visited (green); a selected stop is blue unless danger colours it
        color = GREEN if visited and not selected and danger not in ("overrun", "risky") else danger_color(danger, selected)
        # A stop that is not one road away looks disabled (it can still be clicked to look at it, not to drive there).
        disabled = i != game.position and not game.can_travel_to(i)
        outline, tag_color = WHITE, WHITE
        if disabled:
            tint = _DISABLED_TINTS.get(danger) or (_DISABLED_TINTS["visited"] if visited else None)
            color, outline = tint if tint else (DISABLED_BG, DISABLED_TEXT)
            tag_color = outline
        pygame.draw.circle(surface, color, (x, y), radius)
        pygame.draw.circle(surface, outline, (x, y), radius, line)
        if selected and (danger or disabled or ACCESS["colorblind"] or ACCESS["high_contrast"]):
            # keep the selection visible: a ring, so it does not depend on the circle's colour alone
            pygame.draw.circle(surface, WHITE if ACCESS["high_contrast"] else BLUE, (x, y),
                               radius + max(3, int(round(4 * unit))), 2)
        tag = ("X" if danger == "overrun" else "!") if (symbols and danger) else node["tag"]
        tag_font = pick_font((FONT, SMALL, TINY), [tag], 2 * radius - 6, 2 * radius - 4)
        image = text_surface(tag, tag_font, tag_color)
        surface.blit(image, image.get_rect(center=(x, y)))

        label = labels[i]
        if label is not None:
            if label.right >= hx - jag:   # over the horde: a dark box keeps the name readable
                _backing(surface, label.inflate(4, 2))
            surface.blit(text_surface(node["label"], label_font, MUTED if disabled else WHITE), label.topleft)
            if danger and not symbols:
                word = "OVERRUN" if danger == "overrun" else "RISKY"
                tag_img = text_surface(word, TINY, RED if danger == "overrun" else ORANGE)
                tw, th = tag_img.get_size()
                spot = pygame.Rect(int(clamp(label.centerx - tw // 2, map_rect.x + 2, map_rect.right - tw - 2)),
                                   label.bottom, tw, th)
                if (map_rect.contains(spot) and not any(spot.colliderect(c) for j, c in enumerate(circles) if j != i)
                        and not any(spot.colliderect(t) for t in taken if t is not label)):
                    _backing(surface, spot.inflate(6, 2), 185)   # dark box so the word reads on any terrain
                    surface.blit(tag_img, spot.topleft)
                    taken.append(spot)

    # Where the convoy is: a ring and a label (the label only when there is a clear spot for it).
    px, py = positions[game.position]
    ring_r = radius + ring
    pygame.draw.circle(surface, YELLOW, (px, py), ring_r, max(2, int(round(3 * unit))))
    ring_box = pygame.Rect(px - ring_r - 2, py - ring_r - 2, 2 * ring_r + 4, 2 * ring_r + 4)
    here_font = TINY if unit < 1.3 else SMALL

    # The horde's front (hx, hy) was worked out above; this box keeps the text clear of it.
    group = pygame.Rect(hx - step - grain - 1, hy - step // 2 - grain - 1, 2 * (step + grain) + 2, step + 2 * grain + 2)

    keep_clear = circles + [ring_box, group] + taken
    placed = _place_text([text_surface("CONVOY", here_font, YELLOW)], (px, py), ring_r + 2, map_rect, keep_clear)
    if placed:
        surface.blit(placed[0], placed[1].topleft)
        keep_clear.append(placed[1])
    state_color = HORDE_STATE_COLORS[state]
    placed = _place_text([text_surface(f"HORDE: {state.upper()}", here_font, state_color),
                          text_surface("HORDE", here_font, state_color)],
                         (hx, hy), max(group.w, group.h) // 2 + 1, map_rect, keep_clear)
    if placed:
        _backing(surface, placed[1].inflate(4, 2))
        surface.blit(placed[0], placed[1].topleft)

    if symbols and dangers:
        legend = "  ".join(text for key, text in (("overrun", "X overrun"), ("risky", "! risky")) if key in dangers)
        image = text_surface(legend, TINY, RED if "overrun" in dangers else ORANGE)
        legend_spot = image.get_rect(bottomright=(map_rect.right - 4, map_rect.bottom - 3))
        _backing(surface, legend_spot.inflate(6, 2), 185)
        surface.blit(image, legend_spot.topleft)
    surface.set_clip(old_clip)


def draw_map_info(surface, game, g):
    """The info panel under the map: the selected stop, trip costs, route, a danger line and what the stop holds,
    with fuel and the horde gap in a column on the right. Lower priority lines are dropped when space is tight."""
    info = pygame.Rect(g["info"])
    dest = NODES[game.selected]
    trip = game.plan_trip()
    danger = game.travel_danger()
    state = game.horde_state()
    draw_panel(surface, info, PANEL, 1)
    draw_frame(surface, info, RED if danger == "overrun" else (ORANGE if danger == "risky" else BLUE), 1 * PIX)

    lx, ly, lw, lh = g["info_left"]
    big = info.h >= 130
    # The fonts follow the text-size setting (scaled_font / screen_fonts). Rows name their font ("heading", "main" or
    # "minor"); the largest set in which every row fits the panel's height is chosen below, so a larger text size
    # shrinks the text back rather than dropping rows.
    size = surface.get_size()
    medium, body, small, tiny = screen_fonts(size)
    sets = ([(medium, small)] if big else []) + [(small, tiny), (tiny, tiny)]
    heading_fonts = (scaled_font(size, 23), body) if big else (body, small)
    heading = f"SELECTED: {dest['name']}"

    rows = [((heading,), WHITE, "heading")]
    banners = {}   # row index -> banner colour: NOT ENOUGH FUEL (red) and the supplies warning (orange) stand out
    if trip["km"] == 0:
        rows.append((("The convoy is already here.",), YELLOW, "main"))
    else:
        direction = "WEST" if trip["delta"] > 0 else ("EAST (backwards)" if trip["delta"] < 0 else "DETOUR")
        rows.append(((f"Fuel required: {trip['fuel']}  |  {trip['km']} km {direction}  |  {trip['days']} day(s)",
                      f"Fuel {trip['fuel']} | {trip['km']} km {direction} | {trip['days']} day(s)",
                      f"{trip['km']} km {direction}, {trip['days']} day(s)"), YELLOW, "main"))
        reachable = game.selected == game.position or game.can_travel_to(game.selected)
        if reachable and game.fuel < trip["fuel"]:   # the same test that disables TRAVEL
            banners[len(rows)] = RED
            rows.append(((f"NOT ENOUGH FUEL: need {trip['fuel']}, have {game.fuel}",
                          f"NOT ENOUGH FUEL ({game.fuel}/{trip['fuel']})", "NOT ENOUGH FUEL", "NO FUEL"),
                         WHITE, "main"))
        warning = game.supply_warning()
        if warning:   # the food / water will not last the trip: survivors leave (and vehicles can be lost with them)
            lost = f", up to {warning['vehicles']} vehicle(s) lost" if warning["vehicles"] else ""
            banners[len(rows)] = ORANGE
            rows.append(((f"WARNING: not enough {warning['short']} for this trip: up to {warning['leave']} survivor(s) leave{lost}",
                          f"LOW {warning['short'].upper()}: up to {warning['leave']} survivor(s) leave{lost}",
                          f"LOW {warning['short'].upper()}: survivors leave", "LOW SUPPLIES"),
                         DARK, "main"))
        not_connected = game.selected != game.position and not game.can_travel_to(game.selected)
        statuses = []   # (text variants, colour); a stop can be not connected and overrun / risky at once
        if not_connected:
            statuses.append((("NOT CONNECTED: you can only drive to a stop one road away (the bright ones on the map).",
                              "NOT CONNECTED: pick a bright stop one road away.", "Not connected."), ORANGE))
        if danger == "overrun":
            statuses.append((("OVERRUN: going back east would drive the convoy into the horde.",
                              "OVERRUN: east leads into the horde.", "OVERRUN: into the horde."), RED))
        elif danger == "risky":
            statuses.append((("RISKY: the horde may catch the convoy on this trip and attack.",
                              "RISKY: the horde may catch the convoy.", "RISKY: possible attack."), ORANGE))
        elif not_connected:
            pass
        elif trip["delta"] > 0:
            statuses.append(((f"Horde gap grows by {trip['delta']} km (before time passes).",
                              f"Horde gap +{trip['delta']} km (before time passes).", f"Gap +{trip['delta']} km."), GREEN))
        elif trip["delta"] < 0:
            statuses.append(((f"Horde gap shrinks by {-trip['delta']} km (before time passes).",
                              f"Horde gap -{-trip['delta']} km (before time passes).", f"Gap -{-trip['delta']} km."), RED))
        else:
            statuses.append((("Detour: the gap doesn't change, but time passes and the horde closes in.",
                              "Detour: gap unchanged, but the horde closes in.", "Detour: gap unchanged."), ORANGE))
        for variants, color in statuses:
            rows.append((variants, color, "minor"))
        if trip.get("wear") and not not_connected:   # the road itself hurts, whatever happens on the way (travel.route_wear)
            rows.append(((f"ROUGH ROAD: every vehicle loses about {trip['wear']}% health on arrival.",
                          f"ROUGH ROAD: -{trip['wear']}% health on arrival.", f"Rough road: -{trip['wear']}% health."),
                         ORANGE, "minor"))
        route = "direct road" if not trip["through"] else "via " + ", ".join(trip["through"])
        rows.append(((f"Route: {route} ({trip['km']} km)", f"Route: {route}", route), MUTED, "minor"))

    # Size the fonts for the worst case a stop can show (fuel line + NOT ENOUGH FUEL + supply warning, and up to three
    # minor rows), not for this stop's rows, so the text size is the same for every stop. Rows that still do not fit
    # are dropped by the drawing loop below.
    worst_case = ("heading", "main", "main", "main", "minor", "minor", "minor")
    for main_font, minor_font in sets:
        fonts = {"heading": pick_font(heading_fonts, [heading], lw), "main": main_font, "minor": minor_font}
        if sum(fonts[key].get_linesize() + 2 for key in worst_case) <= lh:
            break

    y = ly
    dropped = False   # a row that did not fit: then the stop's description has no room either
    for index, (variants, color, key) in enumerate(rows):
        font = fonts[key]
        step = font.get_linesize() + 2
        if y + step > ly + lh:
            dropped = True
            break
        if index in banners:
            draw_panel(surface, (lx - 4, y, lw + 8, step), banners[index], 1)
        text_in_rect(surface, fit_variants(font, lw, variants), (lx, y, lw, step), color, font)
        y += step

    sites = dest.get("sites", [])
    if dest["kind"] == "coast":
        detail = "Final destination: reach the coast to escape by ship."
    elif len(sites) == 1:
        detail = SITES[sites[0]]["detail"]
    elif sites:
        detail = "Sites: " + ", ".join(SITES[site]["name"] for site in sites) + ". Scavenge one at a time."
    else:
        detail = "Explore this location."
    step = minor_font.get_linesize() + 2
    room = (ly + lh - y) // step                       # the stop's description is the first thing to go
    if room >= 1 and not dropped:
        lines = wrap_pixels(detail, minor_font, lw)
        if len(lines) > room:
            lines = lines[:room]
            lines[-1] = ellipsize(lines[-1], minor_font, lw)
        for line in lines:
            text_in_rect(surface, line, (lx, y, lw, step), MUTED, minor_font)
            y += step

    rx, ry, rw, rh = g["info_right"]
    short_of_fuel = trip["km"] > 0 and game.fuel < trip["fuel"]
    need = f" (need {trip['fuel']})" if short_of_fuel else ""
    right_rows = [
        ((f"Fuel available: {game.fuel}{need}", f"Fuel: {game.fuel}{need}", f"Fuel: {game.fuel}"),
         RED if short_of_fuel else WHITE),
        ((f"Horde gap: {game.horde} km ({state})", f"Gap: {game.horde} km ({state})", f"Gap: {game.horde} km"),
         HORDE_STATE_COLORS[state]),
    ]
    y = ry
    step = main_font.get_linesize() + 2
    for variants, color in right_rows:
        if y + step > ry + rh:
            break
        text_in_rect(surface, fit_variants(main_font, rw, variants), (rx, y, rw, step), color, main_font)
        y += step
