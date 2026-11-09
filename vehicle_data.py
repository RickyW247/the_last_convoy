"""Vehicle configuration for THE LAST CONVOY.

This module contains data only (plus one tiny lookup) and deliberately does not import main.py or pygame.
"""
from config import (MEDICAL_RECOVER_RATE, INJURY_RECOVER_RATE, RECOVERY_SUPPORT_RECOVERY_DISCOUNT,
                    RECOVERY_SUPPORT_REPAIR_DISCOUNT, REINFORCED_PROTECTION_BONUS)

# Scrap needed to recover each vehicle (specialist and heavy vehicles cost more).
RECOVERY_COSTS = {
    "Semi-Truck": 5,
    "Fuel Tanker": 6,
    "Ambulance": 4,
    "Military Humvee": 5,
    "Tow/Recovery Truck": 4,
    "Box Truck": 4,
    "City Bus": 4,
    "Motorhome": 4,
    "Fire Engine": 6,
    # New roster (design doc sections 5 and 20): heavy, military and "expensive to maintain" vehicles cost more.
    "Coach Bus": 4,
    "Moving Truck": 5,
    "Utility Service Truck": 4,
    "Flatbed Truck": 5,
    "Refrigerated Truck": 5,
    "Dump Truck": 6,
    "Car Carrier Truck": 6,
    "Prison Transport Bus": 5,
    "Road Maintenance Truck": 4,
    "Garbage Truck": 5,
    "Military Cargo Truck": 5,
    "Armored Personnel Carrier": 6,
    "Mobile Command Vehicle": 6,
    "Limousine": 5,
    "TV Broadcasting Van": 4,
    "Tank": 8,
    "Excavator": 6,
    "Bulldozer": 7,
    "Crane Truck": 6,
    "Wrecking Ball Truck": 8,
    "Monster Truck": 5,
    "Armored Cash Truck": 5,
    "Tourist Bus": 5,
    "Mobile Laboratory": 5,
    "Prototype Military Vehicle": 7,
    "Presidential Limo": 6,
    "Formula 1 Car": 7,
}

