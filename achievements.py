"""Achievements of THE LAST CONVOY (design doc section 20.5): tracking, unlocking and saving (no pygame).

Completed achievements live in achievements.json, in the same folder as settings.json (settings_store.USE_TEMP_FOLDER
decides whether that is the temporary or the permanent folder). They belong to the player, not to a run: RESTART GAME,
TITLE SCREEN, loading a save and starting a new run never touch them. The file also keeps the few lifetime counters
some achievements need (runs won, vehicle types ever seen, screens ever shown).

Game.achievements is one AchievementTracker. The rules call its hooks (on_arrival, on_victory, on_defeat, on_event, check) through
StateMixin._achieve; a tracker made with path=None keeps everything in memory (what tests and Game(music=NullAudio())
get, so no file is read or written).

Rewards are PLACEHOLDERS: apply_reward() does nothing yet. So are the achievements marked "placeholder" in
achievement_data.py (their event / vehicle does not exist yet): they are listed but can never be completed.
"""
import json
import os
import stat
import tempfile
import time

from achievement_data import ACHIEVEMENTS, BY_ID
from config import ACHIEVEMENTS_IN_SANDBOX
from platform_web import IS_WEB, storage_read, storage_write

FILE_VERSION = 1
MAX_FILE_BYTES = 256 * 1024   # a real file is a few KB; anything bigger is not ours
FILE_NAME = "achievements.json"
COUNTER_NAMES = ("wins", "vehicles_recovered")   # the lifetime counters kept in the file
MAX_SCREENS_SEEN = 64   # screen names kept in the file (there are about 16 real ones; the cap stops a junk file growing)


def default_path():
    """achievements.json beside settings.json. Loads settings_store (and so pygame's font code), so only the real game
    calls it (state.py does, when it builds the real audio too); tests use path=None."""
    import settings_store
    return os.path.join(settings_store._settings_dir(), FILE_NAME)


def event_id_of(event):
    """The id of an event given as a dict or an object (None when it has none)."""
    if isinstance(event, dict):
        return event.get("id")
    return getattr(event, "id", None)


def apply_reward(game, achievement):
    """PLACEHOLDER: what completing `achievement` gives. Nothing yet (achievement["reward"] is only text for the
    future achievements screen). Bonus vehicles, survivors, events and cosmetics are wired in here later."""
    return None


def _folder_is_ours(folder):
    """Same rule as settings_store: on Linux / macOS only trust a real folder owned by this user that others cannot write."""
    if not hasattr(os, "getuid"):
        return True
    try:
        info = os.lstat(folder)
    except OSError:
        return False
    return (stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and info.st_uid == os.getuid() and not info.st_mode & 0o022)


