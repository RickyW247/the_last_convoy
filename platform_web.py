"""Browser (pygbag / WebAssembly) support for THE LAST CONVOY. No pygame here.

IS_WEB is True only when the game runs inside a browser through pygbag (sys.platform == "emscripten"). On desktop
nothing in this module changes behaviour: every helper falls back to "not web".

Persistent storage: the browser's virtual file system is wiped on reload, so settings, achievements and the three
save slots are kept in the browser's localStorage instead (one key per file, prefixed with STORAGE_PREFIX). Values are
plain text (the JSON the game already writes). localStorage can be missing or full (private windows, blocked site data):
every call is wrapped so the game simply carries on without saving.
"""
import sys

IS_WEB = sys.platform == "emscripten"
STORAGE_PREFIX = "TheLastConvoy/"
MAX_VALUE_CHARS = 8 * 1024 * 1024   # same ceiling as savegame.MAX_FILE_BYTES

_window = None
if IS_WEB:
    try:
        import platform as _platform   # pygbag's platform module exposes the JavaScript window
        _window = _platform.window
    except Exception:
        _window = None


def _storage():
    """The browser's localStorage object, or None."""
    if _window is None:
        return None
    try:
        return _window.localStorage
    except Exception:
        return None


def storage_available():
    """True on the web when localStorage can be used."""
    return _storage() is not None


def storage_read(name):
    """The text saved under `name`, or None (missing, unreadable, or not on the web)."""
    store = _storage()
    if store is None:
        return None
    try:
        value = store.getItem(STORAGE_PREFIX + name)
    except Exception:
        return None
    if value is None:
        return None
    value = str(value)
    return value if len(value) <= MAX_VALUE_CHARS else None


def storage_write(name, text):
    """Save `text` under `name`. Returns True when it was stored."""
    store = _storage()
    if store is None:
        return False
    try:
        store.setItem(STORAGE_PREFIX + name, str(text))
        return True
    except Exception:
        return False   # full, or blocked


def storage_exists(name):
    return storage_read(name) is not None


def storage_delete(name):
    """Remove `name`. Returns True when the call went through (even if there was nothing to remove)."""
    store = _storage()
    if store is None:
        return False
    try:
        store.removeItem(STORAGE_PREFIX + name)
        return True
    except Exception:
        return False


def open_url(url):
    """Open a web address in a new browser tab (web only). Returns True when it was asked for."""
    if _window is None or not str(url).startswith(("https://", "http://")):
        return False
    try:
        _window.open(str(url), "_blank")
        return True
    except Exception:
        return False