# Prototype baseline values for the eight vehicle types from the design document.
# These are initial balancing values and can be tuned during playtesting.
VEHICLE_SPECS = {
    "Pickup Truck": {"speed": 70, "health": 80, "passengers": 2, "cargo": 40, "defense": 5, "fuel_capacity": 10, "fuel_consumption": 8},
    "Passenger Van": {"speed": 65, "health": 90, "passengers": 8, "cargo": 35, "defense": 3, "fuel_capacity": 12, "fuel_consumption": 10},
    "School Bus": {"speed": 45, "health": 130, "passengers": 30, "cargo": 30, "defense": 4, "fuel_capacity": 22, "fuel_consumption": 18},
    "Semi-Truck": {"speed": 40, "health": 150, "passengers": 3, "cargo": 50, "defense": 6, "fuel_capacity": 28, "fuel_consumption": 22},
    "Fuel Tanker": {"speed": 35, "health": 140, "passengers": 2, "cargo": 30, "defense": 5, "fuel_capacity": 60, "fuel_consumption": 24},
    "Ambulance": {"speed": 60, "health": 85, "passengers": 4, "cargo": 30, "defense": 3, "fuel_capacity": 14, "fuel_consumption": 11},
    "Military Humvee": {"speed": 75, "health": 100, "passengers": 5, "cargo": 20, "defense": 15, "fuel_capacity": 15, "fuel_consumption": 12},
    "Tow/Recovery Truck": {"speed": 50, "health": 120, "passengers": 3, "cargo": 50, "defense": 7, "fuel_capacity": 20, "fuel_consumption": 16},
    # Expanded roster (design doc section 5). Same untested baseline values, to be tuned during playtesting.
    "Sedan": {"speed": 75, "health": 70, "passengers": 4, "cargo": 15, "defense": 2, "fuel_capacity": 9, "fuel_consumption": 6},
    "Civilian SUV": {"speed": 68, "health": 80, "passengers": 6, "cargo": 25, "defense": 2, "fuel_capacity": 11, "fuel_consumption": 8},
    "Utility SUV": {"speed": 68, "health": 95, "passengers": 5, "cargo": 30, "defense": 5, "fuel_capacity": 13, "fuel_consumption": 10},
    "Postal Van": {"speed": 62, "health": 85, "passengers": 2, "cargo": 40, "defense": 3, "fuel_capacity": 12, "fuel_consumption": 9},
    "Box Truck": {"speed": 48, "health": 110, "passengers": 2, "cargo": 46, "defense": 4, "fuel_capacity": 20, "fuel_consumption": 15},
    "City Bus": {"speed": 50, "health": 120, "passengers": 22, "cargo": 20, "defense": 3, "fuel_capacity": 20, "fuel_consumption": 15},
    "Motorhome": {"speed": 50, "health": 105, "passengers": 10, "cargo": 25, "defense": 3, "fuel_capacity": 22, "fuel_consumption": 17},
    "Fire Engine": {"speed": 38, "health": 160, "passengers": 4, "cargo": 25, "defense": 8, "fuel_capacity": 26, "fuel_consumption": 22},
    # Added from design doc sections 5 and 20. Untested baseline values, to be tuned during playtesting.
    # Civilian and passenger vehicles (design doc 5.2)
    "Hatchback": {"speed": 72, "health": 65, "passengers": 3, "cargo": 12, "defense": 2, "fuel_capacity": 8, "fuel_consumption": 5},
    "Taxi": {"speed": 76, "health": 72, "passengers": 4, "cargo": 10, "defense": 2, "fuel_capacity": 9, "fuel_consumption": 7},
    "Station Wagon": {"speed": 72, "health": 75, "passengers": 5, "cargo": 28, "defense": 2, "fuel_capacity": 10, "fuel_consumption": 7},
    "Minivan": {"speed": 66, "health": 80, "passengers": 7, "cargo": 22, "defense": 2, "fuel_capacity": 11, "fuel_consumption": 8},
    "Coach Bus": {"speed": 55, "health": 125, "passengers": 28, "cargo": 15, "defense": 3, "fuel_capacity": 28, "fuel_consumption": 22},
    "Sports Car": {"speed": 95, "health": 55, "passengers": 2, "cargo": 6, "defense": 1, "fuel_capacity": 9, "fuel_consumption": 9},
    # Motorcycles and lightweight vehicles (5.3)
    "Motorcycle": {"speed": 90, "health": 35, "passengers": 1, "cargo": 4, "defense": 1, "fuel_capacity": 4, "fuel_consumption": 2},
    "Dirt Bike": {"speed": 80, "health": 30, "passengers": 1, "cargo": 3, "defense": 1, "fuel_capacity": 3, "fuel_consumption": 2},
    "Scooter": {"speed": 45, "health": 25, "passengers": 1, "cargo": 3, "defense": 0, "fuel_capacity": 2, "fuel_consumption": 1},
    # Cargo and commercial vehicles (5.4)
    "Delivery Van": {"speed": 64, "health": 90, "passengers": 2, "cargo": 43, "defense": 3, "fuel_capacity": 14, "fuel_consumption": 10},
    "Moving Truck": {"speed": 46, "health": 115, "passengers": 3, "cargo": 48, "defense": 4, "fuel_capacity": 22, "fuel_consumption": 17},
    "Utility Service Truck": {"speed": 55, "health": 110, "passengers": 3, "cargo": 30, "defense": 5, "fuel_capacity": 18, "fuel_consumption": 13},
    "Flatbed Truck": {"speed": 52, "health": 110, "passengers": 2, "cargo": 44, "defense": 4, "fuel_capacity": 20, "fuel_consumption": 15},
    "Refrigerated Truck": {"speed": 45, "health": 115, "passengers": 2, "cargo": 40, "defense": 4, "fuel_capacity": 22, "fuel_consumption": 18},
    "Dump Truck": {"speed": 40, "health": 140, "passengers": 2, "cargo": 45, "defense": 6, "fuel_capacity": 24, "fuel_consumption": 20},
    "Landscaping Truck": {"speed": 58, "health": 95, "passengers": 3, "cargo": 28, "defense": 3, "fuel_capacity": 14, "fuel_consumption": 11},
    "Garbage Truck": {"speed": 42, "health": 135, "passengers": 3, "cargo": 38, "defense": 5, "fuel_capacity": 22, "fuel_consumption": 18},
    "Car Carrier Truck": {"speed": 42, "health": 130, "passengers": 2, "cargo": 35, "defense": 5, "fuel_capacity": 25, "fuel_consumption": 20},
    # Emergency-service vehicles (5.5)
    "Police SUV": {"speed": 76, "health": 95, "passengers": 3, "cargo": 12, "defense": 8, "fuel_capacity": 13, "fuel_consumption": 10},
    "Police Sedan": {"speed": 78, "health": 75, "passengers": 3, "cargo": 8, "defense": 5, "fuel_capacity": 10, "fuel_consumption": 8},
    "Prison Transport Bus": {"speed": 48, "health": 125, "passengers": 20, "cargo": 12, "defense": 7, "fuel_capacity": 20, "fuel_consumption": 15},
    "Road Maintenance Truck": {"speed": 52, "health": 115, "passengers": 2, "cargo": 28, "defense": 5, "fuel_capacity": 18, "fuel_consumption": 14},
    # Military vehicles (5.6)
    "Military Cargo Truck": {"speed": 45, "health": 140, "passengers": 6, "cargo": 48, "defense": 10, "fuel_capacity": 24, "fuel_consumption": 20},
    "Armored Personnel Carrier": {"speed": 50, "health": 180, "passengers": 10, "cargo": 12, "defense": 20, "fuel_capacity": 28, "fuel_consumption": 24},
    "Mobile Command Vehicle": {"speed": 48, "health": 130, "passengers": 6, "cargo": 18, "defense": 8, "fuel_capacity": 24, "fuel_consumption": 22},
    # Bonus vehicles (design doc 20.2.1); see BONUS_VEHICLES
    "Hearse": {"speed": 62, "health": 75, "passengers": 3, "cargo": 15, "defense": 2, "fuel_capacity": 12, "fuel_consumption": 10},
    "Limousine": {"speed": 60, "health": 75, "passengers": 9, "cargo": 15, "defense": 2, "fuel_capacity": 14, "fuel_consumption": 13},
    "Presidential Limo": {"speed": 58, "health": 170, "passengers": 6, "cargo": 12, "defense": 16, "fuel_capacity": 20, "fuel_consumption": 19},
    "Ice Cream Van": {"speed": 52, "health": 65, "passengers": 2, "cargo": 22, "defense": 1, "fuel_capacity": 12, "fuel_consumption": 9},
    "TV Broadcasting Van": {"speed": 55, "health": 90, "passengers": 4, "cargo": 20, "defense": 3, "fuel_capacity": 16, "fuel_consumption": 14},
    "Clown Car": {"speed": 30, "health": 30, "passengers": 14, "cargo": 4, "defense": 0, "fuel_capacity": 8, "fuel_consumption": 6},
    "Tank": {"speed": 28, "health": 250, "passengers": 3, "cargo": 8, "defense": 30, "fuel_capacity": 30, "fuel_consumption": 32},
    "Excavator": {"speed": 20, "health": 160, "passengers": 1, "cargo": 5, "defense": 6, "fuel_capacity": 22, "fuel_consumption": 22},
    "Bulldozer": {"speed": 22, "health": 180, "passengers": 1, "cargo": 5, "defense": 8, "fuel_capacity": 24, "fuel_consumption": 24},
    "Crane Truck": {"speed": 35, "health": 140, "passengers": 2, "cargo": 20, "defense": 5, "fuel_capacity": 24, "fuel_consumption": 20},
    "Wrecking Ball Truck": {"speed": 18, "health": 150, "passengers": 2, "cargo": 5, "defense": 4, "fuel_capacity": 22, "fuel_consumption": 24},
    # Additional potential bonus vehicles (20.2.2)
    "Monster Truck": {"speed": 55, "health": 130, "passengers": 2, "cargo": 10, "defense": 5, "fuel_capacity": 18, "fuel_consumption": 18},
    "Armored Cash Truck": {"speed": 55, "health": 140, "passengers": 3, "cargo": 10, "defense": 14, "fuel_capacity": 14, "fuel_consumption": 12},
    "Vintage Police Car": {"speed": 70, "health": 65, "passengers": 3, "cargo": 8, "defense": 3, "fuel_capacity": 10, "fuel_consumption": 9},
    "Tourist Bus": {"speed": 52, "health": 115, "passengers": 32, "cargo": 15, "defense": 3, "fuel_capacity": 28, "fuel_consumption": 24},
    "Mobile Laboratory": {"speed": 50, "health": 110, "passengers": 4, "cargo": 20, "defense": 4, "fuel_capacity": 18, "fuel_consumption": 15},
    "Food Truck": {"speed": 50, "health": 100, "passengers": 3, "cargo": 30, "defense": 3, "fuel_capacity": 16, "fuel_consumption": 13},
    "Prototype Military Vehicle": {"speed": 80, "health": 120, "passengers": 4, "cargo": 12, "defense": 18, "fuel_capacity": 22, "fuel_consumption": 26},
    # Speed-run reward (achievement "Chequered Flag"): the fastest vehicle in the game, and the most fragile.
    "Formula 1 Car": {"speed": 120, "health": 40, "passengers": 1, "cargo": 2, "defense": 0, "fuel_capacity": 6, "fuel_consumption": 14},
}

