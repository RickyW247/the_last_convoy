"""Small reusable UI pieces for THE LAST CONVOY: the Button class, a bar, text drawing and text helpers.

Text is never scaled: helpers pick a font that fits (pick_font), wrap by pixel width (wrap_pixels), and shorten
with "..." (fit_text, ellipsize) so that no string runs outside its rectangle. Rendered text surfaces are kept in
a small bounded cache (text_surface), so the same string is not rendered again every frame.
"""
import pygame

from textscale import text_k, text_px
from theme import (ACCESS, ANTIALIAS, BLUE, BORDER, DARK, DISABLED_BG, DISABLED_TEXT, FONT, PANEL_LIGHT, SMALL,
                   TEXT_FONTS, TEXT_SIZES, TINY, TITLE, WHITE, YELLOW)

# ---- Pixel-art building blocks -----------------------------------------------------------------------------------
PIX = 2   # one "pixel" of the UI frame in screen pixels: outlines, bevels and corner steps are whole multiples of it


def _lighter(color):
    return tuple(int(c + (255 - c) * 0.22) for c in tuple(color)[:3])


def _darker(color):
    return tuple(int(c * 0.6) for c in tuple(color)[:3])


def draw_panel(surface, rect, fill, raised=0, outline=None):
    """A pixel-art panel: hard edges, a one-step cut at each corner, a dark outline and a bevel (a light edge top and
    left and a dark one bottom and right). raised=1 looks like a button standing out, -1 like one pressed in or a
    sunken field, 0 is flat. The outline is the border colour in high contrast, else a dark colour."""
    rect = pygame.Rect(rect)
    if rect.w < 1 or rect.h < 1:
        return
    p = PIX
    outline = outline if outline is not None else (BORDER if ACCESS["high_contrast"] else DARK)
    if rect.w < 6 * p or rect.h < 6 * p:   # too small for the stepped corners
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, outline, rect, 1)
        return
    x, y, w, h = rect
    pygame.draw.rect(surface, outline, (x + p, y, w - 2 * p, h))
    pygame.draw.rect(surface, outline, (x, y + p, w, h - 2 * p))
    ix, iy, iw, ih = x + p, y + p, w - 2 * p, h - 2 * p
    pygame.draw.rect(surface, fill, (ix + p, iy, iw - 2 * p, ih))
    pygame.draw.rect(surface, fill, (ix, iy + p, iw, ih - 2 * p))
    if raised:
        light, dark = (_lighter(fill), _darker(fill)) if raised > 0 else (_darker(fill), _lighter(fill))
        pygame.draw.rect(surface, light, (ix + p, iy, iw - 2 * p, p))
        pygame.draw.rect(surface, light, (ix, iy + p, p, ih - 2 * p))
        pygame.draw.rect(surface, dark, (ix + p, iy + ih - p, iw - 2 * p, p))
        pygame.draw.rect(surface, dark, (ix + iw - p, iy + p, p, ih - 2 * p))


def draw_frame(surface, rect, color, thickness=2 * PIX):
    """Only a pixel-art frame (the same stepped corners as draw_panel), drawn over what is there: the keyboard focus
    ring and selection rings."""
    rect = pygame.Rect(rect)
    p, t = PIX, max(1, thickness)
    if rect.w < 4 * p or rect.h < 4 * p:
        pygame.draw.rect(surface, color, rect, min(t, 2))
        return
    x, y, w, h = rect
    pygame.draw.rect(surface, color, (x + p, y, w - 2 * p, t))
    pygame.draw.rect(surface, color, (x + p, y + h - t, w - 2 * p, t))
    pygame.draw.rect(surface, color, (x, y + p, t, h - 2 * p))
    pygame.draw.rect(surface, color, (x + w - t, y + p, t, h - 2 * p))


def clamp(value, low, high):
    return max(low, min(high, value))


def fit_text(text, font, max_width):
    """`text`, cut short with "..." when it is wider than max_width pixels in `font`."""
    text = str(text)
    if font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + "...")[0] > max_width:
        text = text[:-1]
    return text.rstrip() + "..." if text else ""


def ellipsize(text, font, max_width):
    """`text` with "..." added, cut so that the whole fits `max_width` (marks text that was left out)."""
    text = str(text)
    while text and font.size(text + "...")[0] > max_width:
        text = text[:-1]
    return text.rstrip() + "..."


def fit_variants(font, width, variants):
    """The first of `variants` (longest first) that fits `width` in `font`; the last one (cut by fit_text) if none."""
    for variant in variants:
        if font.size(variant)[0] <= width:
            return variant
    return variants[-1]


def pick_font(fonts, strings, max_width, max_height=None):
    """The largest font of `fonts` (listed largest first) in which every string fits `max_width` pixels and one
    line fits `max_height`. When none fits, the last (smallest) font; callers then shorten with fit_text."""
    strings = [str(s) for s in strings]
    for font in fonts:
        if max_height is not None and font.get_linesize() > max_height:
            continue
        if all(font.size(s)[0] <= max_width for s in strings):
            return font
    return fonts[-1]


