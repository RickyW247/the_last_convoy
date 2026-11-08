"""Button construction for THE LAST CONVOY: which buttons each screen has, where they are, what they do and
when they are enabled. The ui package only draws the buttons it is given; main.py handles the clicks.

Every screen takes its button rectangles from the live window layout (the layout package), so the buttons match what
the ui package draws at any window size. make_buttons only builds buttons: it never changes the game. The survivors,
missions and vehicles page numbers are kept valid by paging.clamp_pages(), which main.py calls once per frame (the only
place that writes them).
"""
import webbrowser

import pygame

import savegame
import settings_store
import theme
from platform_web import IS_WEB, open_url
from background_data import BACKGROUND_ORDER
from config import DIFFICULTY_ORDER
from credits_items import credits_items, credits_page_count, credits_page_index, turn_credits_page
from instructions_data import PAGE_COUNT
from ui.history import history_max_scroll, history_page_rows
from ui.convoy import convoy_scroll_state, scene_rect, scroll_arrow_rects, scroll_convoy
from layout import (
    END_STAT_ROWS, WIDTH, HEIGHT, calculate_layout, confirm_popup_layout, credits_layout, difficulty_layout, fit_ratio,
    history_layout, instructions_layout,
    lore_layout, map_layout, menu_layout, missions_layout, page_count, popup_layout, settings_layout,
    site_popup_layout, survivors_layout, title_layout, vehicles_layout,
)
from layout.popups import abandon_popup_layout, confirm_body_lines
from layout.backgrounds import background_layout   # the background screen (after the lore screen)
from layout.vehicles import vehicles_buttons   # the vehicles screen's button row, with room for RECOVER ALL
from layout.upgrade import upgrade_layout   # the upgrade screen's layout lives in its own module too   # imported from its module: layout/__init__.py is not edited for it
from layout.menus import saves_layout   # the SAVE / LOAD page of the pause menu (savegame.py)
from map_data import SITES
from textscale import cycle_text_level, text_level, tpx
from achievement_data import ACHIEVEMENTS
from layout.achievements import achievements_layout
from paging import filtered_missions, survivor_total, turn_upgrade_page, upgrade_page
from ui.vehicles_screen import vehicle_table_order   # the rows the vehicles table lists (owned vehicles + the standard ones)
from widgets import Button, pick_font, text_ladder


def _big_font(size, rect, labels, base=21):
    """The font for the big title-screen buttons: the largest of the text ladder (up to `base` px at the default
    window and text size) in which every label fits the button's width and height."""
    room = rect[2] - 16
    return pick_font(text_ladder(size, base), labels, room, int(rect[3] * 0.62))


def open_link(url):
    """Open a web address in the player's browser (credits links). Only http(s) addresses; never raises."""
    if url.startswith(("https://", "http://")):
        if IS_WEB:
            open_url(url)   # a new browser tab (webbrowser does not work inside the browser)
            return
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _with_click_sounds(game, buttons):
    """Make every button's action tell the sound manager which button was pressed, so the click that is played right
    after the press (keys.press_button / main.py's play_click) is the one listed for that button in
    sound_manager.BUTTON_CLICK_SOUNDS. Returns the same list."""
    for button in buttons:
        def action(original=button.action, label=button.label):
            game.sound_manager.note_button(label)
            return original()
        button.action = action
    return buttons


def continue_from_lore(game):
    """CONTINUE on the lore screen: while the story is still typing it shows the whole text (like SPACE); once it is all
    there, it moves on to the background screen."""
    if game.lore_typing_done():
        game.show_background()
    else:
        game.skip_lore_typing()


def request_scavenge(game):
    """SCAVENGE (button or S key). At a stop with several sites it opens the site popup (pick a site, then press
    the popup's SCAVENGE button to confirm). At a single-site stop (the Open Highway, the Mountain Pass) there is
    nothing to choose, so it searches at once."""
    game.start_scavenge()


def make_end_buttons(game, size):
    """PLAY AGAIN, HISTORY and TITLE SCREEN on the victory / game over popup of a window of this size (none while the game
    is still running). The rectangles are the ones ui.draw_end_overlay draws the popup with."""
    if game.status == "playing":
        return []
    play, history, title = popup_layout(int(size[0]), int(size[1]), "end", END_STAT_ROWS)["buttons"]
    return _with_click_sounds(game, [
        Button(play, "PLAY AGAIN", game.reset),
        Button(history, "HISTORY", game.open_end_history),
        Button(title, "TITLE SCREEN", game.return_to_title),
    ])


