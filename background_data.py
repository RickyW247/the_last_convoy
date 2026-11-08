"""Player backgrounds of THE LAST CONVOY (design doc section 21). Pygame-free data only.

Both the starting vehicles (starting_vehicles() below, used where a run starts) and the abilities / the Criminal trait
are applied. The rules live in game/background_rules.py (BackgroundMixin), which reads the "ability_key" / "trait_key"
of each background and the numbers in this file; the places that use them are repair() / repair_cost() /
recovery_price() (game/convoy.py), _search_site() / find_survivors() (game/scavenge.py), and the event code
(game/event_manager.py, game/effect_handler.py). Balance numbers are first guesses: change them here and nowhere else.

"vehicles" must name types that exist in vehicle_data.VEHICLE_SPECS, at most one of each (the convoy holds one vehicle
per type). Where the design doc names a specific vehicle, that vehicle is used; a comment beside it says which design doc
vehicle it is, and which background still uses a stand-in (the Criminal "armoured van").
"""
from vehicle_data import VEHICLE_SPECS

DEFAULT_BACKGROUND = "Civilian"

BACKGROUND_ORDER = ["Military", "Police", "Government", "Corporate", "Criminal", "Civilian"]

BACKGROUNDS = {
    "Military": {
        "blurb": "You served in the U.S. military, in logistics, transport or support.",
        "vehicles": ["Military Humvee", "Military Cargo Truck", "Fuel Tanker"],
        "ability": "Military Logistics",
        "ability_key": "military_logistics",
        "ability_text": "Military vehicles receive reduced maintenance costs.",
        "playstyle": "A durable starting convoy with strong transport capabilities.",
        "trait": None,
        "trait_key": None,
    },
    "Police": {
        "blurb": "You were a police officer during the emergency response and civilian evacuation.",
        "vehicles": ["Police Sedan", "Prison Transport Bus", "Police SUV"],   # Police patrol car, Police transport van
        "ability": "Emergency Response",
        "ability_key": "emergency_response",
        "ability_text": "Selected emergency and rescue events incur reduced time penalties.",
        "playstyle": "A flexible convoy suited to rescue operations and emergencies.",
        "trait": None,
        "trait_key": None,
    },
    "Government": {
        "blurb": "You worked in a government emergency management or disaster response department.",
        "vehicles": ["Passenger Van", "Ambulance", "Box Truck"],   # Utility SUV = Government utility SUV
        "ability": "Resource Coordination",
        "ability_key": "resource_coordination",
        "ability_text": "Scavenging operations have a chance to yield additional supplies.",
        "playstyle": "A balanced convoy focused on resource management and supporting survivors.",
        "trait": None,
        "trait_key": None,
    },
    "Corporate": {
        "blurb": "You worked for a logistics or industrial company and took its last vehicles and resources.",
        "vehicles": ["Semi-Truck", "Pickup Truck", "Delivery Van"],   # Delivery Van = Commercial delivery van
        "ability": "Fleet Management",
        "ability_key": "fleet_management",
        "ability_text": "Vehicle repair costs are reduced.",
        "playstyle": "A cargo-oriented convoy suited to carrying supplies and accumulating resources.",
        "trait": None,
        "trait_key": None,
    },
    "Criminal": {
        "blurb": "You led a gang. When the outbreak hit you gathered your people, vehicles and supplies.",
        "vehicles": ["Sports Car", "Utility SUV", "Pickup Truck"],   # Sports Car = Modified muscle car, Utility SUV = stand-in for the Armoured van (the real Armored Cash-in-Transit Van is a bonus vehicle), Pickup = Stolen pickup
        "ability": "Underworld Connections",
        "ability_key": "underworld_connections",
        "ability_text": "Certain locations and events offer rare supplies, valuable goods and other opportunities.",
        "playstyle": "High risk: criminal networks, intimidation and alternative solutions to encounters.",
        "trait": ("Untrusted Reputation", "Ordinary survivors are less likely to join, and some settlements may refuse to cooperate."),
        "trait_key": "untrusted_reputation",
    },
    "Civilian": {
        "blurb": "You were an ordinary civilian who took charge of a group of survivors in the first chaos.",
        "vehicles": ["Pickup Truck", "Passenger Van", "School Bus"],
        "ability": "Improvisation",
        "ability_key": "improvisation",
        "ability_text": "Basic vehicle repairs require fewer mechanical parts.",
        "playstyle": "A balanced, accessible convoy without a specialised focus.",
        "trait": None,
        "trait_key": None,
    },
}