class AchievementTracker:
    def __init__(self, path=None):
        self.path = path
        self.completed = {}            # achievement id -> {"day": run day it was earned, "date": "YYYY-MM-DD"}
        self.counters = {name: 0 for name in COUNTER_NAMES}    # lifetime counters
        self.vehicle_types_seen = set()
        self.screens_seen = set()      # Game.screen values that have been shown ("Field Study"), all runs together
        self.new_unlocks = []          # ids earned since pop_new_unlocks() (for a future "unlocked" toast)
        self._load()

    # ---- file ----------------------------------------------------------------------------------------------------
    def _load(self):
        """Read the file. A missing, damaged, oversized or foreign file just means nothing is completed yet."""
        if not self.path:
            return
        if IS_WEB:   # the browser keeps it in localStorage (platform_web), not in a file
            try:
                raw = storage_read(FILE_NAME)
                data = json.loads(raw) if raw and len(raw) <= MAX_FILE_BYTES else {}
            except ValueError:
                return
        else:
            if not os.path.isfile(self.path):
                return
            try:
                if not _folder_is_ours(os.path.dirname(self.path)):
                    return
                with open(self.path, "rb") as handle:
                    raw = handle.read(MAX_FILE_BYTES + 1)
                data = json.loads(raw.decode("utf-8")) if len(raw) <= MAX_FILE_BYTES else {}
            except (OSError, ValueError):
                return
        if not isinstance(data, dict):
            return
        done = data.get("completed")
        if isinstance(done, dict):
            for key, info in done.items():
                if isinstance(key, str) and isinstance(info, dict):   # ids this version does not know are kept
                    day, date = info.get("day"), info.get("date")
                    self.completed[key] = {"day": day if isinstance(day, int) and not isinstance(day, bool) else 0,
                                           "date": date if isinstance(date, str) and len(date) <= 20 else ""}
        saved = data.get("counters")
        if isinstance(saved, dict):
            for name in COUNTER_NAMES:
                value = saved.get(name)
                if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10 ** 6:
                    self.counters[name] = value
        seen = data.get("vehicle_types_seen")
        if isinstance(seen, list):
            self.vehicle_types_seen = {name for name in seen if isinstance(name, str) and len(name) <= 80}
        screens = data.get("screens_seen")
        if isinstance(screens, list):
            self.screens_seen = {name for name in screens[:MAX_SCREENS_SEEN] if isinstance(name, str) and len(name) <= 40}

    def save(self):
        """Write the file (atomically: a crash cannot leave a half-written one). Failures are ignored: the achievements
        still count for this session."""
        if not self.path:
            return
        data = {"version": FILE_VERSION, "completed": self.completed, "counters": self.counters,
                "vehicle_types_seen": sorted(self.vehicle_types_seen),
                "screens_seen": sorted(self.screens_seen)}
        if IS_WEB:
            storage_write(FILE_NAME, json.dumps(data))
            return
        folder = os.path.dirname(self.path)
        temporary = None
        try:
            os.makedirs(folder, mode=0o700, exist_ok=True)
            if not _folder_is_ours(folder):
                return
            handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder, prefix="achievements-",
                                                 suffix=".tmp", delete=False)
            temporary = handle.name
            with handle:
                json.dump(data, handle, indent=2)
            os.replace(temporary, self.path)
            temporary = None
        except OSError:
            pass
        finally:
            if temporary:
                try:
                    os.remove(temporary)
                except OSError:
                    pass

    def reset(self):
        """Forget every achievement and counter (tests; no button calls this)."""
        self.completed, self.counters, self.vehicle_types_seen = {}, {name: 0 for name in COUNTER_NAMES}, set()
        self.screens_seen = set()
        self.new_unlocks = []
        self.save()

    # ---- questions for the screens -------------------------------------------------------------------------------
    def is_complete(self, achievement_id):
        return achievement_id in self.completed

    def has_progress(self):
        """True when there is anything for RESET to erase: a completed achievement, a lifetime counter, a seen vehicle type or a visited screen."""
        return bool(self.completed or any(self.counters.values()) or self.vehicle_types_seen
                    or self.screens_seen)

    def completed_count(self):
        return sum(1 for a in ACHIEVEMENTS if a["id"] in self.completed)

    def progress(self, achievement, game=None):
        """(current, target) for the achievement, for a progress display: a count where the condition counts something,
        else (1, 1) when complete and (0, 1) when not."""
        if achievement["id"] in self.completed:
            target = achievement["condition"].get("count", 1)
            return target, target
        cond = achievement["condition"]
        kind = cond["kind"]
        if kind == "wins":
            return min(self.counters["wins"], cond["count"]), cond["count"]
        if kind == "vehicle_types_seen":
            return min(len(self.vehicle_types_seen), cond["count"]), cond["count"]
        if kind == "screens_visited":
            wanted = set(cond["screens"])
            return len(wanted & self.screens_seen), len(wanted)
        if kind == "lifetime_counter":
            return min(self.counters.get(cond["counter"], 0), cond["count"]), cond["count"]
        if kind in ("run_stat", "win_with_stat"):   # win_with_stat only completes at victory, but shows its progress
            return min(getattr(game, cond["stat"], 0) if game is not None else 0, cond["count"]), cond["count"]
        return 0, 1

    def unlocked_vehicles(self):
        """Bonus vehicle types unlocked by the achievements completed so far (achievement_data "unlocks_vehicle")."""
        names = set()
        for achievement_id in self.completed:
            unlocked = BY_ID.get(achievement_id, {}).get("unlocks_vehicle")
            if isinstance(unlocked, str):
                names.add(unlocked)
            elif unlocked:   # a tuple of vehicle types (one achievement can unlock several)
                names.update(unlocked)
        return names

    def unlocked_event_groups(self):
        """Event groups unlocked by the achievements completed so far (achievement_data "unlocks_events"). Events of a
        group stay out of the random draw until then (effect_handler.event_available)."""
        return {BY_ID[i]["unlocks_events"] for i in self.completed if i in BY_ID and BY_ID[i].get("unlocks_events")}

    def pop_new_unlocks(self):
        """The ids earned since the last call (oldest first)."""
        earned, self.new_unlocks = self.new_unlocks, []
        return earned

    # ---- awarding ------------------------------------------------------------------------------------------------
    def _blocked(self, game):
        tainted = getattr(game, "sandbox", False) or getattr(game, "sandbox_used", False)   # on now, or ever in this run
        return bool(tainted) and not ACHIEVEMENTS_IN_SANDBOX

    def unlock(self, game, achievement_id):
        """Complete an achievement for good. Returns True when it is newly completed."""
        achievement = BY_ID.get(achievement_id)
        if (achievement is None or achievement.get("placeholder") or achievement_id in self.completed
                or self._blocked(game)):
            return False
        self.completed[achievement_id] = {"day": int(getattr(game, "day", 0) or 0), "date": time.strftime("%Y-%m-%d")}
        self.new_unlocks.append(achievement_id)
        self.save()
        game.say(f"Achievement unlocked: {achievement['name']}!")
        apply_reward(game, achievement)
        return True

    def _owned(self, game):
        return set(game.owned_vehicle_types())

    def check(self, game):
        """Re-check every achievement that is a count: call after anything that can change vehicles or the run
        statistics. Also notes the vehicle types now in the convoy."""
        if self._blocked(game):
            return
        owned = self._owned(game)
        if not owned <= self.vehicle_types_seen:
            self.vehicle_types_seen |= owned
            self.save()
        for achievement in ACHIEVEMENTS:
            cond = achievement["condition"]
            if achievement["id"] in self.completed or cond["kind"] not in ("wins", "vehicle_types_seen", "run_stat",
                                                                                "lifetime_counter", "screens_visited"):
                continue
            current, target = self.progress(achievement, game)
            if current >= target:
                self.unlock(game, achievement["id"])

    def on_victory(self, game):
        """The convoy reached the coast."""
        if self._blocked(game):
            return
        for achievement in ACHIEVEMENTS:
            cond = achievement["condition"]
            if cond["kind"] == "win_with_survivors" and game.survivors == cond["survivors"]:
                self.unlock(game, achievement["id"])
            elif cond["kind"] == "win_with_stat" and getattr(game, cond["stat"], 0) >= cond["count"]:
                self.unlock(game, achievement["id"])
            elif cond["kind"] == "win_without_stat" and getattr(game, cond["stat"], 0) <= cond["max"]:
                self.unlock(game, achievement["id"])
            elif cond["kind"] == "win_within_days" and game.day - 1 <= cond["days"]:
                # Game.day starts at 1, so the days that have passed are day - 1. The evacuation adds none.
                self.unlock(game, achievement["id"])
            elif cond["kind"] == "win_on_difficulty" and game.difficulty == cond["difficulty"]:
                self.unlock(game, achievement["id"])
            elif cond["kind"] == "win_with_convoy":
                owned = self._owned(game)
                if (set(cond["vehicles"]) <= owned and game.vehicles
                        and all(v.has_upgrade(cond["upgrade"]) for v in game.vehicles)):
                    self.unlock(game, achievement["id"])
        self.counters["wins"] += 1
        self.save()
        self.check(game)

    def on_defeat(self, game):
        """The run was lost because no survivor is left (Game.end_run only calls this in that case)."""
        if not self._blocked(game):
            for achievement in ACHIEVEMENTS:
                if achievement["condition"]["kind"] == "defeat":
                    self.unlock(game, achievement["id"])

    def on_arrival(self, game):
        """The convoy arrived at a stop."""
        if not self._blocked(game):
            owned = self._owned(game)
            for achievement in ACHIEVEMENTS:
                cond = achievement["condition"]
                if cond["kind"] == "arrive_with_vehicle" and cond["vehicle"] in owned:
                    self.unlock(game, achievement["id"])
        self.check(game)

    def on_screen(self, game, screen):
        """Game.screen was set to `screen` (StateMixin.screen property): note it, and complete "Field Study" once every
        screen of SCREENS_TO_VISIT has been shown. Screens are player progress, so SANDBOX MODE blocks them like the rest."""
        if (not isinstance(screen, str) or screen in self.screens_seen or len(self.screens_seen) >= MAX_SCREENS_SEEN
                or self._blocked(game)):
            return
        self.screens_seen.add(screen)
        self.save()
        for achievement in ACHIEVEMENTS:
            if achievement["condition"]["kind"] == "screens_visited" and achievement["id"] not in self.completed:
                current, target = self.progress(achievement, game)
                if current >= target:
                    self.unlock(game, achievement["id"])

    def on_vehicle_recovered(self, game):
        """A vehicle was recovered with RECOVER VEHICLE: count it towards the lifetime total ("Salvage Legend")."""
        if self._blocked(game):
            return
        self.counters["vehicles_recovered"] = self.counters.get("vehicles_recovered", 0) + 1
        self.save()
        self.check(game)

    def on_event(self, game, event_id):
        """An event was resolved (event_id may be None when it is not known)."""
        if event_id is not None and not self._blocked(game):
            owned = self._owned(game)
            for achievement in ACHIEVEMENTS:
                cond = achievement["condition"]
                if (cond["kind"] == "event" and event_id in cond["events"]
                        and cond.get("vehicle", None) in (None, *owned)):
                    self.unlock(game, achievement["id"])
        self.check(game)   # an event can add a vehicle


def unwired(event_ids=None, vehicle_names=None):
    """Achievements that cannot be completed yet because an event id or vehicle name they need does not exist.
    Placeholder achievements are skipped (they are known not to be wired). Returns a list of (achievement id, what is
    missing). Pass the real ids / names; None skips that kind of check."""
    problems = []
    for achievement in ACHIEVEMENTS:
        if achievement.get("placeholder"):
            continue
        cond = achievement["condition"]
        if cond["kind"] == "event":
            if event_ids is not None:
                problems += [(achievement["id"], f"event {e!r}") for e in cond["events"] if e not in event_ids]
            if vehicle_names is not None and cond.get("vehicle") and cond["vehicle"] not in vehicle_names:
                problems.append((achievement["id"], f"vehicle {cond['vehicle']!r}"))
        elif cond["kind"] == "arrive_with_vehicle" and vehicle_names is not None and cond["vehicle"] not in vehicle_names:
            problems.append((achievement["id"], f"vehicle {cond['vehicle']!r}"))
        elif cond["kind"] == "win_with_convoy" and vehicle_names is not None:
            problems += [(achievement["id"], f"vehicle {v!r}") for v in cond["vehicles"] if v not in vehicle_names]
    return problems
