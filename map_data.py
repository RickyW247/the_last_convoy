"""Map data and pathfinding for THE LAST CONVOY.

Pure data and logic: this module must not import pygame or any drawing code. map_system.py draws it.
"""
import heapq
import math
import random

__all__ = ["SURVIVOR_FINDS", "SITE_VEHICLES", "RARE_FUEL", "FUEL_SITES", "SITES", "NODES", "START", "PACIFIC", "MILITARY_BASE",
           "MILITARY_SITE_KEYS", "ROAD_EDGES", "ADJACENT", "shortest_path", "is_military_base",
           "LAYOUTS", "choose_layout", "load_layout", "layout_name", "scenery_for"]

# Survivor groups found while scavenging: (chance per scavenge, smallest group, largest group).
# Not affected by difficulty. Keyed by the site key (see SITES).
SURVIVOR_FINDS = {
    "start": (0.20, 1, 3),    # the open starting highway: survivors only
    "fuel": (0.08, 1, 2),     # Gas Station
    "food": (0.15, 2, 4),     # Supermarket
    "mixed": (0.22, 2, 5),    # Truck Stop
    "repair": (0.10, 1, 3),   # Repair Depot
    "farm": (0.10, 1, 2),     # Farm
    "hospital": (0.30, 2, 5),  # Hospital
    "town": (0.25, 2, 5),     # Small Town
    "diner": (0.10, 1, 3),    # Diner
    "pharmacy": (0.12, 1, 3),  # Pharmacy
    "warehouse": (0.05, 1, 2),  # Warehouse
    "water": (0.05, 1, 2),    # Water Tower
    "garage": (0.08, 1, 2),   # Auto Garage
    "shelter": (0.45, 1, 4),  # Survivor Shelter
    "police": (0.12, 1, 3),   # Police Station
    "scrapyard": (0.05, 1, 2),  # Scrapyard
    "school": (0.20, 1, 4),   # School
    "church": (0.35, 1, 4),   # Church
    "orchard": (0.10, 1, 2),  # Orchard
    "convenience": (0.15, 1, 3),  # Convenience Store
    "marina": (0.10, 1, 2),   # Marina
    "airfield": (0.08, 1, 2),  # Airfield
    "motel": (0.20, 1, 3),    # Motel
    "lumber": (0.05, 1, 2),   # Lumber Yard
    "barracks": (0.25, 1, 3),  # Barracks (Military Base)
    "motor_pool": (0.05, 1, 2),  # Motor Pool (Military Base)
}