def wrap_pixels(string, font, max_width):
    """Split text into lines that fit `max_width` pixels in `font` (a single word wider than that is kept whole;
    draw such lines through fit_text)."""
    lines, current = [], ""
    for word in str(string).split():
        trial = (current + " " + word).strip()
        if current and font.size(trial)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def wrap_text(text, max_chars):
    """Wrap by character count. Kept for old callers; the popups and screens wrap by pixel width (wrap_pixels)."""
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return lines


def scaled_font(size, base=15):
    """The font for text that is `base` px in the default 1000 x 680 window with the Normal text-size setting: larger
    in a bigger window or with a larger setting, smaller with the Small setting (textscale.text_px, the same factor
    the layout multiplies its text rows by, so a font always fits its row). `size` is the window size."""
    target = text_px(size[0], size[1], base)
    best = TINY
    for px, font in TEXT_SIZES:
        if px <= target:
            best = font
    return best


def text_ladder(size, base=15):
    """The fonts a screen or popup may choose from in a window of this size, largest first: scaled_font(size) and
    every smaller one. Use it wherever "the largest font that fits" is picked, so text grows with the window."""
    cap = scaled_font(size, base).get_linesize()
    return tuple(font for font in TEXT_FONTS if font.get_linesize() <= cap)


def screen_fonts(size):
    """(medium, body, small, tiny): the scaled versions of the fixed MEDIUM / FONT / SMALL / TINY fonts for a window of
    this size, the same ones the HUD uses (text-size setting and window size). Use them instead of the fixed fonts so a
    screen follows the text-size setting; pair them with k = textscale.text_k(*size) for the rows they sit in."""
    return (scaled_font(size, 17), scaled_font(size, 19), scaled_font(size, 15), scaled_font(size, 13))


