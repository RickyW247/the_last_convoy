"""Game state of THE LAST CONVOY: construction, a fresh run (reset), run statistics, the event log and the end of a run.

This module imports no pygame code: the real music / sound managers (and settings.json) are only loaded when
Game() is built without injected ones. Tests pass Game(music=NullAudio(), sound=NullAudio()) (game/null_audio.py).
"""
from achievements import AchievementTracker, default_path
from background_data import DEFAULT_BACKGROUND, starting_vehicles
from config import MAP_LAYOUT
from .event_manager import EventManager
from history_log import add_entry
from map_data import NODES, START, choose_layout
from .mission_manager import MissionManager
from .survivor_manager import SurvivorManager

from .vehicle import Vehicle


# What SANDBOX MODE gives (it is only ever topped up to these, never lowered): fuel, and food / water / scrap each.
# The three cargo amounts add up to 900, which still fits the HUD's widest CARGO label.
SANDBOX_FUEL = 999
SANDBOX_CARGO_EACH = 300


def _real_music():
    """The real music manager at its saved volume, and the saved mute choice (loads pygame code and settings.json)."""
    import settings_store
    from music_manager import MusicManager
    saved_volume = settings_store.saved_music_volume()   # None: nothing saved, use the default volume
    manager = MusicManager() if saved_volume is None else MusicManager(volume=saved_volume)
    return manager, settings_store.saved_music_muted()


def _real_sound():
    """The real sound-effect manager at its saved volume (the click sounds have their own saved volume)."""
    import settings_store
    from sound_manager import SoundManager
    saved_sfx = settings_store.saved_sfx_volume()
    return SoundManager() if saved_sfx is None else SoundManager(volume=saved_sfx)


def _supply(name):
    """A resource (fuel, food, water or scrap) stored in game._<name>. In sandbox mode a change that would LOWER it is
    ignored, so nothing the rules do (travel, daily use, repairs, ambushes, events) can use it up, while increases
    still work. Outside sandbox mode it is an ordinary attribute."""
    attr = "_" + name

    def get(self):
        return getattr(self, attr, 0)

    def set_(self, value):
        if getattr(self, "sandbox", False) and value < getattr(self, attr, 0):
            return
        setattr(self, attr, value)

    return property(get, set_)


def _survivor_count():
    """The convoy's survivor count, stored in game._survivors. Every drop of it (deaths, survivors who leave, no seats,
    events, the evacuation, ...) is added to game.survivors_lost, whichever rule causes it, so "Flawless Command" can
    check that none were lost. Increases (recruits, events) are never subtracted again."""
    def get(self):
        return getattr(self, "_survivors", 0)

    def set_(self, value):
        old = getattr(self, "_survivors", 0)
        if value < old:
            self.survivors_lost = getattr(self, "survivors_lost", 0) + old - max(0, value)
        self._survivors = value

    return property(get, set_)


def _screen_property():
    """The current screen name, stored in game._screen. Every change is reported to the achievements (on_screen), so
    "Field Study" notices each screen however the navigation code switches to it."""
    def get(self):
        return getattr(self, "_screen", None)

    def set_(self, value):
        self._screen = value
        if getattr(self, "achievements", None) is not None:
            self._achieve("on_screen", value)

    return property(get, set_)


