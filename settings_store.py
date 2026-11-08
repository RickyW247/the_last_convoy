"""Saved player settings for THE LAST CONVOY (the accessibility options, fullscreen, text size and music volume),
kept in settings.json in a folder that belongs to the player (temporary or permanent, see USE_TEMP_FOLDER).

No pygame here. Loading never fails: a missing or damaged file just means the default settings, and a file that
cannot be written is ignored (the options still work for this session).
"""
import json
import os
import stat
import sys
import tempfile

import textscale
import theme
from platform_web import IS_WEB, storage_read, storage_write

APP_FOLDER = "TheLastConvoy"
# True: settings live in the system's temporary folder, so they are not permanent (the system may clear them, on
# Linux usually at reboot). False: the per-user configuration folder, where they stay until the player deletes them.
USE_TEMP_FOLDER = True


def _temp_dir():
    """A folder in the system's temp directory that belongs to this player (/tmp is shared between users)."""
    try:
        owner = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "")
    except OSError:
        owner = ""
    return os.path.join(tempfile.gettempdir(), f"{APP_FOLDER}-{owner}" if owner else APP_FOLDER)


def _settings_dir():
    """The folder for settings: temporary or per-user (see USE_TEMP_FOLDER); never the game's own folder, which
    may be read-only once the game is installed."""
    if USE_TEMP_FOLDER:
        return _temp_dir()
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, APP_FOLDER)


SETTINGS_PATH = os.path.join(_settings_dir(), "settings.json")
# Where earlier versions kept the file (next to the code). With the permanent folder it is still read once if there
# is no new file yet, so players keep their settings; it is never written. Temporary settings ignore it, so an old
# permanent file can't bring back values that were meant to be gone.
LEGACY_PATH = None if USE_TEMP_FOLDER else os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
KEYS = ("high_contrast", "colorblind")   # the accessibility options (theme.ACCESS)
DISPLAY_KEYS = ("fullscreen",)           # the display options

_display = {key: False for key in DISPLAY_KEYS}   # the display options as last loaded / set

# Options with a value rather than on / off: the text size level (a name such as the one textscale.text_level()
# returns) and the music volume (0.0-1.0). None means "never saved": the game's own default applies.
_values = {"text_level": None, "music_volume": None, "music_muted": False, "sfx_volume": None}


MAX_FILE_BYTES = 64 * 1024   # a real settings file is a few hundred bytes; anything bigger is not ours


def _folder_is_ours(folder):
    """On Linux and macOS /tmp is shared, so someone else could create the folder first (or make it a link) and
    then read or steer what the game writes. Only trust a real folder owned by this user that nobody else can
    write to. (Windows temp folders are already private to each user.)"""
    if not hasattr(os, "getuid"):
        return True
    try:
        info = os.lstat(folder)
    except OSError:
        return False
    return (stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and info.st_uid == os.getuid() and not info.st_mode & 0o022)


def _read():
    """The settings file as a dict ({} when it is missing, damaged, too big or in a folder that isn't ours)."""
    data = {}
    if IS_WEB:   # the browser keeps settings in localStorage, not in files
        raw = storage_read("settings.json")
        try:
            data = json.loads(raw) if raw and len(raw) <= MAX_FILE_BYTES else {}
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {}
    for path in (SETTINGS_PATH, LEGACY_PATH):
        if not path or not os.path.exists(path):
            continue
        try:
            if not _folder_is_ours(os.path.dirname(path)) and path == SETTINGS_PATH:
                break
            with open(path, "rb") as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            data = json.loads(raw.decode("utf-8")) if len(raw) <= MAX_FILE_BYTES else {}
        except (OSError, ValueError):
            data = {}
        break   # the first file that exists is the one used, even if it is damaged
    return data if isinstance(data, dict) else {}


def load():
    """The saved accessibility options as a dict of bools (missing keys are False)."""
    data = _read()
    return {key: data.get(key) is True for key in KEYS}


def load_display():
    """The saved display options (fullscreen) as a dict of bools (missing keys are False)."""
    data = _read()
    return {key: data.get(key) is True for key in DISPLAY_KEYS}


def load_text_level():
    """The saved text size level (a string), or None when nothing usable is saved. The caller checks that the
    name is still one of the levels it knows."""
    value = _read().get("text_level")
    return value if isinstance(value, str) and 0 < len(value) <= 32 else None