# ---------------------------------------------------------------------------
# Sites: the places inside a stop that can be scavenged, one at a time. The same site can exist in several
# stops. Keyed by site key; "sites" of a node (below) lists these keys.
#   "name" is the full name (also used by RECOVERY_SITES), "short" fits on a button, "detail" is the help text.
#   "finds" is what one search yields: resource -> (smallest, largest). The amount is rolled every search (a smallest of 0
#       means "sometimes nothing") and scaled by the difficulty. Resources: fuel (the tank) and food, water, scrap (cargo).
#       The order matters for cargo: when the convoy is nearly full, the first resources fill the free space first.
#   "message" is said in the log after the search.
#   "rare_fuel" (optional) is a small extra chance of fuel: (chance per search, smallest, largest). It is there so that no
#       stop can leave the convoy stuck without fuel (checked by _validate).
#   "no_survivors" (optional) is said when the site can hold survivors (SURVIVOR_FINDS) and none were found.
# The three military sites ("military", "barracks", "motor_pool") exist ONLY at the Military Base (checked by _validate).
# ---------------------------------------------------------------------------
SITES = {
    "start": {"name": "Open Highway", "short": "Open Highway",
              "detail": "Starting highway: almost no supplies (rarely a little fuel), but stranded survivors may be found.",
              "finds": {}, "rare_fuel": (0.15, 2, 4), "no_survivors": "No one was found along the highway."},
    "fuel": {"name": "Gas Station", "short": "Gas Station",
             "detail": "Potential supplies: fuel and basic provisions. Survivors sometimes found.",
             "finds": {"fuel": (5, 12), "food": (0, 3)},
             "message": "Scavenged fuel and a few supplies from the gas station."},
    "food": {"name": "Supermarket", "short": "Supermarket",
             "detail": "Potential supplies: canned food and bottled water. Survivors may be found.",
             "finds": {"food": (6, 12), "water": (3, 8)},
             "message": "Found canned food and bottled water in the supermarket."},
    "mixed": {"name": "Truck Stop", "short": "Truck Stop",
              "detail": "Potential supplies: mixed supplies. Survivors are most likely here.",
              "finds": {"food": (2, 6), "water": (3, 7), "scrap": (1, 4)},
              "message": "Scavenging party returned with mixed supplies."},
    "repair": {"name": "Repair Depot", "short": "Repair Depot",
               "detail": "Potential supplies: scrap and spare parts. Survivors are rare.",
               "finds": {"scrap": (3, 7), "fuel": (0, 4)},
               "message": "Searched the repair depot for scrap and spare parts."},
    "farm": {"name": "Farm", "short": "Farm",
             "detail": "Lots of food and water, rarely some fuel. Survivors occasionally.",
             "finds": {"food": (10, 18), "water": (6, 12)}, "rare_fuel": (0.15, 2, 5),
             "message": "Gathered plenty of food and fresh water at the farm."},
    "hospital": {"name": "Hospital", "short": "Hospital",
                 "detail": "Some water, rarely some fuel. Survivors are likely here.",
                 "finds": {"water": (3, 6), "food": (0, 2)}, "rare_fuel": (0.10, 2, 4),
                 "message": "Searched the hospital for supplies."},
    "military": {"name": "Military Installation", "short": "Military Inst.",
                 "detail": "Armoury and stores: scrap and fuel. Military vehicles can be recovered at this base. Dangerous!",
                 "finds": {"scrap": (5, 10), "fuel": (3, 8)},
                 "message": "Salvaged scrap and fuel from the military installation."},
    "barracks": {"name": "Barracks", "short": "Barracks",
                 "detail": "Rations and water from the mess hall. Some soldiers may still be found.",
                 "finds": {"food": (5, 10), "water": (3, 7)},
                 "message": "Raided the barracks mess hall for rations and water."},
    "motor_pool": {"name": "Motor Pool", "short": "Motor Pool",
                   "detail": "Fuel from the vehicle depot and scrap from stripped trucks. Survivors are rare.",
                   "finds": {"fuel": (5, 10), "scrap": (2, 5)},
                   "message": "Drained fuel and stripped scrap in the motor pool."},
    "town": {"name": "Small Town", "short": "Small Town",
             "detail": "Mixed supplies. Survivors are likely here.",
             "finds": {"food": (2, 6), "water": (3, 7), "scrap": (1, 4)},
             "message": "Scavenging party returned with mixed supplies."},
    "diner": {"name": "Diner", "short": "Diner",
              "detail": "Meals and drinks left in the kitchen. Survivors sometimes found.",
              "finds": {"food": (4, 9), "water": (3, 6)},
              "message": "Found meals and drinks in the diner's kitchen."},
    "hardware": {"name": "Hardware Store", "short": "Hardware",
                 "detail": "Plenty of scrap. Survivors are unlikely.",
                 "finds": {"scrap": (4, 8)},
                 "message": "Hauled scrap and tools out of the hardware store."},
    "pharmacy": {"name": "Pharmacy", "short": "Pharmacy",
                 "detail": "A little water and food. Survivors may be found.",
                 "finds": {"water": (2, 4), "food": (0, 2)},
                 "message": "Searched the pharmacy for water and a few supplies."},
    "warehouse": {"name": "Warehouse", "short": "Warehouse",
                  "detail": "Crates of food, some water and scrap. Survivors are rare.",
                  "finds": {"food": (3, 8), "water": (2, 5), "scrap": (2, 5)},
                  "message": "Broke open crates in the warehouse."},
    "water": {"name": "Water Tower", "short": "Water Tower",
              "detail": "A lot of clean water. Survivors are rare.",
              "finds": {"water": (7, 13)},
              "message": "Filled up on clean water at the water tower."},
    "garage": {"name": "Auto Garage", "short": "Auto Garage",
               "detail": "Fuel and scrap. Survivors sometimes found.",
               "finds": {"fuel": (3, 8), "scrap": (2, 5)},
               "message": "Drained fuel and stripped scrap at the auto garage."},
    "scrapyard": {"name": "Scrapyard", "short": "Scrapyard",
                  "detail": "Heaps of scrap and some fuel left in wrecked cars. Survivors are rare.",
                  "finds": {"scrap": (5, 10), "fuel": (2, 6)},
                  "message": "Stripped scrap and drained fuel from the wrecks at the scrapyard."},
    "shelter": {"name": "Survivor Shelter", "short": "Shelter",
                "detail": "Few supplies, but survivors are very likely here.",
                "finds": {"food": (0, 2), "water": (1, 3)},
                "message": "Checked the survivor shelter."},
    "police": {"name": "Police Station", "short": "Police Station",
               "detail": "Scrap and some fuel. Survivors may be found.",
               "finds": {"scrap": (3, 6), "fuel": (0, 3)},
               "message": "Searched the police station for scrap and fuel."},
    "school": {"name": "School", "short": "School",
               "detail": "Food and water from the cafeteria. Survivors are likely here.",
               "finds": {"food": (2, 5), "water": (2, 4)},
               "message": "Searched the school cafeteria and classrooms."},
    "church": {"name": "Church", "short": "Church",
               "detail": "Few supplies, but survivors often shelter here.",
               "finds": {"food": (0, 3), "water": (1, 4)},
               "message": "Checked the church hall and storerooms."},
    "orchard": {"name": "Orchard", "short": "Orchard",
                "detail": "Plenty of fruit, a little water, rarely some fuel. Survivors occasionally.",
                "finds": {"food": (6, 12), "water": (1, 3)}, "rare_fuel": (0.12, 2, 4),
                "message": "Picked fruit and filled bottles at the orchard."},
    "convenience": {"name": "Convenience Store", "short": "Corner Store",
                    "detail": "Snacks and bottled drinks. Survivors may be found.",
                    "finds": {"food": (2, 6), "water": (2, 5)},
                    "message": "Cleared the shelves of the convenience store."},
    "marina": {"name": "Marina", "short": "Marina",
               "detail": "Boat fuel and fresh water. Survivors sometimes found.",
               "finds": {"fuel": (3, 7), "water": (2, 5)},
               "message": "Siphoned boat fuel and filled up on water at the marina."},
    "airfield": {"name": "Airfield", "short": "Airfield",
                 "detail": "Aviation fuel and a little scrap. Survivors sometimes found.",
                 "finds": {"fuel": (4, 9), "scrap": (1, 3)},
                 "message": "Pumped fuel and picked up scrap at the airfield."},
    "motel": {"name": "Motel", "short": "Motel",
              "detail": "A little of everything left in the rooms. Survivors may be found.",
              "finds": {"food": (1, 3), "water": (1, 3), "scrap": (0, 2)},
              "message": "Went through the motel rooms."},
    "lumber": {"name": "Lumber Yard", "short": "Lumber Yard",
               "detail": "Plenty of scrap, rarely some fuel. Survivors are rare.",
               "finds": {"scrap": (4, 8)}, "rare_fuel": (0.10, 2, 3),
               "message": "Hauled scrap and cut timber at the lumber yard."},
    "pass": {"name": "Mountain Pass", "short": "Mountain Pass",
             "detail": "Alternative route: shorter, but little to find (rarely some fuel) and ambushes are likely.",
             "finds": {"scrap": (1, 3)}, "rare_fuel": (0.15, 2, 4),
             "message": "Searched the roadside at the pass for scrap."},
}

