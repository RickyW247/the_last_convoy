"""Save and load for THE LAST CONVOY: three save slots, each one JSON file (no pygame).

Files live next to settings.json, in the same folder logic (settings_store.USE_TEMP_FOLDER): for now the system's
temporary folder, so saves are NOT permanent (the system may clear them). Set USE_TEMP_FOLDER = False there and the
saves move to the permanent per-user data folder: <folder>/TheLastConvoy/saves/slot1.json ... slot3.json.

Writing is safe: the new file is written next to the real one and swapped in with os.replace, so a crash can never
leave a half-written save. Loading never trusts the file: _parse checks every field and raises SaveError with a message
for the player, and nothing in the running game is touched until the whole file has passed. The map layout is the one
thing that must be switched before the last checks (they need the stops), so a failure after that puts the previous
layout back.

What is saved is the state of the run (supplies, survivors, vehicles and upgrades, position, journey, horde, day,
log and history, missions, conditions, run statistics, difficulty and sandbox). Settings (volumes, text size, ...)
and achievements (achievements.py, achievements.json) are not part of a save: they belong to the player. A run can be saved while it is going on (also mid-journey), not while an event, a result or
a vehicle choice is waiting for the player.
"""
import json
import os
import sys
import tempfile
import time

import map_data
import settings_store
from platform_web import IS_WEB, storage_delete, storage_exists, storage_read, storage_write
from config import DIFFICULTIES, HORDE_STATES, TRAVEL_DAY_DELAY
from game import Vehicle
from map_data import NODES, load_layout
from vehicle_data import VEHICLE_SPECS

APP_FOLDER = "TheLastConvoy"
GAME_VERSION = "2.0"        # the game version that wrote the file (informational)
SAVE_VERSION = 1             # the file format: raise it when the layout changes, and keep reading the old ones
SLOT_COUNT = 3
MAX_FILE_BYTES = 8 * 1024 * 1024   # a real save is some tens of KB (the history grows with the run)
MISSION_STATUSES = ("Locked", "Available", "Active", "Completed", "Failed")
BAD_FILE = "This file is not a valid save game."


class SaveError(Exception):
    """A save could not be written or read; the text is meant for the player."""


def _save_dir():
    """The folder for saves: temporary or per-user, following settings_store.USE_TEMP_FOLDER (the game's own folder
    may be read-only once installed)."""
    if settings_store.USE_TEMP_FOLDER:
        return os.path.join(settings_store._temp_dir(), "saves")
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, APP_FOLDER, "saves")


SAVE_DIR = _save_dir()   # tests point this at a temporary folder


def slot_path(slot):
    """The file of slot `slot` (0, 1 or 2; the screens call them 1 to 3)."""
    if not isinstance(slot, int) or not 0 <= slot < SLOT_COUNT:
        raise SaveError("There is no such save slot.")
    return os.path.join(SAVE_DIR, f"slot{slot + 1}.json")


# ---- Files -------------------------------------------------------------------------------------------------------
def write_slot(slot, data):
    """Write `data` (a dict) as slot `slot`, replacing what was there."""
    path = slot_path(slot)
    try:
        text = json.dumps(data, separators=(",", ":"))
    except (TypeError, ValueError):
        raise SaveError("The game could not be turned into a save file.")
    if IS_WEB:   # the browser keeps saves in localStorage
        if not storage_write(f"slot{slot + 1}.json", text):
            raise SaveError("The save could not be stored (is the browser's storage full or blocked?).")
        refresh_summaries()
        return
    temporary = None
    try:
        os.makedirs(SAVE_DIR, mode=0o700, exist_ok=True)
        if settings_store.USE_TEMP_FOLDER and not settings_store._folder_is_ours(SAVE_DIR):
            raise SaveError("The save folder is not safe to use (it belongs to someone else).")
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=SAVE_DIR, prefix=f"slot{slot + 1}-",
                                             suffix=".tmp", delete=False)
        temporary = handle.name
        with handle:
            handle.write(text)
        os.replace(temporary, path)
        temporary = None
    except SaveError:
        raise
    except OSError:
        raise SaveError("The save file could not be written (is the disk full or the folder read-only?).")
    finally:
        if temporary:
            try:
                os.remove(temporary)
            except OSError:
                pass
    refresh_summaries()


