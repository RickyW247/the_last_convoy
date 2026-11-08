"""The HUD of THE LAST CONVOY: the title / location / day block and a grid of stat cells (label + bar), laid out by
layout.hud_layout. Drawing only.

What the bars mean:
  FUEL        fuel carried / fuel capacity
  CONVOY HP   combined vehicle health / combined maximum (the bar changes colour like the vehicle bars)
  HORDE       the gap to the horde in km (a full bar is far away), with its danger state in words and colour
  CARGO       ONE bar shared by FOOD, WATER and SCRAP against the cargo capacity; the empty part is free space
  SURVIVORS   survivors / seats; when some are hungry, thirsty or injured the label also lists how many of each (orange,
              red as soon as one of them is starving / dehydrated / critical), as far as the cell is wide enough
"""
import pygame

from widgets import draw_panel

from config import HORDE_BAR_MAX_KM
from layout import calculate_layout, hud_layout
from textscale import tpx
from theme import (BLUE, GREEN, HORDE_STATE_COLORS, MUTED, ORANGE, PANEL, RED, TEXT_FONTS, TINY, TITLE, WHITE,
                   YELLOW)
from widgets import (Button, draw_bar, draw_segmented_bar, draw_text, fit_text, heading_fonts, scaled_font,
                     wrap_pixels)

# Cargo parts in bar order (left to right), with the colour of each.
CARGO_PARTS = (("food", "FOOD", "F", GREEN), ("water", "WATER", "W", BLUE), ("scrap", "SCRAP", "S", ORANGE))


LOW_FUEL_SHARE = 0.25   # fuel at or below this share of the convoy's fuel capacity is LOW
FUEL_WARNINGS = {"low": ("LOW FUEL", ORANGE), "none": ("NO FUEL", RED)}   # state -> (words, colour); "ok" has none


def fuel_state(fuel, capacity):
    """"none" with no fuel at all, "low" at or below LOW_FUEL_SHARE of the capacity, else "ok"."""
    if fuel <= 0:
        return "none"
    return "low" if fuel <= LOW_FUEL_SHARE * max(1, capacity) else "ok"


def health_color(health, maximum):
    """The colour of a health bar: the same limits as the vehicle bars on the convoy scene."""
    share = health / max(1, maximum)
    return GREEN if share >= 0.6 else (YELLOW if share >= 0.3 else RED)


_INFINITY = None


def infinity_sign():
    """The infinity sign for sandbox mode: the symbol when every text font has a glyph for it (a pixel font may not),
    otherwise the word INF, so it never shows as an empty box."""
    global _INFINITY
    if _INFINITY is None:
        try:
            has = all(font.metrics("\u221e")[0] is not None for font in TEXT_FONTS)
        except (pygame.error, TypeError, IndexError):
            has = False
        _INFINITY = "\u221e" if has else "INF"
    return _INFINITY


def _fuel_variants(v):
    """The fuel label: the numbers, plus LOW FUEL / NO FUEL in words and colour when the fuel is running out (the
    warning alone is the shortest variant, so it still shows in a narrow cell)."""
    warning = FUEL_WARNINGS.get(v.get("fuel_state", "ok"))
    if warning is None:
        return [[(f"FUEL {v['fuel']}/{v['fuel_cap']}", YELLOW)], [(f"FUEL {v['fuel']}", YELLOW)]]
    words, color = warning
    return [[(f"FUEL {v['fuel']}/{v['fuel_cap']}", color), (words, color)],
            [(f"FUEL {v['fuel']}", color), (words, color)],
            [(words, color)]]


