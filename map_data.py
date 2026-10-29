"""Map data and pathfinding for THE LAST CONVOY.

Pure data and logic: this module must not import pygame or any drawing code. map_system.py draws it.
"""
import heapq

__all__ = ["SURVIVOR_FINDS", "SITES", "NODES", "START", "PACIFIC", "ROAD_EDGES", "ADJACENT", "shortest_path"]

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
}

# ---------------------------------------------------------------------------
# Sites: the places inside a stop that can be scavenged, one at a time. The same site can exist in several
# stops. Keyed by site key (the keys also select the scavenging rules in game.py).
# "name" is the full name (also used by RECOVERY_SITES), "short" fits on a button.
# ---------------------------------------------------------------------------
SITES = {
    "start": {"name": "Open Highway", "short": "Open Highway",
              "detail": "Starting highway: no supplies, but stranded survivors may be found."},
    "fuel": {"name": "Gas Station", "short": "Gas Station",
             "detail": "Potential supplies: fuel and basic provisions. Survivors sometimes found."},
    "food": {"name": "Supermarket", "short": "Supermarket",
             "detail": "Potential supplies: canned food and bottled water. Survivors may be found."},
    "mixed": {"name": "Truck Stop", "short": "Truck Stop",
              "detail": "Potential supplies: mixed supplies. Survivors are most likely here."},
    "repair": {"name": "Repair Depot", "short": "Repair Depot",
               "detail": "Potential supplies: scrap and spare parts. Survivors are rare."},
    "farm": {"name": "Farm", "short": "Farm",
             "detail": "Lots of food and water. Survivors occasionally."},
    "hospital": {"name": "Hospital", "short": "Hospital",
                 "detail": "Some water. Survivors are likely here."},
    "military": {"name": "Military Installation", "short": "Military Inst.",
                 "detail": "Scrap and fuel. Vehicles can be recovered. Dangerous!"},
    "town": {"name": "Small Town", "short": "Small Town",
             "detail": "Mixed supplies. Survivors are likely here."},
    "diner": {"name": "Diner", "short": "Diner",
              "detail": "Meals and drinks left in the kitchen. Survivors sometimes found."},
    "hardware": {"name": "Hardware Store", "short": "Hardware",
                 "detail": "Plenty of scrap. Survivors are unlikely."},
    "pharmacy": {"name": "Pharmacy", "short": "Pharmacy",
                 "detail": "A little water and food. Survivors may be found."},
    "warehouse": {"name": "Warehouse", "short": "Warehouse",
                  "detail": "Crates of food, some water and scrap. Survivors are rare."},
    "water": {"name": "Water Tower", "short": "Water Tower",
              "detail": "A lot of clean water. Survivors are rare."},
    "garage": {"name": "Auto Garage", "short": "Auto Garage",
               "detail": "Fuel and scrap. Survivors sometimes found."},
    "shelter": {"name": "Survivor Shelter", "short": "Shelter",
                "detail": "Few supplies, but survivors are very likely here."},
    "police": {"name": "Police Station", "short": "Police Station",
               "detail": "Scrap and some fuel. Survivors may be found."},
    "pass": {"name": "Mountain Pass", "short": "Mountain Pass",
             "detail": "Alternative route: shorter, but little to find and ambushes are likely."},
}

# ---------------------------------------------------------------------------
# The map. Each node has a position "axis" in km on the straight Start-to-Pacific line and a position "pos" on
# the map screen. Side stops share their parent's axis position (a detour costs time, not distance west).
# A node's index in this list is its id; "sites" lists the site keys that can
# be scavenged there (the convoy scavenges one chosen site at a time, as often as it likes).
# ---------------------------------------------------------------------------
NODES = [
    {"name": "Starting Highway", "kind": "start", "axis": 0, "pos": (920, 265), "tag": "S", "label": "START / EAST",
     "sites": ["start"]},
    {"name": "City 1", "kind": "city", "axis": 90, "pos": (770, 350), "tag": "1", "sites": ["fuel", "farm", "diner"]},
    {"name": "City 2", "kind": "city", "axis": 200, "pos": (610, 275), "tag": "2",
     "sites": ["food", "hospital", "pharmacy"]},
    {"name": "City 3", "kind": "city", "axis": 310, "pos": (445, 375), "tag": "3",
     "sites": ["mixed", "military", "warehouse"]},
    {"name": "City 4", "kind": "city", "axis": 430, "pos": (275, 300), "tag": "4",
     "sites": ["repair", "town", "hardware"]},
    {"name": "Pacific Coast", "kind": "coast", "axis": 560, "pos": (105, 390), "tag": "C", "sites": []},
    # Dead-end side cities, one off each of City 1-4 (City 5 off City 1, ... City 8 off City 4).
    {"name": "City 5", "kind": "city", "axis": 90, "pos": (860, 205), "tag": "5", "sites": ["farm", "water", "shelter"]},
    {"name": "City 6", "kind": "city", "axis": 200, "pos": (680, 200), "tag": "6",
     "sites": ["hospital", "police", "diner"]},
    {"name": "City 7", "kind": "city", "axis": 310, "pos": (390, 470), "tag": "7", "ambush": 0.35,
     "sites": ["military", "garage", "warehouse"]},
    {"name": "City 8", "kind": "city", "axis": 430, "pos": (190, 215), "tag": "8",
     "sites": ["town", "shelter", "fuel"]},
    {"name": "Mountain Pass", "kind": "pass", "axis": 320, "pos": (440, 215), "tag": "P", "ambush": 0.40,
     "sites": ["pass"]},
]
for _node in NODES:
    _node.setdefault("label", _node["name"].upper())
START, PACIFIC = 0, 5

# Roads: (stop, stop, road km, type). Road km is never less than the straight-line distance between the stops.
ROAD_EDGES = [
    (0, 1, 100, "main"), (1, 2, 120, "main"), (2, 3, 140, "main"), (3, 4, 150, "main"), (4, 5, 140, "main"),
    (1, 6, 40, "spur"), (2, 7, 40, "spur"), (3, 8, 40, "spur"), (4, 9, 40, "spur"),
    (2, 10, 125, "alt"), (10, 4, 110, "alt"),   # City 2 - Mountain Pass - City 4 (bypasses City 3)
]
ADJACENT = {i: [] for i in range(len(NODES))}
for _a, _b, _km, _kind in ROAD_EDGES:
    ADJACENT[_a].append((_b, _km))
    ADJACENT[_b].append((_a, _km))

_PATH_CACHE = {}

def shortest_path(a, b):
    """Shortest road route between two stops: (list of stop ids including both ends, total road km)."""
    key = (a, b)
    if key in _PATH_CACHE:
        return _PATH_CACHE[key]
    heap = [(0, [a])]
    visited = set()
    result = ([a], 0)
    while heap:
        dist, path = heapq.heappop(heap)
        node = path[-1]
        if node in visited:
            continue
        visited.add(node)
        if node == b:
            result = (path, dist)
            break
        for nxt, km in ADJACENT[node]:
            if nxt not in visited:
                heapq.heappush(heap, (dist + km, path + [nxt]))
    _PATH_CACHE[key] = result
    return result