def fit_paragraph(string, fonts, width, height, line_gap=2):
    """(font, lines) for wrapped text that fits a `width` x `height` box.

    The largest of `fonts` (largest first) in which the whole text fits is used. If even the smallest is too
    tall, its lines are cut to what fits and the last visible line ends in "..." so the cut is visible.
    """
    for font in fonts:
        lines = wrap_pixels(string, font, width)
        if len(lines) * (font.get_linesize() + line_gap) <= height:
            return font, lines
    font = fonts[-1]
    lines = wrap_pixels(string, font, width)
    room = max(1, height // (font.get_linesize() + line_gap))
    if len(lines) > room:
        lines = lines[:room]
        lines[-1] = ellipsize(lines[-1], font, width)
    return font, lines


# ---- Cached text surfaces ----------------------------------------------------------------------------------------
_TEXT_CACHE = {}
_TEXT_CACHE_LIMIT = 768   # the least recently used surfaces are dropped, so the cache stays small


def text_surface(text, font, color=WHITE):
    """The rendered `text` in `font` and `color`, from a bounded cache keyed by (font, string, colour).

    The returned surface is shared: blit it, never draw on it.
    """
    key = (font, str(text), tuple(color))
    surface = _TEXT_CACHE.pop(key, None)
    if surface is None:
        surface = font.render(key[1], ANTIALIAS, color)   # un-smoothed in the pixel-art look (theme.PIXEL_TEXT)
    _TEXT_CACHE[key] = surface   # (re)inserted last, so the oldest entries come first
    while len(_TEXT_CACHE) > _TEXT_CACHE_LIMIT:
        del _TEXT_CACHE[next(iter(_TEXT_CACHE))]
    return surface


_DIM_CACHE = {}


def draw_dim(surface, alpha=205):
    """Darken the whole surface (behind a popup). The translucent layer is cached per size and alpha, so nothing is
    allocated every frame."""
    key = (surface.get_size(), alpha)
    shade = _DIM_CACHE.get(key)
    if shade is None:
        shade = pygame.Surface(key[0], pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        if len(_DIM_CACHE) > 4:
            _DIM_CACHE.clear()
        _DIM_CACHE[key] = shade
    surface.blit(shade, (0, 0))


def draw_text(surface, text, x, y, color=WHITE, font=FONT):
    surface.blit(text_surface(text, font, color), (x, y))


def text_in_rect(surface, string, rect, color, font, align="left"):
    """Draw one line of text vertically centred in `rect`, cut short with "..." so that it stays inside it."""
    x, y, w, h = rect
    image = text_surface(fit_text(string, font, w), font, color)
    ty = y + (h - image.get_height()) // 2
    if align == "right":
        surface.blit(image, (x + w - image.get_width(), ty))
    elif align == "center":
        surface.blit(image, (x + (w - image.get_width()) // 2, ty))
    else:
        surface.blit(image, (x, ty))


def heading_fonts(size):
    """The fonts a heading may use in a window of this size, largest first: the bold TITLE size in the default
    text size, then the (larger) text ladder from there up when the window or the text-size setting is larger."""
    if text_k(size[0], size[1]) <= 1.0:
        return (TITLE, FONT, SMALL)
    return text_ladder(size, 27)


def draw_heading(surface, string, rect, color=WHITE, fonts=None, align="left"):
    """A heading in the largest of `fonts` (default: heading_fonts of the window) that fits the rectangle."""
    font = pick_font(fonts or heading_fonts(surface.get_size()), [string], rect[2], rect[3])
    text_in_rect(surface, string, rect, color, font, align)


def draw_lines(surface, lines, rect, font, color=WHITE, align="left", line_gap=2):
    """Draw `lines` one under the other from the top of `rect`; each is cut with fit_text to the rect's width.
    Returns the y below the last line."""
    x, y, w, _h = rect
    step = font.get_linesize() + line_gap
    for line in lines:
        text_in_rect(surface, line, (x, y, w, step), color, font, align)
        y += step
    return y


def _bar_frame(surface, x, y, width, height):
    """The frame and dark well of a pixel-art bar; returns the inside rectangle (x, y, w, h) the fill goes in."""
    t = PIX if height >= 8 and width >= 8 else 1
    pygame.draw.rect(surface, BORDER, (x, y, width, height))
    inner = (x + t, y + t, max(0, width - 2 * t), max(0, height - 2 * t))
    pygame.draw.rect(surface, DARK, inner)
    return inner


def _bar_block(surface, x, y, width, height, color):
    """One filled stretch of a bar: the colour with a light stripe on top and a dark one at the bottom (pixel shading)."""
    pygame.draw.rect(surface, color, (x, y, width, height))
    if height >= 6:
        pygame.draw.rect(surface, _lighter(color), (x, y, width, PIX))
        pygame.draw.rect(surface, _darker(color), (x, y + height - PIX, width, PIX))


def draw_bar(surface, x, y, width, height, value, maximum, color):
    """A pixel-art bar: a framed dark well filled in steps of whole UI pixels (so the end of the fill moves in chunks)."""
    ix, iy, iw, ih = _bar_frame(surface, x, y, width, height)
    share = clamp(value / max(1, maximum), 0, 1)
    fill = int(iw * share)
    if share > 0:
        fill = max(PIX, fill // PIX * PIX) if iw >= PIX else fill
        fill = min(fill, iw)
    if fill > 0 and ih > 0:
        _bar_block(surface, ix, iy, fill, ih, color)


def draw_segmented_bar(surface, x, y, width, height, segments, maximum):
    """One bar shared by several things that add up to `maximum` (for example food + water + scrap against the cargo
    capacity). `segments` is [(value, colour), ...] from left to right; whatever is left of the bar is free space.
    Each part is at least one pixel wide when it is not zero, and a thin dark line separates neighbouring parts, so
    the parts can be told apart by position and not only by colour."""
    ix, iy, iw, ih = _bar_frame(surface, x, y, width, height)
    shown = [(value, color) for value, color in segments if value > 0]
    total = max(1, maximum)
    used = 0
    edge_before = 0
    for index, (value, color) in enumerate(shown):
        used += value
        edge = int(iw * clamp(used / total, 0, 1) + 0.5)
        edge = min(iw, max(edge, edge_before + 1))
        if edge > edge_before and ih > 0:
            _bar_block(surface, ix + edge_before, iy, edge - edge_before, ih, color)
            if index and edge - edge_before >= 3:
                pygame.draw.rect(surface, DARK, (ix + edge_before, iy, 1, ih))   # the line between two parts
        edge_before = edge


class Button:
    def __init__(self, rect, label, action, enabled=True, font=None):
        self.font = font   # None: chosen when drawn (_auto_font); a popup sets one font for all its buttons
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.enabled = enabled
        self.focused = False   # set by keys.KeyNav each frame: the button the keyboard is on

    def draw(self, surface, selected=False):
        if not self.enabled:
            color, text_color, raised = DISABLED_BG, DISABLED_TEXT, 0
        else:
            color, text_color = (BLUE if selected else PANEL_LIGHT), WHITE
            raised = -1 if selected else 1   # a selected / toggled-on button looks pressed in
        draw_panel(surface, self.rect, color, raised)
        # Long labels use a smaller font, and are cut short if they still do not fit inside the button.
        room = max(1, self.rect.w - 8)
        font = self.font if self.font is not None else self._auto_font(surface.get_size(), room)
        label = text_surface(fit_text(self.label, font, room), font, text_color)
        centre = (self.rect.centerx, self.rect.centery + (PIX if raised < 0 else 0))   # the label sinks with the button
        surface.blit(label, label.get_rect(center=centre))
        if self.focused and self.enabled:
            draw_frame(surface, self.rect, YELLOW)   # keyboard focus ring

    def _auto_font(self, window, room):
        """The largest font of the window's text ladder that fits the label's width and the button's height. Never
        smaller than the old SMALL-or-TINY choice, so small windows look as before."""
        legacy = SMALL if SMALL.size(self.label)[0] <= room else TINY
        for font in text_ladder(window):
            if font.get_linesize() <= self.rect.h * 0.62 and font.size(self.label)[0] <= room:
                return font if font.get_linesize() >= legacy.get_linesize() else legacy
        return legacy

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)