def _labels(v):
    """The label of every cell, as variants from the fullest to the shortest. A variant is a list of
    (text, colour) pieces drawn one after the other; `v` holds the numbers (see _values and _worst_values)."""
    state_color = HORDE_STATE_COLORS[v["state"]]
    word = v["state"].upper()
    gap = v["gap"]
    hp_color = health_color(v["health"], v["max_health"])
    cargo = f"CARGO {v['used']}/{v['cargo']}"
    # Survivors: the plain wordings, preceded by longer ones that add the conditions when there are any (the label font is
    # chosen from the plain ones only, so a condition never makes the whole HUD's text smaller; if it does not fit, it is left out).
    survivor_variants = [[(f"SURVIVORS {v['survivors']}/{v['seats']}", WHITE)],
                         [(f"SURV {v['survivors']}/{v['seats']}", WHITE)], [(f"SURV {v['survivors']}", WHITE)],
                         [(f"{v['survivors']}/{v['seats']}", WHITE)]]
    needs = v.get("needs", ())
    if needs:
        survivor_variants = [
            [(f"SURVIVORS {v['survivors']}/{v['seats']}", WHITE)] + [(f"{long} {n}", color) for long, _s, n, color in needs],
            [(f"SURV {v['survivors']}/{v['seats']}", WHITE)] + [(f"{short}{n}", color) for _l, short, n, color in needs],
            [(f"SURV {v['survivors']}", WHITE)] + [(f"{short}{n}", color) for _l, short, n, color in needs],
        ] + survivor_variants
    parts = [(key, long, short, color, v[key]) for key, long, short, color in CARGO_PARTS]
    labels = {
        "fuel": (_fuel_variants(v), 1),
        "convoy": ([[(f"CONVOY HP {v['hp_pct']}%", hp_color)], [(f"HP {v['hp_pct']}%", hp_color)]], 1),
        # The danger state is always in words next to HORDE (colour is never the only signal).
        "horde": ([[(f"HORDE {gap} km {word}", state_color)], [(f"HORDE {gap}km {word}", state_color)],
                   [(f"HORDE {gap} {word}", state_color)], [(f"{gap}km {word}", state_color)],
                   [(f"{gap}km {word[:4]}", state_color)]], 1),
        "survivors": (survivor_variants, 1),
        # The total, then what it is made of in the colours of the bar's parts.
        "cargo": ([[(cargo, WHITE)] + [(f"{long} {n}", color) for _k, long, _s, color, n in parts],
                   [(cargo, WHITE)] + [(f"{short}{n}", color) for _k, _l, short, color, n in parts],
                   [(cargo, WHITE)], [(f"CARGO {v['used']}", WHITE)]], 2),
    }
    if v.get("sandbox"):   # sandbox mode: fuel and the cargo supplies never run out, so they show the infinity sign
        inf = infinity_sign()
        labels["fuel"] = ([[(f"FUEL {inf}", YELLOW)]], 1)
        labels["cargo"] = ([[(f"CARGO {inf}", WHITE)] + [(f"{long} {inf}", color) for _k, long, _s, color, _n in parts],
                            [(f"CARGO {inf}", WHITE)] + [(f"{short}{inf}", color) for _k, _l, short, color, _n in parts],
                            [(f"CARGO {inf}", WHITE)]], 2)
    return labels


def _needs(game):
    """[(WORD, letter, number of survivors, colour)] for every condition that affects somebody: hungry (starving too),
    thirsty (dehydrated too) and injured (critical too). Orange, red when any of them is in the worst stage."""
    report = game.condition_report()
    needs = []
    for word, letter, mild, severe in (("HUNGRY", "H", "hungry", "starving"), ("THIRSTY", "T", "thirsty", "dehydrated"),
                                       ("INJURED", "I", "injured", "critical")):
        total = report[mild] + report[severe]
        if total:
            needs.append((word, letter, total, RED if report[severe] else ORANGE))
    return needs


def _values(game, totals):
    """The numbers the labels and bars show right now."""
    return {
        "needs": _needs(game),
        "fuel": game.fuel, "fuel_cap": totals["fuel_capacity"],
        "fuel_state": fuel_state(game.fuel, totals["fuel_capacity"]),
        "health": totals["health"], "max_health": totals["max_health"], "hp_pct": game.convoy_health_pct(),
        "gap": game.horde, "state": game.horde_state(),
        "survivors": game.survivors, "seats": totals["passengers"],
        "food": game.food, "water": game.water, "scrap": game.scrap, "used": game.cargo_used(),
        "cargo": totals["cargo"],
        "sandbox": getattr(game, "sandbox", False),
    }


