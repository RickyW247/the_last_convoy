"""Vehicle upgrades of THE LAST CONVOY: the catalogue and the pure functions that apply it (no pygame, no game state).

Every upgrade has a clear scrap cost, a defined effect on the vehicle's statistics and the vehicle types it fits
(design document, section 9). Upgrades are installed once per vehicle and stay installed. A few also change how the
vehicle looks (`look`: the name of another sprite, see ui/vehicle_rendering.py): so far the Semi-Truck's cargo
upgrade, which hitches the trailer. This module is data and arithmetic only: Vehicle (game/vehicle.py) applies the
effects, Game (game/convoy.py) charges the scrap and decides where upgrades may be installed.

Trailers (Utility, Flatbed, Travel and the Semi-Truck's own Cargo Trailer) share the group "trailer": a vehicle tows at
most one, so the installed one has to be uninstalled before another can be installed. The three towable trailers carry a
`trailer` sprite name: they are drawn behind the vehicle (ui/vehicle_rendering.py get_rig_sprite) instead of replacing its
picture, so they work for every vehicle that can tow (all except the bikes, the tracked machines and the crane, wrecking
ball and car carrier trucks) without a PNG per combination. Which upgrades fit which vehicles is decided by the tuples
at the top (ALL_TYPES, ARMOUR_TYPES, RACK_TYPES, SEATING_TYPES, TRAILER_TYPES).

Balance: the costs and numbers below are first guesses for playtesting; change them here and nowhere else.
"""
from vehicle_data import VEHICLE_SPECS

# Every vehicle in the game (VEHICLE_SPECS, in its order), so a vehicle added there is covered by the general upgrades
# at once. The tuples below narrow that down for the upgrades that only make sense on some vehicles.
ALL_TYPES = tuple(VEHICLE_SPECS)

# The bikes: too small for welded plates, seats or a hitch (they get crash bars, panniers, an engine and a tank).
BIKE_TYPES = ("Motorcycle", "Dirt Bike", "Scooter")
ARMOUR_TYPES = tuple(t for t in ALL_TYPES if t not in BIKE_TYPES + ("Formula 1 Car",))

# Trailers: every vehicle can tow one except the bikes (nothing to hitch it to) and the machines that cannot pull a
# trailer: the tracked ones (Tank, Excavator, Bulldozer), the Crane and Wrecking Ball trucks (their boom and ball sit
# where the hitch would be) and the Car Carrier, which already is a trailer rig.
NO_TRAILER_TYPES = BIKE_TYPES + ("Tank", "Excavator", "Bulldozer", "Crane Truck", "Wrecking Ball Truck",
                                 "Car Carrier Truck", "Formula 1 Car")
TRAILER_TYPES = tuple(t for t in ALL_TYPES if t not in NO_TRAILER_TYPES)

# Cargo racks: vehicles with a bare roof or open bed to strap things to (cars, SUVs, small vans, buses, light trucks and
# the bikes' panniers). Not the vehicles that are a load-carrying box already (Semi, Box, Moving, Delivery and Postal
# vans/trucks...), the machinery, the specialist vehicles and the armoured ones.
RACK_TYPES = ("Pickup Truck", "Passenger Van", "School Bus", "Ambulance", "Military Humvee", "Tow/Recovery Truck",
              "Sedan", "Civilian SUV", "Utility SUV", "City Bus", "Motorhome",
              "Hatchback", "Taxi", "Station Wagon", "Minivan", "Coach Bus", "Tourist Bus", "Prison Transport Bus",
              "Police SUV", "Police Sedan", "Vintage Police Car", "Landscaping Truck", "Monster Truck",
              "Motorcycle", "Dirt Bike", "Scooter")

# Extra seating: vehicles with a passenger cabin or a bed that benches fit into (not the novelty and armoured specials,
# which are built around their seats already, nor the machinery and the bikes).
SEATING_TYPES = ("Passenger Van", "School Bus", "Ambulance", "Military Humvee", "Tow/Recovery Truck",
                 "Sedan", "Civilian SUV", "Utility SUV", "City Bus", "Motorhome",
                 "Hatchback", "Taxi", "Station Wagon", "Minivan", "Coach Bus", "Tourist Bus", "Prison Transport Bus",
                 "Police SUV", "Police Sedan", "Limousine", "Military Cargo Truck", "Armored Personnel Carrier",
                 "Utility Service Truck", "Road Maintenance Truck", "Landscaping Truck")

