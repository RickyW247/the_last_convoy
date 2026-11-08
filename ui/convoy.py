"""The convoy screen of THE LAST CONVOY: scene art (background, zombies, vehicles), event log and the lower
panel with the info panel (the HUD is in hud.py). The scene art is also used by the title screen. Drawing only."""
import math
import os
import zlib
from functools import lru_cache

import pygame

from widgets import PIX, draw_frame, draw_panel

from .common import draw_paragraph, scaled_image
from .hud import draw_hud   # noqa: F401  (the HUD moved to hud.py; still importable from here)
from layout import (
    calculate_layout, fit_ratio, SCENE_BAR_Y, SCENE_BASELINE, SCENE_LABEL_Y, SCENE_REF_H, ZOMBIE_SLOTS,
    ZOMBIE_Y_MAX, ZOMBIE_Y_MIN,
)
from map_data import SITES
from .map_system import draw_minimap
from .pixel_art import ART_BLOCK, COARSE, choose_vehicle_scale, pixelate
from theme import ACCESS, FONT, GREEN, MUTED, PANEL, RED, SMALL, TINY, WHITE, YELLOW
from .vehicle_rendering import get_rig_sprite, get_vehicle_sprite, reference_sprite_height, rig_dust_points
from upgrade_data import TRAILER_DUST, UPGRADE_LOOKS
from vehicle_data import DEFAULT_DUST_POINTS, VEHICLE_DUST_POINTS, VEHICLE_LOOKS
from textscale import text_scale, tpx
from widgets import draw_bar, draw_text, fit_text, scaled_font, text_ladder, text_surface


BACKGROUND_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "backgrounds", "convoy_background.png"
)


_BACKGROUND_IMAGES = {}   # scenery name -> its low-resolution picture (see BACKGROUNDS)

# Where the road's top edge is in convoy_background.png, as a fraction of its height (measured on the picture). The vehicles
# and zombies are placed relative to the scene, so the background is cropped to keep the road at this height.
BACKGROUND_ROAD_Y = 0.76


# The sceneries the convoy can drive through (map_data.scenery_for picks one per stop, Game.scenery() tells the screen).
#   "path":   the PNG in assets/backgrounds.
#   "block":  the art-pixel size the picture is shrunk to (pixel_art.pixelate); re-measure if the art is redrawn.
#   "loop":   "wrap" or "mirror" (see BACKGROUND_LOOP below).
#   "road_y": where the road's top edge is, as a fraction of the picture's height.
# convoy_background_desert.png is 2172 x 724 and its left and right edges do not match, so it loops as a mirror.
DESERT_ART_BLOCK = 4
BACKGROUNDS = {
    "highway": {"path": BACKGROUND_PATH, "block": ART_BLOCK["background"], "loop": "wrap",
                "road_y": BACKGROUND_ROAD_Y},
    "desert": {"path": os.path.join(os.path.dirname(BACKGROUND_PATH), "convoy_background_desert.png"),
               "block": ART_BLOCK.get("background_desert", DESERT_ART_BLOCK), "loop": "wrap", "road_y": 0.76},
}
DEFAULT_SCENERY = "highway"


def _scenery_info(scenery):
    return BACKGROUNDS.get(scenery) or BACKGROUNDS[DEFAULT_SCENERY]


def game_scenery(game):
    """The scenery name for `game` (the title screen's game too); a game without scenery() shows the highway."""
    pick = getattr(game, "scenery", None)
    return pick() if callable(pick) else DEFAULT_SCENERY


def get_background_image(scenery=DEFAULT_SCENERY):
    """Load a scenery's background once and shrink it to its true low resolution (pixel_art.pixelate); it is drawn at a
    whole-number scale (draw_scene_background)."""
    info = _scenery_info(scenery)
    image = _BACKGROUND_IMAGES.get(info["path"])
    if image is None:
        image = pixelate(pygame.image.load(info["path"]).convert(), info["block"])
        _BACKGROUND_IMAGES[info["path"]] = image
    return image


# The background scrolls to the right, so the convoy (which faces west) looks like it is driving.
BACKGROUND_SCROLL_SPEED = 5.0   # art pixels per second; 0 switches the scrolling off. It moves in whole art pixels.
# How the picture repeats: "mirror" follows it with its own mirror image, so there is never a visible seam but the
# scenery repeats reversed; "wrap" repeats it as it is, which only looks right if the left and right edges of
# convoy_background.png match.
BACKGROUND_LOOP = "wrap"
# 1.0 = the least zoom that still covers the scene; raise it (1.1, 1.25 ...) to zoom IN, never below 1.0.
BACKGROUND_ZOOM = 1.0

SCENE_ASPECT = (10, 3)   # width : height of the convoy scene before it is widened (scene_rect)

_LOOP_STRIPS = {}   # picture path -> its loop strip


def _get_loop_strip(scenery=DEFAULT_SCENERY):
    """A scenery's low-resolution background, followed by its mirror image when its "loop" is "mirror"."""
    info = _scenery_info(scenery)
    strip = _LOOP_STRIPS.get(info["path"])
    if strip is None:
        low = get_background_image(scenery)
        if info["loop"] == "mirror":
            strip = pygame.Surface((low.get_width() * 2, low.get_height()))
            strip.blit(low, (0, 0))
            strip.blit(pygame.transform.flip(low, True, False), (low.get_width(), 0))
        else:
            strip = low
        _LOOP_STRIPS[info["path"]] = strip
    return strip


