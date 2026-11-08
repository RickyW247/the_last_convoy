"""The vehicle upgrade screen of THE LAST CONVOY: the upgrades that fit the selected vehicle, what each costs and does,
and a card with the vehicle's picture and the change an upgrade makes. Drawing only (layout/upgrade.py places it).
"""
from functools import lru_cache

import pygame

from layout.geometry import LINE_H
from layout.upgrade import CELL_PAD, upgrade_card_layout, upgrade_layout, upgrade_row_at
from paging import upgrade_page
from textscale import text_k, tpx
from theme import BLUE, GREEN, MUTED, PANEL, PANEL_LIGHT, RED, ROAD, WHITE, YELLOW
from upgrade_data import describe_effects, get_upgrade, stat_changes
from widgets import (PIX, draw_frame, draw_heading, draw_panel, fit_variants, screen_fonts, text_in_rect,
                     wrap_pixels)

from .common import CARD_BG, SCREEN_BG, scaled_image
from .pixel_art import choose_pixel_scale
from .vehicle_rendering import get_rig_source, get_rig_sprite, get_vehicle_source, get_vehicle_sprite

ROW_HOVER_BG = (40, 60, 66)    # the same colours as the vehicles screen's table rows
ROW_SELECTED_BG = (46, 68, 74)
_HEADS = ("UPGRADE", "EFFECT", "COST")


@lru_cache(maxsize=16)
def _smooth_picture(name, trailer, size):
    """The sprite's full-resolution PNG (with its trailer, if any) shrunk smoothly to `size` (cached per sprite and size)."""
    return pygame.transform.smoothscale(get_rig_source(name, trailer) if trailer else get_vehicle_source(name), size)


def _hovered_row(surface, game, rows, page=0):
    """Index (in the whole list) of the table row under the mouse, or None (also None while a popup is open on top of the
    screen)."""
    if game.confirm_popup or game.event_result or game.event_manager.active or game.abandon_pick_needed():
        return None
    width, height = surface.get_size()
    return upgrade_row_at(width, height, pygame.mouse.get_pos(), rows, page)