def make_confirm_buttons(game, size):
    """YES and NO on the "are you sure?" popup, in the rectangles ui.draw_confirm_popup draws it with (none while no
    confirmation is pending). YES does the action, NO closes the popup."""
    if game.confirm_popup is None:
        return []
    yes, no = confirm_popup_layout(int(size[0]), int(size[1]), confirm_body_lines(game.confirm_popup))["buttons"]
    return _with_click_sounds(game, [Button(yes, "YES", game.confirm_yes), Button(no, "NO", game.confirm_no)])


def make_site_buttons(game, size):
    """The SCAVENGE popup's buttons: one per site of the stop ("1. Gas Station", ... each only selects its site),
    then SCAVENGE (searches the selected site) and CANCEL, in the rectangles ui.draw_site_popup draws the popup with
    (none while the popup is closed)."""
    if not game.site_picker:
        return []
    sites = game.current_sites()
    g = site_popup_layout(int(size[0]), int(size[1]), len(sites))
    buttons = [Button(g["sites"][i], f"{i + 1}. {SITES[site]['name']}", lambda i=i: game.select_site(i))
               for i, site in enumerate(sites)]
    buttons.append(Button(g["scavenge"], "SCAVENGE", lambda: game.scavenge_site(game.selected_site)))
    buttons.append(Button(g["cancel"], "CANCEL", game.close_site_picker))
    return _with_click_sounds(game, buttons)


def make_abandon_buttons(game, size):
    """The "which vehicles to abandon?" popup's buttons: one per vehicle ("1. Pickup Truck", ... each ticks / unticks its
    vehicle), then ABANDON (gives up all the ticked ones; enabled only when exactly as many are ticked as must go), in
    the rectangles ui.draw_abandon_popup draws the popup with (none while nothing has to be chosen, see
    Game.abandon_pick_needed)."""
    if not game.abandon_pick_needed():
        return []
    g = abandon_popup_layout(int(size[0]), int(size[1]), len(game.vehicles))
    buttons = [Button(g["rows"][i], f"{i + 1}. {vehicle.vehicle_type}", lambda i=i: game.select_abandon(i))
               for i, vehicle in enumerate(game.vehicles)]
    buttons.append(Button(g["confirm"], "ABANDON", game.abandon_picked_vehicle, game.abandon_ready()))
    return _with_click_sounds(game, buttons)


def _step_volume(game, direction):
    """The settings screen's - / + buttons: change the music volume by one step, remembered for the next launch."""
    manager = game.music_manager
    (manager.increase_volume if direction > 0 else manager.decrease_volume)()
    settings_store.set_music_volume(round(manager.volume, 2))


def _step_sfx_volume(game, direction):
    """The settings screen's sound-effect - / + buttons: change the sound-effect volume by one step, remembered for
    the next launch. (keys.press_button plays the button click after the action, so the new volume is heard.)"""
    sounds = game.sound_manager
    (sounds.increase_volume if direction > 0 else sounds.decrease_volume)()
    settings_store.set_sfx_volume(round(sounds.volume, 2))


def _cycle_and_save_text_level(game):
    """The settings screen's TEXT SIZE button: next level, remembered for the next launch. The button's text is the
    current size's name (it changes with every press), so its click is always looked up as "TEXT SIZE": every size
    plays the same sound (sound_manager.BUTTON_CLICK_SOUNDS)."""
    game.sound_manager.note_button("TEXT SIZE")
    cycle_text_level()
    settings_store.set_text_level(text_level())


def _open_difficulty(game):
    """The settings screen's DIFFICULTY button: opens the difficulty screen. Its label is the current level's name (it
    changes), so its click is looked up as "DIFFICULTY" (sound_manager.BUTTON_CLICK_SOUNDS)."""
    game.sound_manager.note_button("DIFFICULTY")
    game.show_menu_screen("difficulty")