# The animation clock. The road animation (background scroll, vehicle bounce, dust) runs on this instead of
# pygame.time.get_ticks(), so main.py can stop it (pause menu, window out of focus) and it carries on from the same
# picture instead of jumping ahead by the time that passed.
_ANIM = {"stopped_at": None, "lost": 0, "speed": 1, "since": 0, "gained": 0}
# "speed": how many times faster the clock runs (SPACE held while travelling). "since": the real time of the last speed
# change, and "gained": the extra milliseconds the faster running has added so far, so a change never makes time jump.


def animation_time():
    """Milliseconds of animation time: like pygame.time.get_ticks(), but it stands still while paused and runs
    `speed` times faster while the road animation is sped up (set_animation_speed)."""
    now = pygame.time.get_ticks() if _ANIM["stopped_at"] is None else _ANIM["stopped_at"]
    return now - _ANIM["lost"] + _ANIM["gained"] + (now - _ANIM["since"]) * (_ANIM["speed"] - 1)


def set_animation_paused(paused):
    """Stop (True) or continue (False) the animation clock; calling it every frame with the same value is fine."""
    now = pygame.time.get_ticks()
    if paused and _ANIM["stopped_at"] is None:
        _ANIM["stopped_at"] = now
    elif not paused and _ANIM["stopped_at"] is not None:
        gap = now - _ANIM["stopped_at"]
        _ANIM["lost"] += gap
        _ANIM["since"] += gap   # the pause is not part of the speed-up either
        _ANIM["stopped_at"] = None


def set_animation_speed(speed):
    """Run the animation clock `speed` times faster (1 = normal): the background scroll, the vehicle bounce, the dust
    and the zombies. Calling it every frame with the same value is fine; time never jumps when the speed changes."""
    if speed == _ANIM["speed"]:
        return
    now = pygame.time.get_ticks() if _ANIM["stopped_at"] is None else _ANIM["stopped_at"]
    _ANIM["gained"] += (now - _ANIM["since"]) * (_ANIM["speed"] - 1)
    _ANIM["since"] = now
    _ANIM["speed"] = speed


