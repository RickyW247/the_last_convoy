"""Layout of the map screen and the shared hit-testing of its stops (no pygame).
"""
import map_data
from map_data import NODES

from .frame import screen_frame
from .geometry import LINE_H, buttons_in_row, clamp, fit_ratio, inset, layout_cache, rect_bottom, rect_right, tpx


MAP_OLD_AREA = (18, 195, 964, 345)         # where the terrain was drawn on the old 1000 x 680 canvas; the
                                           # NODES "pos" values are coordinates in that space
MAP_INFO_MIN_H, MAP_INFO_MAX_H = 92, 150
# Side-by-side layout (info panel left, map right): used whenever it gives a clearly bigger map than the stacked layout
# (info panel under the map) in this window, so it follows the window's shape (a wide, low window) and not the text size.
# It is chosen when its map is at least this many times as wide as the stacked layout's map.
MAP_SIDE_GAIN = 1.05
MAP_SIDE_INFO_MIN_H = 210                  # the info column is at least this tall (in 1.0-scale pixels) when the body allows
MAP_SIDE_INFO_FRAC = 0.30                  # share of the body width taken by the info column
MAP_SIDE_INFO_MIN_W, MAP_SIDE_INFO_MAX_W = 300, 480
MAP_SIDE_STATUS_H = 64                     # height of the "Fuel available / Horde gap" strip at the bottom of the column


def _stacked_parts(body, inner, gap, k, lh):
    """(map rectangle, info rectangle, subtitle or None) with the info panel under the map, across the whole body."""
    info_h = clamp(int(inner[3] * 0.20), tpx(MAP_INFO_MIN_H, k), tpx(MAP_INFO_MAX_H, k))
    info = (body[0], rect_bottom(body) - info_h, body[2], info_h)
    top = body[1]
    avail_h = info[1] - gap - top
    subtitle = None
    if avail_h - lh - gap >= 220:       # the secondary text only when it costs the map little
        subtitle = (body[0], top, body[2], lh)
        top += lh + gap
        avail_h -= lh + gap
    map_rect = fit_ratio((body[0], top, body[2], max(1, avail_h)), MAP_OLD_AREA[2], MAP_OLD_AREA[3])
    return map_rect, info, subtitle


def _side_parts(body, gap, k, lh):
    """(map rectangle, info rectangle, subtitle or None) with the info column on the right of the map."""
    info_w = clamp(int(body[2] * MAP_SIDE_INFO_FRAC), tpx(MAP_SIDE_INFO_MIN_W, k), tpx(MAP_SIDE_INFO_MAX_W, k))
    area = (body[0], body[1], max(1, body[2] - info_w - gap), body[3])
    top, avail_h = area[1], area[3]
    subtitle = None
    if avail_h - lh - gap >= 220:
        subtitle = (area[0], top, area[2], lh)
        top += lh + gap
        avail_h -= lh + gap
    map_rect = fit_ratio((area[0], top, area[2], max(1, avail_h)), MAP_OLD_AREA[2], MAP_OLD_AREA[3])
    # The column sits against the map and is as tall as it, so the pair reads as one block; in a low window the map is
    # short, so the column may be taller than the map (down to the bottom of the body) to keep room for its text.
    info_h = min(body[3], max(map_rect[3], tpx(MAP_SIDE_INFO_MIN_H, k)))
    info_y = min(map_rect[1], rect_bottom(body) - info_h)
    info = (min(rect_right(body) - info_w, rect_right(map_rect) + gap), info_y, info_w, info_h)
    if subtitle:
        subtitle = (map_rect[0], subtitle[1], map_rect[2], lh)
    return map_rect, info, subtitle