# Each upgrade: id (stored on vehicles), name, category (design document 9.2), cost in scrap, the vehicle types it fits,
# effects (change to the vehicle's stats; negative lowers it), blurb (shown on the upgrade screen) and optionally the
# name of the sprite the vehicle is drawn with once it is installed, `group` (a vehicle can have only one upgrade of a
# group) and `trailer` (the name of the sprite towed behind the vehicle).
UPGRADES = (
    {"id": "armor_plating", "name": "Armour Plating", "category": "Armour", "cost": 5, "types": ARMOUR_TYPES,
     "effects": {"health": 25, "defense": 1},
     "blurb": "Welded plates over the body: tougher, and a little harder to hit."},
    {"id": "reinforced_bumper", "name": "Reinforced Bumper", "category": "Defense", "cost": 6, "types": ALL_TYPES,
     "effects": {"defense": 4},
     "blurb": "A ram bar and brush guards that keep ambushers off the vehicle."},
    {"id": "engine_tuneup", "name": "Engine Tune-Up", "category": "Engine", "cost": 6, "types": ALL_TYPES,
     "effects": {"speed": 6},
     "blurb": "A rebuilt engine. The convoy goes as fast as its slowest vehicle, so tune that one first."},
    {"id": "fuel_injectors", "name": "Efficient Injectors", "category": "Engine", "cost": 4, "types": ALL_TYPES,
     "effects": {"fuel_consumption": -2},
     "blurb": "Cleaner burning: this vehicle uses less fuel on every trip."},
    {"id": "extra_tank", "name": "Extra Fuel Tank", "category": "Fuel",  "cost": 5,
     "types": tuple(t for t in ALL_TYPES if t != "Fuel Tanker"),
     "effects": {"fuel_capacity": 8},
     "blurb": "A second tank bolted under the frame."},
    {"id": "cargo_racks", "name": "Cargo Racks", "category": "Cargo", "cost": 5,
     "types": RACK_TYPES,
     "effects": {"cargo": 20},
     "blurb": "Roof and bed racks for more food, water and scrap."},
    {"id": "semi_trailer", "name": "Cargo Trailer", "category": "Cargo", "cost": 8, "types": ("Semi-Truck",),
     "effects": {"cargo": 100, "speed": -5, "fuel_consumption": 4},
     "look": "Semi-Truck Trailer", "group": "trailer",
     "blurb": "Hitch a freight trailer: a huge load, but a heavier, slower, thirstier rig."},
    {"id": "extra_seating", "name": "Extra Seating", "category": "Passenger", "cost": 5,
     "types": SEATING_TYPES,
     "effects": {"passengers": 3},
     "blurb": "Bolted-in benches for more survivors."},
    {"id": "utility_trailer", "name": "Utility Trailer", "category": "Trailer", "cost": 7, "types": TRAILER_TYPES,
     "effects": {"cargo": 40, "speed": -4, "fuel_consumption": 3},
     "group": "trailer", "trailer": "Utility Trailer",
     "blurb": "A mesh-sided cargo trailer: plenty of room for supplies, but a slower, thirstier convoy."},
    {"id": "flatbed_trailer", "name": "Flatbed Trailer", "category": "Trailer", "cost": 9, "types": TRAILER_TYPES,
     "effects": {"cargo": 70, "speed": -5, "fuel_consumption": 4},
     "group": "trailer", "trailer": "Flatbed Trailer",
     "blurb": "A long open flatbed with loading ramps: the biggest load, and the heaviest to pull."},
    {"id": "travel_trailer", "name": "Travel Trailer", "category": "Trailer", "cost": 8, "types": TRAILER_TYPES,
     "effects": {"passengers": 6, "speed": -5, "fuel_consumption": 3},
     "group": "trailer", "trailer": "Travel Trailer",
     "blurb": "A camper to sleep in: room for six more survivors, towed behind."},
)

_BY_ID = {upgrade["id"]: upgrade for upgrade in UPGRADES}

# Fail loudly at import on a renamed or mistyped vehicle, or on a vehicle that ended up with nothing to install.
_unknown = sorted({t for upgrade in UPGRADES for t in upgrade["types"]} - set(VEHICLE_SPECS))
if _unknown:
    raise ValueError(f"UPGRADES name vehicle types that are not in VEHICLE_SPECS: {_unknown}")
_bare = [t for t in VEHICLE_SPECS if not any(t in upgrade["types"] for upgrade in UPGRADES)]
if _bare:
    raise ValueError(f"These vehicle types have no upgrade that fits them: {_bare}")

