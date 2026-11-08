"""The paged list screens of THE LAST CONVOY: survivors (table) and missions (cards). Drawing only."""
import pygame

from widgets import PIX, draw_frame, draw_panel

from .common import CARD_BG, SCREEN_BG
from paging import filtered_missions
from layout import LINE_H, MISSION_LINE_H, missions_layout, page_count, survivors_layout
from map_data import NODES
from textscale import tpx
from theme import BLUE, GREEN, MUTED, ORANGE, PANEL, RED, WHITE, YELLOW
from widgets import draw_heading, fit_variants, pick_font, scaled_font, text_in_rect, text_ladder


def _no_manager(surface, message, rect, buttons, k=1.0):
    """The 'manager is not connected' notice, with the screen's buttons."""
    small = scaled_font(surface.get_size(), 15)
    text_in_rect(surface, message, (rect[0], rect[1], rect[2], tpx(LINE_H, k) + 6), YELLOW, small)
    for button in buttons:
        button.draw(surface)


def _draw_conditions(surface, game, cells, font):
    """The row of three cells under the subtitle: how many survivors are in each stage of hunger, thirst and injury
    (game.condition_report). The conditions overlap, so the numbers do not have to add up to the total. A cell is
    red when anyone is in its worst stage, orange when anyone is in the mild one, muted when nobody is affected."""
    report = game.condition_report()
    rows = (("HUNGER", "hungry", "starving"), ("THIRST", "thirsty", "dehydrated"), ("INJURY", "injured", "critical"))
    for cell, (title, mild, severe) in zip(cells, rows):
        a, b = report[mild], report[severe]
        color = RED if b else ORANGE if a else MUTED
        variants = (f"{title}  {a} {mild}, {b} {severe}", f"{a} {mild}, {b} {severe}", f"{mild.title()} {a} / {severe.title()} {b}",
                    f"{a} / {b}")
        text_in_rect(surface, fit_variants(font, cell[2], variants), cell, color, font)


def draw_survivors_screen(surface, game, buttons):
    """The convoy's survivors as a paged table. Rows per page, columns and footer come from survivors_layout, so
    the page numbers always match the rows on screen. The page is shown clamped (buttons.clamp_pages stores it)."""
    g = survivors_layout(*surface.get_size())
    tiny, small = scaled_font(surface.get_size(), 13), scaled_font(surface.get_size(), 15)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "SURVIVORS", g["header"])
    sx, sy, sw, _sh = g["subtitle"]
    text_in_rect(surface, fit_variants(tiny, sw, ("People travelling with your convoy.", "Your convoy's people.")),
                  g["subtitle"], MUTED, tiny)

    manager = getattr(game, "survivor_manager", None)
    if manager is None:
        _no_manager(surface, "Survivor manager is not connected.", g["list"], buttons, g["k"])
        return

    survivors = manager.get_survivors()
    total_text = fit_variants(small, g["total"][2], (f"TOTAL SURVIVORS: {len(survivors)}", f"TOTAL: {len(survivors)}"))
    text_in_rect(surface, total_text, g["total"], GREEN, small, "right")

    _draw_conditions(surface, game, g["conditions"], tiny)

    draw_panel(surface, g["list"], CARD_BG, -1)
    per_page = g["per_page"]
    pages = page_count(len(survivors), per_page)
    page = max(0, min(getattr(game, "survivor_page", 0), pages - 1))
    start = page * per_page
    page_survivors = survivors[start:start + per_page]

    hx, hy, hw, hh = g["heading"]
    columns = g["columns"]
    for (x, w), label in zip(columns, ("NAME", "GENDER", "AGE", "VEHICLE")):
        text_in_rect(surface, label, (x + 4, hy, w - 8, hh), GREEN, tiny)
    pygame.draw.line(surface, (70, 82, 86), (hx, hy + hh), (hx + hw, hy + hh), 1)

    survivor_vehicles = getattr(game, "survivor_vehicles", {})
    rows = []
    for survivor in page_survivors:
        name = (f"{survivor.get('first_name', 'Unknown')} {survivor.get('last_name', '')}").strip()
        vehicle = survivor_vehicles.get(survivor["id"], "Unassigned")
        rows.append((str(name), str(survivor.get("gender", "Unknown")), str(survivor.get("age", "?")), str(vehicle)))

    row_h = g["row_h"]
    # The largest font of the window's text ladder in which every cell on this page fits its column and the row.
    font = next((f for f in text_ladder(surface.get_size())
                 if f.get_linesize() <= row_h - 4
                 and all(f.size(cell)[0] <= w - 8 for row in rows for cell, (_x, w) in zip(row, columns))), tiny)
    for i, (row, survivor) in enumerate(zip(rows, page_survivors)):
        y = g["rows_top"] + i * row_h
        band = pygame.Rect(g["list"][0] + 3, y, g["list"][2] - 6, row_h - 2)
        if i % 2 == 0:
            draw_panel(surface, band, (38, 49, 51), 0)
        unassigned = row[3] == "Unassigned"
        colors = (WHITE, MUTED, MUTED, MUTED if unassigned else GREEN)
        for (x, w), cell, color in zip(columns, row, colors):
            text_in_rect(surface, cell, (x + 4, y, w - 8, row_h - 2), color, font)

    shown = f"Showing {start + 1 if survivors else 0}-{start + len(page_survivors)} of {len(survivors)}"
    text_in_rect(surface, fit_variants(tiny, g["showing"][2], (shown, f"{start + 1 if survivors else 0}-"
                                                                  f"{start + len(page_survivors)}/{len(survivors)}")),
                  g["showing"], MUTED, tiny)
    text_in_rect(surface, f"PAGE {page + 1}/{pages}", g["page"], WHITE, tiny, "right")
    for button in buttons:
        button.draw(surface)