# Passive special abilities (design doc section 6): vehicle type -> ability key. The game reads the key
# ("medical_care": conditions.py; "reinforced_protection" and "recovery_support": see config.py for the numbers).
# Not every vehicle has one; ABILITY_INFO below says how each is shown on the vehicles screen.
VEHICLE_ABILITIES = {
    "Ambulance": "medical_care",
    "Military Humvee": "reinforced_protection",
    "Tow/Recovery Truck": "recovery_support",
}

# Display text of each ability key: its name, a "text" (one or two short sentences) and a "short" form for narrow cards.
ABILITY_INFO = {
    "medical_care": {
        "name": "Medical Care",
        "text": f"Injured survivors heal faster ({round(MEDICAL_RECOVER_RATE * 100)}%/day, not {round(INJURY_RECOVER_RATE * 100)}%).",
        "short": "Injured heal faster.",
    },
    "reinforced_protection": {
        "name": "Reinforced Protection",
        "text": f"+{REINFORCED_PROTECTION_BONUS} defense for the whole convoy.",
        "short": f"+{REINFORCED_PROTECTION_BONUS} convoy defense.",
    },
    "recovery_support": {
        "name": "Recovery Support",
        "text": (f"Repairs and recoveries cost {RECOVERY_SUPPORT_REPAIR_DISCOUNT} less scrap."
                 if RECOVERY_SUPPORT_REPAIR_DISCOUNT == RECOVERY_SUPPORT_RECOVERY_DISCOUNT else
                 f"Repairs cost {RECOVERY_SUPPORT_REPAIR_DISCOUNT} less scrap, recoveries {RECOVERY_SUPPORT_RECOVERY_DISCOUNT} less."),
        "short": f"-{RECOVERY_SUPPORT_REPAIR_DISCOUNT} scrap on repairs and recoveries.",
    },
}


