"""Pygame-free balance constants and tiny text helpers for THE LAST CONVOY.

Nothing in this module may import pygame (directly or indirectly), so the game rules in the game package can be
imported and tested without a display or fonts. Colours and fonts live in theme.py, screen layout in the layout package and the Button class in widgets.py.
"""

# ---- Lore screen typing effect (navigation.update_lore, ui/screens.draw_lore_screen) ----
LORE_TYPING_CPS = 40               # characters typed per second
LORE_PARAGRAPH_PAUSE = 0.35        # seconds of pause at the end of each paragraph
LORE_CURSOR_BLINK_MS = 500         # the cursor is shown / hidden for this long once typing has finished (solid while typing)
TYPING_SOUND_INTERVAL_MS = 55      # at most one typing sound per this many ms

# ---- Map ----
MAP_LAYOUT = None   # None: every run uses a random layout from map_data.LAYOUTS; 1-5 forces that layout (testing)

MAP_BG_PIXEL_ART = False   # map screen / minimap background: True = chunky low-resolution pixel art, False = the PNG as drawn, smooth

# ---- Horde ----
HORDE_START_KM = 150   # fallback only; the real starting gap comes from DIFFICULTIES["horde_start_km"]
HORDE_DAILY_ADVANCE_KM = (8, 12)   # trips now last several days, so the horde moves less per day (was 25-35)
# When the gap reaches 0 the horde attacks the convoy every day instead of ending the run (before difficulty scaling).
# Kills per day = random KILLS + ESCALATION x (days already under attack), and at least MIN_FRACTION of the survivors
# left, so staying in an overrun stop wipes a convoy out within about 2-3 days. Vehicles lose a % of max health daily.
HORDE_ATTACK_SURVIVOR_KILLS = (2, 4)
HORDE_ATTACK_ESCALATION = 1
HORDE_ATTACK_MIN_FRACTION = 0.3
HORDE_ATTACK_VEHICLE_DAMAGE_PCT = (25, 40)
HORDE_BAR_MAX_KM = 400
DISTANT_MIN_KM = 150
APPROACHING_MIN_KM = 80
HORDE_STATES = ["Distant", "Approaching", "Close", "Overrun"]

# ---- Travel ----
KM_PER_SPEED_DAY = 3
FUEL_BASE_COST = 1
# Fuel used by a trip = FUEL_BASE_COST + km x (the convoy's combined fuel_consumption) / FUEL_USE_DIVISOR, rounded.
# Fuel is used only when travelling (not on days spent scavenging or repairing). The starting convoy (pickup, van,
# bus: consumption 8 + 10 + 18 = 36) uses 0.03 fuel per km; every vehicle added raises it. Lower = more fuel used.
FUEL_USE_DIVISOR = 1200
AMBUSH_CHANCE = 0.18        # per trip; each travel day rolls AMBUSH_CHANCE x AMBUSH_DAILY_FACTOR
SCRAP_FIND_CHANCE = 0.13    # per trip; each travel day rolls SCRAP_FIND_CHANCE x AMBUSH_DAILY_FACTOR
AMBUSH_DAILY_FACTOR = 0.4
# The automatic road-ambush damage (used when no ambush event can be shown): a random % of every vehicle's maximum
# health, before the convoy's defense absorbs part of it (Game.defense_reduction), and never less than
# AMBUSH_MIN_DAMAGE_PCT after that.
AMBUSH_DAMAGE_PCT = (5, 13)
AMBUSH_MIN_DAMAGE_PCT = 1
# Road wear: a rough road costs EVERY vehicle this % of its maximum health on arrival, whatever the player chose on the
# way (defense does not reduce it). By stop kind; a trip uses the highest value of any stop on it, so both legs of the
# Mountain Pass hurt. A node can override it with wear=N in map_data (0 = smooth road). Not charged on reaching the coast.
ROUTE_WEAR = {"pass": 10}
# Journeys: a trip takes ceil(km / km_per_day) x TRAVEL_DAY_SCALE days (at least MIN_TRIP_DAYS) and the convoy lives
# through it one day at a time. Each travel day has TRAVEL_EVENT_CHANCE of a random event. Raise the scale for longer trips.
TRAVEL_DAY_SCALE = 3
MIN_TRIP_DAYS = 2
TRAVEL_EVENT_CHANCE = 0.6
# Journey pacing (seconds, real time; only used when Game.animate_travel is on, which main.setup() does). The convoy
# screen shows "TRAVELLING..." and one day passes per TRAVEL_DAY_DELAY. After an event's result is dismissed (or a
# vehicle was picked to abandon) the journey waits TRAVEL_EVENT_DELAY before the next day, so events never stack.
TRAVEL_START_DELAY = 3.2
TRAVEL_DAY_DELAY = 4.0
TRAVEL_EVENT_DELAY = 6.4
TRAVEL_FAST_FORWARD = 4     # holding SPACE while travelling makes the delays pass this many times faster
TRAVEL_ANIMATION_FAST_FORWARD = 4   # holding SPACE while travelling makes the road animation (scroll, bounce, dust, zombies) this many times faster; 1 = no speed-up