# Derived from SITES (kept as names of their own for the modules that use them).
RARE_FUEL = {key: site["rare_fuel"] for key, site in SITES.items() if "rare_fuel" in site}
FUEL_SITES = {key for key, site in SITES.items() if "fuel" in site["finds"] or "rare_fuel" in site}

# The sites that make up the Military Base, and only it. Every layout has exactly one base (a dead end) and no other stop
# may hold one of these sites (checked by _validate). Military vehicles can only be recovered there (convoy.py).
MILITARY_SITE_KEYS = frozenset({"military", "barracks", "motor_pool"})

# Vehicles that can be found while scavenging a site (scavenge.py, config.VEHICLE_SCAVENGE_ENABLED): site key ->
# (chance per search, [vehicle types that make sense at that place]). A site that is missing here never holds a vehicle
# (the open highway "start", the Mountain Pass "pass", and the places where nothing drivable would be left: the water
# tower, the church...). Bonus vehicles may be listed too, but one is only found once an achievement has unlocked it
# (scavenge.py; always in sandbox mode), and military vehicles only at the military sites (all checked by _validate_sites, which imports vehicle_data: data only, no pygame).
SITE_VEHICLES = {
    "fuel": (0.08, ["Pickup Truck", "Sedan", "Hatchback", "Civilian SUV", "Fuel Tanker", "Semi-Truck"]),   # Gas Station
    "food": (0.08, ["Delivery Van", "Box Truck", "Refrigerated Truck", "Station Wagon", "Minivan"]),   # Supermarket
    "mixed": (0.10, ["Semi-Truck", "Box Truck", "Moving Truck", "Flatbed Truck", "Fuel Tanker", "Motorhome",
                     "Pickup Truck"]),   # Truck Stop
    "repair": (0.10, ["Tow/Recovery Truck", "Utility Service Truck", "Road Maintenance Truck", "Flatbed Truck",
                      "Utility SUV", "Pickup Truck"]),   # Repair Depot
    "garage": (0.12, ["Pickup Truck", "Sedan", "Utility SUV", "Taxi", "Sports Car", "Tow/Recovery Truck"]),   # Auto Garage
    "scrapyard": (0.10, ["Sedan", "Hatchback", "Taxi", "Garbage Truck", "Dump Truck", "Tow/Recovery Truck"]),
    "farm": (0.08, ["Pickup Truck", "Utility SUV", "Flatbed Truck", "Landscaping Truck"]),
    "orchard": (0.06, ["Pickup Truck", "Utility SUV", "Landscaping Truck"]),
    "hospital": (0.10, ["Ambulance", "Passenger Van", "Sedan", "Civilian SUV"]),
    "police": (0.10, ["Police SUV", "Police Sedan", "Prison Transport Bus"]),   # Police Station
    "school": (0.10, ["School Bus", "Passenger Van", "Minivan"]),
    "shelter": (0.05, ["Passenger Van", "Minivan", "School Bus"]),   # Survivor Shelter
    "church": (0.05, ["Passenger Van", "Minivan", "Station Wagon"]),
    "town": (0.08, ["Sedan", "Hatchback", "Station Wagon", "Minivan", "Taxi", "Postal Van", "Civilian SUV",
                    "City Bus"]),   # Small Town
    "diner": (0.06, ["Pickup Truck", "Sedan", "Station Wagon", "Semi-Truck"]),
    "hardware": (0.06, ["Pickup Truck", "Delivery Van", "Flatbed Truck", "Utility Service Truck"]),
    "pharmacy": (0.04, ["Delivery Van", "Hatchback", "Sedan"]),
    "convenience": (0.05, ["Delivery Van", "Sedan", "Hatchback"]),   # Convenience Store
    "warehouse": (0.08, ["Box Truck", "Moving Truck", "Refrigerated Truck", "Flatbed Truck", "Semi-Truck"]),
    "lumber": (0.08, ["Flatbed Truck", "Dump Truck", "Pickup Truck", "Semi-Truck"]),   # Lumber Yard
    "marina": (0.05, ["Pickup Truck", "Civilian SUV", "Motorhome"]),
    "airfield": (0.06, ["Fuel Tanker", "Utility SUV", "Pickup Truck", "Fire Engine"]),
    "motel": (0.08, ["Sedan", "Station Wagon", "Civilian SUV", "Motorhome", "Sports Car"]),
    "water": (0.04, ["Utility Service Truck", "Pickup Truck"]),   # Water Tower
    # The Military Base (the only place military vehicles can be found, as with recovery).
    "military": (0.12, ["Military Humvee", "Military Cargo Truck"]),   # Military Installation
    "barracks": (0.08, ["Military Humvee", "Military Cargo Truck", "Armored Personnel Carrier"]),
    "motor_pool": (0.15, ["Military Humvee", "Military Cargo Truck", "Armored Personnel Carrier",
                          "Mobile Command Vehicle", "Tow/Recovery Truck"]),
}