def _draw_picture(surface, box, look, trailer=None):
    """The vehicle in a box on a stretch of road: the original PNG shrunk smoothly to fit (never enlarged), or the
    placeholder sprite at a whole-number scale when the PNG cannot be loaded (the same as the vehicles screen's card)."""
    pic = pygame.Rect(box)
    if pic.h < 28 or pic.w < 40:
        return
    draw_panel(surface, pic, (70, 99, 102), 0)
    road_h = min(30, pic.h // 3)
    pygame.draw.rect(surface, ROAD, (pic.x, pic.bottom - road_h, pic.w, road_h))
    room = (pic.w - 12, pic.h - 10)
    source = get_rig_source(look, trailer) if trailer else get_vehicle_source(look)
    if source is not None:
        fit = min(room[0] / source.get_width(), room[1] / source.get_height(), 1.0)
        size = (max(1, int(source.get_width() * fit)), max(1, int(source.get_height() * fit)))
        picture = _smooth_picture(look, trailer, size) if size != source.get_size() else source
    else:
        fine, coarse = get_rig_sprite(look, trailer), get_rig_sprite(look, trailer, coarse=True)
        index, scale = choose_pixel_scale([fine.get_size(), coarse.get_size()], room, (4, 4))
        sprite = (fine, coarse)[index]
        size = (max(1, int(sprite.get_width() * scale)), max(1, int(sprite.get_height() * scale)))
        picture = scaled_image(("vehicle", look, trailer, index), sprite, size)
    surface.blit(picture, (pic.centerx - size[0] // 2, pic.bottom - 6 - size[1]))


def _draw_card(surface, game, g, vehicle, upgrade, installed, fonts):
    """The card: the vehicle's name, its picture (as it will look with the highlighted upgrade, marked PREVIEW) and
    what the upgrade does."""
    _medium, font, small, tiny = fonts
    card = tuple(g["card"])
    k = g["k"]
    parts = upgrade_card_layout(card, k)
    lh = parts["line_h"]
    draw_panel(surface, card, CARD_BG, -1)
    draw_frame(surface, card, BLUE, 1 * PIX)
    draw_heading(surface, game.selected_vehicle_type, parts["name"], WHITE, (font, small, tiny))

    look = vehicle.sprite_type
    trailer = vehicle.trailer
    preview = bool(upgrade and (upgrade.get("look") or upgrade.get("trailer")) and not installed)
    if preview:
        look = upgrade.get("look") or look
        trailer = upgrade.get("trailer") or (None if upgrade.get("look") else trailer)
    _draw_picture(surface, parts["picture"], look, trailer)
    if preview:
        px, py = parts["picture"][0] + 6, parts["picture"][1] + 4
        text_in_rect(surface, "PREVIEW", (px, py, 70, lh), YELLOW, tiny)

    if upgrade is None:
        return
    tx, ty, tw, th = parts["text"]
    bottom = ty + th
    y = ty
    for line in wrap_pixels(f"{upgrade['category'].upper()}: {upgrade['blurb']}", tiny, tw):
        if y + lh > bottom:
            return
        text_in_rect(surface, line, (tx, y, tw, lh), MUTED, tiny)
        y += lh
    y += 2
    if installed:
        if y + lh <= bottom:
            text_in_rect(surface, "Installed.", (tx, y, tw, lh), GREEN, tiny)
        return
    for label, old, new in stat_changes(vehicle.stats, upgrade["effects"]):
        if y + lh > bottom:
            return
        text_in_rect(surface, f"{label} {old} -> {new}", (tx, y, tw, lh), WHITE, tiny)
        y += lh


def draw_upgrade_screen(surface, game, buttons):
    """Show the upgrades of the selected vehicle with their effects and costs, the card and the buttons. Reached with
    the vehicles screen's UPGRADE VEHICLE button; INSTALL UPGRADE buys the highlighted row, BACK returns."""
    size = surface.get_size()
    upgrades = game.available_upgrades()
    g = upgrade_layout(*size, len(upgrades))
    fonts = screen_fonts(size)
    _medium, _body, small, tiny = fonts
    k = text_k(*size)
    lh = tpx(LINE_H, k)
    vehicle = game.owned_vehicle(game.selected_vehicle_type)

    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, f"UPGRADE VEHICLE: {game.selected_vehicle_type.upper()}", g["header"])

    # The table: a heading row, then one row per upgrade that fits this vehicle.
    table = pygame.Rect(g["table"])
    header = pygame.Rect(g["table_header"])
    draw_panel(surface, header, PANEL_LIGHT, 1)
    columns = g["columns"]
    for (x, w), label in zip(columns, _HEADS):
        text_in_rect(surface, label, (x + CELL_PAD, header.y, w - 2 * CELL_PAD, header.h), WHITE, tiny)

    row_h = g["row_h"]
    font = small if small.get_linesize() <= row_h - 4 else tiny
    selected_id = game.selected_upgrade_id()
    page = upgrade_page(game, size)
    first = page * g["per_page"]
    hovered = _hovered_row(surface, game, len(upgrades), page)
    for number, upgrade in enumerate(upgrades[first:first + g["per_page"]]):   # one page of the table
        index = first + number
        installed = vehicle is not None and vehicle.has_upgrade(upgrade["id"])
        row = pygame.Rect(table.x, g["rows_top"] + number * row_h, table.w, row_h - 2)
        if upgrade["id"] == selected_id:
            draw_panel(surface, row, ROW_SELECTED_BG, 0)
            draw_frame(surface, row, BLUE, 1 * PIX)
        elif index == hovered:
            draw_panel(surface, row, ROW_HOVER_BG, 0)
            draw_frame(surface, row, MUTED, 1 * PIX)
        elif number % 2 == 0:
            draw_panel(surface, row, CARD_BG, -1)
        if installed:
            cost_text, cost_color = "INSTALLED", GREEN
        else:
            price = game.upgrade_price(upgrade)   # the catalogue cost, less for a Military background's military vehicle
            cost_text, cost_color = f"{price} scrap", (RED if game.scrap < price else WHITE)
        cells = ((upgrade["name"], MUTED if installed else WHITE),
                 (describe_effects(upgrade["effects"]), MUTED if installed else WHITE),
                 (cost_text, cost_color))
        for (x, w), (text, color) in zip(columns, cells):
            text_in_rect(surface, text, (x + CELL_PAD, row.y, w - 2 * CELL_PAD, row.h), color, font)

    if g["paged"]:   # the PREVIOUS / NEXT buttons are in `buttons`; the page number sits between them
        lx, ly, lw, lh_ = g["page_label"]
        text_in_rect(surface, fit_variants(tiny, lw, (f"Page {page + 1} / {g['pages']}", f"{page + 1}/{g['pages']}")),
                     (lx, ly, lw, lh_), MUTED, tiny, "center")

    upgrade = get_upgrade(selected_id) if selected_id else None
    price = game.upgrade_price(upgrade) if upgrade is not None else 0
    if vehicle is not None:
        installed_selected = upgrade is not None and vehicle.has_upgrade(upgrade["id"])
        _draw_card(surface, game, g, vehicle, upgrade, installed_selected, fonts)

    # Status lines: what is selected and what it costs, then why it cannot be installed (or that it can).
    stx, sty, stw, _sth = g["status"]
    if upgrade is not None:
        text_in_rect(surface, fit_variants(tiny, stw, (
            f"Selected: {upgrade['name']} ({upgrade['category']}), {price} scrap | Scrap: {game.scrap}",
            f"{upgrade['name']}: {price} scrap | Scrap: {game.scrap}", f"Scrap: {game.scrap}")),
            (stx, sty, stw, lh), YELLOW, tiny)
        problem = game.upgrade_problem(upgrade["id"])
        if problem == "Already installed.":   # it can come off again
            color, variants = MUTED, ("Installed. UNINSTALL UPGRADE removes it: free, no time.", "Installed. You can uninstall it.",
                                      "Installed.")
        elif problem:
            color, variants = (MUTED if problem == "Already installed." else RED), (problem, problem.split(" for ")[0] + ".")
            if problem.startswith("Uninstall the "):   # another trailer is on the vehicle
                variants = (problem, "Uninstall the other trailer first.", "One trailer only.")
            elif problem == game.UPGRADE_PLACE_MESSAGE:
                variants = (problem, "Needs a stop with a Truck Stop, Depot or Military Inst.", "Needs a repair stop.")
            elif problem == game.UPGRADE_ROAD_MESSAGE:
                variants = (problem, "Not on the road: wait until the convoy stops.", "Not on the road.")
        else:
            color = GREEN
            variants = ("Ready: press INSTALL UPGRADE. It takes a day.", "Press INSTALL UPGRADE (1 day).", "Ready.")
        text_in_rect(surface, fit_variants(tiny, stw, variants), (stx, sty + lh + 2, stw, lh), color, tiny)
    for button in buttons:
        button.draw(surface)