def ability_info(vehicle_type):
    """The display info (name / text / short) of the vehicle type's special ability, or None when it has none."""
    return ABILITY_INFO.get(VEHICLE_ABILITIES.get(vehicle_type))


# One-line descriptions shown on the vehicle preview card (they only describe the stats that exist).
VEHICLE_ROLES = {
    "Pickup Truck": "Versatile early-game hauler with decent cargo.",
    "Passenger Van": "Extra seats for rescued survivors.",
    "School Bus": "Huge passenger capacity; slow and thirsty for fuel.",
    "Semi-Truck": "Very high cargo capacity; slow with heavy fuel use.",
    "Fuel Tanker": "Huge fuel storage; slow, with little cargo.",
    "Ambulance": "Medical vehicle with modest cargo and seats.",
    "Military Humvee": "Strong defense and fast, but small.",
    "Tow/Recovery Truck": "Sturdy utility truck with decent cargo.",
    "Sedan": "Fast and fuel-efficient, but small and fragile.",
    "Civilian SUV": "All-round utility with moderate seats and cargo.",
    "Utility SUV": "Rugged off-roader with solid durability and cargo.",
    "Postal Van": "Practical light cargo hauler with good road speed.",
    "Box Truck": "High cargo capacity; slower, with few seats.",
    "City Bus": "High passenger capacity; a little faster than a school bus.",
    "Motorhome": "Roomy with plenty of seats, but little heavy cargo.",
    "Fire Engine": "Very durable and well protected; slow and thirsty.",
    # Added from design doc sections 5 and 20.
    "Hatchback": "Compact and fuel-efficient, but very little room.",
    "Taxi": "Fast passenger car with little cargo space.",
    "Station Wagon": "Balanced speed and storage for a small car.",
    "Minivan": "Good seating for its size; light on protection and cargo.",
    "Coach Bus": "High passenger capacity and highway speed; costly to run.",
    "Sports Car": "Excellent speed, but almost no seats, cargo or protection.",
    "Motorcycle": "Very fast and thrifty with fuel; carries one rider and little else.",
    "Dirt Bike": "Light rough-terrain bike; tiny capacity.",
    "Scooter": "Sips fuel and is easy to keep running; slow and fragile.",
    "Delivery Van": "Versatile light cargo hauler with reasonable speed.",
    "Moving Truck": "High cargo capacity; slow and thirsty.",
    "Utility Service Truck": "Maintenance truck with less storage than a cargo truck.",
    "Flatbed Truck": "Hauls bulky loads; few seats and an exposed bed.",
    "Refrigerated Truck": "Large cargo box with high running costs.",
    "Dump Truck": "Heavy-duty bulk hauler with poor fuel economy.",
    "Landscaping Truck": "Practical work truck with room for tools and a few seats.",
    "Garbage Truck": "Sturdy, slow hauler with plenty of cargo room; thirsty and unpleasant to ride in.",
    "Car Carrier Truck": "Big, heavy transporter; slow with high fuel use.",
    "Police SUV": "Fast and protective, with little cargo or seating.",
    "Police Sedan": "Quick response car with light protection; fragile.",
    "Prison Transport Bus": "Armoured bus with barred windows and plenty of seats; slow, with little cargo.",
    "Road Maintenance Truck": "Tool-laden utility truck with few seats.",
    "Military Cargo Truck": "Protected hauler with high cargo; slow and thirsty.",
    "Armored Personnel Carrier": "Very high protection and durability; guzzles fuel.",
    "Mobile Command Vehicle": "Costly to run command post with limited general use.",
    "Hearse": "Grim-looking transport with a few seats and little cargo.",
    "Limousine": "Long and roomy for passengers; fragile and costly to maintain.",
    "Presidential Limo": "Heavily armoured limousine; very tough and well protected, but thirsty with few seats.",
    "Ice Cream Van": "Cheerful novelty van; fragile with modest cargo.",
    "TV Broadcasting Van": "Antenna-topped specialist van; thirsty and upkeep-heavy.",
    "Clown Car": "Absurdly many seats for its size; slow and flimsy.",
    "Tank": "Extremely tough and well protected; slow, with huge fuel use.",
    "Excavator": "Heavy machinery that crawls along, burning lots of fuel.",
    "Bulldozer": "Slow and very sturdy; high fuel use and costly repairs.",
    "Crane Truck": "Heavy recovery machine; slow and costly to operate.",
    "Wrecking Ball Truck": "Extremely slow demolition rig, hard to maintain.",
    "Monster Truck": "Big wheels and good durability; thirsty with little room.",
    "Armored Cash Truck": "Tough, well protected truck with limited cargo.",
    "Vintage Police Car": "Fragile novelty classic with light protection.",
    "Tourist Bus": "Huge passenger capacity; heavy fuel use.",
    "Mobile Laboratory": "Specialist research vehicle with modest cargo.",
    "Food Truck": "Mobile kitchen with decent cargo space.",
    "Prototype Military Vehicle": "Fast and well protected, but extremely thirsty.",
    "Formula 1 Car": "The fastest vehicle there is; one seat, no protection, and it drinks fuel.",
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
    "Sedan": {"label": "SEDAN"},
    "Civilian SUV": {"label": "CIV SUV"},
    "Utility SUV": {"label": "UTIL SUV"},
    "Postal Van": {"label": "POSTAL VAN"},
    "Box Truck": {"label": "BOX TRUCK"},
    "City Bus": {"label": "BUS"},
    "Motorhome": {"label": "MOTORHOME"},
    "Fire Engine": {"label": "FIRE ENGINE"},
    # Added from design doc sections 5 and 20.
    "Hatchback": {"label": "HATCHBACK"},
    "Taxi": {"label": "TAXI"},
    "Station Wagon": {"label": "WAGON"},
    "Minivan": {"label": "MINIVAN"},
    "Coach Bus": {"label": "COACH BUS"},
    "Sports Car": {"label": "SPORTS CAR"},
    "Motorcycle": {"label": "MOTORCYCLE"},
    "Dirt Bike": {"label": "DIRT BIKE"},
    "Scooter": {"label": "SCOOTER"},
    "Delivery Van": {"label": "DELIVERY VAN"},
    "Moving Truck": {"label": "MOVING TRUCK"},
    "Utility Service Truck": {"label": "SERVICE TRUCK"},
    "Flatbed Truck": {"label": "FLATBED"},
    "Refrigerated Truck": {"label": "FRIDGE TRUCK"},
    "Dump Truck": {"label": "DUMP TRUCK"},
    "Landscaping Truck": {"label": "WORK TRUCK"},
    "Garbage Truck": {"label": "GARBAGE"},
    "Car Carrier Truck": {"label": "CAR CARRIER"},
    "Police SUV": {"label": "POLICE SUV"},
    "Police Sedan": {"label": "POLICE SEDAN"},
    "Prison Transport Bus": {"label": "PRISON BUS"},
    "Road Maintenance Truck": {"label": "ROAD CREW"},
    "Military Cargo Truck": {"label": "MIL TRUCK"},
    "Armored Personnel Carrier": {"label": "APC"},
    "Mobile Command Vehicle": {"label": "COMMAND VAN"},
    "Hearse": {"label": "HEARSE"},
    "Limousine": {"label": "LIMO"},
    "Presidential Limo": {"label": "PRES LIMO"},
    "Ice Cream Van": {"label": "ICE CREAM"},
    "TV Broadcasting Van": {"label": "TV VAN"},
    "Clown Car": {"label": "CLOWN CAR"},
    "Tank": {"label": "TANK"},
    "Excavator": {"label": "EXCAVATOR"},
    "Bulldozer": {"label": "BULLDOZER"},
    "Crane Truck": {"label": "CRANE TRUCK"},
    "Wrecking Ball Truck": {"label": "WRECKING BALL"},
    "Monster Truck": {"label": "MONSTER TRUCK"},
    "Armored Cash Truck": {"label": "CASH TRUCK"},
    "Vintage Police Car": {"label": "VINTAGE COP"},
    "Tourist Bus": {"label": "TOURIST BUS"},
    "Mobile Laboratory": {"label": "MOBILE LAB"},
    "Food Truck": {"label": "FOOD TRUCK"},
    "Prototype Military Vehicle": {"label": "PROTOTYPE"},
    "Formula 1 Car": {"label": "FORMULA 1"},
}