# ---------------------------------------------------------------------------
# The map. Each node has a position "axis" in km on the straight Start-to-Pacific line and a position "pos" on
# the map screen. Side stops share their parent's axis position (a detour costs time, not distance west).
# A node's index in the list is its id; "sites" lists the site keys that can be scavenged there.
#
# LAYOUTS holds the predefined maps; every run uses one of them (choose_layout, called by Game.reset). Rules every
# layout keeps (checked by _validate when this module loads): the same 14 stops with the same ids in every layout
# (0-5 Starting Highway, City 1-4, Pacific Coast; 6-9 City 5-8; 10 Mountain Pass; 11 Military Base; 12 Riverside;
# 13 Lakeside, so missions can name any stop); the start connects to City 1; road km is never less than the axis
# distance; the Mountain Pass is never a dead end and the quickest Start-to-Pacific route through it is shorter than the
# quickest one without it (a risky shortcut); the Military Base is always a dead end (one road) and holds all of the
# military sites and none of the other stops do; no two roads cross or run into each other and no road passes over a
# stop it does not serve (see _validate_geometry).
# NODES / ROAD_EDGES / ADJACENT are filled in place by load_layout, so `from map_data import NODES` stays valid.
# ---------------------------------------------------------------------------
START, PACIFIC, MILITARY_BASE = 0, 5, 11

# The sites of every named stop (the same in every layout; the stops move around, their sites do not).
_STOP_SITES = {
    "City 1": ["fuel", "farm", "diner"],
    "City 2": ["food", "hospital", "school"],
    "City 3": ["mixed", "scrapyard", "warehouse"],
    "City 4": ["repair", "town", "hardware"],
    "City 5": ["orchard", "water", "shelter"],
    "City 6": ["hospital", "police", "pharmacy"],
    "City 7": ["scrapyard", "garage", "warehouse"],
    "City 8": ["town", "church", "fuel"],
    "Military Base": ["military", "barracks", "motor_pool"],
    "Riverside": ["marina", "convenience", "diner"],
    "Lakeside": ["airfield", "motel", "lumber"],
}


def _node(name, kind, axis, pos, tag, sites, **extra):
    node = {"name": name, "kind": kind, "axis": axis, "pos": pos, "tag": tag, "sites": sites}
    node.update(extra)
    node.setdefault("label", name.upper())
    return node


def _stop(name, axis, pos, tag, **extra):
    """A stop whose sites come from _STOP_SITES."""
    return _node(name, "city", axis, pos, tag, list(_STOP_SITES[name]), **extra)


def _core(pos):
    """The six stops every layout shares (ids 0-5); only their screen positions differ."""
    return [
        _node("Starting Highway", "start", 0, pos[0], "S", ["start"], label="START / EAST"),
        _stop("City 1", 90, pos[1], "1"),
        _stop("City 2", 200, pos[2], "2"),
        _stop("City 3", 310, pos[3], "3"),
        _stop("City 4", 430, pos[4], "4"),
        _node("Pacific Coast", "coast", 560, pos[5], "C", []),
    ]


