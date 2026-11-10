"""The remaining screens of THE LAST CONVOY: pause menu, difficulty, settings, map, title, lore and the victory /
game over popup. Drawing only. (The credits screen is ui/credits.py, the "are you sure?" popup ui/confirm.py.)"""
import pygame

from widgets import PIX, draw_frame, draw_panel

import savegame
import story_data as story
from layout.menus import saves_layout
from .common import CARD_BG, draw_paragraph, SCREEN_BG
from .convoy import draw_scene_art
from .credits import draw_credits_screen   # noqa: F401  (it used to live here; kept for old imports)
from config import DIFFICULTIES, DIFFICULTY_ORDER, LORE_CURSOR_BLINK_MS
from layout import (
    END_STAT_ROWS, LINE_H, difficulty_layout, lore_layout, map_layout, menu_card_layout, menu_layout,
    popup_layout, settings_layout, title_layout,
)
from .map_system import draw_map, draw_map_info
from theme import (
    ACCESS, BIG, BLUE, DARK, FONT, GREEN, HEAD_FONTS, MEDIUM, MUTED, PANEL, RED, SMALL, TINY, TITLE, WHITE, YELLOW,
)
from theme import ANTIALIAS
from textscale import text_k, tpx
from platform_web import IS_WEB
from widgets import (
    draw_bar, draw_heading, draw_lines, draw_text, fit_paragraph, fit_text, fit_variants, pick_font, scaled_font,
    screen_fonts, text_in_rect, text_ladder, wrap_pixels,
)


def draw_menu_screen(surface, game, buttons):
    """The pause menu: SETTINGS, INSTRUCTIONS, DIFFICULTY and MUTE MUSIC (plus RESTART GAME and TITLE SCREEN during a
    run) and QUIT GAME in a column, plus BACK. The heading says PAUSED during a run, MENU before one. The buttons (with their rectangles from menu_layout) are given;
    MUTE MUSIC is shown pressed while muted. RESTART / TITLE SCREEN / QUIT GAME ask first in the "are you sure?"
    popup (ui/confirm.py)."""
    if game.menu_page == "saves":
        draw_saves_page(surface, game, buttons)
        return
    g = menu_layout(*surface.get_size(), game.started)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "PAUSED" if game.started else "MENU", g["header"])
    for button in buttons:
        button.draw(surface, selected=button.label == "UNMUTE MUSIC" and game.music_muted)   # shown pressed while muted


def _slot_lines(number, summary, pending):
    """(title, colour, detail, detail colour) of one save slot's card. `pending` is the (kind, slot) waiting for a
    second press, if any; it replaces the detail with a yellow question."""
    if summary is None:
        title, colour, detail, detail_colour = f"SLOT {number}: EMPTY", MUTED, "Nothing saved here.", MUTED
    elif summary["damaged"]:
        title, colour = f"SLOT {number}: CANNOT BE LOADED", RED
        detail, detail_colour = summary.get("reason") or "The file is damaged.", MUTED
    else:
        title, colour = f"SLOT {number}: DAY {summary['day']} - {summary['location']}", WHITE
        extra = ", sandbox" if summary["sandbox"] else ""
        detail = (f"{summary['survivors']} survivors, {summary['vehicles']} vehicles, "
                  f"{summary['difficulty']}{extra}. Saved {summary['saved_at']}")
        detail_colour = MUTED
    if pending and pending[1] == number - 1:
        detail, detail_colour = {
            "save": "Overwrite this save? Press CONFIRM.",
            "load": "Replace the run in progress? Press CONFIRM.",
            "delete": "Delete this save for good? Press CONFIRM.",
        }[pending[0]], YELLOW
    return title, colour, detail, detail_colour