def read_slot(slot):
    """The parsed JSON of slot `slot`. Raises SaveError when it is empty, too big, unreadable or not JSON."""
    path = slot_path(slot)
    if IS_WEB:
        raw = storage_read(f"slot{slot + 1}.json")
        if raw is None:
            raise SaveError("This slot is empty.")
        try:
            return json.loads(raw)
        except ValueError:
            raise SaveError("This save file is damaged and cannot be read.")
    if not os.path.isfile(path):
        raise SaveError("This slot is empty.")
    if settings_store.USE_TEMP_FOLDER and not settings_store._folder_is_ours(SAVE_DIR):
        raise SaveError("The save folder is not safe to use (it belongs to someone else).")
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise SaveError("This save file is too big to be a save game.")
        return json.loads(raw.decode("utf-8"))
    except SaveError:
        raise
    except (OSError, ValueError):
        raise SaveError("This save file is damaged and cannot be read.")


def delete_slot(slot):
    """Delete slot `slot`. Returns the message to show."""
    path = slot_path(slot)
    if IS_WEB:
        storage_delete(f"slot{slot + 1}.json")
        refresh_summaries()
        return f"Slot {slot + 1} deleted."
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        refresh_summaries()
        return "The save file could not be deleted."
    refresh_summaries()
    return f"Slot {slot + 1} deleted."


# ---- What the slot cards show (read once, then kept until something changes) ---------------------------------
_summaries = None


def refresh_summaries():
    """Forget the cached slot summaries (the next slot_summaries() reads the files again)."""
    global _summaries
    _summaries = None


def _summary_of(slot):
    """None for an empty slot, {"damaged": True, "reason": ...} for a file that cannot be loaded, else the summary dict."""
    if IS_WEB:
        if not storage_exists(f"slot{slot + 1}.json"):
            return None
    elif not os.path.isfile(slot_path(slot)):
        return None
    try:
        data = read_slot(slot)
        if not isinstance(data, dict) or not isinstance(data.get("version"), int) or not isinstance(data.get("state"), dict):
            raise SaveError(BAD_FILE)
        if data["version"] > SAVE_VERSION:
            raise SaveError("Saved by a newer version of the game.")
        summary = data.get("summary")
        summary = summary if isinstance(summary, dict) else {}
    except SaveError as problem:
        return {"damaged": True, "reason": str(problem)}
    return {"damaged": False, "saved_at": str(summary.get("saved_at", "")), "day": summary.get("day"),
            "location": str(summary.get("location", "")), "survivors": summary.get("survivors"),
            "vehicles": summary.get("vehicles"), "difficulty": str(summary.get("difficulty", "")),
            "sandbox": summary.get("sandbox") is True}


def slot_summaries():
    """A list of SLOT_COUNT summaries (see _summary_of), cached."""
    global _summaries
    if _summaries is None:
        _summaries = [_summary_of(slot) for slot in range(SLOT_COUNT)]
    return _summaries