# ---- Pacific evacuation (game/evacuation.py, design doc 2.3 / 19.2) ----
# Reaching the coast starts three scripted events (the port gate, the harbour master's quota, boarding under fire); then
# min(survivors, berths) survivors escape. Choices can add berths. False: reaching the coast wins at once (old behaviour, for tests).
EVACUATION_ENABLED = True
EVAC_BASE_BERTHS = 16   # places on the last ship before any choice changes them

# ---- Repair and defense ----
REPAIR_SCRAP_COST = 2
REPAIR_FRACTION = 0.25
DEFENSE_REDUCTION_PER_POINT = 1
DEFENSE_REDUCTION_CAP = 60

# ---- Consumption ----
SURVIVORS_PER_FOOD = 5
SURVIVORS_PER_WATER = 4

# ---- Survivor conditions (game/conditions.py) ----
# A day without enough food or water, per survivor: (fed -> hungry, hungry -> starving, starving -> leaves the convoy),
# and the same for thirst. Not scaled by difficulty (the difficulty already changes how fast supplies run out through
# "consumption").
SHORTAGE_RATES = {"hunger": (0.50, 0.40, 0.20), "thirst": (0.70, 0.50, 0.30)}
# Recovery on a day with enough food / water, chance per survivor: starving -> hungry and hungry -> fed (one stage a day
# at most), and the same for thirst. Recovery takes days, so early help is worth more (design doc 12.3). Thirst is the
# faster to deteriorate (see above) and also the faster to cure. Higher = quicker recovery.
NEED_RECOVER_RATES = {"hunger": 0.30, "thirst": 0.45}
# Injuries (chance per survivor per day): injured -> critical, critical -> dies, and the recovery steps critical ->
# injured -> healthy, which is faster with a Medical Care vehicle (the ambulance).
INJURY_WORSEN_RATE = 0.10
INJURY_DEATH_RATE = 0.15
INJURY_RECOVER_RATE = 0.10
MEDICAL_RECOVER_RATE = 0.35
# Share of the survivors left alive after a horde attack that it wounds (before the convoy's defense and the difficulty's
# "horde" multiplier), at least one.
HORDE_ATTACK_INJURY_FRACTION = 0.25
# The same for an automatic road ambush (travel.ambush, used when no ambush event can be shown): the share of the
# survivors it wounds before the convoy's defense cuts it, rounded, so a strong defense can spare everyone.
AMBUSH_INJURY_FRACTION = 0.10

