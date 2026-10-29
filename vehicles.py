"""Vehicle configuration for THE LAST CONVOY.

This module contains data only and deliberately does not import main.py.
"""

# Scrap needed to recover each vehicle (specialist and heavy vehicles cost more).
RECOVERY_COSTS = {
    "Semi-Truck": 5,
    "Fuel Tanker": 6,
    "Ambulance": 4,
    "Military Humvee": 5,
    "Tow/Recovery Truck": 4,
}

# Prototype baseline values for the eight vehicle types from the design document.
# These are initial balancing values and can be tuned during playtesting.
VEHICLE_SPECS = {
    "Pickup Truck": {"speed": 70, "health": 80, "passengers": 2, "cargo": 40, "defense": 5, "fuel_capacity": 50, "fuel_consumption": 8},
    "Passenger Van": {"speed": 65, "health": 90, "passengers": 8, "cargo": 35, "defense": 3, "fuel_capacity": 65, "fuel_consumption": 10},
    "School Bus": {"speed": 45, "health": 130, "passengers": 30, "cargo": 30, "defense": 4, "fuel_capacity": 90, "fuel_consumption": 18},
    "Semi-Truck": {"speed": 40, "health": 150, "passengers": 3, "cargo": 150, "defense": 6, "fuel_capacity": 120, "fuel_consumption": 22},
    "Fuel Tanker": {"speed": 35, "health": 140, "passengers": 2, "cargo": 30, "defense": 5, "fuel_capacity": 250, "fuel_consumption": 24},
    "Ambulance": {"speed": 60, "health": 85, "passengers": 4, "cargo": 30, "defense": 3, "fuel_capacity": 60, "fuel_consumption": 11},
    "Military Humvee": {"speed": 75, "health": 100, "passengers": 5, "cargo": 20, "defense": 15, "fuel_capacity": 55, "fuel_consumption": 12},
    "Tow/Recovery Truck": {"speed": 50, "health": 120, "passengers": 3, "cargo": 50, "defense": 7, "fuel_capacity": 70, "fuel_consumption": 16},
}

# One-line descriptions shown on the vehicle preview card (they only describe the stats that exist).
VEHICLE_ROLES = {
    "Pickup Truck": "Versatile early-game hauler with decent cargo.",
    "Passenger Van": "Extra seats for rescued survivors.",
    "School Bus": "Huge passenger capacity; slow and thirsty for fuel.",
    "Semi-Truck": "Very high cargo capacity; slow with heavy fuel use.",
    "Fuel Tanker": "Huge fuel storage; slow, with little cargo.",
    "Ambulance": "Medical vehicle with modest cargo and seats.",
    "Military Humvee": "Highest defense and fast, but small.",
    "Tow/Recovery Truck": "Sturdy utility truck with decent cargo.",
}

# Short name shown under each vehicle on the convoy screen. The sprites themselves are PNG files
# (see vehicle_rendering.py); each image carries its own size.
VEHICLE_LOOKS = {
    "Pickup Truck": {"label": "PICKUP"},
    "Passenger Van": {"label": "VAN"},
    "School Bus": {"label": "SCHOOL BUS"},
    "Semi-Truck": {"label": "SEMI-TRUCK"},
    "Fuel Tanker": {"label": "FUEL TANKER"},
    "Ambulance": {"label": "AMBULANCE"},
    "Military Humvee": {"label": "HUMVEE"},
    "Tow/Recovery Truck": {"label": "TOW TRUCK"},
}

# Loaded sprites, filled in by vehicle_rendering.get_vehicle_sprite().
SPRITE_CACHE = {}