def draw_saves_page(surface, game, buttons):
    """The SAVE / LOAD page of the pause menu: a card per slot (what is saved there), a note line and the buttons."""
    g = saves_layout(*surface.get_size())
    _medium, _body, small, tiny = screen_fonts(surface.get_size())
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "SAVE / LOAD", g["header"])
    summaries = savegame.slot_summaries()
    for i, slot in enumerate(g["slots"]):
        draw_panel(surface, slot["card"], CARD_BG, -1)
        title, colour, detail, detail_colour = _slot_lines(i + 1, summaries[i], game.save_pending)
        x, y, w, h = slot["info"]
        font = pick_font((small, tiny), [title, detail], w - 8, h // 2)
        text_in_rect(surface, title, (x, y + h // 2 - font.get_linesize(), w, font.get_linesize()), colour, font)
        text_in_rect(surface, detail, (x, y + h // 2, w, font.get_linesize()), detail_colour, font)
    note, note_colour = game.save_message, YELLOW
    if not note:
        note, note_colour = savegame.save_problem(game) or "Pick a slot to save to or load from.", MUTED
    font = pick_font((small, tiny), [note], g["note"][2], g["note"][3])
    text_in_rect(surface, note, g["note"], note_colour, font)
    for button in buttons:
        button.draw(surface)


def _setting_row(surface, row, label, texts, fonts):
    """The card behind one settings row and its label (the first of `texts`, longest first, that fits), in the
    largest of `fonts` (largest first) that fits the label's width and height."""
    draw_panel(surface, row, CARD_BG, -1)
    font = pick_font(fonts, [texts[-1]], label[2] - 16, label[3])
    text_in_rect(surface, fit_variants(font, label[2] - 16, texts),
                 (label[0] + 8, label[1], label[2] - 16, label[3]), WHITE, font)


def draw_settings_screen(surface, game, buttons):
    """
    Settings screen:
    - Music volume and sound-effect volume (each an adjustable bar).
    - Text size and fullscreen, each a labelled row with its button (the button shows the current setting).
    - The accessibility toggles.
    """

    g = settings_layout(*surface.get_size())
    _medium, _body, small, tiny = screen_fonts(surface.get_size())

    surface.fill(SCREEN_BG)

    # Main panel
    draw_panel(surface, g["panel"], PANEL, 1)

    draw_heading(surface, "SETTINGS", g["header"])

    # -------------------------
    # MUSIC VOLUME
    # -------------------------

    _setting_row(surface, g["row"], g["label"], ("Music volume", "Music"), (small, tiny))

    # Read master volume from MusicManager
    music = game.music_manager
    volume = music.volume

    bx, by, bw, bh = g["bar"]

    # Draw volume bar
    draw_bar(
        surface,
        bx,
        by,
        bw,
        bh,
        round(volume * 20),
        20,
        BLUE
    )

    # -------------------------
    # SOUND EFFECT VOLUME (button clicks)
    # -------------------------

    _setting_row(surface, g["sfx_row"], g["sfx_label"], ("Sound effects", "Effects"), (small, tiny))
    sfx_volume = game.sound_manager.volume
    sx, sy, sw, sh = g["sfx_bar"]
    draw_bar(surface, sx, sy, sw, sh, round(sfx_volume * 20), 20, BLUE)

    # Display both volumes as percentages
    volume = game.music_manager.volume

    nx, ny, nw, nh = g["note"]

    text_in_rect(
        surface,
        fit_variants(tiny, nw - 16, (
            f"Music volume: {round(volume * 100)}%   |   Sound effects volume: {round(sfx_volume * 100)}%",
            f"Music: {round(volume * 100)}% | Sound effects: {round(sfx_volume * 100)}%",
            f"Music {round(volume * 100)}% | Effects {round(sfx_volume * 100)}%")),
        (nx + 8, ny, nw - 16, nh),
        WHITE,
        tiny
    )

    # -------------------------
    # TEXT SIZE AND FULLSCREEN
    # -------------------------

    _setting_row(surface, g["textsize_row"], g["textsize_label"], (
        "Text size (click to change: Small / Normal / Large / Extra large)",
        "Text size (click to change)",
        "Text size",
    ), (small, tiny))
    _setting_row(surface, g["fullscreen_row"], g["fullscreen_label"], (
        "Fullscreen (also F11)",
        "Fullscreen",
    ), (small, tiny))

    _setting_row(surface, g["difficulty_row"], g["difficulty_label"], (
        "Difficulty (click to change: Easy / Normal / Hard)",
        "Difficulty (click to change)",
        "Difficulty",
    ), (small, tiny))

    # -------------------------
    # ACCESSIBILITY SETTINGS
    # -------------------------

    text_in_rect(
        surface,
        "ACCESSIBILITY",
        g["access"],
        YELLOW,
        tiny
    )

    _setting_row(surface, g["contrast_row"], g["contrast_label"], (
        "High contrast: black panels, brighter text and outlines",
        "High contrast",
        "Contrast",
    ), (small, tiny))
    _setting_row(surface, g["colorblind_row"], g["colorblind_label"], (
        "Colour-blind palette: blue / yellow / orange / purple, plus words",
        "Colour-blind palette",
        "Colour-blind",
    ), (small, tiny))

    # -------------------------
    # BUTTONS (the ON / OFF toggles are drawn pressed while on)
    # -------------------------

    switched_on = {
        tuple(g["fullscreen"][:2]): lambda: game.fullscreen,
        tuple(g["contrast"][:2]): lambda: ACCESS["high_contrast"],
        tuple(g["colorblind"][:2]): lambda: ACCESS["colorblind"],
    }

    for button in buttons:

        is_on = switched_on.get(tuple(button.rect.topleft))

        button.draw(
            surface,
            selected=bool(is_on and is_on())
        )


def draw_difficulty_screen(surface, game, buttons):
    """The difficulty screen (reached from the pause menu), with the given buttons. Only resource use, horde speed
    and scavenge yield change.

    The cards, notes and buttons are placed by difficulty_layout; the notes are left out when the window is too small.
    """
    g = difficulty_layout(*surface.get_size())
    _medium, _body, small, tiny = screen_fonts(surface.get_size())
    lh = tpx(LINE_H, g["k"])
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "DIFFICULTY", g["header"])
    sx, sy, sw, sh = g["subtitle"]
    text_in_rect(surface, fit_variants(tiny, sw, (
        "Difficulty changes how fast supplies run out, how fast the horde closes in, and how much scavenging finds.",
        "Difficulty: supply use, horde speed and scavenging yield.")), g["subtitle"], MUTED, tiny)

    for i, name in enumerate(DIFFICULTY_ORDER):
        level = DIFFICULTIES[name]
        card = g["cards"][i]
        parts = menu_card_layout(card, g["k"])
        is_current = name == game.difficulty
        draw_panel(surface, card, (46, 68, 74) if is_current else CARD_BG, 0)
        draw_frame(surface, card, BLUE if is_current else (70, 82, 86), (2 if is_current else 1) * PIX)
        draw_heading(surface, name.upper(), parts["name"], GREEN if is_current else WHITE)

        bx, by, bw, bh = parts["body"]
        stats = [f"Food & water use  x{level['consumption']:g}",
                 f"Horde speed       x{level['horde']:g}",
                 f"Scavenge yield    x{level['scavenge']:g}"]
        font = pick_font((small, tiny), stats, bw)
        y = by
        for line in stats:
            if y + font.get_linesize() > by + bh:
                break
            draw_text(surface, fit_text(line, font, bw), bx, y, WHITE, font)
            y += font.get_linesize() + 4
        y = draw_paragraph(surface, level["blurb"], bx, y + 4, bw, MUTED, tiny, limit=by + bh)
        if is_current and y + lh <= by + bh:
            draw_text(surface, "CURRENT", bx, y + 2, YELLOW, tiny)

    if g["notes"]:
        nx, ny, nw, nh = g["notes"]
        y = draw_paragraph(surface, "Not affected by difficulty: vehicle stats, repair cost, distances, fuel costs, recovery costs.",
                            nx, ny, nw, MUTED, tiny, limit=ny + nh)
        draw_paragraph(surface, "Changing the difficulty during a run restarts the game (you are asked first). It is not saved when you close the game.",
                        nx, y + 2, nw, MUTED, tiny, limit=ny + nh)
    for button in buttons:
        button.draw(surface, selected=(button.label == game.difficulty
                                       or (button.label.startswith("SANDBOX") and game.sandbox)))   # sandbox shows pressed while on


def draw_map_screen(surface, game, buttons):
    """The map screen: heading, the map with its stops, the info panel and TRAVEL / BACK, all from map_layout."""
    g = map_layout(*surface.get_size())
    _medium, _body, _small, tiny = screen_fonts(surface.get_size())
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "HIGHWAY MAP", g["header"])
    if g["subtitle"]:
        text_in_rect(surface, fit_variants(tiny, g["subtitle"][2], (
            "Travel west across the country. Click a stop to inspect it. Costs are measured from where you are now.",
            "Travel west. Click a stop to inspect it. Costs are measured from where you are.",
            "Click a stop to inspect it.")), g["subtitle"], MUTED, tiny)
    draw_map(surface, game, g)
    draw_map_info(surface, game, g)
    for button in buttons:
        button.draw(surface)


def draw_logo(surface, cx, cy, r):
    """The game's emblem: a badge with a west-pointing arrow and a small convoy of three headlights."""
    pygame.draw.circle(surface, DARK, (cx, cy), r)
    pygame.draw.circle(surface, YELLOW, (cx, cy), r, 3)
    pygame.draw.circle(surface, (90, 100, 102), (cx, cy), r - 7, 1)
    arrow = [(-0.62, 0), (-0.12, -0.38), (-0.12, -0.14), (0.62, -0.14), (0.62, 0.14), (-0.12, 0.14), (-0.12, 0.38)]
    pygame.draw.polygon(surface, YELLOW, [(cx + int(px * r), cy - int(r * 0.12) + int(py * r)) for px, py in arrow])
    for i in range(3):
        pygame.draw.circle(surface, WHITE, (cx - int(r * 0.32) + int(i * r * 0.32), cy + int(r * 0.52)), max(2, r // 14))


def draw_brand(surface, head):
    """The logo and the game's name side by side, centred in the rectangle `head` (the title screen's head, and the
    empty HUD strip of the pause-menu screens while no run has started)."""
    head = pygame.Rect(head)
    radius = max(14, head.h // 2 - 2)
    room = head.w - 2 * radius - 16
    size = surface.get_size()
    # The title keeps its pixel fonts at the default text size and grows with the ladder above it (larger window or
    # larger text-size setting).
    title_fonts = (BIG, TITLE, FONT) if text_k(*size) <= 1.0 else text_ladder(size, 34)
    font = pick_font(title_fonts, [story.GAME_TITLE], room, head.h)
    title = font.render(fit_text(story.GAME_TITLE, font, room), ANTIALIAS, WHITE)
    x0 = head.x + (head.w - (2 * radius + 16 + title.get_width())) // 2
    draw_logo(surface, x0 + radius, head.centery, radius)
    surface.blit(title, (x0 + 2 * radius + 16, head.centery - title.get_height() // 2))


def draw_title_screen(surface, game, buttons):
    """Title screen: logo and name above the convoy scene, with PLAY and MENU, all placed by title_layout."""
    g = title_layout(*surface.get_size())
    surface.fill(SCREEN_BG)
    size = surface.get_size()
    hint_font = scaled_font(size, 13)   # the tagline and hint follow the text-size setting, smaller ones included
    draw_brand(surface, g["head"])

    draw_scene_art(surface, game, pygame.Rect(g["scene"]), zombie_limit=8, labels=False)

    tag = g["tagline"]
    tag_font = pick_font(text_ladder(size, 19), [story.TAGLINE], tag[2], tag[3])
    text_in_rect(surface, story.TAGLINE, tag, YELLOW, tag_font, "center")
    for button in buttons:
        button.draw(surface)
    if getattr(game, "quit_armed", False):   # the first ESC on the title screen: ask before quitting
        text_in_rect(surface, fit_variants(hint_font, g["hint"][2], ("Press ESC again to quit   |   any other key: cancel",
                                                                 "ESC again: quit | other key: cancel")),
                     g["hint"], YELLOW, hint_font, "center")
    else:
        text_in_rect(surface, fit_variants(hint_font, g["hint"][2], ("Arrows or Tab: choose   |   ENTER: select   |   ESC: quit",
                                                                 "ENTER: select | ESC: quit", "ENTER: select")),
                     g["hint"], MUTED, hint_font, "center")


def draw_lore_screen(surface, game, buttons):
    """The story: why the convoy must reach the Pacific Coast, placed by lore_layout."""
    g = lore_layout(*surface.get_size())
    size = surface.get_size()
    _medium, body, small, tiny = screen_fonts(size)
    k = text_k(*size)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, story.LORE_TITLE, g["heading"], YELLOW, None, "center")
    rect = pygame.Rect(g["text"])
    # Desktop build: the story may use the 24 px font (and a wider, airier column) when the window has room for it; the browser
    # build keeps its 16 px / 820 text.
    big = None if IS_WEB else scaled_font(size, 26)
    width = min(rect.w, tpx(1300 if big is not None and big is not body else 820, k))
    x = rect.x + (rect.w - width) // 2
    paragraphs = [" ".join(p.split()) for p in story.LORE]   # whitespace-normalised, as Game.lore_revealed counts them
    font, gap = tiny, tpx(10, k)
    fonts = [(body, tpx(18, k)), (small, tpx(14, k)), (tiny, tpx(10, k))]
    if big is not None and big is not body:
        fonts.insert(0, (big, tpx(22, k)))
    spacing = 2 if IS_WEB else max(2, tpx(6, k))   # extra pixels between the lines (desktop: a little airier)
    for font, gap in fonts:   # the largest font in which the story fits
        step = font.get_linesize() + spacing
        bottom = rect.y + sum(len(wrap_pixels(p, font, width)) * step + gap for p in paragraphs)
        if bottom - gap <= rect.bottom:
            break

    # The text is wrapped as a whole (so a word never jumps to the next line while it is typed) and only the first
    # `typed` characters of each paragraph are drawn. The cursor sits after the last typed character.
    step = font.get_linesize() + spacing
    typing = not game.lore_typing_done()
    counts = game.lore_revealed()
    y = rect.y
    cursor = (x, rect.y)
    for paragraph, typed in zip(paragraphs, counts):
        lines = wrap_pixels(paragraph, font, width)
        if typed > 0 or y == rect.y:
            cursor = (x, y)   # an empty first paragraph: the cursor waits at the start of the text
        used = 0   # characters of the paragraph before this line (a line break stands for one space)
        for line in lines:
            shown = max(0, min(len(line), typed - used))
            if shown > 0 and y < rect.bottom:
                draw_text(surface, line[:shown], x, y, WHITE, font)
                cursor = (x + font.size(line[:shown])[0], y)
            used += len(line) + 1
            y += step
        y += gap
    if typing or (pygame.time.get_ticks() // LORE_CURSOR_BLINK_MS) % 2 == 0:   # solid while typing, then it blinks
        cw = max(2, font.size("M")[0] // 2)
        pygame.draw.rect(surface, YELLOW, (cursor[0] + 2, cursor[1] + 2, cw, max(2, font.get_linesize() - 4)))

    for button in buttons:
        button.draw(surface)
    text_in_rect(surface, "Press SPACE to skip" if typing else "Press ENTER to continue", g["hint"], MUTED, tiny,
                 "center")


def end_stats(game):
    """The (label, value, colour) rows summarising the finished run."""
    lost = game.vehicles_lost()
    losses = getattr(game, "condition_losses", {})   # survivors lost to hunger, thirst and injuries (conditions.py)
    starved = losses.get("hunger", 0) + losses.get("thirst", 0)
    injured = losses.get("injury", 0)
    return [
        ("Days survived", game.day, WHITE),
        ("Survivors left", game.survivors, WHITE if game.survivors else RED),
        ("Lost to hunger / thirst", starved, RED if starved else WHITE),
        ("Lost to injuries", injured, RED if injured else WHITE),
        ("Stops visited", f"{game.stops_visited()} of {game.stops_total()}", WHITE),
        ("Vehicles lost", lost, RED if lost else WHITE),
        ("Distance travelled", f"{game.km_traveled} km", WHITE),
        ("Difficulty", f"{game.difficulty} + sandbox" if game.sandbox else game.difficulty, MUTED),
    ]


def draw_end_overlay(surface, game, buttons):
    """Victory / game over popup, drawn straight onto the (already dimmed) window from popup_layout(..., "end"):
    how the run ended, a summary of it, and the buttons to go on."""
    if game.status == "playing":
        return
    won = game.status == "won"
    color = GREEN if won else RED
    g = popup_layout(*surface.get_size(), "end", END_STAT_ROWS)
    medium, font_b, small, tiny = screen_fonts(surface.get_size())
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_frame(surface, g["panel"], color, 2 * PIX)

    draw_heading(surface, "YOU ESCAPED!" if won else "CONVOY LOST", g["title"], color, HEAD_FONTS, "center")

    reason = game.end_reason or game.log[0]
    rx, ry, rw, rh = g["reason"]
    font, lines = fit_paragraph(reason, (font_b, medium, small, tiny), rw, rh, line_gap=4)
    block = len(lines) * (font.get_linesize() + 4)
    draw_lines(surface, lines, (rx, ry + max(0, (rh - block) // 2), rw, rh), font, WHITE, "center", 4)

    text_in_rect(surface, "YOUR JOURNEY", g["journey"], MUTED, tiny)
    sx, sy, sw, _sh = g["stats"]
    row_h = g["row_h"]
    stats = end_stats(game)[:END_STAT_ROWS]
    font = pick_font((medium, small, tiny), [f"{name}  {value}" for name, value, _c in stats], sw - 8, row_h)
    for i, (name, value, value_color) in enumerate(stats):
        y = sy + i * row_h
        pygame.draw.line(surface, (70, 82, 86), (sx, y), (sx + sw, y), 1)
        value_text = str(value)
        value_w = min(font.size(value_text)[0], sw // 2)
        text_in_rect(surface, name, (sx + 4, y, sw - value_w - 16, row_h), MUTED, font)
        text_in_rect(surface, value_text, (sx + sw - value_w - 4, y, value_w, row_h), value_color, font, "right")
    end_y = sy + len(stats) * row_h
    pygame.draw.line(surface, (70, 82, 86), (sx, end_y), (sx + sw, end_y), 1)

    for button in buttons:
        button.draw(surface)
    text_in_rect(surface, fit_variants(tiny, g["hint"][2], ("Arrows or Tab: move   |   ENTER: select   |   H: history   |   ESC: title screen",
                                                               "Tab: move | ENTER: select | H: history | ESC: title",
                                                               "ENTER: select")),
                  g["hint"], MUTED, tiny, "center")
