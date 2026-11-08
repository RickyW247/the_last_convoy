"""Keyboard play for THE LAST CONVOY: every screen can be used without a mouse.

How it works
  * Tab / Shift+Tab move a keyboard focus (a yellow outline) through the enabled buttons of the screen; the arrow
    keys do too wherever they have no other job; ENTER or SPACE presses the focused button.
  * Arrows with another job (on the settings screen Up / Down go to the button above / below): Up / Down turn the instructions pages, pick a vehicle on the vehicles screen (Left / Right flip its table pages) or an upgrade on the upgrade screen; Left / Right
    cycle the map destination through every stop in left-to-right order (wrapping) or flip survivors / missions pages (on the instructions they move the focus).
    On the convoy screen Up / Down move the focus to the button above / below (MENU counts as above the top row);
    Left / Right go to the previous / next button in reading order (Right on REPAIR reaches TRAVEL), then MENU, then
    the convoy scroll arrows "<" ">" of a long convoy (Right on ">" reaches SCAVENGE). With the arrows: Up from
    SCAVENGE / REPAIR reaches "<" / ">", Up again reaches MENU, Up from MENU reaches VEHICLES.
  * PageUp / PageDown scroll the instructions (Home / End: top / bottom), turn the credits pages (Home / End: first /
    last page) and the vehicle table's pages (Home / End: first / last). The mouse wheel does the same.
  * History screen: Up / Down scroll, Left / Right move the focus over NEWER, OLDER, BACK and MENU (ENTER presses),
    PgUp / PgDn / Home / End scroll. After a run has ended the ending popup's HISTORY button (or H) opens it; BACK / H / ESC
    return to the popup.
  * Survivors / missions: Up / Down move the focus by screen position (Up from the top row reaches MENU), Left / Right turn pages.
  * Letter keys on the convoy screen: S scavenge (opens the site popup), R repair, M map, V vehicles, P survivors,
    J missions. H opens / closes the full event history (the RECENT EVENTS bar is its button) on every screen of a run;
    there PgUp / PgDn / Home / End and Up / Down scroll, Left / Right = NEWER / OLDER, ESC goes back.
    O opens / closes the pause menu anywhere; ESC goes back one level (the convoy screen opens the pause menu,
    the title screen quits).
  * The SCAVENGE popup: the focus starts on its SCAVENGE button; Up / Down pick a site, ENTER searches it, 1-9 pick a
    site, Tab / Left / Right switch between SCAVENGE and CANCEL, ESC cancels. S at a single-site stop searches at once. A search ends in the
    result popup (ENTER / SPACE / ESC dismiss it), like an event.
  * The "which vehicles to abandon?" popup (more vehicles than adult drivers; every vehicle to go is chosen in this one
    popup): 1-9 tick / untick a vehicle (it starts with the suggested ones ticked), Tab / arrows move the focus over the
    vehicles and ABANDON, ENTER / SPACE on a vehicle tick it, on ABANDON (the focus starts there) give up all the ticked
    ones. ABANDON works only when exactly as many are ticked as must go. It cannot be cancelled: ESC does nothing.
  * The ending popup: Tab / arrows and ENTER / SPACE pick PLAY AGAIN / TITLE SCREEN (no number keys); ESC goes to the title screen.
  * Event popup: 1-4 pick that choice; Tab / arrows move the focus outline (it starts on no choice, so a stray ENTER
    does nothing) and ENTER / SPACE select. The result popup's OK button is focused: ENTER / SPACE / ESC dismiss it.
  * ESC on the title screen asks "press ESC again to quit" (game.quit_armed); any other key cancels it.
  * The "are you sure?" popup (RESTART GAME / TITLE SCREEN / QUIT GAME): Y does it, N or ESC cancels, Tab / arrows and
    ENTER / SPACE work too; the focus starts on NO so a stray ENTER changes nothing.
  * Credits: Tab / arrows move through the links of the open page and BACK (it starts on BACK), ENTER opens the focused
    link; PageUp / PageDown turn the pages (the focus goes back to BACK, so a stray ENTER opens nothing), or press the
    PREVIOUS / NEXT buttons (Tab / arrows reach them).

Shortcut keys (S, R, M, V, P, J, O, ESC, the popup's ESC and Up / Down, Left / Right on the map, Up / Down on the vehicles
screen, the credits page keys)
play the click of the button they stand for, like a mouse click does; moving the focus is silent.

This module owns no game rules: it only turns keys into the same calls the buttons make.
"""
import pygame

