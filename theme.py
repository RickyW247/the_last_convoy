"""Colours and fonts for THE LAST CONVOY."""
import pygame

pygame.font.init()

BG = (22, 27, 31)
PANEL = (35, 43, 48)
PANEL_LIGHT = (48, 58, 63)
WHITE = (235, 235, 222)
MUTED = (165, 176, 174)
GREEN = (116, 178, 105)
YELLOW = (226, 190, 93)
RED = (205, 91, 82)
ROAD = (61, 65, 65)
ROAD_LINE = (197, 185, 142)
DARK = (15, 18, 20)
BLUE = (100, 155, 190)
ORANGE = (211, 132, 74)

HORDE_STATE_COLORS = {"Distant": GREEN, "Approaching": YELLOW, "Close": ORANGE, "Overrun": RED}

FONT = pygame.font.SysFont("consolas", 19)
SMALL = pygame.font.SysFont("consolas", 15)
TINY = pygame.font.SysFont("consolas", 13)
TITLE = pygame.font.SysFont("consolas", 27, bold=True)
BIG = pygame.font.SysFont("consolas", 34, bold=True)
