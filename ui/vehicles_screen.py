"""The vehicles screen of THE LAST CONVOY: the vehicle table, the preview card and the screen itself.
Drawing only."""
from functools import lru_cache

import pygame

from widgets import PIX, draw_frame, draw_panel

from .common import CARD_BG, scaled_image, SCREEN_BG
from layout import LINE_H, table_pad, vehicle_card_layout, vehicle_row_at, vehicles_layout
from .pixel_art import choose_pixel_scale
from theme import BLUE, FONT, GREEN, MUTED, PANEL, PANEL_LIGHT, RED, ROAD, SMALL, TINY, WHITE, YELLOW
from .vehicle_rendering import get_vehicle_source, get_vehicle_sprite
from upgrade_data import fully_upgraded_stats
from vehicle_data import BONUS_VEHICLES, STANDARD_VEHICLES, VEHICLE_ROLES, VEHICLE_SPECS, ability_info
from textscale import text_k, text_level, tpx
from widgets import (draw_bar, draw_heading, draw_text, fit_variants, pick_font, screen_fonts, text_in_rect,
                     wrap_pixels)


@lru_cache(maxsize=32)
def _smooth_picture(name, size):
    """The vehicle's full-resolution PNG shrunk smoothly to `size` (cached per vehicle and size)."""
    return pygame.transform.smoothscale(get_vehicle_source(name), size)


# Stats in the order of the table columns SPD .. FUSE (the table's cells 2 to 8), and the ones where a lower number is better.
_TABLE_STAT_KEYS = ("speed", "health", "passengers", "cargo", "defense", "fuel_capacity", "fuel_consumption")
_LOWER_IS_BETTER = ("fuel_consumption",)
# The card's stat lines: (stat, label), in the order they are shown.
_CARD_STATS = (("passengers", "Seats"), ("cargo", "Cargo"), ("defense", "Defense"), ("speed", "Speed"),
               ("fuel_capacity", "Fuel"), ("fuel_consumption", "Fuel use"))


def _stat_color(stat, now, base, default):
    """GREEN when upgrades made this stat better than the vehicle type's own value, RED when they made it worse (the
    trailer's slower, thirstier rig), `default` when it is unchanged."""
    if now == base:
        return default
    better = now < base if stat in _LOWER_IS_BETTER else now > base
    return GREEN if better else RED


def _flow_items(items, font, width, gap):
    """Lay (text, colour) items out left to right in lines no wider than `width`: [[(x, text, colour), ...], ...]."""
    lines, line, x = [], [], 0
    for text, color in items:
        w = font.size(text)[0]
        if line and x + w > width:
            lines.append(line)
            line, x = [], 0
        line.append((x, text, color))
        x += w + gap
    if line:
        lines.append(line)
    return lines


def _card_stat_lines(font, width, max_lines, stats, base, owned):
    """The card's stats as coloured lines. A changed stat is first written out in full ("Speed 70 -> 76"); if that
    needs more lines than the card has, the short form with just the new number is used (still coloured)."""
    gap = font.size("   ")[0]
    lines = []
    for long_form in (True, False):
        items = []
        for key, label in _CARD_STATS:
            now = stats[key]
            changed = owned and now != base[key]
            text = f"{label} {base[key]} -> {now}" if long_form and changed else f"{label} {now}"
            items.append((text, _stat_color(key, now, base[key], MUTED) if owned else MUTED))
        lines = _flow_items(items, font, width, gap)
        if len(lines) <= max_lines:
            return lines
    return lines[:max_lines]