# Shown on the background screen while only part of a background is applied. Set to "" once all of it is.
PLACEHOLDER_NOTE = ""

# ---- Ability numbers (first guesses for playtesting) --------------------------------------------------------------
# Military Logistics: the vehicles below count as "military".
# Recovering one or installing an upgrade on it costs this much less scrap, and a REPAIR heals it this much more
# (0.4 = 40% more health per repair: 25% becomes 35%). Repair cost is a day, not scrap, so keep the bonus modest.
MILITARY_VEHICLE_TYPES = ("Military Humvee", "Military Cargo Truck", "Fuel Tanker")
MILITARY_RECOVERY_DISCOUNT = 1
MILITARY_UPGRADE_DISCOUNT = 1
MILITARY_REPAIR_BONUS = 0.4

# Emergency Response: events marked "emergency": True (event_data.py) cost this share of their horde-gap time penalty
# (0.5 = half; only losses of gap are cut, never gains). A penalty is never cut below 1 km.
POLICE_EMERGENCY_TIME_FACTOR = 0.5

# Resource Coordination: each scavenge search has this chance to also yield a bonus of this share of the finds
# (rounded, at least 1 of each resource found). About +15% supplies on average.
GOVERNMENT_SCAVENGE_CHANCE = 0.30
GOVERNMENT_SCAVENGE_SHARE = 0.5

# Fleet Management (Corporate): scrap less per REPAIR (config.REPAIR_SCRAP_COST is 2, so half price), and per vehicle
# recovered.
CORPORATE_REPAIR_DISCOUNT = 1
CORPORATE_RECOVERY_DISCOUNT = 1

# Improvisation (Civilian): every CIVILIAN_REFUND_EVERY-th REPAIR gives CIVILIAN_REPAIR_REFUND scrap back (spare parts
# made from scrap: on average a repair costs 1.5 scrap, not Corporate's flat 1). Counted per run.
CIVILIAN_REPAIR_REFUND = 1
CIVILIAN_REFUND_EVERY = 2

# Underworld Connections (Criminal): a search of one of these site keys (map_data.SITES: Truck Stop, Repair Depot, Auto
# Garage, Warehouse, Hardware Store) has this chance to turn up a stash (ranges are fuel / scrap, scaled by the
# difficulty like any find); events marked "requires": {"background": "Criminal"} appear.
CRIMINAL_STASH_SITES = ("mixed", "repair", "garage", "warehouse", "hardware")
CRIMINAL_STASH_CHANCE = 0.30
CRIMINAL_STASH_FUEL = (2, 4)
CRIMINAL_STASH_SCRAP = (3, 6)
# Untrusted Reputation (Criminal): each person who would join (a scavenging find or an event rescue) only does so
# with this chance, and events marked "settlement": True are skipped this often (the town will not deal with you).
CRIMINAL_RECRUIT_FACTOR = 0.6
CRIMINAL_SETTLEMENT_REFUSAL_CHANCE = 0.4


def starting_vehicles(background):
    """The vehicle types a run with this background starts with (falls back to the default background's)."""
    data = BACKGROUNDS.get(background) or BACKGROUNDS[DEFAULT_BACKGROUND]
    return list(data["vehicles"])


# Fails loudly at import if a background names a vehicle type that does not exist or lists one twice.
for _name, _data in BACKGROUNDS.items():
    _types = _data["vehicles"]
    assert len(set(_types)) == len(_types), f"{_name}: duplicate starting vehicle"
    assert all(t in VEHICLE_SPECS for t in _types), f"{_name}: unknown vehicle in {_types}"
    assert _data.get("ability_key"), f"{_name}: no ability_key"
assert all(t in VEHICLE_SPECS for t in MILITARY_VEHICLE_TYPES), "MILITARY_VEHICLE_TYPES names an unknown vehicle"