# How big each vehicle is drawn in the convoy scene, relative to its PNG's own size (1.0 = unchanged). The PNGs were all
# drawn to about the same width, so at 1.0 an 11 m school bus came out about as long as a 5.5 m pickup. The long and
# heavy vehicles are enlarged towards their real proportions; the others stay as they were. Tune these during playtesting.
# (The vehicles screen's preview card ignores this: it fills its own picture box.)
VEHICLE_SCENE_SIZE = {
    "School Bus": 1.3,
    "Fuel Tanker": 1.4,
    "Semi-Truck": 1.25,
    "City Bus": 1.4,
    "Fire Engine": 1.2,
    "Box Truck": 1.2,
    "Motorhome": 1.15,
    "Civilian SUV": 1.1,
    "Utility SUV": 1.15,
    "Postal Van": 1.1,
    "Military Humvee": 1.4,
    "Tow/Recovery Truck": 1.2,
    # Added from design doc sections 5 and 20. These were first drawn with a placeholder PNG; the factors below keep the
    # on-screen length that stand-in had (the Wrecking Ball Truck and the Prototype now have their own PNGs, and still use
    # their old 1.3: re-tune them if they look too big or small next to the Crane Truck and the APC).
    "Hatchback": 0.9,
    "Station Wagon": 1.0,
    "Coach Bus": 1.37,
    "Motorcycle": 0.85,
    "Dirt Bike": 0.82,
    "Scooter": 0.88,
    "Delivery Van": 1.1,
    "Flatbed Truck": 1.12,
    "Dump Truck": 1.21,
    "Prison Transport Bus": 1.3,
    "Military Cargo Truck": 1.29,
    "Wrecking Ball Truck": 0.9,
    "Mobile Laboratory": 1.1,
    "Prototype Military Vehicle": 0.9,
    # Own PNGs (second batch); sizes keep the old stand-in lengths (assuming ~700 px wide).
    "Minivan": 1.0,
    "Police Sedan": 1.0,
    "Police SUV": 1.05,
    "Sports Car": 0.92,
    "Taxi": 0.95,
    "Ambulance": 1.2,
    # Own PNGs (third batch). Each factor keeps the on-screen length the old stand-in sprite had (stand-in factor x
    # ~700 px, divided by the new PNG's own width), so the vehicles are the same size in the convoy as before.
    # The Presidential Limo is new: about nine tenths of the Limousine's length.
    "Armored Personnel Carrier": 1.4,
    "Bulldozer": 1.3,
    "Clown Car": 1.17,
    "Excavator": 1.4,
    "Food Truck": 1.2,
    "Garbage Truck": 1.4,
    "Hearse": 1.14,
    "Ice Cream Van": 1.26,
    "Limousine": 1.25,
    "Tank": 1.5,
    "Mobile Command Vehicle": 1.25,
    "TV Broadcasting Van": 1.25,
    "Presidential Limo": 1.2,
    # Own PNGs (fourth batch). Each factor keeps the on-screen length the old stand-in sprite had (stand-in factor x
    # ~700 px, divided by the new PNG's own width). The Car Carrier PNG is about twice as wide as the others (1473 px).
    "Moving Truck": 1.35,
    "Utility Service Truck": 1.3,
    "Refrigerated Truck": 1.3,
    "Landscaping Truck": 1.18,
    "Car Carrier Truck": 1.4,
    "Road Maintenance Truck": 0.98,
    # Own PNGs (fifth batch), same rule: stand-in factor x ~700 px / the PNG's width. The Crane Truck PNG is very long
    # (1399 px); the Monster Truck PNG is tall because of its huge tyres.
    "Armored Cash Truck": 1.2,
    "Crane Truck": 1.4,
    "Monster Truck": 1.24,
    "Tourist Bus": 1.3,
    # Own PNGs (sixth batch). Each factor keeps the on-screen length the old stand-in sprite had (stand-in factor x
    # ~700 px, divided by the new PNG's own width, assumed ~680 px for the lab and ~740 px for the police car).
    "Mobile Laboratory": 1.13,
    "Vintage Police Car": 0.95,
    # Formula 1 Car: its PNG is very wide (about 1150 px, 1.6x a usual one), so 0.6 gives it about a pickup's length.
    "Formula 1 Car": 0.7,
}