# ---- Game -> dict ------------------------------------------------------------------------------------------------
def to_dict(game):
    """The savable state of `game` as plain JSON data."""
    journey = dict(game.journey) if game.journey else None
    state = {
        "difficulty": game.difficulty,
        "sandbox": bool(game.sandbox),
        "sandbox_used": bool(game.sandbox or getattr(game, "sandbox_used", False)),
        "map_layout": game.map_layout_name,
        "fuel": game.fuel, "food": game.food, "water": game.water, "scrap": game.scrap,
        "survivors": game.survivors,
        "survivor_records": [dict(record) for record in game.survivor_manager.survivors],
        "vehicles": [{"type": v.vehicle_type, "health": v.health, "upgrades": list(v.upgrades)}
                     for v in game.vehicles],
        "vehicle_upgrades": {name: list(ids) for name, ids in game.vehicle_upgrades.items()},
        "selected_vehicle_type": game.selected_vehicle_type,
        "position": game.position,
        "current_location": game.current_location,
        "selected": game.selected,
        "horde_km": game.horde_km,
        "last_horde_state": game.last_horde_state,
        "horde_attack_streak": getattr(game, "horde_attack_streak", 0),
        "day": game.day,
        "journey": journey,
        "travel_count": game.travel_count,
        "scene_scroll": game.scene_scroll,
        "log": list(game.log),
        "history": list(game.history),
        "visited": sorted(game.visited),
        "km_traveled": game.km_traveled,
        "vehicles_start": game.vehicles_start,
        "vehicles_recovered": game.vehicles_recovered,
        "vehicles_gained": game.vehicles_gained,
        "missions": {mission_id: {"status": m["status"], "progress": list(m["progress"]), "stage": m.get("stage", 0)}
                     for mission_id, m in game.mission_manager.missions.items()},
        "last_event_ids": list(game.event_manager.last_event_ids),
        "conditions": dict(getattr(game, "conditions", {}) or {}),
        "condition_losses": dict(getattr(game, "condition_losses", {}) or {}),
    }
    return {
        "version": SAVE_VERSION,
        "game_version": GAME_VERSION,
        "summary": {"saved_at": time.strftime("%Y-%m-%d %H:%M"), "day": game.day, "location": game.current_location,
                    "survivors": game.survivors, "vehicles": len(game.vehicles), "difficulty": game.difficulty,
                    "sandbox": bool(game.sandbox)},
        "state": state,
    }