def _extras(base, riverside, lakeside):
    """Ids 11-13: the Military Base, Riverside and Lakeside, each given as (axis of its parent stop, screen position)."""
    return [
        _stop("Military Base", base[0], base[1], "M", military_base=True),
        _stop("Riverside", riverside[0], riverside[1], "R"),
        _stop("Lakeside", lakeside[0], lakeside[1], "L"),
    ]


_MAIN = [(0, 1, 100, "main"), (1, 2, 120, "main"), (2, 3, 140, "main"), (3, 4, 150, "main"), (4, 5, 140, "main")]

LAYOUTS = [
    {   # 1: the original map: dead-end side cities and a Mountain Pass that bypasses City 3
        "name": "Classic",
        "nodes": _core([(925, 300), (790, 350), (640, 300), (480, 350), (310, 300), (110, 350)]) + [
            _stop("City 5", 90, (840, 215), "5"),
            _stop("City 6", 200, (700, 195), "6"),
            _stop("City 7", 310, (430, 470), "7", ambush=0.35),
            _stop("City 8", 430, (250, 430), "8"),
            _node("Mountain Pass", "pass", 320, (470, 195), "P", ["pass"], ambush=0.40),
        ] + _extras((430, (280, 190)), (90, (800, 470)), (200, (620, 420))),
        "edges": _MAIN + [(1, 6, 40, "spur"), (2, 7, 40, "spur"), (3, 8, 40, "spur"), (4, 9, 40, "spur"),
                          (4, 11, 40, "spur"), (1, 12, 40, "spur"), (2, 13, 40, "spur"),
                          (2, 10, 125, "alt"), (10, 4, 110, "alt")],
    },
    {   # 2: the pass is a risky shortcut that skips City 2 (225 km instead of 260)
        "name": "Northern Bypass",
        "nodes": _core([(925, 320), (795, 380), (650, 360), (485, 370), (310, 310), (105, 380)]) + [
            _stop("City 5", 90, (860, 260), "5"),
            _stop("City 6", 200, (640, 470), "6"),
            _stop("City 7", 310, (440, 480), "7", ambush=0.35),
            _stop("City 8", 430, (320, 200), "8"),
            _node("Mountain Pass", "pass", 210, (600, 180), "P", ["pass"], ambush=0.40),
        ] + _extras((430, (290, 430)), (90, (800, 500)), (310, (400, 260))),
        "edges": _MAIN + [(1, 6, 40, "spur"), (2, 7, 40, "spur"), (3, 8, 40, "spur"), (4, 9, 40, "spur"),
                          (4, 11, 40, "spur"), (1, 12, 40, "spur"), (3, 13, 40, "spur"),
                          (1, 10, 125, "alt"), (10, 3, 100, "alt")],
    },
    {   # 3: City 7 sits on a safe southern road that skips City 3; the pass is a quicker, riskier northern road over it
        "name": "Southern Detour",
        "nodes": _core([(910, 250), (770, 310), (610, 260), (450, 300), (280, 270), (105, 340)]) + [
            _stop("City 5", 90, (770, 440), "5"),
            _stop("City 6", 200, (660, 160), "6"),
            _stop("City 7", 320, (500, 480), "7", ambush=0.30),
            _stop("City 8", 430, (260, 170), "8"),
            _node("Mountain Pass", "pass", 310, (450, 170), "P", ["pass"], ambush=0.40),
        ] + _extras((90, (790, 190)), (430, (240, 400)), (90, (890, 390))),
        "edges": _MAIN + [(1, 6, 40, "spur"), (2, 7, 40, "spur"), (4, 9, 40, "spur"),
                          (1, 11, 40, "spur"), (4, 12, 40, "spur"), (1, 13, 40, "spur"),
                          (2, 8, 130, "alt"), (8, 4, 130, "alt"),
                          (2, 10, 115, "alt"), (10, 4, 125, "alt")],   # pass 240 km, via City 7 260, main 290
    },
    {   # 4: two parallel roads between City 1 and City 4; the northern one runs through the pass: slightly shorter, more dangerous
        "name": "Twin Roads",
        "nodes": _core([(920, 330), (780, 330), (620, 400), (450, 430), (270, 330), (105, 330)]) + [
            _stop("City 5", 170, (680, 220), "5", ambush=0.25),
            _stop("City 6", 300, (480, 215), "6", ambush=0.30),
            _stop("City 7", 200, (650, 490), "7"),
            _stop("City 8", 310, (350, 470), "8"),
            _node("Mountain Pass", "pass", 370, (330, 215), "P", ["pass"], ambush=0.40),
        ] + _extras((90, (800, 460)), (430, (210, 200)), (310, (490, 520))),
        "edges": _MAIN + [(2, 8, 40, "spur"), (3, 9, 40, "spur"),
                          (1, 11, 40, "spur"), (4, 12, 40, "spur"), (3, 13, 40, "spur"),
                          (1, 6, 90, "alt"), (6, 7, 140, "alt"), (7, 10, 100, "alt"), (10, 4, 65, "alt")],
    },
    {   # 5: long roads, side towns off every city and two optional loops through them
        "name": "Frontier",
        "nodes": _core([(910, 250), (770, 310), (620, 260), (460, 330), (290, 270), (105, 330)]) + [
            _stop("City 5", 90, (760, 180), "5"),
            _stop("City 6", 200, (630, 150), "6"),
            _stop("City 7", 310, (440, 440), "7", ambush=0.35),
            _stop("City 8", 430, (290, 420), "8"),
            _node("Mountain Pass", "pass", 310, (450, 190), "P", ["pass"], ambush=0.40),
        ] + _extras((90, (800, 430)), (200, (610, 380)), (430, (200, 180))),
        "edges": [(0, 1, 110, "main"), (1, 2, 140, "main"), (2, 3, 160, "main"), (3, 4, 170, "main"),
                  (4, 5, 150, "main"),
                  (1, 6, 40, "spur"), (2, 7, 40, "spur"), (3, 8, 40, "spur"), (4, 9, 40, "spur"),
                  (1, 11, 40, "spur"), (2, 12, 40, "spur"), (4, 13, 40, "spur"),
                  (6, 7, 130, "alt"), (8, 9, 140, "alt"),
                  (2, 10, 125, "alt"), (10, 4, 135, "alt")],   # pass 260 km instead of 330 over City 3
    },
]

