"""Small reusable UI pieces for THE LAST CONVOY: the Button class, a bar, text drawing and text helpers."""
import pygame

from theme import BLUE, DARK, FONT, PANEL_LIGHT, SMALL, WHITE


def clamp(value, low, high):
    return max(low, min(high, value))


def draw_text(surface, text, x, y, color=WHITE, font=FONT):
    surface.blit(font.render(str(text), True, color), (x, y))


def wrap_text(text, max_chars):
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


def draw_bar(surface, x, y, width, height, value, maximum, color):
    pygame.draw.rect(surface, DARK, (x, y, width, height), border_radius=3)
    fill = int(width * clamp(value / max(1, maximum), 0, 1))
    if fill:
        pygame.draw.rect(surface, color, (x, y, fill, height), border_radius=3)
    pygame.draw.rect(surface, (90, 100, 102), (x, y, width, height), 1, border_radius=3)


class Button:
    def __init__(self, rect, label, action, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.enabled = enabled

    def draw(self, surface, selected=False):
        if not self.enabled:
            color, text_color = (55, 59, 59), (112, 119, 116)
        else:
            color, text_color = (BLUE if selected else PANEL_LIGHT), WHITE
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, (94, 108, 111), self.rect, 1, border_radius=6)
        label = SMALL.render(self.label, True, text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)