def open_saves(game):
    """The pause menu's SAVE / LOAD button (and the title screen's LOAD GAME): show the three save slots."""
    game.menu_page = "saves"
    game.save_pending = None
    game.save_message = ""


def close_saves(game):
    """Back from the save slots to the pause menu's own buttons."""
    game.menu_page = "main"
    game.save_pending = None
    game.save_message = ""


def _slot_action(game, kind, slot):
    """SAVE, LOAD or DELETE of one slot. Anything that would destroy something (overwriting a save, replacing the run
    in progress, deleting a save) needs a second press on the same button, which now reads CONFIRM; pressing any other
    slot button first cancels it. The result is kept in game.save_message for the page to show."""
    summary = savegame.slot_summaries()[slot]
    asks = {"save": summary is not None, "load": bool(game.started), "delete": True}[kind]
    if asks and game.save_pending != (kind, slot):
        game.save_pending = (kind, slot)
        game.save_message = ""
        return
    game.save_pending = None
    if kind == "save":
        game.save_message = savegame.save_slot(game, slot)[1]
    elif kind == "load":
        game.save_message = savegame.load_slot(game, slot)[1]   # on success the game leaves this page (screen: convoy)
    else:
        game.save_message = savegame.delete_slot(slot)


def _saves_buttons(game, size):
    """The SAVE / LOAD page: SAVE, LOAD and DELETE for each of the three slots, then BACK."""
    g = saves_layout(*size)
    summaries = savegame.slot_summaries()
    can_save = not savegame.save_problem(game)
    buttons = []
    for i, slot in enumerate(g["slots"]):
        summary = summaries[i]
        loadable = summary is not None and not summary["damaged"]

        def label(kind, name, i=i):
            return "CONFIRM" if game.save_pending == (kind, i) else name

        buttons.append(Button(slot["save"], label("save", "SAVE"), lambda i=i: _slot_action(game, "save", i), can_save))
        buttons.append(Button(slot["load"], label("load", "LOAD"), lambda i=i: _slot_action(game, "load", i), loadable))
        buttons.append(Button(slot["delete"], label("delete", "DELETE"), lambda i=i: _slot_action(game, "delete", i),
                              summary is not None))
    buttons.append(Button(g["back"], "BACK", lambda: close_saves(game)))
    return buttons


