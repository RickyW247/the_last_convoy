"""Drawing surface for the fixed-size screens of THE LAST CONVOY.

Those screens are laid out for WIDTH x HEIGHT pixels. They are drawn on `canvas` at that size and then
scaled to fit the window (centred, aspect ratio kept), so they stay usable at any window size. Mouse
positions are converted back with `to_view`. The scaling maths itself is in layout.py (no pygame needed).
"""
import pygame

from layout import HEIGHT, WIDTH, fit_view, window_to_view


class Viewport:
    def __init__(self):
        self.canvas = pygame.Surface((WIDTH, HEIGHT), 0, 32)               # opaque: screens are drawn here
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA, 32)  # transparent: popups go here
        self.rect = pygame.Rect(fit_view(WIDTH, HEIGHT))

    def update(self, window_size):
        """Recalculate where the canvas appears in a window of this size."""
        self.rect = pygame.Rect(fit_view(*window_size))

    def to_view(self, pos):
        """A window pixel (such as the mouse) as coordinates on the WIDTH x HEIGHT canvas."""
        return window_to_view(pos, self.rect)

    def present(self, window, layer):
        """Draw `layer` (the canvas or the overlay) into the window at the current scale."""
        if self.rect.size == layer.get_size():
            window.blit(layer, self.rect.topleft)
        else:
            window.blit(pygame.transform.smoothscale(layer, self.rect.size), self.rect.topleft)
