"""Screens, menus and popups of THE LAST CONVOY: which screen is showing, the pause menu, credits, instructions,
the "are you sure?" popup and fullscreen. Rules only: main.py draws and reads the keys.
"""
from background_data import BACKGROUNDS
from config import LORE_PARAGRAPH_PAUSE, LORE_TYPING_CPS
from instructions_data import PAGE_COUNT
from story_data import LORE

# The lore text as it is typed: whitespace normalised, exactly what widgets.wrap_pixels reassembles from its lines.
LORE_PARAGRAPHS = [" ".join(paragraph.split()) for paragraph in LORE]
LORE_DURATION = sum(len(p) / LORE_TYPING_CPS + LORE_PARAGRAPH_PAUSE for p in LORE_PARAGRAPHS)


class NavigationMixin:
    """The screen property (changing it cleans up after the screen that was left) and every action of the menus."""
    _screen = "title"

    achievement_page = 0    # the achievements screen's page (paging.clamp_pages keeps it valid)

    confirm_popup = None    # "restart", "title", "quit", "daycost", "difficulty", "uninstall" or "reset_achievements" while the popup is open, else None

    pending_difficulty = None   # for the "difficulty" popup: the level to switch to (and restart with) on YES

    day_cost_pending = None   # for the "daycost" popup: {"mark", "retry", "text"} (see SurvivalMixin.confirm_day_cost)

    CONFIRM_ACTIONS = ("restart", "title", "quit", "daycost", "difficulty", "uninstall", "reset_achievements")

    RUN_SCREENS = ("convoy", "map", "vehicles", "upgrade", "missions", "survivors", "history")   # the screens of a run in progress

    MENU_PAGES = ("difficulty", "settings", "instructions", "credits", "achievements")   # screens reached from the pause menu

    @property
    def screen(self):
        return self._screen

    @screen.setter
    def screen(self, value):
        """Every change of screen goes through here, so leaving a screen always cleans up after it: a pending
        ABANDON (vehicles screen), RESTART / TITLE confirmation or QUIT GAME (pause menu) and the title screen's
        "press ESC again to quit" end when their screen is left, and opening the missions screen refreshes which
        missions are available. (Nothing has to remember to do this at the places that change the screen.)"""
        if value == self._screen:
            return
        self._screen = value
        self.confirm_popup = None   # a pending "are you sure?" never outlives its screen
        self.day_cost_pending = None
        self.pending_difficulty = None
        self.uninstall_pending = None
        if value != "vehicles":
            self.abandon_confirm = None
        if value != "menu":
            self.menu_confirm = None
            self.quit_confirm = False
        if value != "title":
            self.quit_armed = False
        if value == "missions":
            manager = getattr(self, "mission_manager", None)
            if manager is not None:
                manager._refresh_availability()   # locked missions may have become available

    def open_upgrade_screen(self):
        """UPGRADE VEHICLE (vehicles screen): the upgrades of the selected, owned vehicle. BACK returns to the vehicles screen."""
        if self.status == "playing" and self.selected_vehicle_type in self.owned_vehicle_types():
            self.selected_upgrade = None   # the first upgrade is highlighted
            self.screen = "upgrade"

    def close_upgrade_screen(self):
        """BACK / ESC on the upgrade screen."""
        if self.screen == "upgrade":
            self.screen = "vehicles"

    def toggle_map(self):
        """M key: the map from any screen of a run in progress, and back to the convoy from the map. Nothing from the
        title, lore, pause-menu or ending screens, and nothing while a popup (event, site picker) is open."""
        if self.screen == "map":
            self.screen = "convoy"
        elif (self.screen in self.RUN_SCREENS and self.status == "playing" and not self.site_picker
              and not self.event_manager.active
              and not getattr(self.event_manager, "result", None)):
            self.screen = "map"

    def open_history(self):
        """The full event history (H key, the RECENT EVENTS bar): from any screen of a run in progress, never over a
        popup. BACK returns to the screen it was opened from."""
        if (self.screen in self.RUN_SCREENS and self.screen != "history" and self.status == "playing"
                and not self.site_picker and not self.event_manager.active
                and not getattr(self.event_manager, "result", None)):
            self.history_return = self.screen
            self.history_scroll = 0
            self.screen = "history"

    def open_end_history(self):
        """HISTORY on the ending popup (or H there): the event history after the run has ended. BACK returns to the popup."""
        if (self.status != "playing" and self.screen != "history"
                and not self.event_manager.active and not self.event_result):
            self.history_return = self.screen
            self.history_scroll = 0
            self.screen = "history"

    def close_history(self):
        """Leave the history screen for the screen it was opened from."""
        if self.screen == "history":
            self.screen = self.history_return

    def toggle_history(self):
        """H key: opens the history, and closes it again."""
        if self.screen == "history":
            self.close_history()
        else:
            self.open_history()

    def scroll_history(self, rows):
        """Move the history screen by `rows` rows (negative: towards the newest); main.py clamps it to the rows."""
        self.history_scroll = max(0, self.history_scroll + rows)

    lore_time = 0.0         # seconds the lore screen's typing effect has been running

    def lore_revealed(self):
        """How many characters of each lore paragraph are typed so far (a list, one count per paragraph). Each paragraph
        types at LORE_TYPING_CPS and is followed by a short pause."""
        left = self.lore_time
        counts = []
        for paragraph in LORE_PARAGRAPHS:
            typed = max(0, min(len(paragraph), int(left * LORE_TYPING_CPS)))
            counts.append(typed)
            left -= len(paragraph) / LORE_TYPING_CPS + LORE_PARAGRAPH_PAUSE
        return counts

    def lore_typing_done(self):
        """True once every character of the lore text is showing."""
        return self.lore_time >= LORE_DURATION

    def skip_lore_typing(self):
        """SPACE / ENTER while the lore text is still typing: show all of it at once."""
        self.lore_time = LORE_DURATION

    def update_lore(self, dt):
        """Advance the typing effect by `dt` seconds (main.py calls this every frame). Returns how many characters
        appeared during this step, so the typing sound can play for them."""
        if self.screen != "lore" or self.lore_typing_done():
            return 0
        before = sum(self.lore_revealed())
        self.lore_time += dt
        return sum(self.lore_revealed()) - before

    def show_lore(self):
        """Display the lore screen. The text types out again, except when coming back from the background screen
        (the story has been read already, so it is all there)."""
        self.lore_time = LORE_DURATION if self.screen == "background" else 0.0
        self.screen = "lore"
        self.update_music()

    def show_background(self):
        """CONTINUE on the lore screen: the player background screen (START GAME there begins the run)."""
        self.screen = "background"
        self.update_music()

    def select_background(self, name):
        """A background card was chosen. It is only stored here: begin_game (START GAME) builds the run from it."""
        if name in BACKGROUNDS:
            self.background = name

    def begin_game(self):
        """START GAME on the background screen: start the convoy journey. The run is rebuilt first, so it starts with
        the chosen background's vehicles (reset reads Game.background). reset() would switch to the game music for a
        moment, so it is told (first_launch) to leave the music alone; update_music below picks the right track."""
        was_first_launch = self.first_launch
        self.first_launch = True
        try:
            self.reset()
        finally:
            self.first_launch = was_first_launch
        self.started = True
        self._achieve("check")   # the starting convoy's vehicle types count for Convoy Collector
        self.screen = "convoy"
        self.update_music()

    def open_menu(self):
        """Open the pause menu from any screen; its BACK returns to the screen it was opened from. (Opened from one
        of its own pages, the place it returns to is kept.)"""
        if self.screen != "menu" and self.screen not in self.MENU_PAGES:
            self.menu_return = self.screen
        self.screen = "menu"
        self.update_music()

    def toggle_menu(self):
        """The MENU button / O key, on every screen: opens the pause menu; on the pause menu itself it closes it
        again; on one of its pages (difficulty, settings, instructions) it goes back to the pause menu."""
        if self.screen == "menu":
            self.close_menu()
        elif self.screen in self.MENU_PAGES:
            self.show_menu_screen("menu")
        else:
            self.open_menu()

    def auto_pause(self):
        """The window lost focus or was minimized: during a run, go to the pause menu (its BACK returns to the screen
        that was open). Nothing changes on the title, lore, menu or ending screens."""
        if self.started and self.status == "playing" and self.screen in self.RUN_SCREENS:
            self.open_menu()

    def close_menu(self):
        """Leave the pause menu for the screen it was opened from."""
        self.screen = self.menu_return
        self.update_music()

    def show_menu_screen(self, screen):
        """Open a screen of the pause menu ("menu" itself, "difficulty" or "settings"). The place the pause menu
        returns to (menu_return) is kept."""
        self.screen = screen
        self.update_music()

    def open_credits(self):
        """Open the credits screen (the CREDITS button of the pause menu opened from the title screen)."""
        self.screen = "credits"
        self.update_music()

    def open_achievements(self):
        """ACHIEVEMENTS in the pause menu (also reachable from the title screen's menu): the achievements screen. BACK
        returns to the pause menu."""
        self.achievement_page = 0
        self.screen = "achievements"
        self.update_music()

    def reset_achievements(self):
        """YES on the RESET ACHIEVEMENTS popup: forget every completed achievement and lifetime counter (achievements.json is
        rewritten empty). Bonus vehicles they unlocked lock again. The current run, saves and settings are untouched."""
        if self.achievements is not None:
            self.achievements.reset()
        self.achievement_page = 0

    def close_achievements(self):
        """Back from the achievements screen to the pause menu."""
        self.show_menu_screen("menu")

    def close_credits(self):
        """Back from the credits screen to the pause menu (which BACK then returns to the title screen)."""
        self.screen = "menu"
        self.update_music()

    def request_menu_action(self, action):
        """RESTART GAME / TITLE SCREEN in the pause menu: the first press asks for confirmation, a second press on
        the same action does it (a run is lost either way). `action` is "restart" or "title"."""
        if self.menu_confirm != action:
            self.menu_confirm = action
            return
        self.menu_confirm = None
        if action == "restart":
            self.restart_to_lore()
        else:
            self.return_to_title()

    def restart_to_lore(self):
        """RESTART GAME: a fresh run, but back on the lore screen (CONTINUE, then START GAME on the background screen, begins it), not straight on the convoy
        screen. The difficulty and the music settings stay. reset() would switch to the game music for the convoy
        screen for a moment, so it is told (first_launch) to leave the music alone; show_lore() then picks the music
        of the lore screen."""
        was_first_launch = self.first_launch
        self.first_launch = True
        try:
            self.reset()
        finally:
            self.first_launch = was_first_launch
        self.started = False   # like a new game from the title screen: START GAME sets it again
        self.show_lore()

    def ask_confirm(self, action):
        """RESTART GAME / TITLE SCREEN / QUIT GAME: open the "are you sure?" popup for `action` ("restart", "title" or
        "quit", or "daycost" for a repair / recovery that would cost a survivor). Nothing happens until confirm_yes."""
        if action in self.CONFIRM_ACTIONS:
            self.confirm_popup = action

    def request_difficulty(self, name):
        """A difficulty card was chosen. A run in progress has to restart for the new level, so that asks first (the
        "difficulty" popup); before a run has started nothing is lost and the level is simply set."""
        if name == self.difficulty:
            return
        if self.started:
            self.pending_difficulty = name
            self.ask_confirm("difficulty")
        else:
            self.set_difficulty(name)

    def confirm_yes(self):
        """YES on the popup: do the action. A restart starts a fresh run and shows the lore screen (the difficulty and
        the music setting stay), TITLE SCREEN goes back to the title screen, QUIT GAME asks main.py to leave."""
        action, self.confirm_popup = self.confirm_popup, None
        self.menu_confirm = None
        if action == "daycost":
            pending, self.day_cost_pending = self.day_cost_pending, None
            if pending is not None:
                self.day_warning = pending["mark"]   # the state is unchanged, so confirm_day_cost lets it through
                pending["retry"]()
        elif action == "restart":
            self.restart_to_lore()
        elif action == "difficulty":
            name, self.pending_difficulty = self.pending_difficulty, None
            self.restart_to_lore()          # a fresh run on the lore screen ...
            if name:
                self.set_difficulty(name)   # ... with the new level (day 1, so the horde's starting gap follows it)
        elif action == "reset_achievements":
            self.reset_achievements()       # erases achievements.json progress; stays on the achievements screen
        elif action == "uninstall":
            self.uninstall_upgrade()        # reads Game.uninstall_pending; free, takes no day
        elif action == "title":
            self.return_to_title()
        elif action == "quit":
            self.quit_requested = True

    def confirm_no(self):
        """NO / ESC on the popup: close it and change nothing."""
        self.confirm_popup = None
        self.day_cost_pending = None
        self.pending_difficulty = None
        self.uninstall_pending = None

    def toggle_fullscreen(self):
        """Fullscreen on or off (settings screen, F11). Only the wanted mode is stored here: main.py has the window."""
        self.fullscreen = not self.fullscreen

    def open_instructions(self):
        """Open the instructions screen."""
        self.instructions_page = 0
        self.screen = "instructions"
        self.update_music()

    def turn_instructions_page(self, step):
        """Move to the next (+1) or previous (-1) instructions page, staying within the pages."""
        self.instructions_page = max(0, min(PAGE_COUNT - 1, self.instructions_page + step))