from buttons import request_scavenge
from paging import turn_upgrade_page, upgrade_page
from credits_items import turn_credits_page
from layout import LINE_H, instructions_layout, vehicles_layout
from layout.upgrade import upgrade_layout
from map_data import NODES
from ui import SCROLL_STEP, history_page_rows, scroll_instructions
from ui.vehicles_screen import vehicle_table_order

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
ARROW_KEYS = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
PAGE_KEYS = (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END)   # scroll the instructions / page the credits
ROW_CLICK_LABEL = "MAP STOP"   # the click of a vehicle-table row: for now the same as a map stop's; give it its own entry in
                               # sound_manager.BUTTON_CLICK_SOUNDS (e.g. "VEHICLE ROW") and change the name here
PAUSE_MENU_SCREENS = ("menu", "difficulty", "settings", "credits", "instructions")   # the pause menu and its pages


def play_click(game, label=None):
    """The button click sound effect (nothing when the sound manager is missing or has no sounds loaded). `label` names
    the button for clicks that do not come from a Button; for buttons the sound manager already knows which one was
    pressed (buttons.py). Which sound belongs to which label: sound_manager.BUTTON_CLICK_SOUNDS."""
    sounds = getattr(game, "sound_manager", None)
    if sounds is not None:
        sounds.play_button_click(label)


def press_button(game, button):
    """Do what a click on `button` does, then play the click sound (after the action, so a volume button is heard
    at its new volume). TRAVEL on the map screen drives and returns to the convoy screen. (The convoy screen's own
    TRAVEL button must stay on the map it just opened.)"""
    if not button.enabled:
        return   # a disabled button does nothing, whoever calls this (keys, clicks, number shortcuts)
    on_map = game.screen == "map"
    button.action()
    if on_map and game.screen == "map" and button.label == "TRAVEL":
        game.screen = "convoy"
    play_click(game)


def _shortcut_click(game, buttons, label):
    """The click of a shortcut key (S, R): the sound of the button it stands for, and only when that button is there and
    enabled, as with the mouse (a disabled button is silent)."""
    for button in buttons:
        if button.label == label:
            if button.enabled:
                play_click(game, label)
            return


def _is_disabled(buttons, label):
    """True when the screen has a button with this label and it is disabled (a shortcut key must not do what a greyed-out
    button cannot). A label with no button (a very short sidebar can hide one) is not disabled."""
    return any(b.label == label and not b.enabled for b in buttons)


def _preferred_label(game, kind):
    """The button the focus starts on when a screen opens (None: the first enabled one)."""
    if kind is not None:
        return None
    if game.screen == "lore":
        return "CONTINUE"
    if game.screen == "background":
        return "START GAME"
    if game.screen == "map":
        return "TRAVEL"
    if game.screen == "difficulty":
        return game.difficulty
    if game.screen == "vehicles":
        return "BACK"   # ABANDON / RECOVER are one stray ENTER away from a lost vehicle or spent scrap
    if game.screen == "upgrade":
        return "BACK"   # INSTALL UPGRADE spends scrap: never by a stray ENTER
    if game.screen == "missions":
        return "BACK"   # not the other filter tab (it looked like the page we were on), nor ACCEPT / ABANDON
    if game.screen == "history":
        return "BACK"
    if game.screen == "achievements":
        return "BACK"
    if game.screen == "credits":
        return "BACK"   # the links come first; ENTER must not open a web page by accident
    if game.screen == "menu" and game.menu_page == "saves":
        return "BACK"   # SAVE / LOAD / DELETE change or replace things: never by a stray ENTER


