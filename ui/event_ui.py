"""Pygame overlay and click handling for player-choice events.

The event and result popups are drawn straight onto the (already dimmed) window from layout.popup_layout, in real
window pixels: the panel is centred and sized from the window, text is wrapped by pixel width and fitted to its
rectangle, and the buttons come from the same layout. Mouse positions are raw window coordinates.
"""
import pygame

from widgets import PIX, draw_frame, draw_panel

from game.effect_handler import (affordable_flags, defended_loss, is_payment, resource_costs, shortfalls,
                            unmet_requirement_notes, vehicle_to_lose)
from layout import LINE_H, popup_layout
from textscale import tpx
from theme import GREEN, MEDIUM, MUTED, PANEL, RED, SMALL, TINY, WHITE, YELLOW
from widgets import (Button, draw_heading, draw_lines, ellipsize, fit_paragraph, fit_text, fit_variants, pick_font,
                     scaled_font, text_in_rect, text_ladder, wrap_pixels)


def _effect_notes(game, choice):
    """Notes for what a choice does beyond spending supplies, with the numbers the effects will really apply (defense
    already taken off): "-13% HP" (damage to every vehicle), "-2 survivors", "lose Pickup Truck" (the vehicle that
    would be given up), "new vehicle". Without a `game` the defense is not counted and no vehicle is named."""
    notes = []
    for effect in choice.get("effects", []) or []:
        kind = effect.get("type")
        amount = int(effect.get("amount", 0))
        if kind == "vehicle_damage_pct" and amount > 0:
            notes.append(f"-{max(1, defended_loss(game, amount, effect))}% HP")
        elif kind == "vehicle_damage" and amount > 0:
            notes.append(f"-{amount} HP each")
        elif kind == "survivors" and amount < 0:
            lost = defended_loss(game, -amount, effect)
            if lost:
                notes.append(f"-{lost} survivor" + ("" if lost == 1 else "s"))
        elif kind == "vehicle_loss":
            vehicle = vehicle_to_lose(game)
            notes.append(f"lose {vehicle.vehicle_type}" if vehicle else "lose a vehicle")
        elif kind == "vehicle_gain":
            notes.append("new vehicle")
        elif kind == "berths" and amount > 0:
            notes.append(f"+{amount} ship berths")
    return notes


def _choice_text(index, choice, game, flags):
    """(label, note) of a choice's button. A choice that spends supplies shows its cost, "[-3 scrap]", a penalty
    "[lose up to 5 fuel]"; what else it does is added (see _effect_notes). A choice the convoy cannot take (greyed out)
    shows what is missing instead: "[need 3 scrap, have 1]" or what it requires ("[needs 2+ vehicles]"). Without a
    `game` only the cost and the effects are shown."""
    label = f"{index + 1}.  {choice.get('label', 'Continue')}"
    costs = resource_costs(choice)
    parts = []
    if game is not None and not flags[index]:
        parts += unmet_requirement_notes(game, choice)
        if is_payment(choice):
            parts += [f"need {need} {field}, have {have}" for field, need, have in shortfalls(game, choice)]
    else:
        if costs and is_payment(choice):
            parts.append(", ".join(f"-{need} {field}" for field, need in costs.items()))
        elif costs:   # a penalty: always pickable, takes what the convoy has
            parts.append("lose up to " + ", ".join(f"{need} {field}" for field, need in costs.items()))
        parts += _effect_notes(game, choice)
    return label, ("  [" + "; ".join(parts) + "]") if parts else ""


def _flags(event, game):
    """Which choices can be picked (all of them when no `game` is given)."""
    choices = event.get("choices", [])
    return affordable_flags(game, choices) if game is not None else [True] * len(choices)


def _option_font(event, g, size, game=None):
    """The one font of the event popup's options: the largest of the window's text ladder in which every option (with its
    cost note) fits its button. The description never uses a bigger one, so the popup's text is one consistent size."""
    choices, flags = event.get("choices", []), _flags(event, game)
    labels = ["".join(_choice_text(i, c, game, flags)) for i, c in enumerate(choices)] or ["1.  Continue"]
    _x, _y, w, h = g["buttons"][0]
    return pick_font(text_ladder(size), labels, w - 16, h - 8)


def make_event_buttons(event, size, game=None):
    """Build one shared Button per choice, stacked at the bottom of the popup of a window of this size; each
    button's action returns its choice index. With a `game`, a choice the convoy cannot pay for is disabled (greyed out:
    no click, no focus) and says what is missing; where a label is too long the cost note is kept and the label cut."""
    choices = event.get("choices", [])
    g = popup_layout(int(size[0]), int(size[1]), "event", max(1, len(choices)))
    flags = _flags(event, game)
    font = _option_font(event, g, size, game)
    room = g["buttons"][0][2] - 8   # the width Button.draw gives its label
    buttons = []
    for i, choice in enumerate(choices):
        label, note = _choice_text(i, choice, game, flags)
        if note and font.size(label + note)[0] > room:
            label = fit_text(label, font, max(0, room - font.size(note)[0]))
        buttons.append(Button(g["buttons"][i], label + note, lambda index=i: index, flags[i], font=font))
    return buttons


def _draw_panel(surface, g):
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_frame(surface, g["panel"], YELLOW, 2 * PIX)


