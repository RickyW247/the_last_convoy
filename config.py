"""Pygame-free balance constants and tiny text helpers for THE LAST CONVOY.

Nothing in this module may import pygame (directly or indirectly), so the game rules in game.py can be
imported and tested without a display or fonts. Colours and fonts live in theme.py, screen layout in layout.py and the Button class in widgets.py.
"""

# ---- Horde ----
HORDE_START_KM = 200
HORDE_DAILY_ADVANCE_KM = (25, 35)
HORDE_BAR_MAX_KM = 400
DISTANT_MIN_KM = 150
APPROACHING_MIN_KM = 80
HORDE_STATES = ["Distant", "Approaching", "Close", "Overrun"]

# ---- Travel ----
KM_PER_SPEED_DAY = 3
FUEL_BASE_COST = 1
FUEL_KM_PER_UNIT = 50
AMBUSH_CHANCE = 0.18
SCRAP_FIND_CHANCE = 0.13

# ---- Repair and defense ----
REPAIR_SCRAP_COST = 2
REPAIR_FRACTION = 0.25
DEFENSE_REDUCTION_PER_POINT = 1
DEFENSE_REDUCTION_CAP = 60

# ---- Consumption ----
SURVIVORS_PER_FOOD = 5
SURVIVORS_PER_WATER = 4

# ---- Difficulty ----
DIFFICULTIES = {
    "Easy": {"consumption": 0.5, "horde": 0.5, "scavenge": 1.5, "blurb": "Supplies last; the horde is slow."},
    "Normal": {"consumption": 1.0, "horde": 1.0, "scavenge": 1.0, "blurb": "The standard experience."},
    "Hard": {"consumption": 1.5, "horde": 1.5, "scavenge": 0.75, "blurb": "Scarce supplies, faster horde."},
}
DIFFICULTY_ORDER = ["Easy", "Normal", "Hard"]

# ---- Vehicle recovery ----
RECOVERY_SITES = ("Truck Stop", "Repair Depot", "Military Installation")
DEFAULT_RECOVERY_COST = 3  # scrap, for vehicle types missing from vehicles.RECOVERY_COSTS


def people(count):
    return f"{count} survivor" + ("" if count == 1 else "s")
