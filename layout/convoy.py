"""The convoy screen's layout: window size, scene-art fractions and calculate_layout (no pygame).

Every other screen builds on calculate_layout()'s margin, gap, HUD rectangle and text factor k (see textscale.py).
"""
import random

from textscale import text_k, tpx


# WIDTH x HEIGHT is the size the window opens at. It is also the coordinate space of the NODES "pos" values.
WIDTH, HEIGHT, FPS = 1000, 680, 60

# The compact convoy screen keeps at least this much height for the actions + minimap row (three button rows), for the
# default text; calculate_layout multiplies it by k.
COMPACT_LOWER_MIN_H = 172

# Legacy minimap coordinates, no longer used by any screen (kept so that old imports keep working).
MINI_CARD = (556, 520, 412, 128)
MINI_SCALE = 0.36

# The convoy scene art (vehicles, labels, zombies) is placed as fractions of the scene rectangle, so it follows
# the scene wherever the layout puts it. The fractions were measured on the 964 x 270 title-screen scene at
# (18, 125), where the art was first drawn in absolute pixels.
SCENE_REF_W, SCENE_REF_H = 964, 270
SCENE_BASELINE = (343 - 125) / SCENE_REF_H    # where the vehicle wheels rest on the road
SCENE_LABEL_Y = (356 - 125) / SCENE_REF_H     # top of the vehicle name label
SCENE_BAR_Y = (375 - 125) / SCENE_REF_H       # vehicle health bar
ZOMBIE_Y_MIN = (300 - 125) / SCENE_REF_H      # zombie feet: farthest from the camera ...
ZOMBIE_Y_MAX = (334 - 125) / SCENE_REF_H      # ... and nearest to it

# Fixed background-zombie positions as (x, y) fractions of the scene rectangle, easternmost first.
_zombie_rng = random.Random(7)
_zombie_pixels = sorted(
    ((_zombie_rng.randint(690, 960), _zombie_rng.randint(300, 334))
     for _ in range(18)),
    key=lambda slot: -slot[0],
)
ZOMBIE_SLOTS = [((x - 18) / SCENE_REF_W, (y - 125) / SCENE_REF_H) for x, y in _zombie_pixels]


def calculate_layout(width, height):
    """Return responsive panel rectangles as (x, y, width, height) tuples, and "k": the text factor of this window
    (1.0 for the default text; every row that holds text is multiplied by it). A new dict on every call."""
    width = max(640, int(width))
    height = max(480, int(height))
    k = text_k(width, height)

    margin = max(12, min(22, width // 65))
    gap = max(8, min(16, width // 100))
    hud_h = min(104, max(88, height * 0.15)) * k
    top = margin
    content_top = top + hud_h + gap
    bottom = height - margin

    # Wide mode requires enough horizontal space and a useful centre panel.
    wide = width >= 1350 and width / height >= 1.45

    if wide:
        sidebar_w = max(205, min(250, int(width * 0.18)))
        available = width - 2 * margin - 2 * gap - sidebar_w
        sidebar = (
            margin,
            content_top,
            sidebar_w,
            bottom - content_top,
        )

        # An optional information panel is only added when it can be useful.
        info_w = 0
        if available >= 1120:
            info_w = min(290, int(available * 0.25))

        centre_w = available - info_w - (gap if info_w else 0)
        scene_h = max(90, min(centre_w * 0.30, height * 0.50))
        scene_h = min(scene_h, bottom - content_top - gap - 90)

        scene = (
            sidebar[0] + sidebar_w + gap,
            content_top,
            max(200, centre_w),
            max(60, int(scene_h)),
        )

        lower_y = scene[1] + scene[3] + gap
        lower_h = max(60, bottom - lower_y)

        # Split the lower centre row evenly, keeping the minimap 16:9.
        event_w = max(100, int((centre_w - gap) * 0.5))
        mini_w = max(100, centre_w - gap - event_w)
        mini_h = min(lower_h, mini_w * 9 / 16)
        mini_h = max(1, int(mini_h))

        events = (scene[0], lower_y, event_w, lower_h)
        minimap = (
            scene[0] + event_w + gap,
            lower_y,
            mini_w,
            mini_h,
        )

        info = None
        if info_w:
            info = (
                scene[0] + centre_w + gap,
                content_top,
                info_w,
                bottom - content_top,
            )

        menu = (width - margin - tpx(74, k), top + tpx(8, k), tpx(62, k), tpx(30, k))
        hud = (margin, top, width - 2 * margin, hud_h)

        return {
            "mode": "wide",
            "k": k,
            "width": width,
            "height": height,
            "margin": margin,
            "gap": gap,
            "hud": hud,
            "menu": menu,
            "sidebar": sidebar,
            "scene": scene,
            "events": events,
            "minimap": minimap,
            "info": info,
            "actions": sidebar,
        }

    # Compact layout: convoy, horizontal event strip, then actions + minimap.
    inner_w = width - 2 * margin
    scene_w = inner_w
    scene_h = scene_w * 3 / 10

    # Reserve enough space below the scene for events and the bottom panels.
    available_h = bottom - content_top
    events_h = min(tpx(64, k), max(tpx(40, k), int(available_h * 0.12)))
    # The scene takes whatever the event strip and the (three-row) actions + minimap panel do not need.
    scene_room = available_h - events_h - 2 * gap - tpx(COMPACT_LOWER_MIN_H, k)
    scene_h = min(scene_h, max(80, available_h * 0.39, scene_room))
    scene_h = int(scene_h)

    scene = (margin, content_top, scene_w, scene_h)
    events_y = scene[1] + scene[3] + gap

    # The bottom area shares the remaining height between actions and minimap.
    lower_y = events_y + events_h + gap
    lower_h = max(50, bottom - lower_y)
    actions_w = int((inner_w - gap) * 0.54)
    mini_w = inner_w - gap - actions_w
    mini_h = int(min(mini_w * 9 / 16, lower_h))

    events = (margin, events_y, inner_w, events_h)
    actions = (margin, lower_y, actions_w, lower_h)
    minimap = (
        margin + actions_w + gap,
        lower_y,
        mini_w,
        mini_h,
    )

    hud = (margin, top, inner_w, hud_h)
    menu = (width - margin - tpx(70, k), top + tpx(7, k), tpx(58, k), tpx(28, k))

    return {
        "mode": "compact",
        "k": k,
        "width": width,
        "height": height,
        "margin": margin,
        "gap": gap,
        "hud": hud,
        "menu": menu,
        "scene": scene,
        "events": events,
        "actions": actions,
        "minimap": minimap,
        "sidebar": actions,
        "info": None,
    }