# Where each vehicle's wheels kick up dust in the convoy scene: the x of the back (right) edge of every wheel where it
# meets the road, as a fraction of the sprite's width (the vehicles face left, so the front wheel comes first). Measured
# on the PNGs; a vehicle with two rear axles lists both. A type that is missing here uses DEFAULT_DUST_POINTS.
DEFAULT_DUST_POINTS = (0.25, 0.80)
VEHICLE_DUST_POINTS = {
    "Pickup Truck": (0.28, 0.83),
    "Passenger Van": (0.28, 0.83),
    "School Bus": (0.19, 0.755),
    "Semi-Truck": (0.26, 0.79, 0.92),
    "Fuel Tanker": (0.17, 0.78, 0.90),
    "Ambulance": (0.25, 0.785),
    "Military Humvee": (0.29, 0.845),
    "Tow/Recovery Truck": (0.235, 0.735, 0.855),
    # Estimated from the new sprites; re-measure if the dust looks off.
    "Sedan": (0.31, 0.83),
    "Civilian SUV": (0.32, 0.79),
    "Utility SUV": (0.28, 0.80),
    "Postal Van": (0.32, 0.80),
    "Box Truck": (0.26, 0.78, 0.92),
    "City Bus": (0.36, 0.81),
    "Motorhome": (0.23, 0.80),
    "Fire Engine": (0.30, 0.83),
    # Measured on the new PNGs (rear edge of each wheel where it meets the road).
    "Hatchback": (0.28, 0.88),
    "Coach Bus": (0.23, 0.73, 0.84),
    "Motorcycle": (0.24, 0.91),
    "Dirt Bike": (0.22, 0.89),
    "Delivery Van": (0.25, 0.81),
    "Flatbed Truck": (0.19, 0.75, 0.89),
    "Dump Truck": (0.23, 0.70, 0.85),
    "Military Cargo Truck": (0.23, 0.77, 0.91),
    "Minivan": (0.25, 0.83),
    "Police Sedan": (0.27, 0.83),
    "Police SUV": (0.29, 0.84),
    "Prison Transport Bus": (0.16, 0.83),
    "Scooter": (0.21, 0.89),
    "Sports Car": (0.30, 0.84),
    "Station Wagon": (0.25, 0.80),
    "Taxi": (0.27, 0.80),
    # Measured on the third batch of PNGs (rear edge of each wheel where it meets the road). The tracked machines
    # (Bulldozer, Excavator, Tank) list the rear end of the track and one point part-way along it.
    "Armored Personnel Carrier": (0.30, 0.48, 0.67, 0.84),
    "Bulldozer": (0.45, 0.79),
    "Clown Car": (0.30, 0.84),
    "Excavator": (0.52, 0.91),
    "Food Truck": (0.22, 0.81),
    "Garbage Truck": (0.19, 0.65, 0.79),
    "Hearse": (0.22, 0.80),
    "Ice Cream Van": (0.28, 0.84),
    "Limousine": (0.20, 0.84),
    "Tank": (0.35, 0.87),
    "Mobile Command Vehicle": (0.20, 0.78),
    "TV Broadcasting Van": (0.25, 0.845),
    "Presidential Limo": (0.24, 0.85),
    # Fourth batch of PNGs (estimated from the pictures; re-measure if the dust looks off). The Car Carrier has a
    # front axle, a second axle under the cab and a three-axle trailer bogie.
    "Moving Truck": (0.25, 0.84),
    "Utility Service Truck": (0.25, 0.81),
    "Refrigerated Truck": (0.26, 0.85),
    "Landscaping Truck": (0.27, 0.80),
    "Car Carrier Truck": (0.13, 0.32, 0.75, 0.81, 0.87),
    "Road Maintenance Truck": (0.29, 0.88),
    # Fifth batch (estimated from the pictures; re-measure if the dust looks off). The Crane Truck has seven axles.
    "Armored Cash Truck": (0.30, 0.89),
    "Crane Truck": (0.19, 0.41, 0.48, 0.67, 0.74, 0.82, 0.90),
    "Monster Truck": (0.40, 0.97),
    "Tourist Bus": (0.31, 0.81, 0.91),
    # Sixth batch (estimated from the pictures; re-measure if the dust looks off).
    "Mobile Laboratory": (0.25, 0.87),
    "Vintage Police Car": (0.34, 0.80),
    # Seventh batch (estimated from the pictures; re-measure if the dust looks off). The Prototype has three axles; the
    # Wrecking Ball Truck has a front axle and a rear tandem (the swinging ball itself kicks up no dust).
    "Prototype Military Vehicle": (0.33, 0.55, 0.855),
    "Wrecking Ball Truck": (0.26, 0.65, 0.76),
    # Eighth batch (estimated from the picture; re-measure if the dust looks off).
    "Formula 1 Car": (0.33, 0.97),
}