def _worst_values():
    """The widest numbers and the longest danger word any label can show. The label font is chosen from these, so the
    text does not change size while the numbers and the danger state change during play."""
    return {
        "fuel": 999, "fuel_cap": 999, "health": 1, "max_health": 1, "hp_pct": 100, "gap": 999,
        "state": "Approaching", "survivors": 99, "seats": 99, "food": 999, "water": 999, "scrap": 999,
        "used": 999, "cargo": 999,
    }


def _width(font, pieces, gap_chars):
    gap = font.size(" " * gap_chars)[0]
    return sum(font.size(text)[0] for text, _color in pieces) + gap * (len(pieces) - 1)


def _pick(font, width, variants, gap_chars):
    """The fullest variant that fits `width`; the shortest when none does (it is then cut with fit_text)."""
    for pieces in variants:
        if _width(font, pieces, gap_chars) <= width:
            return pieces
    return variants[-1]


def _draw_label(surface, font, rect, pieces, gap_chars):
    x, y, width, _height = rect
    if len(pieces) == 1:
        text, color = pieces[0]
        draw_text(surface, fit_text(text, font, width), x, y, color, font)
        return
    gap = font.size(" " * gap_chars)[0]
    for text, color in pieces:
        draw_text(surface, text, x, y, color, font)
        x += font.size(text)[0] + gap


def _draw_identity(surface, game, layout, parts, fonts):
    """Title, location and day, on the left. Rows are stacked by measured font height.

    The location and the day are what the player needs, so they keep the size the text-size setting gives them; the
    title is what gives way. The title follows the same ladder as every other heading (widgets.heading_fonts), so it
    grows and shrinks with the text-size setting in a wide window exactly as it does in a normal one. The title is the last
    thing to go: the largest title that fits (never smaller than the location) is tried with the location on one line
    and then on two, first with the location and day at full size, then with the day a step smaller, then the location
    too; only if none fits is the title dropped (the title screen already shows it) and the same pairs tried again. If nothing fits, the last resort cuts the location with "..."."""
    tiny, small, body = fonts
    window = surface.get_size()
    _hx, hy, _hw, hh = layout["hud"]
    k = layout["k"]
    x, _y, width, _h = parts["identity"]
    margin, gap = tpx(6, k), tpx(4, k)
    room = hh - 2 * margin

    title = "THE LAST CONVOY"
    location = f"LOCATION: {game.current_location}"
    day = f"DAY {game.day}"

    def height(title_font, loc_font, loc_lines, day_font):
        rows = ([title_font.get_linesize()] if title_font is not None else []) \
            + [loc_font.get_linesize()] * loc_lines + [day_font.get_linesize()]
        return sum(rows) + gap * (len(rows) - 1)

    title_ladder = [f for f in heading_fonts(window) if f.size(title)[0] <= width]
    pairs = ((small, body), (small, small), (tiny, small), (tiny, tiny))   # (location font, day font), largest first
    chosen = None   # (title font or None, location font, location lines, day font)
    # The title is kept as long as any combination fits: first with the location and day at full size, then with the
    # day one step smaller, then the location too; only when none fits with a title is it dropped (same pairs again).
    for with_title in (True, False):
        for loc_font, day_font in pairs:
            titles = [f for f in title_ladder if f.get_linesize() >= loc_font.get_linesize()] if with_title else [None]
            for max_lines in (1, 2):   # the whole location on one line, else wrapped onto a second
                lines = wrap_pixels(location, loc_font, width)
                if len(lines) > max_lines or any(loc_font.size(line)[0] > width for line in lines):
                    continue
                chosen = next(((t, loc_font, lines, day_font) for t in titles
                               if height(t, loc_font, len(lines), day_font) <= room), None)
                if chosen:
                    break
            if chosen:
                break
        if chosen:
            break

    y = hy + margin
    if chosen is None:
        # Nothing fits whole: the smallest fonts, location and day sharing one line when two rows do not fit, the
        # location cut so the day always shows.
        if TINY.get_linesize() * 2 + gap > room:
            day_w = TINY.size("  " + day)[0]
            draw_text(surface, fit_text(location, TINY, max(1, width - day_w)), x, y, MUTED, TINY)
            draw_text(surface, day, x + width - TINY.size(day)[0], y, YELLOW, TINY)
            return
        draw_text(surface, fit_text(location, TINY, width), x, y, MUTED, TINY)
        draw_text(surface, day, x, y + TINY.get_linesize() + gap, YELLOW, TINY)
        return

    title_font, loc_font, loc_lines, day_font = chosen
    if title_font is not None:
        draw_text(surface, title, x, y, WHITE, title_font)
        y += title_font.get_linesize() + gap
    for line in loc_lines:
        draw_text(surface, fit_text(line, loc_font, width), x, y, MUTED, loc_font)
        y += loc_font.get_linesize() + gap
    draw_text(surface, day, x, y, YELLOW, day_font)


