"""Button construction for THE LAST CONVOY: which buttons each screen has, where they are, what they do and
when they are enabled. ui.py only draws the buttons it is given; main.py handles the clicks.
"""
from config import DIFFICULTY_ORDER, REPAIR_SCRAP_COST
from game import recovery_cost
from instructions_data import PAGE_COUNT
from layout import WIDTH
from map_data import SITES
from widgets import Button


# The ending screen's panel (x, y, width, height); ui.draw_end_overlay draws it and the buttons sit inside it.
END_PANEL = (WIDTH // 2 - 260, 70, 520, 540)


def make_end_buttons(game):
    """PLAY AGAIN and TITLE SCREEN on the victory / game over screen (none while the game is still running)."""
    if game.status == "playing":
        return []
    x, y, w, h = END_PANEL
    return [
        Button((x + w // 2 - 200, y + h - 80, 190, 46), "PLAY AGAIN [R]", game.reset),
        Button((x + w // 2 + 10, y + h - 80, 190, 46), "TITLE SCREEN", game.return_to_title),
    ]


def make_buttons(game):
    playing = game.status == "playing"
    if game.screen == "title":
        return [
            Button((WIDTH // 2 - 200, 480, 180, 50), "PLAY", game.show_lore),
            Button((WIDTH // 2 + 20, 480, 180, 50), "MENU", game.open_menu),
        ]
    if game.screen == "lore":
        return [
            Button((40, 600, 135, 40), "BACK", lambda: setattr(game, "screen", "title")),
            Button((WIDTH // 2 - 110, 600, 220, 46), "START GAME", game.begin_game),
        ]
    if game.screen == "map":
        trip = game.plan_trip()
        can_travel = playing and trip["km"] > 0 and game.fuel >= trip["fuel"] and game.travel_danger() != "overrun"
        return [
            Button((690, 600, 130, 42), "TRAVEL", game.travel, can_travel),
            Button((832, 600, 135, 42), "BACK", lambda: setattr(game, "screen", "convoy")),
        ]
    if game.screen == "vehicles":
        selected = game.selected_vehicle_type
        owned = game.owned_vehicle_types()
        selected_owned = selected in owned
        at_recovery_site = game.can_recover_here()
        has_driver = game.survivors > len(game.vehicles)
        cost = recovery_cost(selected)
        can_recover = playing and at_recovery_site and not selected_owned and has_driver and game.scrap >= cost
        can_abandon = playing and selected_owned and len(game.vehicles) > 1
        abandon_label = "CONFIRM ABANDON" if game.abandon_confirm == selected else "ABANDON VEHICLE"
        return [
            Button((535, 622, 160, 32), abandon_label, lambda: game.request_abandon(selected), can_abandon),
            Button((705, 622, 160, 32), "RECOVER VEHICLE", lambda: game.recover_vehicle(selected), can_recover),
            Button((875, 622, 90, 32), "BACK", lambda: setattr(game, "screen", "convoy")),
        ]
    if game.screen == "instructions":
        last = PAGE_COUNT - 1
        page = game.instructions_page
        return [
            Button((505, 615, 150, 40), "PREVIOUS PAGE", lambda: game.turn_instructions_page(-1), page > 0),
            Button((665, 615, 150, 40), "NEXT PAGE", lambda: game.turn_instructions_page(1), page < last),
            Button((830, 615, 135, 40), "BACK", lambda: setattr(game, "screen", "menu")),
        ]
    if game.screen == "menu":
        buttons = [
            Button((40 + i * 310 + 45, 420, 200, 40), name, lambda n=name: game.set_difficulty(n))
            for i, name in enumerate(DIFFICULTY_ORDER)
        ]
        buttons.append(Button((40, 600, 200, 40), "INSTRUCTIONS", game.open_instructions))
        buttons.append(Button((830, 600, 135, 40), "BACK", game.close_menu))
        return buttons
    # Convoy screen: one row of buttons. SITE chooses which site of this stop SCAVENGE searches (click to cycle).
    site = game.current_site()
    site_label = f"SITE: {SITES[site]['short']}" if site else "NO SITES HERE"
    return [
        Button((32, 448, 130, 36), "SCAVENGE", game.scavenge, playing and site is not None),
        Button((180, 448, 220, 36), site_label, game.cycle_site, playing and len(game.current_sites()) > 1),
        Button((418, 448, 110, 36), "REPAIR", game.repair, playing and game.scrap >= REPAIR_SCRAP_COST and game.needs_repair()),
        Button((546, 448, 120, 36), "VEHICLES", lambda: setattr(game, "screen", "vehicles"), playing),
        Button((684, 448, 120, 36), "MAP [M]", lambda: setattr(game, "screen", "map"), playing),
        Button((822, 448, 140, 36), "MENU [O]", game.open_menu, playing),
    ]