EXPECTED_STOPS = ["Starting Highway", "City 1", "City 2", "City 3", "City 4", "Pacific Coast",
                  "City 5", "City 6", "City 7", "City 8", "Mountain Pass", "Military Base", "Riverside", "Lakeside"]

# Drawing rules for the roads (map pixels in the 1000 x 680 map space; a main road is drawn 22 wide, a stop's circle about
# 14 in radius): roads closer than ROAD_GAP are touching, a stop closer than NODE_CLEARANCE to a road that is not its own
# sits on it, and two roads leaving the same stop closer together than MIN_ROAD_ANGLE degrees run into each other.
ROAD_GAP = 26
NODE_CLEARANCE = 34
MIN_ROAD_ANGLE = 28
MIN_STOP_DISTANCE = 70
MAP_BOUNDS = (60, 120, 980, 560)   # left, top, right, bottom of the area stops may be drawn in


def _validate_sites():
    """Fail loudly at import if a site's scavenging data is malformed (a typo in a resource name or a swapped range)."""
    for key, site in SITES.items():
        for resource, (low, high) in site["finds"].items():
            if resource not in ("fuel", "food", "water", "scrap") or not 0 <= low <= high:
                raise ValueError(f"site {key}: bad find {resource!r}: ({low}, {high})")
        if "rare_fuel" in site:
            chance, low, high = site["rare_fuel"]
            if not 0 < chance <= 1 or not 1 <= low <= high:
                raise ValueError(f"site {key}: bad rare_fuel {site['rare_fuel']!r}")
    for key in SURVIVOR_FINDS:
        if key not in SITES:
            raise ValueError(f"SURVIVOR_FINDS has unknown site key {key!r}")
    for key in MILITARY_SITE_KEYS:
        if key not in SITES:
            raise ValueError(f"MILITARY_SITE_KEYS has unknown site key {key!r}")
    from vehicle_data import MILITARY_VEHICLES, VEHICLE_SPECS   # data only (no pygame)
    for key, (chance, types) in SITE_VEHICLES.items():
        if key not in SITES:
            raise ValueError(f"SITE_VEHICLES has unknown site key {key!r}")
        if not 0 < chance <= 1 or not types or len(set(types)) != len(types):
            raise ValueError(f"site {key}: bad SITE_VEHICLES entry ({chance}, {types!r})")
        for vehicle_type in types:
            if vehicle_type not in VEHICLE_SPECS:
                raise ValueError(f"site {key}: unknown vehicle {vehicle_type!r} in SITE_VEHICLES")
            if vehicle_type in MILITARY_VEHICLES and key not in MILITARY_SITE_KEYS:
                raise ValueError(f"site {key}: military vehicle {vehicle_type!r} only belongs at the Military Base")
    for key in ("start", "pass"):
        if key in SITE_VEHICLES:
            raise ValueError(f"site {key}: no vehicle can be scavenged on the road")


def _road_km(edges, source, target, skip=None):
    """Shortest road km between two stops over a layout's edges, never entering stop `skip` (None if unreachable)."""
    adjacent = {}
    for a, b, km, _kind in edges:
        adjacent.setdefault(a, []).append((b, km))
        adjacent.setdefault(b, []).append((a, km))
    heap, seen = [(0, source)], set()
    while heap:
        dist, node = heapq.heappop(heap)
        if node == target:
            return dist
        if node in seen:
            continue
        seen.add(node)
        for nxt, km in adjacent.get(node, []):
            if nxt != skip and nxt not in seen:
                heapq.heappush(heap, (dist + km, nxt))
    return None


