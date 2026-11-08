"""The "which vehicles to abandon?" popup of THE LAST CONVOY (a convoy with more vehicles than adults to drive them).
All the vehicles that must go are ticked in this one popup. Drawing only; the rules are Game.abandon_pick_needed /
abandon_need / select_abandon / abandon_ready / abandon_picked_vehicle (game/convoy.py)."""
from layout.popups import abandon_popup_layout
from textscale import text_k
from theme import HEAD_FONTS, MUTED, PANEL, WHITE, YELLOW
from widgets import (PIX, draw_frame, draw_heading, draw_lines, draw_panel, fit_paragraph, fit_variants, screen_fonts,
                     text_in_rect)


def _details(vehicle, suggested):
    """The figures shown beside a vehicle's button, longest variant first (the popup picks the one that fits)."""
    s = vehicle.stats
    health = f"{vehicle.health}/{s['health']}"
    # The suggested mark goes at the START of every variant, so it survives whichever variant fits the row.
    long_mark, short_mark = ("SUGGESTED: ", "* ") if suggested else ("", "")
    return (
        f"{long_mark}Seats {s['passengers']}  Cargo {s['cargo']}  Defense {s['defense']}  Fuel {s['fuel_capacity']}  HP {health}",
        f"{short_mark}Seats {s['passengers']} Cargo {s['cargo']} Def {s['defense']} Fuel {s['fuel_capacity']} HP {health}",
        f"{short_mark}S{s['passengers']} C{s['cargo']} D{s['defense']} F{s['fuel_capacity']} HP {health}",
    )


def draw_abandon_popup(surface, game, buttons):
    """The popup drawn straight onto the (already dimmed) window from abandon_popup_layout; `buttons` are one per
    vehicle, then ABANDON. The highlighted vehicle's button is drawn pressed in. Nothing is drawn while no vehicle has
    to be given up."""
    if not buttons or not game.abandon_pick_needed():
        return
    vehicles = game.vehicles
    size = surface.get_size()
    g = abandon_popup_layout(*size, len(vehicles))
    medium, body, small, tiny = screen_fonts(size)   # follow the text-size setting, like the layout's rows
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_frame(surface, g["panel"], YELLOW, 2 * PIX)

    draw_heading(surface, "ABANDON A VEHICLE" if game.abandon_need() == 1 else "ABANDON VEHICLES", g["title"], YELLOW,
                 HEAD_FONTS if text_k(*size) <= 1.0 else None, "center")

    # Kept short so it fits the message area at every window size (the long wording was cut off after "Choose 1 to leav").
    need = game.abandon_need()
    picked = set(game.abandon_marked_indices())
    suggested = set(game.suggested_abandon_indices())
    message = ("Not enough adult drivers. Pick 1 vehicle to leave behind." if need == 1 else
               f"Not enough adult drivers. Pick {need} vehicles to leave behind ({len(picked)}/{need}).")
    mx, my, mw, mh = g["message"]
    font, lines = fit_paragraph(message, (body, medium, small, tiny), mw, mh, line_gap=2)
    draw_lines(surface, lines, (mx, my, mw, mh), font, WHITE, "center", 2)

    for i, vehicle in enumerate(vehicles):
        buttons[i].draw(surface, selected=(i in picked))
        rect = g["details"][i]
        text = fit_variants(tiny, rect[2], _details(vehicle, i in suggested))
        text_in_rect(surface, text, rect, YELLOW if i in picked else WHITE, tiny, "left")
    buttons[len(vehicles)].draw(surface)

    text_in_rect(surface, fit_variants(tiny, g["hint"][2], (
        "1-9 / Up / Down + SPACE: tick vehicles   |   ENTER on ABANDON: confirm   |   * = suggested",
        "1-9 / Up / Down, SPACE: tick | ENTER: abandon | * suggested",
        "SPACE: tick | ENTER")), g["hint"], MUTED, tiny, "center")