class StateMixin:
    """__init__, reset and the small bookkeeping every other part of Game uses (say, end_run, stop / vehicle counts)."""
    _outcome_lines = None   # while a scavenge runs: the log lines it says, collected for the result popup
    achievements = None     # the AchievementTracker (set in __init__; kept across restarts)
    sandbox_used = False    # sandbox was on at some point in this run (set in reset / toggle_sandbox / save load)

    fuel = _supply("fuel")
    food = _supply("food")
    water = _supply("water")
    scrap = _supply("scrap")
    screen = _screen_property()      # also reports each screen shown to the achievements
    survivors = _survivor_count()   # also counts survivors_lost (reset() zeroes that once the starting convoy is set up)

    def __init__(self, music=None, sound=None, achievements=None):
        """music / sound: audio managers to use. None (the default, what main.py does) builds the real ones from the
        saved settings; tests pass a NullAudio (game/null_audio.py) so no display, sound device or settings file is
        needed. achievements: an AchievementTracker; None builds the real one (achievements.json) when the real audio
        is used, and an in-memory one (no file) when audio was injected."""
        real_audio = music is None
        self.sandbox = False        # SANDBOX MODE (difficulty screen): infinite fuel, food, water and scrap; not part of reset()
        self.difficulty = "Normal"  # not part of reset(): it stays the same across restarts
        self.background = DEFAULT_BACKGROUND   # player background (background_data.py): sets the starting vehicles (reset); kept across restarts
        self.started = False        # False until START GAME on the background screen; restarts (reset) keep it True
        self.menu_return = "convoy"  # where the menu's BACK goes: "title" or "convoy"
        self.menu_confirm = None     # "restart" or "title": pause-menu action waiting for a second press to confirm
        self.menu_page = "main"      # "main" or "saves": the pause menu shows its buttons or the SAVE / LOAD slots (savegame.py)
        self.save_pending = None     # ("save" / "load" / "delete", slot) waiting for a second press on CONFIRM
        self.save_message = ""       # what the last save / load / delete said (shown under the slots)

        self.fullscreen = False      # the wanted window mode (main.py switches the window to match); not part of reset()
        self.quit_requested = False  # set by a confirmed QUIT GAME; main.py's loop then ends

        if music is None:
            music, self.music_muted = _real_music()   # the mute choice is remembered too
        else:
            self.music_muted = False                  # injected audio: nothing is read from settings.json
        self.music_manager = music
        self.sound_manager = _real_sound() if sound is None else sound
        if not self.music_muted:   # while muted nothing starts; UNMUTE MUSIC (audio.py) starts the right track
            self.music_manager.play_music("menu")

        # Achievements belong to the player, not the run: made once here, never touched by reset() (achievements.py).
        self.achievements = achievements if achievements is not None else AchievementTracker(default_path() if real_audio else None)

        self.first_launch = True     # prevents reset() from switching to game music on the title screen

        self.reset()
        self.screen = "title"        # title -> lore -> convoy

        self.first_launch = False
        self.update_music()

    def _achieve(self, hook, *args):
        """Call one of the AchievementTracker's hooks (on_arrival, on_victory, on_defeat, on_event, on_screen, check) with this game."""
        if self.achievements is not None:
            getattr(self.achievements, hook)(self, *args)

    def toggle_sandbox(self):
        """SANDBOX MODE button (difficulty screen). Turning it on tops the supplies up to the sandbox amounts at once;
        turning it off trims fuel and cargo back down to what the convoy can actually carry."""
        self.sandbox = not self.sandbox
        if self.sandbox:
            self.sandbox_used = True   # this run can no longer earn achievements, even after sandbox is turned off
            self.fill_sandbox_supplies()
        else:
            self.trim_supplies()   # sandbox is already False here, so the supply setters allow lowering again

    def fill_sandbox_supplies(self):
        """Raise fuel, food, water and scrap to the sandbox amounts (never lowers one that is already higher)."""
        self._fuel = max(self._fuel, SANDBOX_FUEL)
        self._food = max(self._food, SANDBOX_CARGO_EACH)
        self._water = max(self._water, SANDBOX_CARGO_EACH)
        self._scrap = max(self._scrap, SANDBOX_CARGO_EACH)

    def reset(self):
        sandbox, self.sandbox = self.sandbox, False   # a fresh run starts from the normal amounts (set again at the end)
        self.map_layout_name = choose_layout(MAP_LAYOUT)   # a fresh run uses a random predefined map
        self.fuel = 32
        self.food = 24
        self.water = 24
        self.scrap = 5
        self.survivors = 8
        # The starting convoy comes from the chosen background (background_data.py; Civilian = pickup, van and bus).
        self.vehicles = [Vehicle(vehicle_type) for vehicle_type in starting_vehicles(self.background)]
        # A small starting convoy may not hold everything: start with only as many survivors and as much fuel as fit.
        capacity = self.convoy_stats()
        self.survivors = min(self.survivors, capacity["passengers"])
        self.fuel = min(self.fuel, capacity["fuel_capacity"])
        self.position = START            # node id of the stop the convoy is at
        self.current_location = NODES[START]["name"]
        self.selected_site = 0           # index into the current stop's sites: the one SCAVENGE searches
        self.apply_horde_start()
        self.horde_attack_streak = 0     # days in a row the horde has attacked (it hits harder each day)
        self.day = 1
        self.journey = None              # the trip in progress (see travel.py), None while at a stop
        self.selected = self.default_destination()   # the stop highlighted on the map (the way on from the start)
        self.log = [
            "The convoy is heading west. The horde is behind you.",
            "Reach the Pacific Coast and escape by ship.",
            f"Route: {self.map_layout_name}.",
        ]
        self.history = []                # every message of the run with its day and place (history_log.py)
        self.history_scroll = 0          # first visible row of the history screen
        self.history_return = "convoy"   # the screen the history screen's BACK returns to
        for line in reversed(self.log):
            add_entry(self.history, self.day, self.current_location, line)
        self.status = "playing"
        self.travel_count = 0
        self.scene_scroll = 0
        self.screen = "convoy"           # title, lore, convoy, map, vehicles, missions, survivors, menu (pause menu),
                                         # difficulty, settings, credits, instructions or upgrade
        self.instructions_page = 0
        self.selected_vehicle_type = "Semi-Truck"
        self.repairs_done = 0        # paid REPAIRs this run (the Civilian background refunds every other one)
        self.vehicle_upgrades = {}   # vehicle type -> installed upgrade ids (kept when a vehicle is lost; see convoy.py)
        self.selected_upgrade = None  # the highlighted row of the upgrade screen
        self.abandon_confirm = None  # vehicle type waiting for a second click to confirm abandoning
        self.abandon_pick = None     # vehicle highlighted in the "which vehicle to abandon?" popup (None: suggested)
        self.abandon_marks = None   # clear any leftover ticks from the previous run
        self.site_picker = False     # True while the SCAVENGE popup (choose which site to search) is open
        self.event_manager = EventManager()
        self.mission_manager = MissionManager()
        self.mission_page = 0
        self.mission_filter = "Active"
        self.survivor_manager = SurvivorManager(starting_count=self.survivors)
        self.survivor_page = 0
        self.reset_conditions()          # hunger / thirst / injury counts (conditions.py)
        self.survivor_vehicles = {}
        # Automatically assign survivors to convoy vehicles.
        self.assign_survivors_to_vehicles()

        # Update music when resetting during gameplay, but not during the first launch.
        if not self.first_launch:
            self.update_music()
    
        # Run statistics for the ending screen.
        self.visited = {START}                 # node ids of the stops the convoy has reached
        self.km_traveled = 0
        self.vehicles_start = len(self.vehicles)
        self.vehicles_recovered = 0            # vehicles recovered at a stop (RECOVER VEHICLE)
        self.vehicles_gained = 0               # vehicles that joined through an event (effect_handler.gain_vehicle)
        self.vehicles_wrecked = 0              # vehicles destroyed (not abandoned) this run; "Scorched Earth" needs a win with 5
        self.survivors_lost = 0                # survivors lost this run, however (see _survivor_count); "Flawless Command" needs 0
        self.end_reason = ""                   # why the run ended (shown on the ending screen)
        self.evacuation = None                 # the Pacific evacuation in progress (evacuation.py), None otherwise
        self.survivors_left_behind = 0         # survivors who did not fit on the ship

        self.sandbox = sandbox                 # sandbox mode stays on across restarts, like the difficulty
        self.sandbox_used = sandbox            # True once sandbox was on at any point in this run (blocks achievements)
        if sandbox:
            self.fill_sandbox_supplies()

    def return_to_title(self):
        """From the ending screen: a fresh run, back to the title screen."""
        self.reset()
        self.started = False
        self.screen = "title"
        self.update_music()

    def stops_visited(self):
        """How many different stops the convoy has reached (not counting where it started)."""
        return len(self.visited - {START})

    def stops_total(self):
        return len(NODES) - 1

    @property
    def stops_visited_count(self):
        """stops_visited() as an attribute, so a "run_stat" achievement can read it (achievement_data.py "Grand Tour")."""
        return self.stops_visited()

    def vehicles_lost(self):
        """Vehicles no longer in the convoy, however they were lost (abandoned, left without a driver, events)."""
        return max(0, self.vehicles_start + self.vehicles_recovered + self.vehicles_gained - len(self.vehicles))

    def end_run(self, status, message):
        self.status = status
        self.journey = None
        self.end_reason = message
        self.say(message)
        self.update_music()
        if status == "lost" and self.survivors <= 0:
            self._achieve("on_defeat")   # "Last Rites": losing because every survivor is gone unlocks the Hearse

    def say(self, message):
        if self._outcome_lines is not None:
            self._outcome_lines.append(message)
        self.log.insert(0, message)
        self.log = self.log[:4]
        add_entry(self.history, self.day, self.current_location, message)