def draw_event_overlay(surface, event, buttons=None, game=None):
    """The event popup: title, the description (wrapped by pixel width, in the largest font that fits), a hint and
    the choice buttons. main.py dims the window behind it first. `buttons` are the frame's buttons (they carry the
    keyboard focus outline); they are built here (for `game`) when not given."""
    size = surface.get_size()
    if buttons is None:
        buttons = make_event_buttons(event, size, game)
    g = popup_layout(*size, "event", max(1, len(event.get("choices", []))))
    _draw_panel(surface, g)
    draw_heading(surface, event.get("title", "Unexpected Event"), g["title"], YELLOW, None, "center")

    bx, by, bw, bh = g["body"]
    option_font = buttons[0].font if buttons and buttons[0].font else _option_font(event, g, size, game)
    ladder = tuple(f for f in text_ladder(size) if f.get_linesize() <= option_font.get_linesize())
    font, lines = fit_paragraph(event.get("description", "Choose how the convoy should respond."),
                                ladder, bw, bh, line_gap=4)
    draw_lines(surface, lines, g["body"], font, WHITE, "center", 4)

    count = max(1, len(event.get("choices", [])))
    keys = f"1-{count}" if count > 1 else "1"
    tiny = scaled_font(size, 13)
    text_in_rect(surface, fit_variants(tiny, g["hint"][2], (
        f"{keys}: choose   |   Tab or arrows: move   |   ENTER: select",
        f"{keys}: choose | Tab: move | ENTER: select", f"{keys}: choose")),
        g["hint"], MUTED, tiny, "center")
    for button in buttons:
        button.draw(surface)


def make_result_buttons(result, size):
    """The single OK button on the result popup of a window of this size; its action returns True."""
    return [Button(popup_layout(int(size[0]), int(size[1]), "result")["buttons"][0], "OK [Enter]", lambda: True)]


def _plan_result(result, width, height, fonts=(MEDIUM, SMALL, TINY), line_h=LINE_H):
    """What fits the result popup's body: (font, [(text, colour, kind)]) with kind "chosen", "outcome", "heading",
    "change" or "more". The largest font in which everything fits is used; in the smallest one the result list is
    shortened to "+N more" and then the outcome text is cut with "...", so the cut is always visible."""
    chosen = result.get("choice")
    outcome = result.get("outcome") or "The convoy moves on."
    changes = list(result.get("changes", []))
    gap = 2
    for index, font in enumerate(fonts):
        step = font.get_linesize() + gap
        last = index == len(fonts) - 1
        out_lines = wrap_pixels(outcome, font, width)
        shown = [(text, GREEN if good else RED, "change") for text, good in changes] or \
                [("No lasting effect.", MUTED, "change")]
        head = [(f"You chose: {chosen}", MUTED, "chosen")] if chosen else []

        def total(out_n, change_items):
            extra = line_h + 6   # the RESULT heading and the space around it
            return (len(head) + out_n + len(change_items)) * step + extra

        if total(len(out_lines), shown) <= height:
            break
        if last:
            items = shown
            keep = len(items)
            while keep > 0 and total(len(out_lines), shown) > height:
                keep -= 1   # show one result less, and say how many are left out
                shown = items[:keep] + [(f"+{len(items) - keep} more", MUTED, "more")]
            while len(out_lines) > 1 and total(len(out_lines), shown) > height:
                out_lines = out_lines[:-1]
                out_lines[-1] = ellipsize(out_lines[-1], font, width)
    plan = head + [(line, WHITE, "outcome") for line in out_lines]
    plan.append(("RESULT", MUTED, "heading"))
    plan += shown
    return font, plan


def draw_event_result_overlay(surface, result, buttons=None):
    """Show what the chosen option did: the outcome text and every resource that changed. `buttons` are the
    frame's buttons (the OK button carries the focus outline); they are built here when not given."""
    size = surface.get_size()
    g = popup_layout(*size, "result")
    _draw_panel(surface, g)
    draw_heading(surface, result.get("title", "Event"), g["title"], YELLOW, None, "center")
    bx, by, bw, bh = g["body"]
    line_h = tpx(LINE_H, g["k"])
    font, plan = _plan_result(result, bw, bh, text_ladder(size), line_h)
    step = font.get_linesize() + 2
    y = by
    for text, color, kind in plan:
        if kind == "heading":
            y += 3
            text_in_rect(surface, text, (bx, y, bw, line_h), color, scaled_font(size, 13), "center")
            y += line_h + 3
        else:   # "chosen", "outcome", "change" and "more" lines are all drawn the same way
            text_in_rect(surface, text, (bx, y, bw, step), color, font, "center")
            y += step
    for button in (buttons if buttons is not None else make_result_buttons(result, size)):
        button.draw(surface)


def handle_result_click(pos, result, size):
    """True if the OK button on the result popup was clicked (`pos` is a window pixel)."""
    return any(button.clicked(pos) for button in make_result_buttons(result, size))


def handle_event_click(pos, event, size, game=None):
    """Return the index of the clicked choice, or None if no button was clicked (`pos` is a window pixel). A choice the
    convoy cannot pay for (disabled button) cannot be clicked."""
    for button in make_event_buttons(event, size, game):
        if button.clicked(pos):
            return button.action()
    return None