# ---- Vehicle special abilities (vehicle_data.VEHICLE_ABILITIES, design doc section 6) ----
# Passive: they work automatically while the vehicle is in the convoy. Medical Care (Ambulance) uses MEDICAL_RECOVER_RATE above.
# Reinforced Protection (Military Humvee): this many extra defense points on top of the convoy's combined defense
# (Game.defense_reduction still caps the result at DEFENSE_REDUCTION_CAP).
REINFORCED_PROTECTION_BONUS = 5
# Recovery Support (Tow/Recovery Truck): scrap taken off each repair and off recovering an abandoned vehicle (never below 1).
RECOVERY_SUPPORT_REPAIR_DISCOUNT = 1
RECOVERY_SUPPORT_RECOVERY_DISCOUNT = 1

# ---- Difficulty ----
DIFFICULTIES = {
    "Easy":   {"consumption": 0.5, "horde": 0.5,  "scavenge": 1.5,  "horde_start_km": 200, "blurb": "Supplies last; the horde is slow."},
    "Normal": {"consumption": 1.0, "horde": 1.0,  "scavenge": 1.0,  "horde_start_km": 150, "blurb": "The standard experience."},
    "Hard":   {"consumption": 1.5, "horde": 1.5,  "scavenge": 0.75, "horde_start_km": 120, "blurb": "Scarce supplies, faster horde."},
}
DIFFICULTY_ORDER = ["Easy", "Normal", "Hard"]

# ---- Vehicle recovery ----
# Site KEYS (the keys of map_data.SITES, not their display names) where vehicles are recovered and upgraded. convoy.py
# checks at import that every key exists in map_data.SITES, so a renamed or mistyped key fails loudly.
RECOVERY_SITE_KEYS = ("mixed", "repair", "military")   # Truck Stop, Repair Depot, Military Installation
DEFAULT_RECOVERY_COST = 3  # scrap, for vehicle types missing from vehicle_data.RECOVERY_COSTS

# ---- Vehicle scavenging (scavenge.py, map_data.SITE_VEHICLES) ----
# A search of a site can turn up an abandoned vehicle that fits the place (a Police Station: police cars, a Farm: pickups...).
# The chance per search and the vehicle types are per site in map_data.SITE_VEHICLES (the open highway and the Mountain
# Pass have none). The player is always asked whether to take it. A taken vehicle is free, needs no Truck Stop / Repair
# Depot and no extra day, but still needs a spare adult driver, and counts as a recovered vehicle.
VEHICLE_SCAVENGE_ENABLED = True
VEHICLE_FIND_CHANCE_SCALE = 1.0       # multiplies every site's chance (and the difficulty's "scavenge" factor applies too)
VEHICLE_FIND_HEALTH = (0.40, 0.70)    # a scavenged vehicle starts with this share of its maximum health (min, max)

# ---- Achievements (achievement_data.py, achievements.py; design doc section 20.5) ----
# Completed achievements are saved in achievements.json (beside settings.json), so they survive restarts and new runs.
ACHIEVEMENTS_IN_SANDBOX = False   # False: nothing can be earned while SANDBOX MODE is on (infinite supplies)
COLLECTOR_VEHICLE_TYPES = 20       # Convoy Collector: different vehicle types that have been in a convoy (all runs together)
RECOVERED_VEHICLES_TARGET = 3     # Nothing Left Behind: vehicles recovered in one run
WINS_FOR_LONG_ROAD = 2            # The Long Road Again: runs won (the second win completes it)
SPECIAL_EVENTS_GROUP = "special_survivor_events"   # event group (special_event_data.py) that "The Long Road Again" unlocks
# Field Study (secret, unlocks the Mobile Laboratory): every one of these Game.screen values must have been shown at least
# once (all runs together; kept in achievements.json). The first 13 are the ones listed in game/state.py; check the last
# three ("background", "achievements", "history") against the screen names the game really uses, and add any screen missing.
SCREENS_TO_VISIT = ("title", "lore", "background", "convoy", "map", "vehicles", "missions", "survivors", "menu",
                    "difficulty", "settings", "credits", "instructions", "upgrade", "achievements", "history")
SPEED_RUN_DAYS = 20               # Chequered Flag: the run must be won within this many days


def people(count):
    return f"{count} survivor" + ("" if count == 1 else "s")