def draw_hud(surface, game, layout=None, menu_button=None):
    if not getattr(game, "started", True):
        return   # no run yet (the pause menu opened from the title screen): there is nothing for a HUD to show
    if layout is None:
        layout = calculate_layout(*surface.get_size())

    hx, hy, hw, hh = layout["hud"]
    mx, my, mw, mh = layout["menu"]
    window = surface.get_size()
    tiny, small, body = scaled_font(window, 13), scaled_font(window, 15), scaled_font(window, 19)   # the text ladder

    totals = game.convoy_stats()
    parts = hud_layout(layout)
    cells = parts["cells"]

    draw_panel(surface, (hx, hy, hw, hh), PANEL, 1)
    _draw_identity(surface, game, layout, parts, (tiny, small, body))

    # One label size for every cell: the largest rung in which the fullest wording of every cell fits at its widest.
    worst = _labels(_worst_values())
    label_fonts = [scaled_font(window, base) for base in (15, 14, 13, 12, 11)]   # descending, in-between sizes included
    label_font = label_fonts[-1]
    for font in label_fonts:
        if all(_width(font, variants[0], gap) <= cells[name]["label"][2] for name, (variants, gap) in worst.items()):
            label_font = font
            break

    values = _values(game, totals)
    for name, (variants, gap) in _labels(values).items():
        cell = cells[name]
        _draw_label(surface, label_font, cell["label"], _pick(label_font, cell["label"][2], variants, gap), gap)

        bx, by, bw, bh = cell["bar"]
        if name == "fuel":
            warning = FUEL_WARNINGS.get(values["fuel_state"])
            draw_bar(surface, bx, by, bw, bh, game.fuel, max(1, totals["fuel_capacity"]),
                     warning[1] if warning else YELLOW)   # the bar takes the warning colour too
        elif name == "convoy":
            draw_bar(surface, bx, by, bw, bh, totals["health"], max(1, totals["max_health"]),
                     health_color(totals["health"], totals["max_health"]))
        elif name == "horde":
            draw_bar(surface, bx, by, bw, bh, game.horde, HORDE_BAR_MAX_KM, HORDE_STATE_COLORS[values["state"]])
        elif name == "survivors":
            draw_bar(surface, bx, by, bw, bh, game.survivors, max(1, totals["passengers"]), WHITE)
        elif name == "cargo":
            # Food, water and scrap share the cargo space, so they share one bar: its length is the capacity.
            segments = [(getattr(game, key), color) for key, _long, _short, color in CARGO_PARTS]
            if values["sandbox"]:   # unlimited: the bar is full, in three equal parts
                draw_segmented_bar(surface, bx, by, bw, bh, [(1, color) for _v, color in segments], 3)
            else:
                draw_segmented_bar(surface, bx, by, bw, bh, segments, max(1, totals["cargo"]))

    if menu_button is None:
        menu_button = Button(
            (mx, my, mw, mh),
            "MENU",
            game.open_menu,
            game.status == "playing",
        )

    menu_button.draw(surface)
