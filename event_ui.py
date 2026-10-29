"""Pygame overlay and click handling for player-choice events."""
import pygame
from layout import HEIGHT, WIDTH
from theme import FONT, GREEN, MUTED, PANEL, RED, SMALL, TINY, WHITE, YELLOW
from widgets import Button, wrap_text


def make_event_buttons(event):
    """Build one shared Button per choice; each button's action returns its choice index."""
    choices = event.get("choices", [])
    count = max(1, len(choices))
    button_h = 42
    gap = 10
    total_h = count * button_h + (count - 1) * gap
    start_y = min(HEIGHT - total_h - 24, 355)
    return [
        Button(
            (130, start_y + i * (button_h + gap), WIDTH - 260, button_h),
            f"{i + 1}.  {choice.get('label', 'Continue')}",
            lambda index=i: index,
        )
        for i, choice in enumerate(choices)
    ]


def draw_event_overlay(surface, event):
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 205))
    surface.blit(shade, (0, 0))
    panel = pygame.Rect(95, 125, WIDTH - 190, 445)
    pygame.draw.rect(surface, PANEL, panel, border_radius=10)
    pygame.draw.rect(surface, YELLOW, panel, 2, border_radius=10)
    title = FONT.render(event.get("title", "Unexpected Event"), True, YELLOW)
    surface.blit(title, title.get_rect(center=(WIDTH // 2, 158)))
    y = 195
    for line in wrap_text(event.get("description", "Choose how the convoy should respond."), 76):
        label = SMALL.render(line, True, WHITE)
        surface.blit(label, label.get_rect(center=(WIDTH // 2, y)))
        y += 22
    hint = TINY.render("Choose an option below (or press its number key).", True, MUTED)
    surface.blit(hint, hint.get_rect(center=(WIDTH // 2, 265)))
    for button in make_event_buttons(event):
        button.draw(surface)


def make_result_buttons(result):
    """The single OK button on the result screen; its action returns True."""
    return [Button((WIDTH // 2 - 90, 512, 180, 42), "OK [Enter]", lambda: True)]


def draw_event_result_overlay(surface, result):
    """Show what the chosen option did: the outcome text and every resource that changed."""
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 205))
    surface.blit(shade, (0, 0))
    panel = pygame.Rect(95, 125, WIDTH - 190, 445)
    pygame.draw.rect(surface, PANEL, panel, border_radius=10)
    pygame.draw.rect(surface, YELLOW, panel, 2, border_radius=10)
    title = FONT.render(result.get("title", "Event"), True, YELLOW)
    surface.blit(title, title.get_rect(center=(WIDTH // 2, 158)))
    chosen = result.get("choice")
    if chosen:
        label = TINY.render(f"You chose: {chosen}", True, MUTED)
        surface.blit(label, label.get_rect(center=(WIDTH // 2, 190)))
    y = 222
    for line in wrap_text(result.get("outcome") or "The convoy moves on.", 76)[:4]:
        label = SMALL.render(line, True, WHITE)
        surface.blit(label, label.get_rect(center=(WIDTH // 2, y)))
        y += 22
    y = max(y + 14, 322)
    heading = TINY.render("RESULT", True, MUTED)
    surface.blit(heading, heading.get_rect(center=(WIDTH // 2, y)))
    y += 24
    changes = result.get("changes", [])
    if not changes:
        label = SMALL.render("No lasting effect.", True, MUTED)
        surface.blit(label, label.get_rect(center=(WIDTH // 2, y)))
    for text, good in changes[:7]:
        label = SMALL.render(text, True, GREEN if good else RED)
        surface.blit(label, label.get_rect(center=(WIDTH // 2, y)))
        y += 21
    for button in make_result_buttons(result):
        button.draw(surface)


def handle_result_click(pos, result):
    """True if the OK button on the result screen was clicked."""
    return any(button.clicked(pos) for button in make_result_buttons(result))


def handle_event_click(pos, event):
    """Return the index of the clicked choice, or None if no button was clicked."""
    for button in make_event_buttons(event):
        if button.clicked(pos):
            return button.action()
    return None