def _point_segment_distance(p, a, b):
    """Distance from point p to the segment a-b."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length_sq = dx * dx + dy * dy
    t = 0 if length_sq == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length_sq))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _segments_cross(a, b, c, d):
    """True when the segments a-b and c-d properly intersect."""
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0


def _segment_distance(a, b, c, d):
    """Smallest distance between the segments a-b and c-d (0 when they cross)."""
    if _segments_cross(a, b, c, d):
        return 0.0
    return min(_point_segment_distance(a, c, d), _point_segment_distance(b, c, d),
               _point_segment_distance(c, a, b), _point_segment_distance(d, a, b))


def _validate_geometry(layout):
    """Fail loudly at import if two roads cross, touch or run into each other, a road passes over a stop it does not
    serve, or a stop is drawn outside the map or too close to another (so the map can never be drawn with a tangle)."""
    nodes, edges, name = layout["nodes"], layout["edges"], layout["name"]
    left, top, right, bottom = MAP_BOUNDS
    for node in nodes:
        x, y = node["pos"]
        if not (left <= x <= right and top <= y <= bottom):
            raise ValueError(f"layout {name}: {node['name']} is drawn outside the map area {MAP_BOUNDS}")
    for i, first in enumerate(nodes):
        for second in nodes[i + 1:]:
            if abs(first["pos"][0] - second["pos"][0]) + abs(first["pos"][1] - second["pos"][1]) < MIN_STOP_DISTANCE:
                raise ValueError(f"layout {name}: {first['name']} and {second['name']} are drawn too close")
    seen = set()
    for a, b, _km, _kind in edges:
        if (min(a, b), max(a, b)) in seen:
            raise ValueError(f"layout {name}: road {a}-{b} is listed twice")
        seen.add((min(a, b), max(a, b)))
    for n, (a, b, _km, _kind) in enumerate(edges):
        pa, pb = nodes[a]["pos"], nodes[b]["pos"]
        for i, node in enumerate(nodes):
            if i not in (a, b) and _point_segment_distance(node["pos"], pa, pb) < NODE_CLEARANCE:
                raise ValueError(f"layout {name}: road {nodes[a]['name']} - {nodes[b]['name']} runs over {node['name']}")
        for c, d, _km2, _kind2 in edges[n + 1:]:
            pc, pd = nodes[c]["pos"], nodes[d]["pos"]
            shared = {a, b} & {c, d}
            if shared:
                hub = shared.pop()
                other1, other2 = (b if hub == a else a), (d if hub == c else c)
                hx, hy = nodes[hub]["pos"]
                v1 = (nodes[other1]["pos"][0] - hx, nodes[other1]["pos"][1] - hy)
                v2 = (nodes[other2]["pos"][0] - hx, nodes[other2]["pos"][1] - hy)
                cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
                if math.degrees(math.acos(max(-1.0, min(1.0, cos)))) < MIN_ROAD_ANGLE:
                    raise ValueError(f"layout {name}: the roads from {nodes[hub]['name']} to {nodes[other1]['name']} and "
                                     f"{nodes[other2]['name']} leave at almost the same angle")
            elif _segment_distance(pa, pb, pc, pd) < ROAD_GAP:
                raise ValueError(f"layout {name}: roads {nodes[a]['name']} - {nodes[b]['name']} and "
                                 f"{nodes[c]['name']} - {nodes[d]['name']} cross or touch")


def _validate(layout):
    """Fail loudly at import if a layout breaks the rules above (so a typo can't ship a broken map)."""
    nodes, edges, name = layout["nodes"], layout["edges"], layout["name"]
    if nodes[START]["kind"] != "start" or nodes[PACIFIC]["kind"] != "coast":
        raise ValueError(f"layout {name}: ids 0 and 5 must be the start and the coast")
    if [n["name"] for n in nodes] != EXPECTED_STOPS:
        raise ValueError(f"layout {name}: every layout needs the same {len(EXPECTED_STOPS)} stops in the same id order")
    for node in nodes:
        for site in node["sites"]:
            if site not in SITES:
                raise ValueError(f"layout {name}: {node['name']} has unknown site key {site!r}")
        if node["kind"] != "coast" and not FUEL_SITES & set(node["sites"]):
            raise ValueError(f"layout {name}: {node['name']} has no site that can give fuel (the convoy could get stuck)")
    reach = {START}
    for _ in nodes:
        for a, b, _km, _kind in edges:
            if a in reach or b in reach:
                reach |= {a, b}
    if reach != set(range(len(nodes))):
        raise ValueError(f"layout {name}: every stop must be reachable from the start")
    for a, b, km, _kind in edges:
        if km < abs(nodes[a]["axis"] - nodes[b]["axis"]):
            raise ValueError(f"layout {name}: road {a}-{b} is shorter than the straight line")
    if [b for a, b, _k, _t in edges if a == START] != [1] or any(b == START for a, b, _k, _t in edges):
        raise ValueError(f"layout {name}: the start must connect to City 1 only")
    for pass_id, node in enumerate(nodes):
        if node["kind"] != "pass":
            continue
        neighbours = {b if a == pass_id else a for a, b, _km, _kind in edges if pass_id in (a, b)}
        if len(neighbours) < 2:
            raise ValueError(f"layout {name}: the Mountain Pass must not be a dead end (it needs two roads to different stops)")
        with_pass = (_road_km(edges, START, pass_id) or 0) + (_road_km(edges, pass_id, PACIFIC) or 0)
        without = _road_km(edges, START, PACIFIC, skip=pass_id)
        if without is None:
            raise ValueError(f"layout {name}: the Mountain Pass must be an alternative route, not the only road")
        if with_pass >= without:
            raise ValueError(f"layout {name}: the route through the Mountain Pass ({with_pass} km) must be shorter than "
                             f"the quickest route without it ({without} km)")
    # The Military Base: exactly one, a dead end (one road), with every military site and no other stop has one.
    bases = [i for i, node in enumerate(nodes) if node.get("military_base")]
    if bases != [MILITARY_BASE]:
        raise ValueError(f"layout {name}: the Military Base must be stop {MILITARY_BASE} and the only military_base stop")
    roads = [(a, b) for a, b, _km, _kind in edges if MILITARY_BASE in (a, b)]
    if len(roads) != 1:
        raise ValueError(f"layout {name}: the Military Base must be a dead end (it has {len(roads)} roads)")
    if set(nodes[MILITARY_BASE]["sites"]) != set(MILITARY_SITE_KEYS):
        raise ValueError(f"layout {name}: the Military Base must have exactly the military sites")
    for i, node in enumerate(nodes):
        if i != MILITARY_BASE and MILITARY_SITE_KEYS & set(node["sites"]):
            raise ValueError(f"layout {name}: {node['name']} has a military site, only the Military Base may")
    _validate_geometry(layout)


_validate_sites()
for _layout in LAYOUTS:
    _validate(_layout)

NODES = []
ROAD_EDGES = []   # (stop, stop, road km, type)
ADJACENT = {}
_PATH_CACHE = {}
CURRENT_LAYOUT = 0
LAYOUT_VERSION = 0   # goes up on every load_layout, for anything that caches drawn geometry


def load_layout(index):
    """Make LAYOUTS[index] the active map. The lists / dict are changed in place, so every module that imported
    NODES, ROAD_EDGES or ADJACENT sees the new map."""
    global CURRENT_LAYOUT, LAYOUT_VERSION
    layout = LAYOUTS[index]
    NODES[:] = [dict(node, sites=list(node["sites"])) for node in layout["nodes"]]
    ROAD_EDGES[:] = layout["edges"]
    ADJACENT.clear()
    ADJACENT.update({i: [] for i in range(len(NODES))})
    for a, b, km, _kind in ROAD_EDGES:
        ADJACENT[a].append((b, km))
        ADJACENT[b].append((a, km))
    _PATH_CACHE.clear()
    CURRENT_LAYOUT = index
    LAYOUT_VERSION += 1


def choose_layout(number=None):
    """Start of a run: use layout `number` (1-based, for testing) or a random one. Returns the layout's name."""
    index = random.randrange(len(LAYOUTS)) if number is None else (number - 1) % len(LAYOUTS)
    load_layout(index)
    return layout_name()


def layout_name():
    return LAYOUTS[CURRENT_LAYOUT]["name"]


load_layout(0)


def is_military_base(stop):
    """True when stop id `stop` is the Military Base (the only place military vehicles can be recovered)."""
    return 0 <= stop < len(NODES) and bool(NODES[stop].get("military_base"))


def scenery_for(stop):
    """The look of the convoy scene at stop id `stop`: "highway" (the original background) or "desert". Every stop whose
    axis position lies beyond the Mountain Pass (further west, towards the coast) is desert, so the scenery changes once
    the convoy is past the pass, whichever of the five layouts is loaded (the pass sits at a different axis km in each).
    The pass itself and all stops before it keep the highway."""
    pass_axis = next((node["axis"] for node in NODES if node["kind"] == "pass"), None)
    if pass_axis is None or not 0 <= stop < len(NODES):
        return "highway"
    return "desert" if NODES[stop]["axis"] > pass_axis else "highway"


def shortest_path(a, b):
    """Shortest road route between two stops: (tuple of stop ids including both ends, total road km).

    The route is a tuple because the result is cached and shared: a caller that needs a list makes its own copy."""
    key = (a, b)
    if key in _PATH_CACHE:
        return _PATH_CACHE[key]
    heap = [(0, [a])]
    visited = set()
    result = ((a,), 0)
    while heap:
        dist, path = heapq.heappop(heap)
        node = path[-1]
        if node in visited:
            continue
        visited.add(node)
        if node == b:
            result = (tuple(path), dist)
            break
        for nxt, km in ADJACENT[node]:
            if nxt not in visited:
                heapq.heappush(heap, (dist + km, path + [nxt]))
    _PATH_CACHE[key] = result
    return result
