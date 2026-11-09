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


def viewport_size():
    """The browser page's inner size in CSS pixels as (width, height), or None (not on the web / unreadable)."""
    if _window is None:
        return None
    try:
        width, height = int(_window.innerWidth), int(_window.innerHeight)
    except Exception:
        return None
    return (width, height) if width > 0 and height > 0 else None


def stretch_canvas_to_page():
    """Web only: make the canvas fill the whole browser page, 1 drawing pixel per CSS pixel.

    pygbag's page keeps the canvas in a box of its own (the size of the first surface). When the surface is resized to the
    viewport, that box must follow, or the picture is squeezed into it. Returns True when the styles were set."""
    if _window is None:
        return False
    try:
        document = _window.document
        canvas = document.getElementById("canvas") or getattr(_window, "canvas", None)
        if canvas is None:
            return False
        style = canvas.style
        style.position = "fixed"
        style.left = "0px"
        style.top = "0px"
        style.width = "100vw"
        style.height = "100vh"
        style.margin = "0px"
        style.padding = "0px"
        style.border = "0px"
        style.setProperty("transform", "none")
        style.setProperty("image-rendering", "pixelated")   # scale up with sharp pixels, not a blurry smooth stretch
        body = document.body
        body.style.margin = "0px"
        body.style.padding = "0px"
        body.style.overflow = "hidden"
        body.style.background = "#000"
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