# Bonus vehicles (design doc section 20.2): optional rewards, not part of the standard roster. They are never found
# through normal discovery; they are unlocked by achievements, special events or finishing the campaign. Code that builds
# discovery / reward pools from VEHICLE_SPECS should use STANDARD_VEHICLES instead.
BONUS_VEHICLES = frozenset({
    "Hearse",
    "Limousine",
    "Presidential Limo",
    "Ice Cream Van",
    "TV Broadcasting Van",
    "Clown Car",
    "Tank",
    "Excavator",
    "Bulldozer",
    "Crane Truck",
    "Car Carrier Truck",
    "Coach Bus",
    "Motorcycle",
    "Dirt Bike",
    "Scooter",
    "Wrecking Ball Truck",
    "Monster Truck",
    "Armored Cash Truck",
    "Vintage Police Car",
    "Tourist Bus",
    "Mobile Laboratory",
    "Food Truck",
    "Prototype Military Vehicle",
    "Formula 1 Car",
    "Fire Engine",
    "Mobile Command Vehicle",
    "Utility Service Truck",
    "Road Maintenance Truck",
})
STANDARD_VEHICLES = tuple(name for name in VEHICLE_SPECS if name not in BONUS_VEHICLES)

# Military vehicles (exact VEHICLE_SPECS names): they can only be recovered at the Military Base (convoy.is_military_vehicle,
# Game.can_recover_type_here), except in SANDBOX MODE..
MILITARY_VEHICLES = frozenset({
    "Military Humvee",
    "Military Cargo Truck",
    "Armored Personnel Carrier",
    "Mobile Command Vehicle",
    "Tank",
    "Prototype Military Vehicle",
})
_unknown_military = sorted(MILITARY_VEHICLES - set(VEHICLE_SPECS))
if _unknown_military:   # fail loudly at import on a renamed or mistyped vehicle
    raise ValueError(f"MILITARY_VEHICLES names vehicles that are not in VEHICLE_SPECS: {_unknown_military}")

# Vehicles that have no PNG yet: vehicle type -> an existing vehicle type whose sprite is drawn instead (and whose wheel
# dust points are used). Every vehicle has its own PNG now, so this is empty. When a new vehicle is added without a PNG,
# put it here; when it gets its own PNG, add it to _SPRITE_FILES in vehicle_rendering.py (that entry wins) and add its own
# measured VEHICLE_DUST_POINTS entry above, then delete its line here.
SPRITE_PLACEHOLDERS = {}
for _type, _stand_in in SPRITE_PLACEHOLDERS.items():
    VEHICLE_DUST_POINTS.setdefault(_type, VEHICLE_DUST_POINTS[_stand_in])