@layout_cache(32)
def _map_geometry(width, height):
    """Rectangles of the map screen: header, optional subtitle, the map (same aspect ratio as the old 964 x 345
    terrain area) with the stops placed as fractions of it, the info panel under it and TRAVEL / BACK.

    "positions" are the window pixels of every stop (NODES order), "radius" the circle radius and "reach" how far
    a stop's rings reach from its centre. The stops are placed inside `node_area`, the map shrunk by `reach`, so
    their circles and rings always stay inside the map.

    This part is cached per window size and does not depend on the stops; map_layout adds the stop positions on top,
    because they change with the map layout of each run (map_data.LAYOUTS).
    """
    f = screen_frame(width, height)
    gap, inner, header, body, panel, k = f["gap"], f["inner"], f["header"], f["body"], f["panel"], f["k"]
    lh = tpx(LINE_H, k)

    # Lay the screen out both ways and keep the one that shows the bigger map (the map keeps its aspect ratio, so its
    # width says it all). A wide, low window gives the side-by-side layout a bigger map; a tall one the stacked layout.
    stacked = _stacked_parts(body, inner, gap, k, lh)
    side_parts = _side_parts(body, gap, k, lh)
    side = side_parts[0][2] >= stacked[0][2] * MAP_SIDE_GAIN
    map_rect, info, subtitle = side_parts if side else stacked

    unit = map_rect[2] / MAP_OLD_AREA[2]                     # 1.0 at the old size
    radius = clamp(int(round(17 * unit)), 8, 40)
    ring = max(4, int(round(8 * unit)))                      # distance of the CONVOY ring from the circle
    reach = radius + ring + 2
    node_area = inset(map_rect, reach + 2)

    info_inner = inset(info, 8, 6)
    if side:
        # stacked: the stop's details on top, fuel and horde gap in a strip along the bottom
        status_h = min(tpx(MAP_SIDE_STATUS_H, k), max(1, info_inner[3] // 3))
        info_right = (info_inner[0], rect_bottom(info_inner) - status_h, info_inner[2], status_h)
        info_left = (info_inner[0], info_inner[1], info_inner[2], max(1, info_right[1] - gap - info_inner[1]))
    else:
        right_w = clamp(int(info_inner[2] * 0.34), tpx(140, k), tpx(300, k))
        info_right = (rect_right(info_inner) - right_w, info_inner[1], right_w, info_inner[3])
        info_left = (info_inner[0], info_inner[1], max(1, info_right[0] - gap - info_inner[0]), info_inner[3])

    tw = clamp(int(inner[2] * 0.20), tpx(100, k), tpx(150, k))
    bw = clamp(int(inner[2] * 0.15), tpx(80, k), tpx(140, k))
    _, right = buttons_in_row(f["button_row"], [], [tw, bw], gap)

    leaves = [("header", header)]
    if subtitle:
        leaves.append(("subtitle", subtitle))
    leaves += [("map", map_rect), ("info", info), ("travel", right[0]), ("back", right[1])]
    inside = [("node_area", node_area, map_rect), ("info_left", info_left, info), ("info_right", info_right, info)]
    return {
        "size": f["size"], "k": k, "side": side, "hud": f["hud"], "panel": panel, "header": header, "subtitle": subtitle,
        "map": map_rect, "node_area": node_area, "unit": unit, "radius": radius, "ring": ring, "reach": reach,
        "info": info, "info_left": info_left, "info_right": info_right,
        "travel": right[0], "back": right[1], "leaves": leaves, "inside": inside,
        "groups": [("info columns", [("left", info_left), ("right", info_right)])],
    }


_STOP_PARTS = {}   # (node_area, map_data.LAYOUT_VERSION) -> (positions, per-stop "inside" entries)


def map_layout(width, height):
    """The map screen's layout (see _map_geometry) with the stops' window pixels of the active map layout."""
    g = _map_geometry(int(width), int(height))
    key = (tuple(g["node_area"]), map_data.LAYOUT_VERSION)
    parts = _STOP_PARTS.get(key)
    if parts is None:
        positions = tuple(map_point_in(g["node_area"], node["pos"]) for node in NODES)
        reach, map_rect = g["reach"], g["map"]
        inside = [(f"node{i}", (x - reach, y - reach, 2 * reach, 2 * reach), map_rect)
                  for i, (x, y) in enumerate(positions)]
        if len(_STOP_PARTS) > 64:
            _STOP_PARTS.clear()
        parts = _STOP_PARTS[key] = (positions, inside)
    result = dict(g)
    result["positions"] = parts[0]
    result["inside"] = list(g["inside"]) + parts[1]
    return result


def map_point_in(area, pos):
    """Window pixel of a point of the old map space (`pos`, in the 1000 x 680 canvas coordinates of the NODES)
    inside `area`: the point's fraction of the old map area, applied to `area`."""
    ox, oy, ow, oh = MAP_OLD_AREA
    ax, ay, aw, ah = area
    return (ax + int(round((pos[0] - ox) / ow * aw)), ay + int(round((pos[1] - oy) / oh * ah)))


def map_point(width, height, pos):
    """Window pixel of a point (x, y) of the old map space on the map screen of a window this size."""
    return map_point_in(map_layout(int(width), int(height))["node_area"], pos)


def node_at(width, height, pos):
    """The index of the stop under a window pixel, or None. Uses the positions the map is drawn with
    (map_layout), so clicks and drawing cannot drift apart; the nearest stop wins when circles are close."""
    g = map_layout(int(width), int(height))
    reach = max(g["radius"] + 4, 14)
    best, best_d = None, reach * reach + 1
    for i, (x, y) in enumerate(g["positions"]):
        d = (pos[0] - x) ** 2 + (pos[1] - y) ** 2
        if d < best_d:
            best, best_d = i, d
    return best