def _background_view(scene, scroll=True, scenery=DEFAULT_SCENERY):
    """(enlarged loop strip, left edge of the window on it, scale) for `scene`: where the window looks onto the
    looping background right now. The background and the zombies both use this, so a zombie fixed to a spot of the strip
    moves exactly as the scenery does. The window slides left along the strip as the picture moves right; positions on
    the strip repeat every big.get_width() pixels."""
    low = get_background_image(scenery)
    strip = _get_loop_strip(scenery)
    # The scale follows the scene HEIGHT only (like the vehicles and zombies): the width counted is at most the 10:3 width
    # of that height. A widened scene (scene_rect) shows more of the looping strip instead of zooming the picture in.
    cover_w = min(scene.w, scene.h * SCENE_ASPECT[0] / SCENE_ASPECT[1])
    scale = max(cover_w / low.get_width(), scene.h / low.get_height()) * BACKGROUND_ZOOM
    size = (math.ceil(strip.get_width() * scale), math.ceil(strip.get_height() * scale))
    big = scaled_image(("background-loop", _scenery_info(scenery)["path"]), strip, size)
    if scroll and BACKGROUND_SCROLL_SPEED:
        shift = round(int(animation_time() / 1000 * BACKGROUND_SCROLL_SPEED) * scale)   # whole art pixels
    else:
        shift = 0
    left = ((big.get_width() - scene.w) // 2 - shift) % big.get_width()
    return big, left, scale


def draw_scene_background(surface, scene, scroll=True, scenery=DEFAULT_SCENERY):
    """The background filling `scene`: the low-resolution picture enlarged by the SMALLEST factor that still covers the
    scene (BACKGROUND_ZOOM = 1.0), cropped to the scene (the crop keeps the road at the same height). The factor is no
    longer rounded up to a whole number (that rounding could zoom in by almost 2x, making the cars in the picture bigger
    than the player's vehicles); the picture is resized with nearest-neighbour, so its pixels stay sharp but may differ
    by one screen pixel in size. It slides sideways and wraps around (see BACKGROUND_LOOP); with scroll=False, or a speed
    of 0, it stands still, centred."""
    big, left, _scale = _background_view(scene, scroll, scenery)
    top = round(_scenery_info(scenery)["road_y"] * (big.get_height() - scene.h))
    done = 0
    while done < scene.w:   # one or two pieces: the window may run past the end of the strip and continue at its start
        piece = min(scene.w - done, big.get_width() - left)
        surface.blit(big, (scene.x + done, scene.y), pygame.Rect(left, top, piece, scene.h))
        done += piece
        left = 0


# Road animation. Everything is a function of the clock (no stored state) and moves in whole art pixels.
BOUNCE_STEPS = (0, 1, 1, 0, 0, 0)   # the body's lift in art pixels, one entry per BOUNCE_MS: a small bump of the suspension
BOUNCE_MS = 110
DUST_PUFFS = 14       # puff slots behind each wheel; at any moment about (1 - DUST_GAP) of them are in the air
DUST_LIFE_MS = 1000   # average life of one puff; each puff lives 0.5x to 1.5x of this, and each vehicle has its own rhythm
DUST_GAP = 0.2        # share of the puffs that are skipped in a given round, so the dust comes in uneven bursts
DUST_COLORS = ((196, 177, 142), (176, 158, 126), (150, 134, 108))   # light, medium and dark dust, picked per puff
DUST_ALPHA = 200      # opacity of a fresh puff (0-255, varies a little per puff); it fades out as the puff ages
DUST_MAX_SIDE = 3     # the biggest a puff gets, in art pixels (most stay 1 or 2: fine dust)
VEHICLE_SCENE_H = 80  # height of the tallest vehicle type on the 270 px reference scene (a zombie is about 42 there)
# A text size above Normal makes the HUD and the panels below taller, so the scene gets shorter and the vehicles, sized
# from the scene height, shrank with it. With such a setting the tallest vehicle is never smaller than this share of the
# scene height (or its normal VEHICLE_SCENE_H pixels, if that is less): the vehicles keep about their normal size while
# the background and zombies follow the scene.
VEHICLE_MIN_SHARE = 0.38


def vehicle_bounce(now, number):
    """The lift of vehicle `number` in art pixels at time `now` (ms); each vehicle bounces out of step with the others."""
    return BOUNCE_STEPS[(now // BOUNCE_MS + number * 2) % len(BOUNCE_STEPS)]


def _rand(*keys):
    """A repeatable pseudo-random number in [0, 1) from integer keys (no state: the dust is a function of the clock)."""
    h = 2166136261
    for key in keys:
        h = ((h ^ (key & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 3266489917) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


@lru_cache(maxsize=256)
def _puff_surface(side, color, alpha):
    puff = pygame.Surface((side, side), pygame.SRCALPHA)
    puff.fill((*color, alpha))
    return puff


def draw_dust(surface, now, number, left, baseline, size, pix, vehicle_type, fractions=None):
    """Dust kicked up behind the wheels of a left-facing vehicle: fine square puffs start on the road right behind each
    wheel (VEHICLE_DUST_POINTS), then drift back (right), rise, grow a little and fade.

    Every puff has its own life, start, drift speed, height, size, shade and opacity, drawn afresh each time it is kicked
    up, and each vehicle has its own rhythm, so neither the puffs nor the vehicles look alike. `left` is the sprite's left
    edge, `baseline` the road y its wheels rest on, `size` the sprite's size. `fractions` overrides the wheel points (a
    vehicle with a trailer has the trailer's wheels too, see _dust_fractions)."""
    width, height = size
    fractions = fractions or (VEHICLE_DUST_POINTS.get(vehicle_type) or UPGRADE_LOOKS.get(vehicle_type, {}).get("dust")
                              or DEFAULT_DUST_POINTS)   # `vehicle_type` is the sprite's name: an upgraded vehicle has its own wheels
    reach = max(6 * pix, int(height * 0.8))   # how far back the dust travels
    seed = zlib.crc32(vehicle_type.encode()) ^ (number * 7919)
    rate = 0.8 + 0.5 * _rand(seed, 0)         # this vehicle's rhythm: its dust lives shorter or longer than average
    for wheel, fraction in enumerate(fractions):
        origin = left + int(width * fraction)
        for i in range(DUST_PUFFS):
            slot = (seed, wheel, i)
            life = DUST_LIFE_MS * rate * (0.5 + _rand(*slot, 1))
            t = now + _rand(*slot, 2) * life   # each puff starts at its own point of its cycle
            cycle = int(t // life)
            age = (t % life) / life            # 0 = just kicked up, 1 = gone

            def r(k):
                return _rand(*slot, cycle, k)  # new randomness for every round of this puff

            if r(3) < DUST_GAP:
                continue
            alpha = int(DUST_ALPHA * (1 - age) * (0.55 + 0.45 * r(9))) // 16 * 16
            if alpha <= 0:
                continue
            max_side = 1 + int(r(4) * DUST_MAX_SIDE)
            side = min(max_side, 1 + int(age * max_side * 1.5)) * pix
            drift = int(age * reach * (0.4 + 0.9 * r(5))) // pix * pix
            lift = int(age ** 0.6 * (1 + 5 * r(7))) + int(r(8) * 2)   # whole art pixels
            px = origin + (int(r(6) * 5) - 2) * pix - side // 2 + drift
            py = baseline - side - lift * pix
            surface.blit(_puff_surface(side, DUST_COLORS[int(r(10) * len(DUST_COLORS))], alpha), (px, py))


def _dust_fractions(vehicle, coarse):
    """The wheel dust points of a vehicle that tows a trailer (its own wheels and the trailer's, as fractions of the rig's
    width), or None for a vehicle without one (draw_dust then looks the points up by the sprite name)."""
    if not vehicle.trailer:
        return None
    look = vehicle.sprite_type
    own = VEHICLE_DUST_POINTS.get(look) or UPGRADE_LOOKS.get(look, {}).get("dust") or DEFAULT_DUST_POINTS
    return rig_dust_points(look, vehicle.trailer, own, TRAILER_DUST[vehicle.trailer], coarse)


def _convoy_sprites(vehicles, scene):
    """(scaled sprites, sprite index, scale, gap, unit) for the convoy in `scene`.

    One size for every vehicle, whatever the convoy holds: the picture is scaled with the scene (like the zombies and the
    background), never with the number of vehicles, so a vehicle keeps the same size next to the road and the zombies.
    The size is set by the TALLEST vehicle type, about VEHICLE_SCENE_H reference pixels, so each type keeps its true size
    relative to the others. The sprites are low-resolution pixel art drawn at a whole-number scale; the coarse version
    (2 x 2 art pixels merged) is used when it comes closer to that height (pixel_art.choose_vehicle_scale)."""
    unit = scene.h / SCENE_REF_H   # 1.0 on the 270 px tall title scene: the sprites grow and shrink with the scene
    gap = max(2, int(4 * unit))
    # Measured at size factor 1.0: vehicles enlarged by vehicles.VEHICLE_SCENE_SIZE must not change the scale of the others.
    tallest = [max(reference_sprite_height(t, coarse=c) for t in VEHICLE_LOOKS) for c in (False, True)]
    target = VEHICLE_SCENE_H * unit
    if text_scale() > 1.0:
        target = max(target, min(VEHICLE_SCENE_H, VEHICLE_MIN_SHARE * scene.h))
    index, scale = choose_vehicle_scale(tallest, target)
    scaled = []
    for vehicle in vehicles:
        look = vehicle.sprite_type   # an upgrade can change the picture (the Semi-Truck's trailer)
        s = get_rig_sprite(look, vehicle.trailer, coarse=bool(index))   # the vehicle plus the trailer it tows, if any
        size = (max(1, int(s.get_width() * scale)), max(1, int(s.get_height() * scale)))
        scaled.append(scaled_image(("vehicle", look, vehicle.trailer, index), s, size))
    return scaled, index, scale, gap, unit


def _arrow_margin(scene):
    """Width of the strip at each side of the scene that holds a scroll arrow (only used when the convoy scrolls)."""
    return max(24, int(scene.w * 0.05))


def scroll_arrow_rects(scene):
    """(left, right) rectangles of the convoy scroll arrows, at the sides of the scene, level with the vehicles."""
    scene = pygame.Rect(scene)
    unit = scene.h / SCENE_REF_H
    margin = _arrow_margin(scene)
    w, h = margin - 6, max(24, int(44 * unit))
    cy = scene.y + int(SCENE_BASELINE * scene.h) - int(VEHICLE_SCENE_H * unit / 2)
    top = max(scene.y, min(cy - h // 2, scene.bottom - h))
    return (scene.x + 3, top, w, h), (scene.right - 3 - w, top, w, h)


SCROLL_PAGE = 0.6   # of the scene's width: how far one arrow click slides the convoy (less than 1, so the views overlap)
SCROLL_EASE_MS = 90   # smoothing time of the convoy slide: the view closes about 63% of the remaining distance per this time
_VIEW = {"x": None, "t": 0}   # the animated scroll offset in pixels (None = not scrolling / not started)


def _scroll_plan(widths, view, gap, scene):
    """(scrolling, x0, offsets, view, max_view) for a convoy of sprites with these widths.

    offsets[i] is where vehicle i starts, relative to x0, in a line with no scrolling. When the whole convoy fits it is
    centred and nothing scrolls. Otherwise x0 is just inside the left edge and the line slides left by `view`, a distance
    in PIXELS clamped to 0..max_view (the arrow buttons are disabled at both ends and the vehicles run under them).

    The view is a pixel distance, not "which vehicle is at the left edge": every click then moves the same distance
    however long the vehicles are (a car carrier or crane truck used to make a click move almost nothing or skip several
    vehicles, because the view was snapped to vehicle boundaries and pushed on to keep the next vehicle peeking out)."""
    count = len(widths)
    offsets, pos = [], 0
    for w in widths:
        offsets.append(pos)
        pos += w + gap
    total = pos - gap
    if total <= scene.w * 0.94:
        return False, scene.x + (scene.w - total) // 2, offsets, 0, 0
    pad = int(scene.w * 0.03)
    x0 = scene.x + pad
    max_view = max(0, total - (scene.w - 2 * pad))
    return True, x0, offsets, max(0, min(int(view), max_view)), max_view


def convoy_scroll_state(game, scene):
    """(scrolling, can_scroll_left, can_scroll_right) for the convoy in `scene` (the rectangle draw_scene draws in).
    buttons.py uses it to add the arrow buttons only when some vehicles do not fit."""
    vehicles = game.vehicles
    scene = pygame.Rect(scene)
    if not vehicles:
        return False, False, False
    scaled, _, _, gap, _ = _convoy_sprites(vehicles, scene)
    scrolling, _, _, view, last = _scroll_plan([s.get_width() for s in scaled], getattr(game, "convoy_scroll", 0),
                                               gap, scene)
    return scrolling, view > 0, view < last


def scroll_convoy(game, step, scene):
    """Slide the convoy one page (SCROLL_PAGE of the scene's width) left (-1) or right (+1), kept inside the convoy; the
    shown view eases there (draw_convoy_vehicles)."""
    scene = pygame.Rect(scene)
    scaled, _, _, gap, _ = _convoy_sprites(game.vehicles, scene)
    _, _, _, view, last = _scroll_plan([s.get_width() for s in scaled], getattr(game, "convoy_scroll", 0), gap, scene)
    game.convoy_scroll = max(0, min(last, view + int(step * SCROLL_PAGE * scene.w)))


LABEL_PLATE = (12, 14, 20, 200)   # the dark backing of a name label: the road and its white lane markings are behind it


@lru_cache(maxsize=64)
def _label_plate(width, height):
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill(LABEL_PLATE)
    return plate


@lru_cache(maxsize=256)
def _outlined_text(text, font=TINY):
    """White text with a 1 px dark outline (cached per string and font), so it stays readable on any part of the background."""
    face, edge = text_surface(text, font, WHITE), text_surface(text, font, (0, 0, 0))
    out = pygame.Surface((face.get_width() + 2, face.get_height() + 2), pygame.SRCALPHA)
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (2, 0), (0, 2), (2, 2)):
        out.blit(edge, (dx, dy))
    out.blit(face, (1, 1))
    return out


def draw_scene_label(surface, text, font=TINY, **place):
    """Text on the convoy scene (a vehicle's name, the count of vehicles out of view, the captions at the top) on a dark,
    semi-transparent plate with outlined text, so the road markings, the clouds and the grass behind it never make it
    hard to read. `place` is a pygame Rect anchor, e.g. midtop=(x, y) or topleft=(x, y). Returns the text's rect."""
    label = _outlined_text(text, font)
    rect = label.get_rect(**place)
    plate = rect.inflate(6, 0)
    surface.blit(_label_plate(plate.w, plate.h), plate)
    surface.blit(label, rect)
    return rect


def draw_convoy_vehicles(surface, game, scene, labels=True):
    """Draw the owned vehicles in a left-facing line, sized and placed relative to the scene rectangle. A convoy too long
    for the scene slides sideways (eased) when the arrow buttons change game.convoy_scroll; vehicles run under the arrows."""
    vehicles = game.vehicles
    if not vehicles:
        return
    scene = pygame.Rect(scene)
    scaled, index, scale, gap, unit = _convoy_sprites(vehicles, scene)
    scrolling, x0, offsets, target, _ = _scroll_plan(
        [s.get_width() for s in scaled], getattr(game, "convoy_scroll", 0), gap, scene)

    now = animation_time()
    if scrolling:   # ease the view offset towards the target instead of jumping
        if _VIEW["x"] is None:
            _VIEW["x"] = target
        else:
            dt = max(0, min(100, now - _VIEW["t"]))
            _VIEW["x"] += (target - _VIEW["x"]) * (1 - math.exp(-dt / SCROLL_EASE_MS))
            if abs(target - _VIEW["x"]) < 0.5:
                _VIEW["x"] = target
        view = round(_VIEW["x"])
    else:
        _VIEW["x"] = None
        view = 0
    _VIEW["t"] = now

    # Rows inside the scene: wheels on the road, then the name label, then the health bar. In a very short
    # scene the rows are pulled up so that the label and bar never leave the scene.
    bar_h = max(3, int(5 * unit))
    bar_y = min(scene.y + int(SCENE_BAR_Y * scene.h), scene.bottom - bar_h - 2)
    label_y = min(scene.y + int(SCENE_LABEL_Y * scene.h), bar_y - TINY.get_linesize() - 1)
    baseline = min(scene.y + int(SCENE_BASELINE * scene.h), label_y - 2)   # y where vehicle bodies rest

    pix = max(1, round(scale / (COARSE if index else 1)))   # one art pixel on screen: the unit of the bounce and the dust
    old_clip = surface.get_clip()
    surface.set_clip(scene.clip(old_clip))   # everything of the convoy is cut off at the scene's edges
    left_out = right_out = 0
    for number, (vehicle, spr) in enumerate(zip(vehicles, scaled)):
        x = x0 + offsets[number] - view
        if x + spr.get_width() <= scene.x:
            left_out += 1
            continue
        if x >= scene.right:
            right_out += 1
            continue
        look = UPGRADE_LOOKS.get(vehicle.sprite_type) or VEHICLE_LOOKS[vehicle.vehicle_type]
        # PNG sprites carry their own size, so rest the bottom edge of the image on the road baseline.
        y = baseline - spr.get_height()
        draw_dust(surface, now, number, x, baseline, spr.get_size(), pix, vehicle.sprite_type,
                  _dust_fractions(vehicle, bool(index)))
        surface.blit(spr, (x, y - vehicle_bounce(now, number) * pix))   # only the picture bounces, not its label or bar
        if not labels:   # the title screen shows the bare convoy
            continue
        cx = x + spr.get_width() // 2
        health_pct = vehicle.health / max(1, vehicle.stats["health"])
        text = look["label"]
        if ACCESS["colorblind"]:   # the bar colour is not the only signal: say the health in words too
            percent = f"{round(health_pct * 100)}%"
            room = spr.get_width() + gap
            text = next((t for t in (f"{text} {percent}", percent) if TINY.size(t)[0] <= room), percent)
        draw_scene_label(surface, text, midtop=(cx, label_y))
        bar_color = GREEN if health_pct >= 0.6 else (YELLOW if health_pct >= 0.3 else RED)
        bar_w = max(10, min(spr.get_width() - 10, 70))
        draw_bar(surface, cx - bar_w // 2, bar_y, bar_w, bar_h, vehicle.health, vehicle.stats["health"], bar_color)
    surface.set_clip(old_clip)
    if scrolling and labels:   # say how many vehicles are completely out of view at each side (the arrows are the buttons)
        row = label_y + TINY.get_linesize() // 2
        if left_out:
            more = _outlined_text(f"{left_out}+")
            rect = more.get_rect(midleft=(scene.x + 6, row))
            surface.blit(_label_plate(rect.w + 6, rect.h), rect.inflate(6, 0).topleft)
            surface.blit(more, rect)
        if right_out:
            more = _outlined_text(f"+{right_out}")
            rect = more.get_rect(midright=(scene.right - 6, row))
            surface.blit(_label_plate(rect.w + 6, rect.h), rect.inflate(6, 0).topleft)
            surface.blit(more, rect)


# Zombie sprite asset
_ZOMBIE_SPRITE = None


_ZOMBIE_SPRITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "zombies", "zombie.png"
)


def _get_zombie_sprite():
    """Load and cache the transparent zombie PNG, shrunk to its true low resolution (pixel_art.pixelate)."""
    global _ZOMBIE_SPRITE

    if _ZOMBIE_SPRITE is None:
        if not os.path.isfile(_ZOMBIE_SPRITE_PATH):
            raise FileNotFoundError(
                f"Zombie sprite not found: {_ZOMBIE_SPRITE_PATH}"
            )

        _ZOMBIE_SPRITE = pixelate(pygame.image.load(_ZOMBIE_SPRITE_PATH).convert_alpha(), ART_BLOCK["zombie"])

    return _ZOMBIE_SPRITE


def _get_zombie_source():
    """The full-resolution zombie PNG, cached (the sprite of _get_zombie_sprite is this shrunk to ART_BLOCK["zombie"])."""
    global _ZOMBIE_SOURCE
    if _ZOMBIE_SOURCE is None:
        _get_zombie_sprite()   # raises the same FileNotFoundError when the file is missing
        _ZOMBIE_SOURCE = pygame.image.load(_ZOMBIE_SPRITE_PATH).convert_alpha()
    return _ZOMBIE_SOURCE


_ZOMBIE_SOURCE = None
ZOMBIE_MIN_SCALE = 0.25   # the smallest size factor: a zombie never shrinks to a speck in a tiny window


def zombie_scale(unit):
    """The size factor of every zombie in a scene of size `unit` (scene height / SCENE_REF_H): 1.0 is the zombie's low-resolution
    size (about 43 x 42 px, as on the 270 px reference scene). It follows the scene height continuously, like the
    background does. It used to be a whole number (1x until the scene was 1.5 times the reference height, then 2x), so
    zombies did not change with the window for long stretches: too big in small windows, too small in big ones."""
    return max(ZOMBIE_MIN_SCALE, unit)


@lru_cache(maxsize=32)
def _zombie_picture(size):
    """The zombie PNG shrunk smoothly to `size` (cached: the size only changes when the window does)."""
    return pygame.transform.smoothscale(_get_zombie_source(), size)


def draw_zombie(surface, x, y, s, scale=None):
    """Draw a pixel-art zombie facing left toward the convoy. `scale` is the scene's size factor (zombie_scale, may be
    fractional); without it the factor is the zombie's own depth size `s`. The picture is the original PNG shrunk
    smoothly to that size, so any factor gives a clean picture (a whole-number scale of the 43 x 42 sprite could only
    give 1x, 2x, 3x...)."""
    sprite = _get_zombie_sprite()   # only for the reference size: the PNG shrunk to its true low resolution
    factor = max(ZOMBIE_MIN_SCALE, s if scale is None else scale)
    size = (max(1, round(sprite.get_width() * factor)), max(1, round(sprite.get_height() * factor)))
    scaled = _zombie_picture(size)

    # Anchor the zombie's feet to the ground.
    rect = scaled.get_rect(
        midbottom=(int(x - 5 * s), int(y))
    )
    surface.blit(scaled, rect)


def _zombie_spot(i):
    """Where zombie number `i` stands: (position along the looping background strip, depth), both 0..1. The R2 sequence
    spreads the zombies evenly in both directions without clumping, and adding a zombie never moves the others."""
    return (0.5 + i * 0.7548776662) % 1.0, (0.5 + i * 0.5698402910) % 1.0


def draw_background_zombies(surface, game, scene, limit=None, scroll=True, scenery=None):
    """Draw the zombies behind the convoy, scattered along the whole looping background and scrolling past with it.

    They stand at fixed spots of the background strip (see _background_view), so they move at exactly the speed of the
    scenery; the window shows about as many of them as the horde danger asks for (game.zombie_count(), at most
    len(ZOMBIE_SLOTS)), because the strip is wider than the window and holds proportionally more. They stand on the
    ground between ZOMBIE_Y_MIN and ZOMBIE_Y_MAX of the scene's height (the same band as before), and nearer ones are
    lower, larger and drawn later."""
    scene = pygame.Rect(scene)
    count = min(game.zombie_count() if limit is None else limit, len(ZOMBIE_SLOTS))
    if count <= 0:
        return
    big, left, _scale = _background_view(scene, scroll, scenery or game_scenery(game))
    strip_w = big.get_width()
    unit = scene.h / SCENE_REF_H
    depth_range = ZOMBIE_Y_MAX - ZOMBIE_Y_MIN
    placed = min(4 * len(ZOMBIE_SLOTS), max(count, round(count * strip_w / scene.w)))   # on the whole strip
    margin = int(70 * unit)   # a zombie whose feet are just outside the scene can still show its body
    spots = []
    for i in range(placed):
        u, depth = _zombie_spot(i)
        x = (u * strip_w - left) % strip_w   # where it is in the scene now (the strip repeats every strip_w)
        shown = x
        while shown > -margin:               # back to the leftmost repeat of the strip
            shown -= strip_w
        while shown <= scene.w + margin:     # every repeat the scene can show (a widened scene is wider than one strip)
            if shown >= -margin:
                spots.append((depth, scene.x + shown))
            shown += strip_w
    old_clip = surface.get_clip()
    surface.set_clip(scene.clip(old_clip))   # zombies walking in and out are cut off at the scene's edges
    zscale = zombie_scale(unit)   # the same for every zombie of this scene
    for depth, x in sorted(spots):   # far ones first, so nearer ones cover them
        y = scene.y + (ZOMBIE_Y_MIN + depth * depth_range) * scene.h
        draw_zombie(surface, x, y, (0.8 + 0.4 * depth) * unit, zscale)
    surface.set_clip(old_clip)


def draw_scene_art(surface, game, scene, zombie_limit=None, labels=True):
    """The convoy picture inside `scene`: background, zombies and vehicles, all placed relative to it."""
    scene = pygame.Rect(scene)
    pygame.draw.rect(surface, (20, 27, 29), scene)
    scenery = game_scenery(game)   # "highway", or "desert" once the convoy is past the Mountain Pass
    draw_scene_background(surface, scene, scenery=scenery)
    draw_background_zombies(surface, game, scene, zombie_limit, scenery=scenery)
    draw_convoy_vehicles(surface, game, scene, labels)


SCENE_MAX_WIDEN = 2.0   # on a wide window the scene may grow up to this many times wider than 10:3 (1.0 = never wider)


def scene_rect(area):
    """The rectangle the convoy scene is drawn in, inside the allocated `area`: the same height as the 10:3 fit (so the
    vehicles and zombies keep their size), but widened to the width of the area on wide windows, up to SCENE_MAX_WIDEN
    times the 10:3 width, so that more of a long convoy fits before the scroll arrows are needed. draw_scene and the
    arrow buttons (buttons.py) both use this, so they always agree."""
    area = pygame.Rect(area)
    base = pygame.Rect(fit_ratio(tuple(area), *SCENE_ASPECT))
    width = min(area.w, int(base.w * SCENE_MAX_WIDEN))
    return pygame.Rect(area.x + (area.w - width) // 2, base.y, width, base.h)


def draw_scene(surface, game, scene=None):
    if scene is None:
        scene = calculate_layout(*surface.get_size())["scene"]

    # The picture keeps the height of the 10:3 fit and is widened on wide windows (scene_rect).
    scene = scene_rect(scene)
    draw_scene_art(surface, game, scene)

    small = scaled_font(surface.get_size(), 15)
    # On plates like the vehicle labels: the sky behind them has bright clouds.
    draw_scene_label(surface, "WEST  <---", small, topleft=(scene.x + 12, scene.y + 10))
    draw_scene_label(surface, "CONVOY ON THE ROAD", small, topright=(scene.right - 12, scene.y + 10))


EVENTS_LABEL = "RECENT EVENTS: "


def _events_plan(messages, width, height, fonts, max_lines):
    """(font, lines) for the event log: the newest message after the label on the first line, then the older ones
    (up to max_lines lines in all, or every message that fits). The largest font that shows all the wanted lines
    with each one fitting the width is used; failing that the smallest such font, with the lines cut with "...";
    failing that (a very short panel) the largest font that fits the height, with fewer lines."""
    want = max(1, min(len(messages), max_lines or len(messages)))
    full = partial = None
    for font in fonts:
        room = (height - 8) // (font.get_linesize() + 1)
        if room < 1:
            continue
        count = min(want, room)
        lines = [EVENTS_LABEL + messages[0] if messages else EVENTS_LABEL.strip()] + messages[1:count]
        if count < want:
            partial = partial or (font, lines)
            continue
        full = (font, lines)
        if all(font.size(line)[0] <= width for line in lines):
            return font, lines
    return full or partial or (fonts[-1] if fonts else TINY, [EVENTS_LABEL.strip()])


HISTORY_TAG = "HISTORY"


def draw_events(surface, game, rect=None, max_lines=None, button=None):
    """The recent-events panel: "RECENT EVENTS: <newest>" and below it the older messages, one line each (max_lines
    caps the lines; the compact layout's strip shows two). The font grows with the window. The whole bar is the
    HISTORY button (`button`, built by buttons.py): a "HISTORY [H]" tag sits at its right, the bar lights up under
    the mouse and gets the yellow focus ring from the keyboard."""
    if rect is None:
        rect = calculate_layout(*surface.get_size())["events"]
    rect = pygame.Rect(rect)
    hovered = button is not None and button.enabled and rect.collidepoint(pygame.mouse.get_pos())

    draw_panel(surface, rect, (34, 42, 45) if hovered else (25, 31, 34), 0)
    draw_frame(surface, rect, (120, 132, 133) if hovered else (70, 82, 83), 1 * PIX)

    pad = 10
    fonts = text_ladder(surface.get_size())
    tag_w = 0
    if button is not None:
        # The tag is cut from the width of the text lines, so no line runs under it.
        fitting = [f for f in fonts if f.get_linesize() + 6 <= rect.h - 8]
        tag_font = fitting[0] if fitting else (fonts[-1] if fonts else TINY)
        tag_w = tag_font.size(HISTORY_TAG)[0] + 14
    width = max(20, rect.w - pad * 2 - (tag_w + pad if tag_w else 0))
    messages = [str(message) for message in game.log]
    font, lines = _events_plan(messages, width, rect.h, fonts, max_lines)
    step = font.get_linesize() + 1
    y = rect.y + (max(3, (rect.h - len(lines) * step) // 2) if max_lines else 4)   # centred in the strip
    x = rect.x + pad
    for i, line in enumerate(lines):
        if i == 0:
            label_w = font.size(EVENTS_LABEL)[0]
            draw_text(surface, EVENTS_LABEL.rstrip(), x, y, YELLOW, font)
            if messages:
                draw_text(surface, fit_text(messages[0], font, width - label_w), x + label_w, y, WHITE, font)
        else:
            draw_text(surface, fit_text(line, font, width), x, y, MUTED, font)
        y += step

    if button is not None:
        tag = pygame.Rect(rect.right - pad - tag_w, rect.y + 4, tag_w, min(rect.h - 8, tag_font.get_linesize() + 6))
        draw_panel(surface, tag, (62, 74, 76) if hovered else (45, 55, 57), 1)
        draw_text(surface, HISTORY_TAG, tag.x + 7, tag.y + (tag.h - tag_font.get_linesize()) // 2, YELLOW, tag_font)
        if button.focused and button.enabled:
            draw_frame(surface, rect, YELLOW)   # keyboard focus ring (the bar is the button)


def draw_info_panel(surface, game, rect):
    """Wide layout only: the sites of the current stop (SCAVENGE lets you pick one) and the keys that matter here."""
    k = calculate_layout(*surface.get_size())["k"]
    window = surface.get_size()
    tiny, small, body = scaled_font(window, 13), scaled_font(window, 15), scaled_font(window, 19)
    draw_panel(surface, rect, PANEL, 1)
    pad = tpx(12, k)
    x = rect.x + pad
    width = max(20, rect.w - pad * 2)
    limit = rect.bottom - pad
    y = rect.y + pad
    draw_text(surface, "CURRENT STOP", x, y, YELLOW, tiny)
    y += tpx(20, k)
    draw_text(surface, fit_text(game.current_location, body, width), x, y, WHITE, body)
    y += tpx(34, k)
    sites = game.current_sites()
    if not sites:
        y = draw_paragraph(surface, "Nothing to search here.", x, y, width, MUTED, small)
    else:
        for site in sites:
            if y + tpx(18, k) > limit:
                break
            draw_text(surface, fit_text(SITES[site]["name"], small, width), x, y, GREEN, small)
            y = draw_paragraph(surface, SITES[site]["detail"], x, y + tpx(22, k), width, WHITE, tiny, limit=limit) \
                + tpx(8, k)
    y += tpx(6, k)
    for hint in ("S: scavenge", "R: repair", "M: map", "V: vehicles", "P: survivors", "J: missions", "H: history",
                 "Tab / arrows: move", "Enter: select", "Esc: menu"):
        if y + tpx(16, k) > limit:
            break
        draw_text(surface, hint, x, y, MUTED, tiny)
        y += tpx(18, k)


def draw_lower(surface, game, buttons, layout=None):
    if layout is None:
        layout = calculate_layout(*surface.get_size())

    if layout["mode"] == "compact":
        panel = pygame.Rect(layout["actions"])
        draw_panel(surface, panel, PANEL, 1)

        draw_text(
            surface,
            f"CONVOY ACTIONS ({game.difficulty})",
            panel.x + 10,
            panel.y + 5,
            WHITE,
            scaled_font(surface.get_size(), 13),
        )

    else:
        panel = pygame.Rect(layout["sidebar"])
        draw_panel(surface, panel, PANEL, 1)

    # Draw buttons in their calculated locations.
    for button in buttons:
        if button.label not in ("MENU", "HISTORY"):   # MENU is the HUD's; the HISTORY bar draws itself (draw_events)
            button.draw(surface)

    # Pass layout rectangles to drawing functions as needed.
    history_bar = next((b for b in buttons if b.label == "HISTORY"), None)
    draw_events(surface, game, pygame.Rect(layout["events"]), max_lines=2 if layout["mode"] == "compact" else None,
                button=history_bar)
    draw_minimap(surface, game, pygame.Rect(layout["minimap"]))
    if layout.get("info"):
        draw_info_panel(surface, game, pygame.Rect(layout["info"]))
