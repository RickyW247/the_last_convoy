"""THE LAST CONVOY — Prototype README
Version: 1.15

Development / versioning convention:
- For every update, increment the version number (e.g. 1.15 -> 1.16).
- Keep this README-style summary at the top of main.py updated to reflect current capabilities.
- Add a brief version-history entry for the update; avoid changing gameplay unless requested.
- Keep this README concise: when it grows long, summarize capabilities and older version history
  a bit, while retaining the most important information. Do this on every update without being asked.

Current capabilities:
- Playable Pygame survival prototype: a branching highway map with the Pacific Coast as the goal. The game
  opens on a title screen (logo, PLAY / MENU), then a lore screen, then START GAME begins the run.
- Map: main route Start, City 1-4, Pacific Coast. Dead-end side cities 5-8 branch off City 1-4.
  Mountain Pass bypasses City 3.
- Sites: every city holds three sites (SITES and NODES in map_data.py; the same site can exist in several
  cities). 18 site types: Gas Station, Supermarket, Truck Stop, Repair Depot, Farm, Hospital, Military
  Installation, Small Town, Diner, Hardware Store, Pharmacy, Warehouse, Water Tower, Auto Garage,
  Survivor Shelter, Police Station, plus the Open Highway and Mountain Pass.
- Travel: stops lie on a 0-560 km line. Horde gap = convoy position - horde position; westward travel
  widens it, eastward narrows it, and the horde advances daily. Travel time depends on road distance and
  the slowest vehicle; fuel use depends on road distance.
- Horde danger: Distant, Approaching, Close, Overrun (from the gap), shown on the HUD, event log and
  convoy-screen background as zombies. Routes into an overrun stop are blocked (red); possibly overrun
  routes are risky (orange), on both the map and minimap.
- Vehicles: eight types. Start with pickup truck, passenger van, school bus. Recover vehicles at any stop
  with a Truck Stop, Repair Depot or Military Installation, or abandon them.
- Combat: convoy health is the sum of vehicle health; ambushes damage every vehicle. REPAIR restores 25%
  of each vehicle's max health. Each defense point cuts ambush damage by 1% (cap 60%).
- Scavenging: searches one chosen site of the current stop (any number of times, one day each); survivors
  can be found at most sites. Cargo capacity limits food, water and scrap combined; fuel and passenger
  capacities are separate.
- Survival: daily use is 1 food per 5 survivors and 1 water per 4 (rounded up). Each vehicle needs a
  driver, so the rearmost vehicle is abandoned if survivors drop below the vehicle count. Running out
  of food or water makes one survivor leave daily.
- Screens: convoy (vehicles, minimap, action costs, event log), vehicle table with preview card, menu
  (Easy/Normal/Hard adjust consumption, horde speed and scavenging yields; opens the instructions screen).
- Travel events: after each arrival a weighted random event (10 in event_data.py) offers 2-3 choices with
  declarative effects on resources, survivors, vehicle health or the horde gap. A result screen shows the
  outcome and every change before returning to the convoy screen. Reaching the coast wins.
- Ending screen (win or loss): the reason the run ended, plus days survived, survivors left, stops visited,
  vehicles lost, distance travelled and difficulty; PLAY AGAIN or TITLE SCREEN.
- Pixel-art PNG assets in assets/; hand cursor over clickable buttons; headless tests in test_convoy.py.
- game.py (rules) and config.py (balance constants) do not depend on pygame.

Controls:
- Click a stop on the map (or press the left / right arrow to cycle the stops west / east of the convoy),
  then click TRAVEL (or press Enter).
- Convoy screen: SITE button (or Tab) chooses the site; SCAVENGE / REPAIR buttons (keys S / R); VEHICLES to inspect, recover or abandon
  (ABANDON needs a second click to confirm).
- During an event, click an option or press 1-4; a result screen then shows what happened (click OK or press Enter).
- Title and lore screens: ENTER (or the buttons) moves on; ESC goes back.
- M toggles map / convoy screen; O opens the menu (with INSTRUCTIONS); ESC goes back or quits; R / ENTER plays again after a win or loss.

Project files:
- main.py: window, input handling and main loop (run this file).
- game.py: Vehicle and Game classes, all gameplay rules.   config.py: balance constants, difficulties.
- theme.py: colours, fonts.   layout.py: screen size and coordinates.   widgets.py: Button and draw helpers.
- map_data.py: stops, roads, survivor finds, pathfinding.   map_system.py: map and minimap rendering.
- vehicles.py: vehicle specs, roles, recovery costs.   vehicle_rendering.py: PNG sprite loading and caching.
- buttons.py: builds each screen's buttons (no drawing).   ui.py: draws the screens.
- instructions_data.py: the player instructions text.   story_data.py: title tagline and lore text (edit here).
- event_data.py: event definitions (add new events here).   effect_handler.py: applies event effects.
- event_manager.py: weighted event selection, lifecycle and result.   event_ui.py: event overlay, result screen, buttons.
- test_convoy.py: automated tests (needs the game folder alongside it).
- assets/: vehicles/*.png, backgrounds/convoy_background.png, zombies/zombie.png.

Setup: python -m pip install pygame | Run: python main.py | Test: python test_convoy.py

Version history:
- 1.15: Map and sites: stops now hold several sites (every city has three, 18 site types); the dead-end stops
        became cities 5-8; map labels are all numbers (S start, C coast, P pass); arrow keys replace the 0-5
        hotkeys; scavenging picks one site (SITE button / Tab) and can be repeated.
        Screens: title screen (PLAY / MENU), lore screen, settings renamed MENU with a two-page INSTRUCTIONS
        screen, event result screen with OK, ending summary screen (run statistics, PLAY AGAIN / TITLE SCREEN).
        New files: instructions_data.py, story_data.py. Tests updated. Shortened this README and added the
        README-upkeep instructions.
- 1.14: Moved Vehicle and Game into game.py and balance constants into pygame-free config.py; split
        common.py into theme.py, layout.py and widgets.py; split map data and pathfinding into map_data.py;
        moved make_buttons into buttons.py (ui.py only draws); cached scaled sprites in ui.scaled_image;
        explicit imports everywhere; tests updated. Gameplay unchanged.
- 1.13: Fixed the coast victory check, event choices use the shared Button class with hand cursor, fixed
        vehicle sprite placement, removed unused procedural sprite data, added test_convoy.py.
- 1.12: Added modular weighted travel events, selectable choices and declarative effects.
- 1.11: Replaced procedural vehicle drawing with cached pixel-art PNG assets.
- 1.10: Improved code structure; fixed daily upkeep, damage checks and keyboard controls.
- 1.9:  Branching routes, distance-based horde mechanics, danger indicators, lower convoy panel, HUD.
- 1.8:  Minimap and lower panel, survivor finds at every stop, whole-number food/water use, overrun and
        risky warnings, vehicle table and preview card, fair cargo sharing.
- 1.7:  Current-stop scavenging, vehicle-based health, starvation, drivers, abandoning, defense,
        action costs, settings / difficulty.
- 1.1-1.6: Early prototype: vehicle definitions and management screen, vehicle recovery with scrap costs,
        relative travel distances and horde gap in km, enforced capacities, version label.
"""
import sys