def _sandbox_rect(g):
    """Where the SANDBOX button goes on the difficulty screen: the bottom left of the panel, level with BACK and the
    same height. If BACK already sits there (it would overlap), the button goes to the bottom right instead."""
    panel, back = pygame.Rect(g["panel"]), pygame.Rect(g["back"])
    pad = max(8, back.h // 2)
    width = min(max(back.w, back.h * 5), max(back.w, panel.w // 3))
    rect = pygame.Rect(panel.x + pad, back.y, width, back.h)
    if rect.colliderect(back.inflate(pad, 0)):
        rect.right = panel.right - pad
    return rect


MENU_BUTTON_SCREENS = ("map", "vehicles", "upgrade", "missions", "survivors", "history", "menu", "difficulty", "settings", "credits",
                       "instructions", "achievements")   # screens that get the HUD's MENU button (the convoy and title screens have their own)


def make_buttons(game, layout=None):
    """The buttons of the current screen. The HUD's MENU button is on every screen of a run and of the pause menu,
    so the menu can be opened (or closed) from anywhere (Game.toggle_menu)."""
    if layout is None:
        layout = calculate_layout(WIDTH, HEIGHT)
    buttons = _screen_buttons(game, layout)
    if game.screen in MENU_BUTTON_SCREENS and getattr(game, "started", True):   # no HUD (so no MENU button) before a run
        mx, my, mw, mh = layout["menu"]
        buttons.append(Button((mx, my, mw, mh), "MENU", game.toggle_menu, game.status == "playing"))
    return _with_click_sounds(game, buttons)


def _credits_page_buttons(g, size):
    """PREVIOUS / NEXT for the credits pages, in the slots credits_layout reserves in the button row (none when the
    credits fit on one page; PgUp / PgDn and the mouse wheel turn the pages too)."""
    count = credits_page_count(*size)
    if count < 2:
        return []
    page = credits_page_index(*size)
    return [
        Button(g["prev"], "PREVIOUS", lambda: turn_credits_page(size, -1), page > 0),
        Button(g["next"], "NEXT", lambda: turn_credits_page(size, 1), page < count - 1),
    ]


def _screen_buttons(game, layout):
    playing = game.status == "playing"

    size = (layout["width"], layout["height"])

    if game.screen == "title":
        g = title_layout(*size)
        big = _big_font(size, g["load"], ("PLAY", "LOAD GAME"))   # one font for both, so they match
        return [
            Button(g["play"], "PLAY", game.show_lore, font=big),
            Button(g["load"], "LOAD GAME", lambda: (open_saves(game), game.open_menu()), font=big),
            Button(g["menu"], "MENU", game.open_menu),
        ]

    if game.screen == "lore":
        g = lore_layout(*size)
        return [
            Button(g["back"], "BACK",
                   lambda: setattr(game, "screen", "title")),
            Button(g["start"], "CONTINUE", lambda: continue_from_lore(game)),
        ]

    if game.screen == "background":
        g = background_layout(*size, len(BACKGROUND_ORDER))
        buttons = [
            Button(g["cards"][i], name.upper(), lambda n=name: game.select_background(n))
            for i, name in enumerate(BACKGROUND_ORDER)
        ]
        buttons += [
            Button(g["back"], "BACK", game.show_lore),
            Button(g["start"], "START GAME", game.begin_game),
        ]
        return buttons

    if game.screen == "map":
        trip = game.plan_trip()
        can_travel = (
            game.can_travel_now()   # playing, not on the road, and the selected stop is one road away
            and trip["km"] > 0
            and game.fuel >= trip["fuel"]
            and game.travel_danger() != "overrun"
        )
        g = map_layout(*size)
        return [
            Button(g["travel"], "TRAVEL", game.travel, can_travel),
            Button(g["back"], "BACK",
                   lambda: setattr(game, "screen", "convoy")),
        ]

    if game.screen == "vehicles":
        selected = game.selected_vehicle_type
        owned = game.owned_vehicle_types()
        selected_owned = selected in owned
        at_recovery_site = game.can_recover_type_here(selected)   # military vehicles: only at the Military Base
        has_driver = game.adult_count() > len(game.vehicles)   # only adults can drive
        cost = game.recovery_price(selected)   # less with a Tow/Recovery Truck (Recovery Support)

        can_recover = (
            playing and at_recovery_site and not selected_owned
            and has_driver and game.scrap >= cost
        )
        can_abandon = playing and selected_owned and len(game.vehicles) > 1
        abandon_label = (
            "CONFIRM ABANDON"
            if game.abandon_confirm == selected
            else "ABANDON VEHICLE"
        )

        g = vehicles_layout(*size, len(vehicle_table_order(game)))   # the same row count the screen draws with (the layout is cached by it)
        total_pages = g["pages"]
        page = max(0, min(getattr(game, "vehicle_page", 0), total_pages - 1))   # shown page; clamp_pages stores it
        row = vehicles_buttons(size[0], size[1], True) if game.sandbox else g   # SANDBOX: room for RECOVER ALL
        if selected_owned:
            # An owned vehicle cannot be recovered, so its button opens the upgrade screen instead (UPGRADE VEHICLE).
            # Upgrades are installed at the same stops vehicles are recovered at.
            can_upgrade = playing and game.can_upgrade_here() and bool(game.available_upgrades(selected))
            second = Button(row["recover"], "UPGRADE VEHICLE", game.open_upgrade_screen, can_upgrade)
        else:
            second = Button(row["recover"], "RECOVER VEHICLE",
                            lambda: game.recover_vehicle(selected), can_recover)
        buttons = [
            Button(row["abandon"], abandon_label,
                   lambda: game.request_abandon(selected), can_abandon),
            second,
        ]
        if g["paged"]:   # the vehicle table has more than one page
            buttons += [
                Button(g["prev_page"], "PREVIOUS",
                       lambda: setattr(game, "vehicle_page", max(0, page - 1)), page > 0),
                Button(g["next_page"], "NEXT",
                       lambda: setattr(game, "vehicle_page", min(total_pages - 1, page + 1)), page < total_pages - 1),
            ]
        if game.sandbox:   # SANDBOX MODE only: bring in every listed vehicle at once
            buttons.append(Button(row["recover_all"], "RECOVER ALL", game.recover_all_vehicles,
                                  playing and bool(game.sandbox_recoverable_types())))
        buttons.append(Button(row["back"], "BACK", lambda: setattr(game, "screen", "convoy")))
        return buttons

    if game.screen == "upgrade":
        g = upgrade_layout(*size, len(game.available_upgrades()))
        selected = game.owned_vehicle(game.selected_vehicle_type)
        chosen = game.selected_upgrade_id()
        if selected is not None and chosen and selected.has_upgrade(chosen):
            # An installed upgrade: the same button takes it off again (after an "are you sure?"; free, no day).
            main = Button(g["install"], "UNINSTALL UPGRADE", game.request_uninstall,
                          playing and not game.uninstall_problem())
        else:
            main = Button(g["install"], "INSTALL UPGRADE", game.install_upgrade, playing and not game.upgrade_problem())
        buttons = [main]
        if g["paged"]:   # more upgrades than fit the table: PREVIOUS / NEXT turn its pages (like the vehicles table)
            page = upgrade_page(game, size)
            buttons += [
                Button(g["prev_page"], "PREVIOUS", lambda: turn_upgrade_page(game, size, page - 1), page > 0),
                Button(g["next_page"], "NEXT", lambda: turn_upgrade_page(game, size, page + 1), page < g["pages"] - 1),
            ]
        buttons.append(Button(g["back"], "BACK", game.close_upgrade_screen))
        return buttons

    if game.screen == "instructions":
        last = PAGE_COUNT - 1
        page = game.instructions_page
        g = instructions_layout(*size)
        return [
            Button(g["prev"], "PREVIOUS PAGE",
                   lambda: game.turn_instructions_page(-1), page > 0),
            Button(g["next"], "NEXT PAGE",
                   lambda: game.turn_instructions_page(1), page < last),
            Button(g["back"], "BACK",
                   lambda: setattr(game, "screen", "menu")),
        ]

    if game.screen == "menu":
        if game.menu_page == "saves":
            return _saves_buttons(game, size)
        # The pause menu. MUTE MUSIC mutes / unmutes the music (game.toggle_music_mute).
        g = menu_layout(size[0], size[1], game.started)
        mute_label = "UNMUTE MUSIC" if game.music_muted else "MUTE MUSIC"
        buttons = [
            Button(g["settings"], "SETTINGS", lambda: game.show_menu_screen("settings")),
            Button(g["instructions"], "INSTRUCTIONS", game.open_instructions),
            Button(g["saves"], "SAVE / LOAD", lambda: open_saves(game)),
            Button(g["mute"], mute_label, game.toggle_music_mute),
        ]
        if not game.started:   # ACHIEVEMENTS and CREDITS only in the menu opened from the title screen, never in a run
            buttons.append(Button(g["achievements"], "ACHIEVEMENTS", game.open_achievements))
            buttons.append(Button(g["credits"], "CREDITS", game.open_credits))
        if game.started:   # only while a run is in progress; each asks "are you sure?" in a popup first
            buttons += [
                Button(g["restart"], "RESTART GAME", lambda: game.ask_confirm("restart")),
                Button(g["title"], "TITLE SCREEN", lambda: game.ask_confirm("title")),
            ]
        if not IS_WEB:   # a browser tab cannot close itself, so there is no QUIT GAME on the web
            buttons.append(Button(g["quit"], "QUIT GAME", lambda: game.ask_confirm("quit")))
        buttons.append(Button(g["back"], "BACK", game.close_menu))
        return buttons

    if game.screen == "difficulty":
        g = difficulty_layout(*size)
        buttons = [
            Button(g["difficulty_buttons"][i], name,
                   lambda n=name: game.request_difficulty(n))
            for i, name in enumerate(DIFFICULTY_ORDER)
        ]
        buttons.append(Button(_sandbox_rect(g), "SANDBOX: ON" if game.sandbox else "SANDBOX: OFF", game.toggle_sandbox))
        buttons.append(Button(g["back"], "BACK", lambda: game.show_menu_screen("settings")))   # difficulty is a page of the settings
        return buttons

    if game.screen == "settings":
        g = settings_layout(*size)

        return [
            Button(g["minus"], "-", lambda: _step_volume(game, -1)),
            Button(g["plus"], "+", lambda: _step_volume(game, +1)),
            Button(g["sfx_minus"], "-", lambda: _step_sfx_volume(game, -1)),
            Button(g["sfx_plus"], "+", lambda: _step_sfx_volume(game, +1)),
            Button(g["textsize"], text_level().upper(), lambda: _cycle_and_save_text_level(game)),
            Button(g["fullscreen"], "ON" if game.fullscreen else "OFF", game.toggle_fullscreen),
            Button(g["difficulty"], game.difficulty.upper(), lambda: _open_difficulty(game)),
            Button(g["contrast"], "ON" if theme.ACCESS["high_contrast"] else "OFF",
                   lambda: settings_store.toggle("high_contrast")),
            Button(g["colorblind"], "ON" if theme.ACCESS["colorblind"] else "OFF",
                   lambda: settings_store.toggle("colorblind")),
            Button(g["back"], "BACK", lambda: game.show_menu_screen("menu")),
        ]

    if game.screen == "credits":
        g = credits_layout(*size)
        buttons = _credits_page_buttons(g, size)   # first, so their focus index stays the same on every page
        for line in credits_items(*size):   # each link is a button over its text (ui/credits.py draws the text)
            if line.url:
                link = Button(line.rect, line.text, lambda url=line.url: open_link(url))
                link.url = line.url
                buttons.append(link)
        buttons.append(Button(g["back"], "BACK", game.close_credits))
        return buttons

    if game.screen == "missions":
        g = missions_layout(*size)
        manager = getattr(game, "mission_manager", None)
        per_page = g["per_page"]
        missions = filtered_missions(game)
        total_pages = page_count(len(missions), per_page)
        page = max(0, min(game.mission_page, total_pages - 1))   # shown page; clamp_pages stores it

        def set_filter(name):
            if game.mission_filter != name:
                game.mission_filter = name
                game.mission_page = 0

        buttons = [   # both tabs stay enabled: the open one is drawn highlighted (ui/lists.py), not greyed out
            Button(g["active"], "OPEN", lambda: set_filter("Active")),
            Button(g["completed"], "COMPLETED", lambda: set_filter("Completed")),
        ]
        for (mission_id, state), parts in zip(missions[page * per_page:(page + 1) * per_page], g["card_parts"]):
            if state["status"] == "Available":
                buttons.append(Button(parts["button"], "ACCEPT",
                                      lambda mid=mission_id: manager.accept_mission(game, mid), playing))
            elif state["status"] == "Active":
                buttons.append(Button(parts["button"], "ABANDON",
                                      lambda mid=mission_id: manager.abandon_mission(game, mid), playing))
        buttons += [
            Button(g["prev"], "PREVIOUS",
                   lambda: setattr(game, "mission_page", max(0, page - 1)), page > 0),
            Button(g["next"], "NEXT",
                   lambda: setattr(game, "mission_page", min(total_pages - 1, page + 1)), page < total_pages - 1),
            Button(g["back"], "BACK", lambda: setattr(game, "screen", "convoy")),
        ]
        return buttons

    if game.screen == "achievements":
        g = achievements_layout(*size)
        total_pages = page_count(len(ACHIEVEMENTS), g["per_page"])
        page = max(0, min(game.achievement_page, total_pages - 1))   # shown page; clamp_pages stores it
        return [
            Button(g["prev"], "PREVIOUS",
                   lambda: setattr(game, "achievement_page", max(0, page - 1)), page > 0),
            Button(g["next"], "NEXT",
                   lambda: setattr(game, "achievement_page", min(total_pages - 1, page + 1)), page < total_pages - 1),
            Button(g["back"], "BACK", game.close_achievements),
            Button(g["reset"], "RESET", lambda: game.ask_confirm("reset_achievements"),
                   game.achievements is not None and game.achievements.has_progress()),   # last, so the keyboard order is unchanged
        ]

    if game.screen == "survivors":
        g = survivors_layout(*size)
        total_pages = page_count(survivor_total(game), g["per_page"])
        page = max(0, min(game.survivor_page, total_pages - 1))   # shown page; clamp_pages stores it
        return [
            Button(g["prev"], "PREVIOUS",
                   lambda: setattr(game, "survivor_page", max(0, page - 1)), page > 0),
            Button(g["next"], "NEXT",
                   lambda: setattr(game, "survivor_page", min(total_pages - 1, page + 1)), page < total_pages - 1),
            Button(g["back"], "BACK", lambda: setattr(game, "screen", "convoy")),
        ]

    if game.screen == "history":
        g = history_layout(*size)
        top, step = history_max_scroll(game, size), history_page_rows(game, size)
        scroll = max(0, min(game.history_scroll, top))   # shown position; main.py stores it clamped
        return [
            Button(g["newer"], "NEWER", lambda: game.scroll_history(-step), scroll > 0),
            Button(g["older"], "OLDER", lambda: game.scroll_history(step), scroll < top),
            Button(g["back"], "BACK", game.close_history),
        ]

    # Main convoy screen.
    site = game.current_site()

    actions = [
        ("SCAVENGE", lambda: request_scavenge(game), playing and site is not None),   # site popup, or at once (one site)
        ("REPAIR", game.repair,
         playing and game.scrap >= game.repair_cost() and game.needs_repair()),
        ("TRAVEL", lambda: setattr(game, "screen", "map"), playing),
        ("MISSIONS", lambda: setattr(game, "screen", "missions"), playing),
        ("SURVIVORS", lambda: setattr(game, "screen", "survivors"), playing),
        ("VEHICLES", lambda: setattr(game, "screen", "vehicles"), playing),
    ]

    buttons = []

    if layout["mode"] == "wide":
        # The layout package returns (x, y, width, height) tuples.
        px, py, pw, ph = layout["sidebar"]

        k = layout["k"]   # the text factor: the rows scale with the fonts
        pad = 12
        header_h = tpx(28, k)
        gap = 7
        x = px + pad
        w = max(1, pw - 2 * pad)
        button_h = min(tpx(42, k), max(tpx(30, k), (ph - tpx(134, k)) // 6))
        y = py + 10
        panel_bottom = py + ph

        buttons.append(
            Button((x, y, w, header_h), "ACTIONS", lambda: None, False)
        )
        y += header_h + gap

        for index, (label, action, enabled) in enumerate(actions):
            if index == 3:
                y += gap
                buttons.append(
                    Button((x, y, w, header_h),
                           "MANAGEMENT", lambda: None, False)
                )
                y += header_h + gap

            if y + button_h > panel_bottom - 5:
                break

            buttons.append(
                Button((x, y, w, button_h), label, action, enabled)
            )
            y += button_h + gap

    else:
        # Compact layout: two columns in the bottom-left panel.
        px, py, pw, ph = layout["actions"]

        k = layout["k"]
        pad = 8
        gap = 6
        cols = 2
        rows = 3

        cell_w = max(1, (pw - pad * 2 - gap) // cols)
        cell_h = max(
            1, (ph - pad * 2 - gap * (rows - 1) - tpx(24, k)) // rows
        )

        for index, (label, action, enabled) in enumerate(actions):
            col = index % cols
            row = index // cols

            x = px + pad + col * (cell_w + gap)
            y = py + pad + tpx(20, k) + row * (cell_h + gap)

            buttons.append(
                Button((x, y, cell_w, cell_h), label, action, enabled)
            )

    # Convoy scroll arrows: only when the convoy is too long for the scene (ui/convoy.py decides, with the same
    # geometry the scene is drawn with). They page through the vehicles that do not fit.
    scene = scene_rect(layout["scene"])
    scrolling, can_left, can_right = convoy_scroll_state(game, scene)
    if scrolling:
        left_rect, right_rect = scroll_arrow_rects(scene)
        buttons.append(Button(left_rect, "<", lambda: scroll_convoy(game, -1, scene), can_left))
        buttons.append(Button(right_rect, ">", lambda: scroll_convoy(game, 1, scene), can_right))

    # The whole RECENT EVENTS bar is a button: it opens the full event history (H does the same).
    buttons.append(Button(tuple(layout["events"]), "HISTORY", game.open_history, playing))

    # Menu is separate from gameplay navigation.
    mx, my, mw, mh = layout["menu"]
    buttons.append(
        Button((mx, my, mw, mh), "MENU", game.open_menu, playing)
    )

    return buttons