def _draw_ability(surface, rect, vehicle_type, owned, tiny, lh):
    """The vehicle's special ability in the card's ability rectangle (only called for a vehicle that has one). Its height
    says how many lines the layout could spare (layout.vehicles): 3 lines = the name and two lines of effect, 2 = the name
    and one line, 1 = "Name: short effect" on a single line. GREEN while the vehicle is in the convoy (the ability is
    working), MUTED while it is not owned (what recovering it would add)."""
    ax, ay, aw, ah = rect
    info = ability_info(vehicle_type)
    head_color = GREEN if owned else MUTED
    room = max(1, ah // lh)
    if room == 1:
        one_line = fit_variants(tiny, aw, (f"{info['name']}: {info['short']}", info["name"], info["name"].split()[0]))
        text_in_rect(surface, one_line, (ax, ay, aw, lh), head_color, tiny)
        return
    heading = fit_variants(tiny, aw, (f"ABILITY: {info['name']}", info["name"], info["name"].split()[0]))
    text_in_rect(surface, heading, (ax, ay, aw, lh), head_color, tiny)
    lines = wrap_pixels(info["text"], tiny, aw)
    if len(lines) > room - 1:   # too long for the lines there are at this card width: the short wording
        lines = wrap_pixels(info["short"], tiny, aw)
    for i, line in enumerate(lines[:room - 1]):
        text_in_rect(surface, line, (ax, ay + (i + 1) * lh, aw, lh), WHITE if owned else MUTED, tiny)


def draw_vehicle_card(surface, game, card):
    """Preview card for the selected vehicle in the rectangle `card`: picture, status, health or recovery cost and
    key stats. Rows that do not fit (the role text) are dropped by vehicle_card_layout."""
    card = tuple(card)
    size = surface.get_size()
    k = text_k(*size)   # the layout rows were scaled by this, so the fonts and row steps are too
    _medium, font, small, tiny = screen_fonts(size)
    lh = tpx(LINE_H, k)
    name = game.selected_vehicle_type
    ability = ability_info(name)
    ability_lines = 0
    if ability:   # reserve only as many text lines as the full effect text needs at this card width
        ability_lines = len(wrap_pixels(ability["text"], tiny, max(0, card[2] - 2 * tpx(8, k)))) or 1
    parts = vehicle_card_layout(card, k, ability_lines)
    owned_vehicle = next((v for v in game.vehicles if v.vehicle_type == name), None)
    base_stats = VEHICLE_SPECS[name]
    stats = owned_vehicle.stats if owned_vehicle else base_stats   # an owned vehicle shows its upgraded numbers
    look = owned_vehicle.sprite_type if owned_vehicle else name              # ... and its upgraded picture
    draw_panel(surface, card, CARD_BG, -1)
    draw_frame(surface, card, BLUE, 1 * PIX)
    draw_heading(surface, name, parts["name"], WHITE, (font, small, tiny))

    if parts["role"]:
        rx, ry, rw, _rh = parts["role"]
        for i, line in enumerate(wrap_pixels(VEHICLE_ROLES.get(name, ""), tiny, rw)[:2]):
            draw_text(surface, line, rx, ry + i * lh, MUTED, tiny)

    # Picture: the side-view sprite (facing west / left), scaled from the source image to fill the picture box.
    pic = pygame.Rect(parts["picture"])
    if pic.h >= 28 and pic.w >= 40:
        draw_panel(surface, pic, (70, 99, 102), 0)
        road_h = min(30, pic.h // 3)
        pygame.draw.rect(surface, ROAD, (pic.x, pic.bottom - road_h, pic.w, road_h))
        box = (pic.w - 12, pic.h - 10)
        source = get_vehicle_source(look)
        if source is not None:
            # The original PNG, shrunk smoothly to fit (never enlarged). The pixelated sprite enlarged 3x / 4x looked blurry
            # in a big card; the convoy scene still uses the pixelated one.
            fit = min(box[0] / source.get_width(), box[1] / source.get_height(), 1.0)
            pic_size = (max(1, int(source.get_width() * fit)), max(1, int(source.get_height() * fit)))
            picture = _smooth_picture(look, pic_size) if pic_size != source.get_size() else source
        else:   # the PNG could not be loaded: the placeholder sprite at a whole-number scale
            fine, coarse = get_vehicle_sprite(look), get_vehicle_sprite(look, coarse=True)
            index, scale = choose_pixel_scale([fine.get_size(), coarse.get_size()], box, (4, 4))
            sprite = (fine, coarse)[index]
            pic_size = (max(1, int(sprite.get_width() * scale)), max(1, int(sprite.get_height() * scale)))
            picture = scaled_image(("vehicle", look, index), sprite, pic_size)
        surface.blit(picture, (pic.centerx - pic_size[0] // 2, pic.bottom - 6 - pic_size[1]))

    if parts["ability"]:
        _draw_ability(surface, parts["ability"], name, owned_vehicle is not None, tiny, lh)

    ox, oy, ow, oh = parts["owned"]
    status_font = pick_font((small, tiny), ["NOT OWNED"], ow, oh)
    owned_text = "NOT OWNED"
    if owned_vehicle:
        owned_text = f"OWNED +{len(owned_vehicle.upgrades)}" if owned_vehicle.upgrades else "OWNED"   # +n: upgrades installed
    text_in_rect(surface, owned_text, parts["owned"],
                  GREEN if owned_vehicle else MUTED, status_font)

    dx, dy, dw, _dh = parts["detail"]
    if owned_vehicle:
        full = stats["health"]
        hp_color = GREEN if owned_vehicle.health >= 0.6 * full else (YELLOW if owned_vehicle.health >= 0.3 * full else RED)
        gained = full - base_stats["health"]   # upgrades raise (or lower) the maximum health
        health_text = fit_variants(tiny, dw, ((f"Health {owned_vehicle.health}/{full} ({gained:+d})",) if gained else ())
                                   + (f"Health {owned_vehicle.health}/{full}",))
        text_in_rect(surface, health_text, (dx, dy, dw, lh), _stat_color("health", full, base_stats["health"], WHITE), tiny)
        draw_bar(surface, dx, dy + lh + 3, dw, tpx(10, k), owned_vehicle.health, full, hp_color)
    else:
        text_in_rect(surface, fit_variants(tiny, dw, (f"Recovery: {game.recovery_price(name)} scrap + 1 day",
                                                         f"Recovery: {game.recovery_price(name)} scrap")),
                      (dx, dy, dw, lh), WHITE, tiny)
        text_in_rect(surface, fit_variants(tiny, dw, ("Starts at 70% health once recovered.",
                                                         "Starts at 70% health.", "Starts at 70% HP.")),
                      (dx, dy + lh, dw, lh), MUTED, tiny)

    sx, sy, sw, sh = parts["stats"]
    for i, line in enumerate(_card_stat_lines(tiny, sw, sh // lh, stats, base_stats, owned_vehicle is not None)):
        for x, text, color in line:
            text_in_rect(surface, text, (sx + x, sy + i * lh, sw - x, lh), color, tiny)


ROW_HOVER_BG = (40, 60, 66)   # a table row under the mouse: between the zebra colour and the selected row's (46, 68, 74)

_TABLE_HEADERS = ("VEHICLE", "STATUS", "SPD", "HP", "PASS", "CARGO", "DEF", "FCAP", "FUSE")


_TABLE_HEADERS_COMPACT = ("VEHICLE", "OWN", "SPD", "HP", "PASS", "CARGO", "DEF", "FCAP", "FUSE")


def vehicle_table_order(game):
    """The vehicle names in table order: owned vehicles first, then the ones not owned, each group in catalogue
    (VEHICLE_SPECS) order. Recovering a vehicle moves its row up into the owned group; abandoning it puts the row
    back in its usual catalogue spot among the not-owned ones. main.py's click handling must map a row index from
    layout.vehicle_row_at to a vehicle through this same list: vehicle_table_order(game)[index]."""
    owned_types = {vehicle.vehicle_type for vehicle in game.vehicles}
    # Bonus vehicles are listed only once unlocked (achievements; all of them in sandbox mode) or while owned.
    listed = game.listed_vehicle_types()
    return ([name for name in listed if name in owned_types]
            + [name for name in listed if name not in owned_types])


def _vehicle_table_rows(game, compact):
    """(vehicle name, [nine cell strings], [nine colours]) for each row of the vehicle table, owned vehicles first."""
    owned_by_type = {vehicle.vehicle_type: vehicle for vehicle in game.vehicles}
    rows = []
    for name in vehicle_table_order(game):
        base = VEHICLE_SPECS[name]
        vehicle = owned_by_type.get(name)
        owned = vehicle is not None
        stats = vehicle.stats if owned else base   # an owned vehicle shows its upgraded numbers
        status = "OWNED" if owned else ("-" if compact else "NOT OWNED")
        health = f"{vehicle.health}/{stats['health']}" if owned else str(stats["health"])
        cells = [name, status, stats["speed"], health, stats["passengers"], stats["cargo"], stats["defense"],
                 stats["fuel_capacity"], stats["fuel_consumption"]]
        colors = [WHITE, GREEN if owned else MUTED] + [WHITE if owned else MUTED] * 7
        if owned:   # an upgraded stat is green (red when the upgrade made it worse); the type's own value stays white
            for column, stat in enumerate(_TABLE_STAT_KEYS, start=2):
                colors[column] = _stat_color(stat, stats[stat], base[stat], colors[column])
        if owned and vehicle.health < stats["health"]:
            colors[3] = YELLOW   # a damaged vehicle's health stays yellow
        rows.append((name, [str(c) for c in cells], colors))
    return rows


def _worst_case_cells(compact, names):
    """The widest text each vehicle row can hold in each column, whatever the vehicle's current health or ownership
    is: an owned vehicle at full health ("1000/1000") with the widest status text."""
    status = "OWNED" if compact else "NOT OWNED"
    for name in names:
        base = VEHICLE_SPECS[name]
        stats = fully_upgraded_stats(name, base)   # the widest numbers the vehicle can reach with every upgrade installed
        yield [name, status, stats["speed"], f"{stats['health']}/{stats['health']}", stats["passengers"],
               stats["cargo"], stats["defense"], stats["fuel_capacity"], stats["fuel_consumption"]]


@lru_cache(maxsize=64)
def _table_font(columns, pad, row_h, compact, names, body, small, tiny):
    """The largest of body / small / tiny that fits: the row must be tall enough and every column must hold its
    worst-case text in it. Falls back to tiny.

    Depends only on the table geometry (columns, cell padding, row height) and the fonts, so the font does not flip between
    sizes as a vehicle's health text changes width."""
    worst = list(_worst_case_cells(compact, names))
    for font in (body, small):
        if font.get_linesize() > row_h - 4:
            continue
        if all(font.size(str(cell))[0] <= w - 2 * pad
               for cells in worst for cell, (_x, w) in zip(cells, columns)):
            return font
    return tiny


def vehicle_page(game):
    """The page of the vehicle table that is showing (Game.vehicle_page; 0 until paging.clamp_pages has run)."""
    return getattr(game, "vehicle_page", 0)


def _hovered_row(surface, game):
    """Index (into all vehicles) of the table row under the mouse, or None (also None while a popup is open on top of the screen).
    Same geometry as main.py's click handling (layout.vehicle_row_at)."""
    if game.confirm_popup or game.event_result or game.event_manager.active or game.abandon_pick_needed():
        return None
    width, height = surface.get_size()
    return vehicle_row_at(width, height, pygame.mouse.get_pos(), len(vehicle_table_order(game)), vehicle_page(game))


def _draw_vehicle_table(surface, game, g):
    """The vehicle catalogue: heading row and one row per vehicle type, drawn in the rectangles of `g`."""
    _medium, body, small, tiny = screen_fonts(surface.get_size())
    table = pygame.Rect(g["table"])
    columns = g["columns"]
    row_h = g["row_h"]
    pad = table_pad(g["compact"])
    header = pygame.Rect(g["table_header"])
    draw_panel(surface, header, PANEL_LIGHT, 1)
    heads = _TABLE_HEADERS_COMPACT if g["compact"] else _TABLE_HEADERS
    for (x, w), label in zip(columns, heads):
        text_in_rect(surface, label, (x + pad, header.y, w - 2 * pad, header.h), WHITE, tiny)

    all_rows = _vehicle_table_rows(game, g["compact"])
    per_page = g["per_page"]
    first = max(0, min(vehicle_page(game), g["pages"] - 1)) * per_page
    rows = all_rows[first:first + per_page]   # one page of the catalogue
    hovered = _hovered_row(surface, game)   # the row under the mouse gets a lighter background (and a hand cursor, main.py)
    font = _table_font(tuple(columns), pad, row_h, g["compact"], tuple(STANDARD_VEHICLES) + tuple(n for n in vehicle_table_order(game) if n in BONUS_VEHICLES), body, small, tiny)   # from the table geometry only, never the values
    for slot, (name, cells, colors) in enumerate(rows):
        index = first + slot   # the position in the whole catalogue (hover and the zebra stripes follow it)
        row = pygame.Rect(table.x, g["rows_top"] + slot * row_h, table.w, row_h - 2)
        if name == game.selected_vehicle_type:
            draw_panel(surface, row, (46, 68, 74), 0)
            draw_frame(surface, row, BLUE, 1 * PIX)
        elif index == hovered:
            draw_panel(surface, row, ROW_HOVER_BG, 0)
            draw_frame(surface, row, MUTED, 1 * PIX)
        elif index % 2 == 0:
            draw_panel(surface, row, CARD_BG, -1)
        for (x, w), cell, color in zip(columns, cells, colors):
            text_in_rect(surface, cell, (x + pad, row.y, w - 2 * pad, row.h), color, font)

    if g["paged"]:   # the PREV / NEXT buttons are in `buttons` (drawn by draw_vehicles_screen); the label sits between them
        page = max(0, min(vehicle_page(game), g["pages"] - 1))
        lx, ly, lw, lh_ = g["page_label"]
        text_in_rect(surface, fit_variants(tiny, lw, (f"Page {page + 1} / {g['pages']}", f"{page + 1}/{g['pages']}")),
                     (lx, ly, lw, lh_), MUTED, tiny, "center")


def _summary_items(game, totals):
    """(full text, short text) of each cell of the convoy totals. The short text is only ever used at the Large and
    Extra large text sizes, in a cell too narrow for the full text."""
    owned, kinds = len(game.vehicles), len(game.listed_vehicle_types())
    passengers = f"{game.survivors}/{totals['passengers']}"
    fuel = f"{game.fuel}/{totals['fuel_capacity']}"
    return [
        ("CONVOY TOTALS", "TOTALS"),
        (f"OWNED {owned} / {kinds}", f"OWNED {owned}/{kinds}"),
        (f"SPEED {totals['speed']} (slowest vehicle)", f"SPD {totals['speed']}"),
        (f"HEALTH {totals['health']}/{totals['max_health']}", f"HP {totals['health']}/{totals['max_health']}"),
        (f"PASSENGERS {passengers} (drivers: {game.adult_count()})", f"PASS {passengers} DRV {game.adult_count()}"),
        (f"CARGO {game.cargo_used()}/{totals['cargo']}", f"CARGO {game.cargo_used()}/{totals['cargo']}"),
        (f"DEFENSE {game.total_defense()} (-{game.defense_reduction()}% ambush)",
         f"DEF {game.total_defense()} (-{game.defense_reduction()}%)"),
        (f"FUEL {fuel}  USE {totals['fuel_consumption']}/unit", f"FUEL {fuel} USE {totals['fuel_consumption']}"),
    ]


def _draw_summary(surface, game, g, totals, small, tiny):
    """The totals of the WHOLE convoy (the table lists single vehicles), in their own framed box and the first cell says
    so. layout.vehicles chooses the shape: a 4 x 2 grid, one row of 8 cells, or one column of 8 lines (g["summary_grid"]).
    Normal and Small text always show the full wording; Large and Extra large show the short wording in cells that are
    too narrow for the full one."""
    items = _summary_items(game, totals)
    short_ok = text_level() in ("Large", "Extra large")
    mx, my, mw, mh = g["summary"]
    box = pygame.Rect(mx, my, mw, mh).inflate(10, 4)
    draw_panel(surface, box, PANEL_LIGHT, 1)
    draw_frame(surface, box, YELLOW, 1 * PIX)
    cols, grid_rows = g["summary_grid"]
    cell_h = mh // grid_rows
    if cols == 8:
        # one row: the cells are as wide as their short text is long (the short wording is always used here)
        weights = [len(short) + 2 for _full, short in items]
        edges = [0]
        for weight in weights:
            edges.append(edges[-1] + weight)
        cells = [(mx + mw * edges[i] // edges[-1], my, mw * edges[i + 1] // edges[-1] - mw * edges[i] // edges[-1] - 6, cell_h)
                 for i in range(8)]
    else:
        col_w = mw // cols
        cells = [(mx + (i % cols) * col_w, my + (i // cols) * cell_h, col_w - 6, cell_h) for i in range(8)]
    shown_for_font = [short if short_ok else full for full, short in items]
    font = tiny
    for candidate in (small, tiny):
        if candidate.get_linesize() <= cell_h and all(candidate.size(text)[0] <= cell[2]
                                                     for text, cell in zip(shown_for_font, cells)):
            font = candidate
            break
    for i, ((full, short), cell) in enumerate(zip(items, cells)):
        if cols == 8:
            text = short
        else:
            text = fit_variants(font, cell[2], (full, short)) if short_ok else full
        text_in_rect(surface, text, cell, YELLOW if i == 0 else WHITE, font)


def draw_vehicles_screen(surface, game, buttons):
    """Show the vehicle catalogue, ownership, specifications, and convoy totals, with the given buttons.

    Everything is placed by vehicles_layout for the window size; the summary and help text are left out when the
    window is too small for them.
    """
    g = vehicles_layout(*surface.get_size(), len(vehicle_table_order(game)))
    _medium, _body, small, tiny = screen_fonts(surface.get_size())
    lh = tpx(LINE_H, g["k"])
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "VEHICLE MANAGEMENT", g["header"])

    if g["subtitle"]:
        sx, sy, sw, _sh = g["subtitle"]
        lines = (
            ("Select a vehicle to recover it or upgrade it (both need a Truck Stop, Repair Depot or Military Installation), or abandon it. Each needs one driver.",
             "Select a vehicle to recover, upgrade or abandon it. Each needs one driver."),
            ("SPD speed  HP health  PASS seats  CARGO storage  DEF defense  FCAP fuel capacity  FUSE fuel use",
             "SPD speed  HP health  PASS seats  DEF defense  FCAP fuel cap  FUSE fuel use"),
        )
        if g["subtitle_lines"] == 1:
            # Large / Extra large text in a window too short for two lines: one line with the shorter wording of both.
            merged = ("Select a vehicle to recover, upgrade or abandon it.  SPD speed  HP health  PASS seats  CARGO storage  DEF defense  FCAP fuel capacity  FUSE fuel use",
                      "Select a vehicle to recover, upgrade or abandon it.  SPD speed  HP health  PASS seats  DEF defense  FCAP fuel cap  FUSE fuel use",
                      "Select a vehicle to recover, upgrade or abandon.  SPD speed  HP health  PASS seats  DEF defense  FCAP fuel  FUSE fuel use")
            text_in_rect(surface, fit_variants(tiny, sw, merged), (sx, sy, sw, lh), MUTED, tiny)
        else:
            for i, variants in enumerate(lines):
                text_in_rect(surface, fit_variants(tiny, sw, variants), (sx, sy + i * lh, sw, lh), MUTED, tiny)

    totals = game.convoy_stats()
    if g["summary"]:
        _draw_summary(surface, game, g, totals, small, tiny)

    _draw_vehicle_table(surface, game, g)
    draw_vehicle_card(surface, game, g["card"])

    # The convoy travels as one, so the location is not shown here.
    selected = game.selected_vehicle_type
    owned_types = {vehicle.vehicle_type for vehicle in game.vehicles}
    stx, sty, stw, _sth = g["status"]
    text_in_rect(surface, f"Selected: {selected} | Scrap: {game.scrap}", (stx, sty, stw, lh), YELLOW, tiny)
    if selected in owned_types:
        if game.abandon_confirm == selected:
            color = RED
            variants = (f"Click CONFIRM ABANDON to give up the {selected}. No refund.", "Click CONFIRM ABANDON. No refund.")
        elif not game.can_upgrade_here():
            color = MUTED
            variants = ("Upgrades need a stop with a Truck Stop, Repair Depot or Military Installation.",
                        "Upgrade at a Truck Stop, Depot or Military Inst.", "Upgrade at a repair stop.")
        elif len(game.vehicles) <= 1:
            color = MUTED
            variants = ("Your last vehicle can't be abandoned.", "Can't abandon your last vehicle.")
        else:
            color = MUTED
            variants = ("Abandoned vehicles can be recovered later (no refund).", "Abandoned vehicles can be recovered later.")
    elif game.adult_count() <= len(game.vehicles):
        color = RED
        variants = ("No spare adult survivor to drive another vehicle.", "No spare adult driver.", "No spare driver.")
    elif game.can_recover_here():
        cost = game.recovery_price(selected)
        color = MUTED
        variants = (f"Recovery: {cost} scrap + 1 day; vehicle starts at 70% health.", f"Recovery: {cost} scrap + 1 day.")
    else:
        color = MUTED
        variants = ("Recover vehicles in a stop with a Truck Stop, Depot or Military Installation.",
                    "Needs a stop with a Truck Stop, Depot or Military Inst.")
    text_in_rect(surface, fit_variants(tiny, stw, variants), (stx, sty + lh + 2, stw, lh), color, tiny)
    for button in buttons:
        button.draw(surface, selected=(button.label == "CONFIRM ABANDON"))
