"""The achievements screen (drawing only): one card per achievement, paged like the missions screen. Opened from the
pause menu (ACHIEVEMENTS), so it can be read from the title screen too. Rewards are placeholders: the card says what
each would give, but nothing is given yet."""
from achievement_data import ACHIEVEMENTS
from layout.achievements import achievements_layout
from layout import page_count
from textscale import tpx
from theme import GREEN, MUTED, PANEL, WHITE, YELLOW
from widgets import (PIX, draw_frame, draw_heading, draw_panel, fit_text, fit_variants, pick_font, scaled_font,
                     text_in_rect)

from .common import CARD_BG, SCREEN_BG, draw_paragraph

COUNTED = ("wins", "vehicle_types_seen", "run_stat")   # conditions that count something (shown as "2/3")


def card_lines(achievement, tracker, game):
    """(name, status, status colour, description, reward, earned) texts of one card. A secret achievement stays "???"
    until it is completed."""
    done = tracker.is_complete(achievement["id"])
    if achievement["secret"] and not done:
        return "???", "SECRET", MUTED, "A secret achievement: keep exploring to find it.", "Reward: ???", ""
    if achievement.get("placeholder") and not done:
        return (achievement["name"], "COMING SOON", MUTED, achievement["description"],
                f"Reward: {achievement['reward']} (not active yet)", "")
    if done:
        status, colour = "COMPLETED", GREEN
        info = tracker.completed[achievement["id"]]
        earned = " ".join(part for part in ("Earned", info.get("date", ""), f"(day {info['day']})" if info.get("day") else "") if part)
    else:
        if achievement["condition"]["kind"] in COUNTED:
            current, target = tracker.progress(achievement, game)
            status = f"{current}/{target}"
        else:
            status = "NOT YET"
        colour, earned = YELLOW, ""
    return (achievement["name"], status, colour, achievement["description"],
            f"Reward: {achievement['reward']} (not active yet)", earned)


def draw_achievements_screen(surface, game, buttons):
    size = surface.get_size()
    g = achievements_layout(*size)
    tiny, small = scaled_font(size, 13), scaled_font(size, 15)
    surface.fill(SCREEN_BG)
    draw_panel(surface, g["panel"], PANEL, 1)
    draw_heading(surface, "ACHIEVEMENTS", g["header"])

    tracker = getattr(game, "achievements", None)
    if tracker is None:
        text_in_rect(surface, "Achievements are not connected.", g["subtitle"], YELLOW, small)
        for button in buttons:
            button.draw(surface)
        return

    done = tracker.completed_count()
    total = len(ACHIEVEMENTS)
    sw = g["subtitle"][2]
    text_in_rect(surface, fit_variants(tiny, sw, (
        f"{done} of {total} completed. Kept between runs. Rewards are placeholders for now.",
        f"{done} of {total} completed. Rewards are not active yet.", f"{done} of {total} completed")),
        g["subtitle"], MUTED, tiny)

    draw_panel(surface, g["list"], CARD_BG, -1)
    per_page = g["per_page"]
    pages = page_count(total, per_page)
    page = max(0, min(getattr(game, "achievement_page", 0), pages - 1))
    for achievement, card, parts in zip(ACHIEVEMENTS[page * per_page:(page + 1) * per_page], g["cards"], g["card_parts"]):
        name, status, colour, description, reward, earned = card_lines(achievement, tracker, game)
        complete = tracker.is_complete(achievement["id"])
        draw_panel(surface, card, (38, 49, 51), 0)
        draw_frame(surface, card, GREEN if complete else MUTED, 1 * PIX)

        title_font = pick_font((small, tiny), [name], parts["title"][2], parts["title"][3])
        text_in_rect(surface, name, parts["title"], MUTED if achievement["secret"] and not complete else WHITE, title_font)
        status_font = pick_font((small, tiny), [status], parts["status"][2], parts["status"][3])
        text_in_rect(surface, status, parts["status"], colour, status_font, "right")
        draw_paragraph(surface, description, parts["description"][0], parts["description"][1], parts["description"][2],
                       WHITE if complete else MUTED, tiny, limit=parts["description"][1] + parts["description"][3])
        text_in_rect(surface, fit_text(reward, tiny, parts["reward"][2]), parts["reward"], MUTED, tiny)
        if earned:
            text_in_rect(surface, fit_text(earned, tiny, parts["earned"][2]), parts["earned"], GREEN, tiny, "right")

    text_in_rect(surface, f"PAGE {page + 1}/{pages}", g["footer"], WHITE, tiny, "center")
    for button in buttons:
        if button.label != "MENU":
            button.draw(surface)