import pygame

from buttons import make_buttons, make_end_buttons
from event_ui import (draw_event_overlay, draw_event_result_overlay, handle_event_click, handle_result_click,
                      make_event_buttons, make_result_buttons)
from game import Game
from layout import FPS, HEIGHT, ROW_H, ROW_Y0, TABLE_W, TABLE_X, WIDTH
from map_data import NODES
from map_system import draw_map
from theme import BG
from ui import (draw_end_overlay, draw_hud, draw_instructions_screen, draw_lore_screen, draw_lower, draw_menu_screen,
                draw_scene, draw_title_screen, draw_vehicles_screen)
from vehicles import VEHICLE_SPECS

pygame.init()

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Last Convoy — Prototype")
CLOCK = pygame.time.Clock()

game = Game()


def update_mouse_cursor(buttons):
    mouse_pos = pygame.mouse.get_pos()

    hovering = any(button.clicked(mouse_pos) for button in buttons)

    if hovering:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)


def main():
    running = True
    while running:
        CLOCK.tick(FPS)
        if game.screen != "vehicles":
            game.abandon_confirm = None  # leaving the vehicle screen cancels a pending abandon
        # While an event (or its result screen) is open, only its buttons are clickable, so only they get the hover cursor.
        if game.event_result:
            buttons = make_result_buttons(game.event_result)
        elif game.event_manager.active:
            buttons = make_event_buttons(game.event_manager.current_event)
        elif game.status != "playing":
            buttons = make_end_buttons(game)
        else:
            buttons = make_buttons(game)
        update_mouse_cursor(buttons)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif game.event_result:
                # The result of the chosen option: wait for OK (click, Enter, Space or ESC) before going on.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if handle_result_click(event.pos, game.event_result):
                        game.dismiss_event_result()
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                                    pygame.K_SPACE, pygame.K_ESCAPE):
                    game.dismiss_event_result()
            elif game.event_manager.active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    choice = handle_event_click(event.pos, game.event_manager.current_event)
                    if choice is not None:
                        game.resolve_event_choice(choice)
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    choice = event.key - pygame.K_1
                    if choice < len(game.event_manager.current_event["choices"]):
                        game.resolve_event_choice(choice)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.screen == "instructions":
                        game.screen = "menu"
                    elif game.screen == "menu":
                        game.close_menu()
                    elif game.screen == "lore":
                        game.screen = "title"
                    elif game.screen in ("map", "vehicles"):
                        game.screen = "convoy"
                    else:
                        running = False
                elif not game.started:
                    # Before the game starts: ENTER / SPACE moves on from the title and lore screens.
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        if game.screen == "title":
                            game.show_lore()
                        elif game.screen == "lore":
                            game.begin_game()
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and game.screen == "instructions":
                        game.turn_instructions_page(-1 if event.key == pygame.K_LEFT else 1)
                elif event.key == pygame.K_m and game.status == "playing":
                    game.screen = "map" if game.screen != "map" else "convoy"
                elif event.key == pygame.K_o and game.status == "playing":
                    if game.screen in ("menu", "instructions"):
                        game.close_menu()
                    else:
                        game.open_menu()
                elif game.status != "playing" and event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                    game.reset()
                elif game.status == "playing":
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        if game.screen == "instructions":
                            game.turn_instructions_page(-1 if event.key == pygame.K_LEFT else 1)
                        elif game.screen not in ("vehicles", "menu"):
                            game.cycle_destination(-1 if event.key == pygame.K_LEFT else 1)   # west / east
                    elif event.key == pygame.K_RETURN and game.screen not in ("vehicles", "menu", "instructions"):
                        game.travel()
                        if game.screen == "map":
                            game.screen = "convoy"
                    elif game.screen == "convoy":
                        if event.key == pygame.K_s:
                            game.scavenge()
                        elif event.key == pygame.K_r:
                            game.repair()
                        elif event.key == pygame.K_TAB:
                            game.cycle_site()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.status == "playing":
                    if game.screen == "vehicles":
                        mx, my = event.pos
                        if TABLE_X <= mx <= TABLE_X + TABLE_W and ROW_Y0 - 2 <= my < ROW_Y0 + ROW_H * len(VEHICLE_SPECS) - 2:
                            index = (my - ROW_Y0) // ROW_H
                            vehicle_names = list(VEHICLE_SPECS.keys())
                            if 0 <= index < len(vehicle_names):
                                if vehicle_names[index] != game.selected_vehicle_type:
                                    game.abandon_confirm = None  # picking another row cancels a pending abandon
                                game.selected_vehicle_type = vehicle_names[index]
                    if game.screen == "map":
                        for i, node in enumerate(NODES):
                            x, y = node["pos"]
                            if (event.pos[0] - x) ** 2 + (event.pos[1] - y) ** 2 <= 25 ** 2:
                                game.selected = i
                    buttons = make_buttons(game)
                    for button in buttons:
                        if button.clicked(event.pos):
                            button.action()
                            if game.screen == "map" and button.label == "TRAVEL":
                                game.screen = "convoy"
                            break
                else:
                    for button in make_end_buttons(game):   # victory / game over screen
                        if button.clicked(event.pos):
                            button.action()
                            break

        # Built after the events above, so the buttons match the screen that is about to be drawn.
        screen_buttons = make_buttons(game)
        SCREEN.fill(BG)
        if game.screen == "title":
            draw_title_screen(SCREEN, game, screen_buttons)
        elif game.screen == "lore":
            draw_lore_screen(SCREEN, game, screen_buttons)
        elif game.screen == "map":
            draw_map(SCREEN, game)
            draw_hud(SCREEN, game)
            # Draw map action buttons after the HUD.
            for button in screen_buttons:
                button.draw(SCREEN)
        elif game.screen == "vehicles":
            draw_vehicles_screen(SCREEN, game, screen_buttons)
            draw_hud(SCREEN, game)
        elif game.screen == "menu":
            draw_menu_screen(SCREEN, game, screen_buttons)
            draw_hud(SCREEN, game)
        elif game.screen == "instructions":
            draw_instructions_screen(SCREEN, game, screen_buttons)
            draw_hud(SCREEN, game)
        else:
            draw_hud(SCREEN, game)
            draw_scene(SCREEN, game)
            draw_lower(SCREEN, game, screen_buttons)
        if game.event_result:
            draw_event_result_overlay(SCREEN, game.event_result)
        elif game.event_manager.active:
            draw_event_overlay(SCREEN, game.event_manager.current_event)
        if not game.event_result:   # a win or loss caused by an event shows after its result screen
            draw_end_overlay(SCREEN, game, make_end_buttons(game))
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