def _volume(value):
    """`value` from the file as a float from 0.0 to 1.0, or None when it is not a usable number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    return max(0.0, min(1.0, float(value)))


def load_music_volume():
    """The saved music volume as a float from 0.0 to 1.0, or None when nothing usable is saved."""
    return _volume(_read().get("music_volume"))


def load_sfx_volume():
    """The saved sound-effect volume as a float from 0.0 to 1.0, or None when nothing usable is saved."""
    return _volume(_read().get("sfx_volume"))


def load_music_muted():
    """Whether the music was muted when last saved (False when nothing usable is saved)."""
    return _read().get("music_muted") is True


def save(options=None):
    """Write the options (default: the accessibility ones currently on in theme.ACCESS) and the display options."""
    options = theme.ACCESS if options is None else options
    data = {key: bool(options.get(key)) for key in KEYS}
    data.update({key: bool(_display[key]) for key in DISPLAY_KEYS})
    data.update({key: value for key, value in _values.items() if value is not None})
    if IS_WEB:
        storage_write("settings.json", json.dumps(data))
        return
    folder = os.path.dirname(SETTINGS_PATH)
    temporary = None
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        if not _folder_is_ours(folder):
            return   # not our folder: keep the settings for this session only
        # Write a new private file next to the real one, then swap it in. The swap replaces whatever is at the
        # path (even a link someone placed there) instead of writing through it, and a crash mid-write can never
        # leave a half-written settings file.
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder, prefix="settings-", suffix=".tmp",
                                             delete=False)
        temporary = handle.name
        with handle:
            json.dump(data, handle, indent=2)
        os.replace(temporary, SETTINGS_PATH)
        temporary = None
    except OSError:
        pass
    finally:
        if temporary:
            try:
                os.remove(temporary)
            except OSError:
                pass


def apply_saved():
    """Switch the palette and the text size to the saved options and remember the saved display and volume options
    (call once at start-up; the music volume is applied where the MusicManager is made, see state.py)."""
    theme.set_accessibility(**load())
    _display.update(load_display())
    _values["text_level"] = load_text_level()
    _values["music_volume"] = load_music_volume()
    _values["music_muted"] = load_music_muted()
    _values["sfx_volume"] = load_sfx_volume()
    level = _values["text_level"]
    if level is not None:
        if level in dict(textscale.TEXT_LEVELS):
            textscale.set_text_level(level)   # only a level the game knows is ever applied
        else:
            _values["text_level"] = None      # unknown name: ignore it (and don't save it back)


def toggle(name):
    """Flip one option, recolour the game and save the result."""
    theme.set_accessibility(**{name: not theme.ACCESS[name]})
    save()


def set_fullscreen(on):
    """Remember (and save) whether the game runs fullscreen."""
    _display["fullscreen"] = bool(on)
    save()


def saved_text_level():
    """The text size level to start with (None: keep the default). Valid after apply_saved()."""
    return _values["text_level"]


def saved_music_volume():
    """The music volume to start with (None: keep the default). Valid after apply_saved()."""
    return _values["music_volume"]


def saved_music_muted():
    """Whether the music starts muted (False: not muted). Valid after apply_saved()."""
    return _values["music_muted"]


def set_music_muted(muted):
    """Remember (and save) whether the music is muted. Does nothing when the value has not changed."""
    muted = bool(muted)
    if _values["music_muted"] != muted:
        _values["music_muted"] = muted
        save()


def saved_sfx_volume():
    """The sound-effect volume to start with (None: keep the default). Valid after apply_saved()."""
    return _values["sfx_volume"]


def set_sfx_volume(volume):
    """Remember (and save) the sound-effect volume (0.0-1.0; 0 is silent)."""
    _values["sfx_volume"] = max(0.0, min(1.0, float(volume)))
    save()


def set_text_level(name):
    """Remember (and save) the chosen text size level."""
    _values["text_level"] = str(name)
    save()


def set_music_volume(volume):
    """Remember (and save) the music volume (0.0-1.0). When the player drags the slider, call this when the mouse
    is released, not on every movement, so the file is written once."""
    _values["music_volume"] = max(0.0, min(1.0, float(volume)))
    save()