PAGED_SCREENS = ("missions", "survivors", "vehicles", "achievements")   # the button list changes length from page to page
PAGE_PARTNER = {"NEXT": "PREVIOUS", "PREVIOUS": "NEXT"}   # where the focus goes when the page turn it was on runs out


class KeyNav:
    """The keyboard focus: an index into the frame's button list, reset to a sensible button whenever the screen
    (or the popup on top of it) changes or the focused button is no longer enabled."""

    def __init__(self):
        self.context = None
        self.index = 0
        self.label = None   # label of the focused button: on the paged screens the focus follows it, not the index
        self.memory = {}   # context -> label of the button last focused there, so coming back finds it again

    def _default(self, game, buttons, kind):
        if kind == "event":
            return -1   # no choice is focused until Tab / an arrow key: ENTER must not pick one by accident
        if kind == "confirm":
            return min(1, len(buttons) - 1)   # NO (the buttons are YES, NO): ENTER must not throw a run away
        if kind == "sites":
            return max(0, len(buttons) - 2)   # the SCAVENGE button (the buttons end SCAVENGE, CANCEL): ENTER searches the selected site
        if kind == "abandon":
            return max(0, len(buttons) - 1)   # the ABANDON button (the buttons end with it): ENTER gives up the highlighted vehicle
        wanted = _preferred_label(game, kind)
        if wanted is None and kind is None and game.screen in ("convoy", "menu"):
            wanted = self.memory.get((game.screen, kind))   # the convoy screen and the pause menu remember
        enabled = [i for i, b in enumerate(buttons) if b.enabled]
        for i in enabled:
            if buttons[i].label == wanted:
                return i
        return enabled[0] if enabled else 0

    def _follow_label(self, buttons, context):
        """On the missions / survivors pages the number of buttons changes with the page (a card has an ACCEPT or
        ABANDON button only in some states), so the focus index would land on a different button after a page
        turn. Keep the focus on the button it was on, found again by its label (only when that label is unique, so a
        row of ACCEPT buttons is never guessed at). When that button is disabled (NEXT on the last page) the focus
        moves to its partner (PREVIOUS) instead of jumping to the screen's default button."""
        if context != self.context or context[1] is not None or context[0] not in PAGED_SCREENS or not self.label:
            return
        for wanted in (self.label, PAGE_PARTNER.get(self.label)):
            matches = [i for i, b in enumerate(buttons) if b.label == wanted]
            if len(matches) == 1 and buttons[matches[0]].enabled:
                self.index = matches[0]
                return
            if wanted == self.label and 0 <= self.index < len(buttons) and buttons[self.index].label == wanted \
                    and buttons[self.index].enabled:
                return   # a repeated label (ACCEPT / ABANDON) still where it was: leave it

    def sync(self, game, buttons, kind):
        """Keep the focus valid for this frame's `buttons`. `kind` is the popup on top: None, "end", "event"..."""
        context = (game.screen, kind)
        self._follow_label(buttons, context)
        valid = 0 <= self.index < len(buttons) and buttons[self.index].enabled
        if kind == "event" and context == self.context and self.index == -1:
            valid = True   # "nothing focused yet" is a legal state on the event popup
        if context != self.context or not valid:
            self.context = context
            self.index = self._default(game, buttons, kind)

    def apply(self, buttons):
        """Mark the focused button so that it draws its outline, and remember it for when the screen is left."""
        for i, button in enumerate(buttons):
            button.focused = (
                i == self.index
                and not (self.context and self.context[1] == "sites" and i < len(buttons) - 2)
                and not (self.context and self.context[1] == "abandon" and not button.enabled)   # no outline on a greyed ABANDON
            )

        if self.context and 0 <= self.index < len(buttons):
            self.memory[self.context] = buttons[self.index].label
            self.label = buttons[self.index].label
        else:
            self.label = None

    def move(self, buttons, step):
        """Focus the next (+1) or previous (-1) enabled button, wrapping round."""
        enabled = [i for i, b in enumerate(buttons) if b.enabled]
        if not enabled:
            return
        if self.index in enabled:
            position = (enabled.index(self.index) + step) % len(enabled)
        else:
            position = 0 if step > 0 else len(enabled) - 1
        self.index = enabled[position]

    def press(self, game, buttons):
        if 0 <= self.index < len(buttons) and buttons[self.index].enabled:
            press_button(game, buttons[self.index])

    # ---- keys ----
    def handle_key(self, game, event, buttons, kind, size):
        """Handle one KEYDOWN (no event or result popup is open). `buttons` is what the keys act on: the screen's
        buttons, or the ending popup's. Returns False when the game should quit."""
        self.sync(game, buttons, kind)
        key = event.key
        if kind == "sites":
            return self._site_popup_key(game, event, buttons)
        if key in ENTER_KEYS and game.screen == "lore" and kind is None and not game.lore_typing_done():
            game.skip_lore_typing()   # SPACE / ENTER while the story is typing: show all of it (CONTINUE needs a second press)
            return True
        if key == pygame.K_ESCAPE:
            return self._escape(game)
        game.quit_armed = False   # any other key cancels the title screen's "press ESC again to quit"
        if key == pygame.K_TAB:
            self.move(buttons, -1 if event.mod & pygame.KMOD_SHIFT else 1)
        elif key in ENTER_KEYS:
            self.press(game, buttons)
        elif key in ARROW_KEYS:
            self._arrow(game, key, buttons, size)
        elif key in PAGE_KEYS and kind is None and (game.status == "playing" or game.screen == "history"):
            self._page_key(game, key, size)
        elif key == pygame.K_o and game.status == "playing":
            before = game.screen
            game.toggle_menu()   # on every screen, including the title, lore and pause-menu screens
            if game.screen != before:
                play_click(game, "MENU")
        elif key == pygame.K_h and game.status != "playing":
            if game.screen == "history":
                game.close_history()
                play_click(game, "BACK")
            elif kind == "end":
                game.open_end_history()   # the ending popup's HISTORY button
                if game.screen == "history":
                    play_click(game, "HISTORY")
        elif game.started and game.status == "playing":
            self._letter(game, key, buttons)
        return True

    def _page_key(self, game, key, size):
        """PageUp / PageDown / Home / End: scroll the instructions, or turn the credits pages (other screens ignore them)."""
        if game.screen == "instructions":
            body_h = instructions_layout(*size)["body"][3]
            screenful = max(SCROLL_STEP, body_h - 2 * LINE_H)   # keeps two lines of the old view on screen
            if key == pygame.K_PAGEUP:
                scroll_instructions(game, size, -screenful)
            elif key == pygame.K_PAGEDOWN:
                scroll_instructions(game, size, screenful)
            else:   # the scroll is clamped to what overflows, so a huge step reaches the top / bottom
                scroll_instructions(game, size, -10 ** 9 if key == pygame.K_HOME else 10 ** 9)
        elif game.screen == "history":
            page = history_page_rows(game, size)
            if key == pygame.K_PAGEUP:
                game.scroll_history(-page)
            elif key == pygame.K_PAGEDOWN:
                game.scroll_history(page)
            else:   # main.py clamps the scroll to the rows, so a huge step reaches the newest / oldest
                game.scroll_history(-10 ** 6 if key == pygame.K_HOME else 10 ** 6)
        elif game.screen == "vehicles":   # a paged vehicle table: PgUp / PgDn turn the page, Home / End go to the first / last
            pages = vehicles_layout(int(size[0]), int(size[1]), len(vehicle_table_order(game)))["pages"]
            before = max(0, min(getattr(game, "vehicle_page", 0), pages - 1))
            target = {pygame.K_PAGEUP: before - 1, pygame.K_PAGEDOWN: before + 1, pygame.K_HOME: 0, pygame.K_END: pages - 1}[key]
            game.vehicle_page = max(0, min(target, pages - 1))
            if game.vehicle_page != before:
                play_click(game, "NEXT" if game.vehicle_page > before else "PREVIOUS")
        elif game.screen == "upgrade":   # a paged upgrade table: PgUp / PgDn turn the page, Home / End go to the first / last
            pages = upgrade_layout(int(size[0]), int(size[1]), len(game.available_upgrades()))["pages"]
            before = upgrade_page(game, size)
            target = {pygame.K_PAGEUP: before - 1, pygame.K_PAGEDOWN: before + 1, pygame.K_HOME: 0, pygame.K_END: pages - 1}[key]
            turn_upgrade_page(game, size, target)
            if upgrade_page(game, size) != before:
                play_click(game, "NEXT" if upgrade_page(game, size) > before else "PREVIOUS")
        elif game.screen == "credits":
            step = {pygame.K_PAGEUP: -1, pygame.K_PAGEDOWN: 1, pygame.K_HOME: -10 ** 6, pygame.K_END: 10 ** 6}[key]
            if turn_credits_page(size, step):
                self.context = None   # the page's links are different buttons: focus starts again on BACK
                play_click(game, "NEXT" if step > 0 else "PREVIOUS")

    def after_site_pick(self, buttons, index):
        """A site button (index) of the SCAVENGE popup was pressed (key or click): it is selected now, so the focus
        moves to the SCAVENGE button that confirms it. (The popup's buttons end with SCAVENGE, CANCEL.)"""
        if 0 <= index < len(buttons) - 2:
            self.index = len(buttons) - 2

    def _site_popup_key(self, game, event, buttons):
        """Keyboard navigation for the SCAVENGE popup."""
        key = event.key
        site_count = len(buttons) - 2
        scavenge = site_count
        cancel = site_count + 1

        if key == pygame.K_ESCAPE:
            game.close_site_picker()
            play_click(game, "CANCEL")

        elif key == pygame.K_TAB:
            # Focus only SCAVENGE and CANCEL
            if self.index not in (scavenge, cancel):
                self.index = scavenge
            else:
                self.index = cancel if self.index == scavenge else scavenge

        elif key in ENTER_KEYS:
            self.press(game, buttons)

        elif key == pygame.K_UP and site_count:
            game.selected_site = (game.selected_site - 1) % site_count
            play_click(game)   # picking a site, like clicking its button

        elif key == pygame.K_DOWN and site_count:
            game.selected_site = (game.selected_site + 1) % site_count
            play_click(game)

        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            if self.index == scavenge:
                self.index = cancel
            else:
                self.index = scavenge

        elif pygame.K_1 <= key <= pygame.K_9:
            number = key - pygame.K_1
            if number < site_count:
                press_button(game, buttons[number])
                self.index = scavenge

        return True

    def abandon_key(self, game, event, buttons):
        """Keys on the "which vehicles to abandon?" popup (the buttons are one per vehicle, then ABANDON): Tab / arrows move
        the focus over the vehicles and ABANDON (it starts on ABANDON), 1-9 tick / untick a vehicle, ENTER / SPACE press
        the focused button (a vehicle: tick it; ABANDON: give up every ticked vehicle, only when exactly enough are
        ticked). The choice is forced, so ESC does nothing."""
        self.sync(game, buttons, "abandon")
        count = len(buttons) - 1
        if count < 1:
            return
        key = event.key
        if key in ENTER_KEYS:
            self.press(game, buttons)
        elif key == pygame.K_TAB:
            self.move(buttons, -1 if event.mod & pygame.KMOD_SHIFT else 1)
        elif key in ARROW_KEYS:
            self.move(buttons, -1 if key in (pygame.K_UP, pygame.K_LEFT) else 1)
        elif pygame.K_1 <= key <= pygame.K_9 and key - pygame.K_1 < count:
            number = key - pygame.K_1
            game.select_abandon(number)
            play_click(game)   # ticking a vehicle, like clicking its button
            self.index = count if game.abandon_ready() else number   # all chosen: the focus goes on to ABANDON

    def confirm_key(self, game, event, buttons):
        """Keys on the "are you sure?" popup: Y = YES, N or ESC = NO, Tab / arrows move the focus, ENTER / SPACE press
        the focused button (it starts on NO)."""
        self.sync(game, buttons, "confirm")
        key = event.key
        if key in (pygame.K_ESCAPE, pygame.K_n):
            game.confirm_no()
            play_click(game, "NO")
        elif key == pygame.K_y:
            game.confirm_yes()
            play_click(game, "YES")
        elif key == pygame.K_TAB:
            self.move(buttons, -1 if event.mod & pygame.KMOD_SHIFT else 1)
        elif key in ARROW_KEYS:
            self.move(buttons, -1 if key in (pygame.K_UP, pygame.K_LEFT) else 1)
        elif key in ENTER_KEYS:
            self.press(game, buttons)

    def event_key(self, game, event, buttons):
        """Navigation keys on the event popup (its 1-4 keys are handled by main.py). Returns the index of the
        choice that ENTER / SPACE selected, or None."""
        self.sync(game, buttons, "event")
        key = event.key
        if key == pygame.K_TAB:
            self.move(buttons, -1 if event.mod & pygame.KMOD_SHIFT else 1)
        elif key in ARROW_KEYS:
            self.move(buttons, -1 if key in (pygame.K_UP, pygame.K_LEFT) else 1)
        elif key in ENTER_KEYS and 0 <= self.index < len(buttons) and buttons[self.index].enabled:
            play_click(game, "EVENT CHOICE")
            return buttons[self.index].action()
        return None

    @staticmethod
    def _escape(game):
        if game.screen == "history":
            game.close_history()            # history: BACK to where it was opened (the ending popup after a finished run)
            play_click(game, "BACK")
            return True
        if game.status != "playing":
            game.return_to_title()          # from the ending popup
            play_click(game, "TITLE SCREEN")
            return True
        screen = game.screen
        if screen == "difficulty":
            game.show_menu_screen("settings")   # one level back: to the settings
        elif screen in ("instructions", "settings", "achievements"):
            game.show_menu_screen("menu")   # one level back: to the pause menu
        elif screen == "credits":
            game.close_credits()
        elif screen == "menu":
            if game.menu_page == "saves":
                game.menu_page, game.save_pending, game.save_message = "main", None, ""   # one level back: the menu's buttons
            else:
                game.close_menu()
        elif screen == "lore":
            game.screen = "title"
        elif screen == "background":
            game.show_lore()                # one level back: to the lore screen
        elif screen == "history":
            game.close_history()
        elif screen == "upgrade":
            game.close_upgrade_screen()     # one level back: to the vehicles screen
        elif screen in ("map", "vehicles", "missions", "survivors"):
            game.screen = "convoy"
        elif screen == "convoy":
            game.open_menu()
            play_click(game, "MENU")
            return True
        else:
            if getattr(game, "quit_armed", False):
                return False                # the title screen, second ESC: quit
            game.quit_armed = True          # the title screen, first ESC: ask (the hint line says so)
            return True
        play_click(game, "BACK")            # every other level back is the BACK button's job
        return True

    def _arrow(self, game, key, buttons, size):
        step = -1 if key in (pygame.K_UP, pygame.K_LEFT) else 1
        vertical = key in (pygame.K_UP, pygame.K_DOWN)
        screen = game.screen

        if game.status != "playing" and screen != "history":
            self.move(buttons, step)

        elif screen == "map":
            if vertical:
                # UP / DOWN select MENU, TRAVEL and BACK
                self.move(buttons, step)
            else:
                # LEFT / RIGHT cycle through every stop in the order they sit on the map, left to right (wrapping)
                game.select_destination(self._next_stop(game, step))
                play_click(game, "MAP STOP")   # the same click as clicking a stop on the map

        elif screen == "instructions":
            if vertical:
                game.turn_instructions_page(step)
            else:
                self.move(buttons, step)

        elif screen == "vehicles" and vertical:
            self._select_vehicle(game, step, size)

        elif screen == "vehicles" and self._find(buttons, "NEXT") is not None:
            wanted = "PREVIOUS" if step < 0 else "NEXT"   # a paged vehicle table: Left / Right flip pages, like the other lists
            for button in buttons:
                if button.label == wanted and button.enabled:
                    press_button(game, button)

        elif screen == "upgrade" and vertical:
            self._select_upgrade(game, step)

        elif screen == "upgrade" and self._find(buttons, "NEXT") is not None:
            wanted = "PREVIOUS" if step < 0 else "NEXT"   # a paged upgrade table: Left / Right flip pages, like the vehicles table
            for button in buttons:
                if button.label == wanted and button.enabled:
                    press_button(game, button)

        elif screen == "convoy":
            if vertical:
                self._convoy_vertical(buttons, key)
            else:
                self._convoy_horizontal(buttons, step)

        elif screen == "history":
            if vertical:
                game.scroll_history(step)    # one row; main.py clamps
            else:
                self.move(buttons, step)     # Left / Right walk NEWER, OLDER, BACK, MENU (ENTER pages)

        elif screen in ("survivors", "missions", "achievements"):
            if vertical:
                self._move_spatial(buttons, key)   # Up from the top row reaches MENU (it sits in the HUD above)
            else:
                wanted = "PREVIOUS" if step < 0 else "NEXT"
                for button in buttons:
                    if button.label == wanted and button.enabled:
                        press_button(game, button)

        elif screen == "settings" and vertical:
            self._move_spatial(buttons, key)   # the button above / below (a row of - / + buttons is not a list)

        elif screen == "menu" and game.menu_page == "saves":
            if vertical:
                self._move_spatial(buttons, key)   # the same button in the slot above / below
            else:
                self.move(buttons, step)

        else:
            self.move(buttons, step)

    @staticmethod
    def _find(buttons, label):
        """The index of the button with this label, or None."""
        for i, button in enumerate(buttons):
            if button.label == label:
                return i
        return None

    def _focus_first(self, buttons, labels):
        """Focus the first enabled button among `labels` (in that order). Returns False when none is enabled."""
        for label in labels:
            i = self._find(buttons, label)
            if i is not None and buttons[i].enabled:
                self.index = i
                return True
        return False

    def _convoy_horizontal(self, buttons, step):
        """Left / Right on the convoy screen walk one ring: the action buttons in reading order, then the HISTORY bar, then MENU, then the
        convoy scroll arrows "<" and ">" (they exist only for a long convoy), and back to the first action. So Right
        on VEHICLES reaches MENU, Right on MENU reaches "<", Right on "<" reaches ">", Right on ">" reaches SCAVENGE;
        Left does the same the other way round. Disabled buttons are skipped."""
        special = ("HISTORY", "MENU", "<", ">")
        ring = [i for i, b in enumerate(buttons) if b.enabled and b.label not in special]
        for label in special:
            i = self._find(buttons, label)
            if i is not None and buttons[i].enabled:
                ring.append(i)
        if not ring:
            return
        if self.index in ring:
            self.index = ring[(ring.index(self.index) + step) % len(ring)]
        else:
            self.index = ring[0 if step > 0 else -1]

    def _convoy_vertical(self, buttons, key):
        """Up / Down on the convoy screen. With the scroll arrows present: Up from SCAVENGE goes to "<" and from REPAIR
        to ">", Up from an arrow goes to MENU, Up from MENU goes to VEHICLES (Down goes the opposite way). Otherwise,
        and for the other buttons, the nearest button above / below is chosen (_move_spatial)."""
        current = buttons[self.index].label if 0 <= self.index < len(buttons) else None
        if self._find(buttons, "<") is not None:   # the arrows exist: a long convoy
            if key == pygame.K_UP:
                targets = {"SCAVENGE": ("<", ">", "MENU"), "REPAIR": (">", "<", "MENU"),
                           "<": ("MENU",), ">": ("MENU",), "MENU": ("VEHICLES",)}
            else:
                targets = {"MENU": ("<", ">", "SCAVENGE"), "<": ("SCAVENGE",), ">": ("REPAIR", "SCAVENGE"),
                           "VEHICLES": ("MENU",)}
            if current in targets and self._focus_first(buttons, targets[current]):
                return
        self._move_spatial(buttons, key)

    def _move_spatial(self, buttons, key):
        """Focus the nearest enabled button above (Up) or below (Down) the focused one, judged by where the buttons
        are on screen (so the MENU button is "above" the top row). When nothing lies in that direction the focus
        wraps round in list order."""
        step = -1 if key == pygame.K_UP else 1
        if not 0 <= self.index < len(buttons):
            self.move(buttons, step)
            return
        rects = [b.rect for b in buttons]
        cx, cy = rects[self.index].center
        best, best_score = None, None
        for i, button in enumerate(buttons):
            if i == self.index or not button.enabled:
                continue
            dx = rects[i].centerx - cx
            dy = rects[i].centery - cy
            along = dy * step               # positive when the button lies in the pressed direction
            if along <= 0:
                continue
            score = along + 2 * abs(dx)     # prefer the same column over a nearer button far off to the side
            if best_score is None or score < best_score:
                best, best_score = i, score
        if best is None:
            self.move(buttons, step)
        else:
            self.index = best

    @staticmethod
    def _next_stop(game, step):
        """The stop after (step 1) or before (step -1) the selected one in screen order: by x position on the map, then
        y, so Right always moves to the next stop to the right, side stops and the pass included, and wraps round."""
        order = sorted(range(len(NODES)), key=lambda i: NODES[i]["pos"])
        here = order.index(game.selected) if game.selected in order else 0
        return order[(here + step) % len(order)]

    @staticmethod
    def _select_vehicle(game, step, size):
        """Up / Down on the vehicles screen: select the previous / next row of the vehicle table (wrapping), and turn
        to the page that row is on."""
        names = vehicle_table_order(game)   # the order the table is drawn in: owned vehicles first
        current = names.index(game.selected_vehicle_type) if game.selected_vehicle_type in names else 0
        chosen = names[(current + step) % len(names)]
        if chosen != game.selected_vehicle_type:
            game.abandon_confirm = None      # picking another row cancels a pending abandon
            game.selected_vehicle_type = chosen
            per_page = vehicles_layout(int(size[0]), int(size[1]), len(names))["per_page"]
            game.vehicle_page = (current + step) % len(names) // per_page
            play_click(game, ROW_CLICK_LABEL)   # like clicking the row

    @staticmethod
    def _select_upgrade(game, step):
        """Up / Down on the upgrade screen: highlight the previous / next upgrade of the vehicle."""
        ids = [upgrade["id"] for upgrade in game.available_upgrades()]
        if not ids:
            return
        current = ids.index(game.selected_upgrade_id())
        chosen = ids[(current + step) % len(ids)]
        if chosen != game.selected_upgrade_id():
            game.select_upgrade(chosen)
            play_click(game, ROW_CLICK_LABEL)   # like clicking the row

    @staticmethod
    def _letter(game, key, buttons):
        screen = game.screen
        if key == pygame.K_h:
            game.toggle_history()   # every screen of a run in progress, never over a popup (Game.open_history)
            if game.screen != screen:
                play_click(game, "BACK" if screen == "history" else "HISTORY")
        elif key == pygame.K_m:
            game.toggle_map()   # only on the screens of a run in progress (Game.toggle_map)
            if game.screen != screen:
                play_click(game, "TRAVEL" if game.screen == "map" else "BACK")   # the buttons that open / close the map
        elif screen == "convoy":
            if key == pygame.K_s:
                if _is_disabled(buttons, "SCAVENGE"):
                    return
                request_scavenge(game)
                _shortcut_click(game, buttons, "SCAVENGE")
            elif key == pygame.K_r:
                if _is_disabled(buttons, "REPAIR"):
                    return   # the button is greyed out (no scrap, or nothing to repair): the key does nothing either
                game.repair()
                _shortcut_click(game, buttons, "REPAIR")
            elif key == pygame.K_v:
                game.screen = "vehicles"
                play_click(game, "VEHICLES")
            elif key == pygame.K_p:
                game.screen = "survivors"
                play_click(game, "SURVIVORS")
            elif key == pygame.K_j:
                game.screen = "missions"
                play_click(game, "MISSIONS")