_STATUS_COLORS = {
    "Available": GREEN,
    "Active": YELLOW,
    "Completed": BLUE,
    "Locked": MUTED,
    "Failed": (220, 90, 90),
    "Abandoned": MUTED,
}


def _objective_lines(state):
    """[(text, colour)] for each objective of a mission, plus how many are completed."""
    objectives = state["data"].get("objectives", [])
    progress = state.get("progress", [])
    lines, done = [], 0
    for j, objective in enumerate(objectives):
        current = progress[j] if j < len(progress) else 0
        target = objective.get("target", 1)
        if current >= target:
            done += 1
        objective_type = objective.get("type", "objective")
        if objective_type == "collection":
            description = f"Collect {objective.get('resource', 'resources').title()}"
        elif objective_type == "destination":
            stop_id = objective.get("stop_id")
            # An objective's own description wins: min_axis / stop_ids objectives have no single stop to name.
            description = objective.get("description") or (
                f"Reach {NODES[stop_id]['name']}"
                if isinstance(stop_id, int) and 0 <= stop_id < len(NODES) else "Reach destination")
        elif objective_type == "rescue":
            description = "Recruit survivors"
        elif objective_type == "stockpile":
            # A level, not a running total: "Hold 40 fuel: 12/40" (it can fall again while the mission is open).
            description = objective.get("description") or f"Hold {objective.get('resource', 'supplies')}"
        else:
            description = objective.get("description", objective.get("type", "Objective").replace("_", " ").title())
        lines.append((f"{description}: {current}/{target}", GREEN if current >= target else MUTED))
    return lines, done


def _unfinished_prerequisites(manager, state):
    """Titles of the prerequisite missions a locked mission still waits for (empty for any other mission)."""
    if state["status"] != "Locked":
        return []
    pending = []
    for prerequisite in state["data"].get("prerequisites", []):
        other = manager.missions.get(prerequisite)
        if other is None:
            pending.append(str(prerequisite))
        elif other["status"] != "Completed":
            pending.append(str(other["data"].get("title", prerequisite)))
    return pending


