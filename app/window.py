"""Window management: creates and manages the game window, resizing, fullscreen,
desktop-size detection and DPI-awareness handling."""

import os
import sys

import pygame

from platform_web import IS_WEB, stretch_canvas_to_page, viewport_size


MIN_SIZE = (640, 480) # the smallest window

WINDOWED_SIZE = None              # the window size to come back to when fullscreen ends
window_fullscreen = False         # the mode the window is in now (game.fullscreen is the mode that is wanted)
_web_frames = 0                   # web only: frames seen by fit_web_viewport (re-applies the canvas styles now and then)


def enable_dpi_awareness():
    """Windows only: request real-pixel window coordinates.

    Currently disabled because it caused the initial window to appear
    extremely small on scaled Windows displays.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor (Windows 8.1+)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()       # older Windows
    except Exception:
        pass


def initialize_windowed_size(width, height):
    """Set the windowed size to the game's default dimensions."""
    global WINDOWED_SIZE
    WINDOWED_SIZE = [width, height]


def desktop_size():
    """Return the desktop size, or None if pygame cannot determine it."""
    try:
        sizes = pygame.display.get_desktop_sizes() if hasattr(
            pygame.display, "get_desktop_sizes"
        ) else []

        if sizes:
            return tuple(sizes[0])

        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return info.current_w, info.current_h

    except pygame.error:
        pass

    return None


def window_fills(surface, size):
    """Check that the pygame surface and OS window have the same size."""
    if surface is None or tuple(surface.get_size()) != tuple(size):
        return False

    if hasattr(pygame.display, "get_window_size"):
        try:
            return tuple(pygame.display.get_window_size()) == tuple(size)
        except pygame.error:
            return True

    return True


def move_window_to_origin():
    """Move a borderless window to the top-left of the screen."""
    try:
        from pygame._sdl2.video import Window
        Window.from_display_module().position = (0, 0)
    except Exception:
        pass


def open_fullscreen():
    """Open fullscreen at the desktop's resolution, with a borderless fallback."""
    size = desktop_size()

    if size is None:
        raise pygame.error("desktop size unknown")

    try:
        surface = pygame.display.set_mode(size, pygame.FULLSCREEN)

        if window_fills(surface, size):
            return surface

    except pygame.error:
        pass

    previous = os.environ.get("SDL_VIDEO_WINDOW_POS")
    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    try:
        surface = pygame.display.set_mode(size, pygame.NOFRAME)
    finally:
        if previous is None:
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
        else:
            os.environ["SDL_VIDEO_WINDOW_POS"] = previous

    move_window_to_origin()

    if window_fills(surface, size):
        return surface

    raise pygame.error("fullscreen window does not fill the screen")


def open_windowed():
    """Restore the resizable window, respecting minimum and desktop dimensions."""
    width, height = WINDOWED_SIZE

    width = max(MIN_SIZE[0], int(width))
    height = max(MIN_SIZE[1], int(height))

    desktop = desktop_size()

    if desktop:
        width = min(width, max(MIN_SIZE[0], desktop[0]))
        height = min(height, max(MIN_SIZE[1], desktop[1]))

    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def fit_web_viewport(surface):
    """Browser only: make the drawing surface the same size (and so shape) as the page's viewport.

    pygbag scales the canvas to fit the page while keeping the surface's aspect ratio, so a surface whose shape differs
    from the page leaves grey bars. Matching the surface to the viewport removes them; the layout code already adapts
    to any size. Returns the surface to draw on (a new one only when the size changed). No-op on the desktop."""
    if not IS_WEB:
        return surface

    wanted = viewport_size()
    if wanted is None:
        return surface

    global _web_frames
    _web_frames += 1

    wanted = (max(MIN_SIZE[0], wanted[0]), max(MIN_SIZE[1], wanted[1]))
    if surface is not None and tuple(surface.get_size()) == wanted:
        if _web_frames % 60 == 0:
            stretch_canvas_to_page()   # the page's own script may restyle the canvas: put it back about once a second
        return surface

    try:
        surface = pygame.display.set_mode(wanted, pygame.RESIZABLE)
    except pygame.error:
        surface = pygame.display.get_surface() or surface

    stretch_canvas_to_page()   # the canvas's box on the page follows the new surface size
    return surface


def set_window_mode(surface, fullscreen):
    """Switch window mode and return the resulting surface and actual mode."""
    global WINDOWED_SIZE, window_fullscreen

    if fullscreen == window_fullscreen:
        return surface, window_fullscreen

    if IS_WEB:
        # In the browser the canvas is already sized by the page; fullscreen is the browser's own, asked for with
        # toggle_fullscreen (it may need a user gesture, so a failure just leaves the mode as it was).
        try:
            pygame.display.toggle_fullscreen()
            window_fullscreen = fullscreen
        except Exception:
            pass
        return pygame.display.get_surface() or surface, window_fullscreen

    try:
        if fullscreen:
            if surface is not None and not window_fullscreen:
                WINDOWED_SIZE[:] = surface.get_size()

            surface = open_fullscreen()

        else:
            surface = open_windowed()

        window_fullscreen = fullscreen

    except pygame.error:
        if fullscreen:          # fullscreen failed part-way: make sure a normal window is open again
            try:
                surface = open_windowed()
            except pygame.error:
                surface = pygame.display.get_surface() or surface

            window_fullscreen = False

    return surface, window_fullscreen