# Short stat names, the same as the vehicle table's column headings, in the order effects are listed.
STAT_ORDER = ("health", "defense", "speed", "cargo", "passengers", "fuel_capacity", "fuel_consumption")
STAT_LABELS = {"health": "HP", "defense": "DEF", "speed": "SPD", "cargo": "CARGO", "passengers": "PASS",
               "fuel_capacity": "FCAP", "fuel_consumption": "FUSE"}
STAT_FLOORS = {"speed": 1, "fuel_consumption": 1}   # no stat goes below 0, and these two never below 1

# How an upgraded vehicle is drawn in the convoy scene, by sprite name (see Vehicle.sprite_type): the label under it and
# where it kicks up dust (x of the back edge of each wheel on the road, as a fraction of the sprite's width).
UPGRADE_LOOKS = {
    "Semi-Truck Trailer": {"label": "SEMI + TRAILER", "dust": (0.16, 0.48, 0.55, 0.895, 0.96)},
}

# Size factor of each towed trailer in the convoy scene, the same idea as vehicle_data.VEHICLE_SCENE_SIZE: 1.0 is about a
# pickup's length, above 1 is bigger, below 1 is smaller. Change one number to resize that trailer alone.
TRAILER_SCENE_SIZE = {
    "Utility Trailer": 1.0,
    "Flatbed Trailer": 1.0,
    "Travel Trailer": 1.4,
}

# Towed trailers (the `trailer` of an upgrade): where each one kicks up dust, as the x of the back edge of each wheel
# on the road, as a fraction of the trailer sprite's own width. Estimated from the PNGs: re-measure if the dust looks off.
TRAILER_DUST = {
    "Utility Trailer": (0.68, 0.80),
    "Flatbed Trailer": (0.67, 0.80),
    "Travel Trailer": (0.67, 0.78),
}


def get_upgrade(upgrade_id):
    """The upgrade with this id, or None."""
    return _BY_ID.get(upgrade_id)


def upgrades_for(vehicle_type):
    """The upgrades that fit this vehicle type, in catalogue order."""
    return [upgrade for upgrade in UPGRADES if vehicle_type in upgrade["types"]]


def fits(upgrade, vehicle_type):
    return vehicle_type in upgrade["types"]


def apply_effects(stats, effects):
    """A copy of `stats` with `effects` added (floors applied)."""
    changed = dict(stats)
    for stat, delta in effects.items():
        if stat in changed:
            changed[stat] = max(STAT_FLOORS.get(stat, 0), changed[stat] + delta)
    return changed


def describe_effects(effects):
    """The effects as a short line: "+25 HP  +1 DEF" (in STAT_ORDER)."""
    return "  ".join(f"{effects[stat]:+d} {STAT_LABELS[stat]}" for stat in STAT_ORDER if effects.get(stat))


def stat_changes(stats, effects):
    """[(label, old, new)] for each stat the effects change, in STAT_ORDER (what the upgrade screen previews)."""
    after = apply_effects(stats, effects)
    return [(STAT_LABELS[stat], stats[stat], after[stat]) for stat in STAT_ORDER
            if stat in stats and after[stat] != stats[stat]]


def conflicting_upgrade(upgrade, installed_ids):
    """The id of the installed upgrade that blocks this one (same group, e.g. another trailer), or None."""
    group = upgrade.get("group")
    if not group:
        return None
    return next((i for i in installed_ids if i != upgrade["id"] and _BY_ID.get(i, {}).get("group") == group), None)


def trailer_for(installed_ids):
    """The name of the trailer sprite towed by a vehicle with these upgrades installed, or None."""
    for upgrade_id in installed_ids:
        upgrade = _BY_ID.get(upgrade_id)
        if upgrade and upgrade.get("trailer"):
            return upgrade["trailer"]
    return None


def look_for(vehicle_type, installed_ids):
    """The sprite name a vehicle is drawn with: its own type, or the look of the latest installed upgrade that has one."""
    sprite = vehicle_type
    for upgrade_id in installed_ids:
        upgrade = _BY_ID.get(upgrade_id)
        if upgrade and upgrade.get("look"):
            sprite = upgrade["look"]
    return sprite


def fully_upgraded_stats(vehicle_type, stats):
    """`stats` with every upgrade that fits the type installed: the widest the vehicle's numbers can ever get, for
    sizing the table columns so that the text size does not jump when an upgrade is installed."""
    result = dict(stats)
    for upgrade in upgrades_for(vehicle_type):
        result = apply_effects(result, {k: v for k, v in upgrade["effects"].items() if v > 0})
    return result