def draw_mission_card(surface, mission_id, state, card, parts, tiny, small, k, locked_hint=None):
    """One mission card: title and status on the top row, the objectives (as many as fit; the rest become
    "+N more"), "Objectives: a/b" and the ACCEPT / ABANDON button (drawn by the screen) at the bottom.
    A locked mission has no button, so locked_hint (the titles of the prerequisites still to finish) takes its place."""
    status = state["status"]
    color = _STATUS_COLORS.get(status, WHITE)
    draw_panel(surface, card, (38, 49, 51), 0)
    draw_frame(surface, card, color, 1 * PIX)

    title = str(state["data"].get("title", mission_id))
    tx, ty, tw, th = parts["title"]
    stage, stage_count = state["data"].get("stage"), state["data"].get("stage_count")
    if stage and stage_count:   # a multi-stage mission shows which stage is current
        variants = (f"{title} - Stage {stage}/{stage_count}", f"{title} ({stage}/{stage_count})", title)
        title_font = small
        title_text = fit_variants(small, tw, variants)
        if small.size(title_text)[0] > tw:
            title_font = tiny
            title_text = fit_variants(tiny, tw, variants)
    else:
        title_font = pick_font((small, tiny), [title], tw, th)
        title_text = title
    text_in_rect(surface, title_text, parts["title"], WHITE, title_font)
    status_font = pick_font((small, tiny), [status.upper()], parts["status"][2], parts["status"][3])
    text_in_rect(surface, status.upper(), parts["status"], color, status_font, "right")

    lines, done = _objective_lines(state)
    ox, oy, ow, oh = parts["objectives"]
    room = parts["lines"]
    line_h = tpx(MISSION_LINE_H, k)
    if not lines:
        shown = [("No objectives", MUTED)]
    elif len(lines) <= room:
        shown = lines
    elif room >= 2:
        shown = lines[:room - 1] + [(f"+{len(lines) - (room - 1)} more", MUTED)]
    else:
        shown = lines[:1]
    # Objective lines, the counter and the prerequisite hint use the larger font (small) whenever it fits its row;
    # one font for all the objective lines of the card so they line up.
    line_font = pick_font((small, tiny), [t for t, _c in shown], ow, line_h)
    for i, (text_line, line_color) in enumerate(shown[:max(1, room)]):
        text_in_rect(surface, text_line, (ox, oy + i * line_h, ow, line_h), line_color, line_font)
    fx, fy, fw, fh = parts["footer"]
    counter = f"Objectives: {done}/{len(lines)}"
    counter_font = pick_font((small, tiny), [counter], fw, fh)
    if lines:
        text_in_rect(surface, counter, parts["footer"], WHITE, counter_font)
    if status == "Locked" and locked_hint:
        names = ", ".join(locked_hint)
        bx, by, bw, bh = parts["button"]
        # No button on a locked card, so the hint may use the footer row from the end of the counter to the card's
        # right edge (not just the button's width).
        start = fx + (counter_font.size(counter)[0] + tpx(12, k) if lines else 0)
        hint_rect = (start, by, max(1, bx + bw - start), bh)
        variants = (f"Requires: {names}", f"Needs: {names}", names)
        hint_font = small if any(small.size(v)[0] <= hint_rect[2] for v in variants) else tiny
        text_in_rect(surface, fit_variants(hint_font, hint_rect[2], variants), hint_rect, YELLOW, hint_font, "right")


def draw_missions_screen(surface, game, buttons):
    """Missions as paged cards. The cards per page and every part of a card come from missions_layout."""
    g = missions_layout(*surface.get_size())
    k = g["k"]
    tiny, small = scaled_font(surface.get_size(), 13), scaled_font(surface.get_size(), 15)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "MISSIONS", g["title"])
    text_in_rect(surface, fit_variants(tiny, g["subtitle"][2], (
        "Review objectives, track progress, and accept missions.", "Review objectives and accept missions.")),
        g["subtitle"], MUTED, tiny)

    manager = getattr(game, "mission_manager", None)
    if manager is None:
        _no_manager(surface, "Mission manager is not connected.", g["list"], buttons, g["k"])
        return

    missions = filtered_missions(game)
    draw_panel(surface, g["list"], CARD_BG, -1)
    per_page = g["per_page"]
    pages = page_count(len(missions), per_page)
    page = max(0, min(game.mission_page, pages - 1))
    if not missions:
        x, y, w, _h = g["cards"][0]
        text_in_rect(surface, "No missions have been defined.", (x + 8, y, w - 16, tpx(28, k)), MUTED, small)
    else:
        page_missions = missions[page * per_page:(page + 1) * per_page]
        for (mission_id, state), card, parts in zip(page_missions, g["cards"], g["card_parts"]):
            draw_mission_card(surface, mission_id, state, card, parts, tiny, small, k,
                              _unfinished_prerequisites(manager, state))

    text_in_rect(surface, f"PAGE {page + 1}/{pages}", g["footer"], WHITE, tiny, "center")
    current = {"Active": "OPEN", "Completed": "COMPLETED"}.get(game.mission_filter)
    for button in buttons:
        button.draw(surface, selected=button.label == current)   # the open tab is drawn highlighted