# ---- dict -> checked values ----------------------------------------------------------------------------------
def _num(value, name, low=0, high=10 ** 7, integer=True):
    """`value` as a number from `low` to `high`, or SaveError. integer=True also refuses fractions."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        raise SaveError(f"{BAD_FILE} ({name})")
    if integer and isinstance(value, float):
        if value != int(value):
            raise SaveError(f"{BAD_FILE} ({name})")
        value = int(value)
    if not low <= value <= high:
        raise SaveError(f"{BAD_FILE} ({name})")
    return value


def _text(value, name, limit=300):
    if not isinstance(value, str) or len(value) > limit:
        raise SaveError(f"{BAD_FILE} ({name})")
    return value


def _str_list(value, name):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SaveError(f"{BAD_FILE} ({name})")
    return list(value)


def _parse(data):
    """Check a loaded file and return the clean values (a dict) _commit puts into the game. Touches nothing."""
    if not isinstance(data, dict):
        raise SaveError(BAD_FILE)
    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise SaveError(BAD_FILE)
    if version > SAVE_VERSION:
        raise SaveError("This save was made by a newer version of the game.")
    s = data.get("state")
    if not isinstance(s, dict):
        raise SaveError(BAD_FILE)

    p = {}
    if s.get("difficulty") not in DIFFICULTIES:
        raise SaveError(f"{BAD_FILE} (difficulty)")
    p["difficulty"] = s["difficulty"]
    p["sandbox"] = s.get("sandbox") is True
    p["sandbox_used"] = p["sandbox"] or s.get("sandbox_used") is True   # older saves have no key: only sandbox itself counts
    p["map_layout"] = _text(s.get("map_layout"), "map layout", 80)
    for name in ("fuel", "food", "water", "scrap"):
        p[name] = _num(s.get(name), name, 0, 10 ** 6)

    records = s.get("survivor_records")
    if not isinstance(records, list) or not records:
        raise SaveError(f"{BAD_FILE} (survivors)")
    ids = set()
    for record in records:
        if not isinstance(record, dict) or "id" not in record or "can_drive" not in record:
            raise SaveError(f"{BAD_FILE} (survivors)")
        try:
            if record["id"] in ids:
                raise SaveError(f"{BAD_FILE} (survivors)")
            ids.add(record["id"])
        except TypeError:
            raise SaveError(f"{BAD_FILE} (survivors)")
    p["survivor_records"] = [dict(record) for record in records]
    p["survivors"] = _num(s.get("survivors"), "survivors", 1, 10 ** 5)
    if p["survivors"] != len(records):
        raise SaveError(f"{BAD_FILE} (survivors)")

    raw_vehicles = s.get("vehicles")
    if not isinstance(raw_vehicles, list) or not 1 <= len(raw_vehicles) <= len(VEHICLE_SPECS):
        raise SaveError(f"{BAD_FILE} (vehicles)")
    vehicles, seen = [], set()
    for item in raw_vehicles:
        if not isinstance(item, dict) or item.get("type") not in VEHICLE_SPECS or item["type"] in seen:
            raise SaveError(f"{BAD_FILE} (vehicles)")
        seen.add(item["type"])
        upgrades = _str_list(item.get("upgrades", []), "upgrades")
        vehicle = Vehicle(item["type"], upgrades)
        if len(vehicle.upgrades) != len(upgrades):
            raise SaveError(f"{BAD_FILE} (an upgrade that does not exist or does not fit)")
        health = _num(item.get("health"), "vehicle health", 0, 10 ** 6)
        vehicle.health = max(1, min(health, vehicle.stats["health"]))
        vehicles.append(vehicle)
    p["vehicles"] = vehicles

    remembered = s.get("vehicle_upgrades", {})
    if not isinstance(remembered, dict):
        raise SaveError(f"{BAD_FILE} (upgrades)")
    p["vehicle_upgrades"] = {_text(name, "upgrades", 80): _str_list(ids, "upgrades") for name, ids in remembered.items()}
    chosen = s.get("selected_vehicle_type")
    p["selected_vehicle_type"] = chosen if chosen in VEHICLE_SPECS else vehicles[0].vehicle_type

    p["position"] = _num(s.get("position"), "position", 0, 10 ** 4)
    p["selected"] = _num(s.get("selected"), "selected stop", 0, 10 ** 4)
    p["current_location"] = _text(s.get("current_location"), "location", 200)
    p["horde_km"] = _num(s.get("horde_km"), "horde", -10 ** 6, 10 ** 6, integer=False)
    if s.get("last_horde_state") not in HORDE_STATES:
        raise SaveError(f"{BAD_FILE} (horde)")
    p["last_horde_state"] = s["last_horde_state"]
    p["horde_attack_streak"] = _num(s.get("horde_attack_streak", 0), "horde attacks", 0, 10 ** 5)
    p["day"] = _num(s.get("day"), "day", 1, 10 ** 6)
    p["travel_count"] = _num(s.get("travel_count"), "travels", 0, 10 ** 6)
    p["scene_scroll"] = _num(s.get("scene_scroll"), "scene", -10 ** 6, 10 ** 6)
    for name in ("km_traveled", "vehicles_start", "vehicles_recovered", "vehicles_gained"):
        p[name] = _num(s.get(name), name, 0, 10 ** 7)

    journey = s.get("journey")
    if journey is None:
        p["journey"] = None
    else:
        if not isinstance(journey, dict):
            raise SaveError(f"{BAD_FILE} (journey)")
        days = _num(journey.get("days"), "journey", 1, 1000)
        p["journey"] = {
            "dest": _num(journey.get("dest"), "journey", 0, 10 ** 4),
            "km": _num(journey.get("km"), "journey", 0, 10 ** 5),
            "days": days,
            "day": _num(journey.get("day"), "journey", 0, days),
            "axis_to": _num(journey.get("axis_to"), "journey", -10 ** 4, 10 ** 4),
            "delta": _num(journey.get("delta"), "journey", -10 ** 4, 10 ** 4),
            "fuel": _num(journey.get("fuel"), "journey", 0, 10 ** 5),
            "wear": _num(journey.get("wear", 0), "journey", 0, 100),
        }

    log = s.get("log")
    if not isinstance(log, list) or any(not isinstance(line, str) for line in log) or len(log) > 100:
        raise SaveError(f"{BAD_FILE} (log)")
    p["log"] = list(log)[:4]
    history = s.get("history")
    if not isinstance(history, list) or len(history) > 200000:
        raise SaveError(f"{BAD_FILE} (history)")
    p["history"] = list(history)
    visited = s.get("visited")
    if not isinstance(visited, list):
        raise SaveError(f"{BAD_FILE} (visited stops)")
    p["visited"] = {_num(stop, "visited stops", 0, 10 ** 4) for stop in visited}

    missions = s.get("missions", {})
    if not isinstance(missions, dict):
        raise SaveError(f"{BAD_FILE} (missions)")
    p["missions"] = {}
    for mission_id, state in missions.items():   # a mission this version no longer has is simply skipped
        if not isinstance(state, dict) or state.get("status") not in MISSION_STATUSES:
            raise SaveError(f"{BAD_FILE} (missions)")
        progress = state.get("progress")
        if not isinstance(progress, list) or any(isinstance(n, bool) or not isinstance(n, (int, float)) for n in progress):
            raise SaveError(f"{BAD_FILE} (missions)")
        stage = state.get("stage", 0)   # older saves have no stage: the first one
        if isinstance(stage, bool) or not isinstance(stage, int) or not 0 <= stage < 100:
            raise SaveError(f"{BAD_FILE} (missions)")
        p["missions"][mission_id] = {"status": state["status"], "progress": list(progress), "stage": stage}

    last = s.get("last_event_ids", [])
    if not isinstance(last, list):
        raise SaveError(f"{BAD_FILE} (events)")
    p["last_event_ids"] = list(last)[-2:]
    for name in ("conditions", "condition_losses"):
        value = s.get(name)
        if value is not None and not isinstance(value, dict):
            raise SaveError(f"{BAD_FILE} ({name})")
        p[name] = dict(value) if value else None
    return p


def _check_nodes(p):
    """The checks that need the stops of the saved map layout (the layout must be switched first)."""
    count = len(NODES)
    if not (p["position"] < count and p["selected"] < count and all(stop < count for stop in p["visited"])
            and (p["journey"] is None or p["journey"]["dest"] < count)):
        raise SaveError(f"{BAD_FILE} (a stop that is not on the map)")


def _apply_layout(name):
    """Switch the map to the predefined layout called `name`. Returns False when there is none of that name."""
    for index, layout in enumerate(map_data.LAYOUTS):
        if layout["name"] == name:
            load_layout(index)
            return True
    return False


# ---- Checked values -> game ----------------------------------------------------------------------------------
def _commit(game, p):
    """Put the checked values `p` into `game`, replacing the run (plain assignments: this cannot fail half way)."""
    game._fuel, game._food, game._water, game._scrap = p["fuel"], p["food"], p["water"], p["scrap"]
    game.sandbox = p["sandbox"]
    game.sandbox_used = p["sandbox_used"]
    game.difficulty = p["difficulty"]
    game.map_layout_name = p["map_layout"]
    game.survivors = p["survivors"]
    game.survivor_manager.survivors = p["survivor_records"]
    game.vehicles = p["vehicles"]
    game.vehicle_upgrades = p["vehicle_upgrades"]
    game.position = p["position"]
    game.current_location = p["current_location"]
    game.journey = p["journey"]
    game.selected = p["selected"]
    game.selected_site = 0
    game.horde_km = p["horde_km"]
    game.last_horde_state = p["last_horde_state"]
    game.horde_attack_streak = p["horde_attack_streak"]
    game.day = p["day"]
    game.travel_count = p["travel_count"]
    game.scene_scroll = p["scene_scroll"]
    game.log = p["log"]
    game.history = p["history"]
    game.history_scroll = 0
    game.history_return = "convoy"
    game.visited = p["visited"]
    game.km_traveled = p["km_traveled"]
    game.vehicles_start = p["vehicles_start"]
    game.vehicles_recovered = p["vehicles_recovered"]
    game.vehicles_gained = p["vehicles_gained"]
    game.status = "playing"
    game.end_reason = ""
    game.evacuation = None            # a loaded run is never in the Pacific evacuation (evacuation.py); it cannot be saved there
    game.survivors_left_behind = 0
    game.started = True

    game.event_manager = type(game.event_manager)()   # nothing is waiting on an event
    game.event_manager.last_event_ids = p["last_event_ids"]
    game.mission_manager = type(game.mission_manager)()
    for mission_id, saved in p["missions"].items():
        state = game.mission_manager.missions.get(mission_id)
        if state is not None:
            game.mission_manager.restore_stage(mission_id, saved["stage"])   # multi-stage missions: back to the saved stage
        if state is not None and len(saved["progress"]) == len(state["progress"]):
            state["status"], state["progress"] = saved["status"], saved["progress"]
    game.mission_page, game.mission_filter, game.survivor_page = 0, "Active", 0

    game.reset_conditions()
    if p["conditions"] is not None and isinstance(getattr(game, "conditions", None), dict):
        game.conditions.clear()
        game.conditions.update(p["conditions"])
    if p["condition_losses"] is not None:
        game.condition_losses = p["condition_losses"]
    if hasattr(game, "sync_conditions"):
        game.sync_conditions()

    game.selected_vehicle_type = p["selected_vehicle_type"]
    game.selected_upgrade = None
    game.abandon_confirm = game.abandon_pick = game.abandon_marks = None
    game.site_picker = False
    game.day_warning = None
    game.day_cost_pending = None
    game.uninstall_pending = None
    game.quit_armed = False
    game.survivor_vehicles = {}
    game.assign_survivors_to_vehicles()
    game.travel_delay = TRAVEL_DAY_DELAY if p["journey"] else 0.0   # a trip in progress carries on after a short pause
    game.screen = "convoy"     # (Game.screen also closes any pending popup)
    game.update_music()


def load_into(game, data):
    """Replace the run in `game` with the saved one in `data`, or raise SaveError and leave the run as it was."""
    p = _parse(data)
    previous = game.map_layout_name
    if not _apply_layout(p["map_layout"]):
        _apply_layout(previous)
        raise SaveError("This save uses a map layout that this version of the game does not have.")
    try:
        _check_nodes(p)
    except SaveError:
        _apply_layout(previous)
        raise
    _commit(game, p)


# ---- What the buttons call -------------------------------------------------------------------------------------
def save_problem(game):
    """Why the run cannot be saved right now, as a message, or "" when it can."""
    if not game.started:
        return "Start a game first: there is nothing to save yet."
    if game.status != "playing":
        return "The run is over: there is nothing to save."
    if game.event_manager.active or game.event_manager.result or game.abandon_pick_needed() or game.site_picker:
        return "Finish what is on screen first (an event, a result or a choice), then save."
    return ""


def save_slot(game, slot):
    """Save the run in slot `slot`. Returns (ok, message)."""
    problem = save_problem(game)
    if problem:
        return False, problem
    try:
        write_slot(slot, to_dict(game))
    except SaveError as error:
        return False, str(error)
    return True, f"Game saved to slot {slot + 1}."


def load_slot(game, slot):
    """Load slot `slot` into the game. Returns (ok, message); on a failure the run is unchanged."""
    try:
        load_into(game, read_slot(slot))
    except SaveError as error:
        return False, str(error)
    return True, f"Loaded slot {slot + 1}."
