"""The TRAVELLING... banner drawn over the top of the convoy scene while the convoy is on the road."""
import pygame

from textscale import tpx
from theme import BLUE, MUTED, PANEL, WHITE, YELLOW
from .convoy import scene_rect
from widgets import PIX, draw_frame, draw_panel, fit_variants, scaled_font, text_in_rect

DOT_STEP_MS = 400   # one more dot every 0.4 s: "TRAVELLING", "TRAVELLING.", "TRAVELLING.." ...


def draw_travel_banner(surface, game, layout):
    """One slim strip across the top of the scene (over its "WEST <---" / "CONVOY ON THE ROAD" captions, clear of the
    vehicles even in a small window): "TRAVELLING... to <stop> - day x of y", a hint that SPACE speeds it up, and a
    progress bar along its bottom edge. The event log below stays visible."""
    journey = game.journey
    if not journey:
        return
    k = layout["k"]
    scene = scene_rect(layout["scene"])   # the rectangle the scene art is drawn in (it can be wider than layout["scene"])
    pad = tpx(6, k)
    rect = pygame.Rect(scene.x + pad, scene.y + pad, max(120, scene.w - 2 * pad), tpx(28, k))
    draw_panel(surface, rect, PANEL, 1)
    draw_frame(surface, rect, YELLOW, PIX)

    font = scaled_font(surface.get_size(), 15)
    dots = "." * (pygame.time.get_ticks() // DOT_STEP_MS % 4)
    title = f"TRAVELLING{dots:<3}"   # padded, so the text does not jump while the dots change
    dest = game.current_location.replace("On the road to ", "")
    day, days = min(journey["day"], journey["days"]), journey["days"]
    inner = rect.w - 2 * pad
    line = fit_variants(font, inner, (
        f"{title} to {dest}  -  day {day} of {days}   |   hold SPACE: faster",
        f"{title} to {dest}  -  day {day} of {days}",
        f"{title} {dest}  {day}/{days}", f"{title} {day}/{days}", title))
    text_in_rect(surface, line, (rect.x + pad, rect.y + tpx(2, k), inner, rect.h - tpx(8, k)), WHITE, font, "center")

    bar = pygame.Rect(rect.x + pad, rect.bottom - tpx(6, k), inner, max(3, tpx(3, k)))
    pygame.draw.rect(surface, MUTED, bar, 1)
    done = bar.copy()
    done.w = int(bar.w * day / max(1, days))
    pygame.draw.rect(surface, BLUE, done)
