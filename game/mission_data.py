
"""
Data-driven mission definitions for THE LAST CONVOY.

Each mission contains:
- id: Unique mission identifier.
- title: Mission name.
- description: Mission briefing.
- prerequisites: Mission IDs that must be completed first.
- objectives: List of objectives to complete.
- rewards: Rewards granted upon completion.
- failure_conditions: Conditions that cause mission failure.

Multi-stage missions: instead of "objectives", give a mission a "stages" list. Each stage is a dict with "title",
"description", "objectives" and optional "rewards" (paid when that stage is done). Stages are played in order; the
mission's own "rewards" are paid after the last one. The missions screen shows the current stage's objectives (see
MissionManager._stage_view). Mission events (mission_event_data.py) are tied in with an "event" objective.

Supported objective types:
- collection: Collect a specified amount of fuel, food, water, or scrap.
- destination: Reach a specific map stop ("stop_id"), any of several
  ("stop_ids"), or any stop at least "min_axis" km along the Start-to-Pacific
  line. Use "min_axis" for stops some map layouts let the player bypass: it
  also counts every later stop, so a bypassed or already-passed stop can
  never make the mission impossible.
  A destination objective may also use "node_flag": "military_base" (any stop whose map_data node has that flag).
- rescue: Recruit a specified number of survivors.
- vehicle: HOLD a vehicle type ("vehicle": a name from vehicle_data.VEHICLE_SPECS) in the convoy right now. A level
  like stockpile: it is lost again if the vehicle is.
- travel: complete "target" journeys (arrivals at a stop) while the stage is active. With "vehicle", only journeys on
  which the convoy owns that vehicle type count.
- event: a dedicated mission event ("event_id", an event of mission_event_data.py). It opens at the next stop once every
  other objective of the stage is met, and is done when the player resolves it with a choice that is not
  "declines_mission". Declining ("not now") brings it back at the next stop.
- stockpile: HOLD at least "target" of a resource ("resource": fuel, food, water or scrap) in the convoy at the same
  time as every other objective of the mission. Not cumulative: progress is the amount currently held (capped at the
  target), so it falls again when the resource is spent, and spending what was collected does not count.
"""

MISSIONS = [
    {
        "id": "fuel_run",
        "title": "Fuel Run",
        "description": (
            "Fuel is running dangerously low. Scavenge enough fuel "
            "to keep the convoy moving before the horde catches up."
        ),
        "prerequisites": [],
        "objectives": [
            {
                "type": "collection",
                "resource": "fuel",
                "target": 20,
            }
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "food",
                "amount": 10,
            }
        ],
        "failure_conditions": [],
    },
    {
        "id": "stockpile_supplies",
        "title": "Stockpile Supplies",
        "description": (
            "The survivors need food and clean water. Gather enough "
            "supplies to prepare the convoy for the journey ahead."
        ),
        "prerequisites": [],
        "objectives": [
            {
                "type": "collection",
                "resource": "food",
                "target": 15,
            },
            {
                "type": "collection",
                "resource": "water",
                "target": 10,
            },
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "fuel",
                "amount": 10,
            },
            {
                "type": "resource",
                "resource": "scrap",
                "amount": 5,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "reach_safe_haven",
        "title": "Reach Safe Haven",
        "description": (
            "A radio transmission mentions a possible safe haven "
            "nearby. Push on to City 3, or the road around it, and investigate."
        ),
        "prerequisites": ["fuel_run"],
        "objectives": [
            {
                "type": "destination",
                "min_axis": 310,
                "target": 1,
                "description": "Reach City 3 (or the road around it)",
            }
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "food",
                "amount": 10,
            },
            {
                "type": "resource",
                "resource": "water",
                "amount": 10,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "rescue_the_lost",
        "title": "Rescue the Lost",
        "description": (
            "A desperate distress call comes from survivors stranded "
            "near the highway. Find and recruit three people."
        ),
        "prerequisites": [],
        "objectives": [
            {
                "type": "rescue",
                "target": 3,
            }
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "food",
                "amount": 15,
            },
            {
                "type": "resource",
                "resource": "water",
                "amount": 10,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "long_haul",
        "title": "The Long Haul",
        "description": (
            "The horde is growing larger behind you. Keep the convoy "
            "moving and reach City 4."
        ),
        "prerequisites": ["reach_safe_haven", "rescue_the_lost"],
        "objectives": [
            {
                "type": "collection",
                "resource": "fuel",
                "target": 15,
            },
            {
                "type": "destination",
                "min_axis": 430,
                "target": 1,
                "description": "Reach City 4",
            },
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "fuel",
                "amount": 20,
            },
            {
                "type": "resource",
                "resource": "scrap",
                "amount": 15,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "full_tank",
        "title": "Full Tank",
        "description": (
            "Nobody makes it to the coast on fumes. Have at least 40 fuel "
            "in the convoy's tanks at once; fuel you burn does not count."
        ),
        "prerequisites": [],
        "objectives": [
            {
                "type": "stockpile",
                "resource": "fuel",
                "target": 40,
                "description": "Hold 40 fuel",
            }
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "scrap",
                "amount": 8,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "well_stocked",
        "title": "Well Stocked",
        "description": (
            "Hunger and thirst thin a convoy faster than the horde. Carry "
            "at least 35 food and 30 water at the same time."
        ),
        "prerequisites": ["stockpile_supplies"],
        "objectives": [
            {
                "type": "stockpile",
                "resource": "food",
                "target": 35,
                "description": "Hold 35 food",
            },
            {
                "type": "stockpile",
                "resource": "water",
                "target": 30,
                "description": "Hold 30 water",
            },
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "fuel",
                "amount": 15,
            },
        ],
        "failure_conditions": [],
    },
    {
        "id": "scrap_reserve",
        "title": "Scrap Reserve",
        "description": (
            "Upgrades and repairs eat scrap. Build a reserve of 20 scrap "
            "and keep it in the cargo hold."
        ),
        "prerequisites": ["reach_safe_haven"],
        "objectives": [
            {
                "type": "stockpile",
                "resource": "scrap",
                "target": 20,
                "description": "Hold 20 scrap",
            }
        ],
        "rewards": [
            {
                "type": "resource",
                "resource": "food",
                "amount": 10,
            },
            {
                "type": "resource",
                "resource": "water",
                "amount": 10,
            },
        ],
        "failure_conditions": [],
    },

    # ------------------------------------------------------------------------------------------------------------------
    # Multi-stage missions. Each one carries the dedicated events of mission_event_data.py and finishes an achievement
    # (achievement_data.py) that needed content.
    # ------------------------------------------------------------------------------------------------------------------
    {
        "id": "clear_the_road",
        "title": "Clear the Road",
        "description": "Roads further west are blocked by collapsed overpasses. Find a way through before the horde catches up.",
        "prerequisites": ["reach_safe_haven"],
        "stages": [
            {
                "title": "A Wall of Wrecks",
                "description": "Scrap and fuel are the price of cutting through a collapsed overpass. Stock up, then push on until the road is blocked.",
                "objectives": [
                    {"type": "collection", "resource": "scrap", "target": 10, "description": "Collect 10 scrap"},
                    {"type": "event", "event_id": "heavy_machinery", "target": 1,
                     "description": "Clear the blocked road"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "scrap", "amount": 12},
            {"type": "resource", "resource": "fuel", "amount": 10},
        ],
        "failure_conditions": [],
    },
    {
        "id": "last_broadcast",
        "title": "The Last Broadcast",
        "description": "Somewhere out there people are still listening to the radio. Give them something to hear.",
        "prerequisites": ["rescue_the_lost"],
        "stages": [
            {
                "title": "A Signal in the Static",
                "description": "Push on until the radio picks up something strange.",
                "objectives": [
                    {"type": "destination", "min_axis": 200, "target": 1, "description": "Reach the next city"},
                    {"type": "event", "event_id": "news_van_signal", "target": 1, "description": "Find the news van"},
                ],
                "rewards": [{"type": "resource", "resource": "scrap", "amount": 5}],
            },
            {
                "title": "Broadcast from the End",
                "description": "The van's transmitter eats fuel. Fill the tanks, then transmit.",
                "objectives": [
                    {"type": "vehicle", "vehicle": "TV Broadcasting Van", "target": 1, "description": "Keep the news van"},
                    {"type": "stockpile", "resource": "fuel", "target": 20, "description": "Hold 20 fuel"},
                    {"type": "event", "event_id": "tv_broadcast", "target": 1, "description": "Make the broadcast"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "food", "amount": 10},
            {"type": "resource", "resource": "water", "amount": 10},
            {"type": "survivors", "amount": 1},
        ],
        "failure_conditions": [],
    },
    {
        "id": "sweet_tooth",
        "title": "A Little Sweetness",
        "description": "The children of the convoy have not smiled in weeks. Rumour has it there is one thing left to fix that.",
        "prerequisites": ["stockpile_supplies"],
        "stages": [
            {
                "title": "A Tinny Little Tune",
                "description": "Get some distance down the road and listen.",
                "objectives": [
                    {"type": "destination", "min_axis": 200, "target": 1, "description": "Reach the next city"},
                    {"type": "event", "event_id": "ice_cream_jingle", "target": 1, "description": "Follow the jingle"},
                ],
            },
            {
                "title": "Sweet Survival",
                "description": "The van is yours. Find someone who needs it.",
                "objectives": [
                    {"type": "vehicle", "vehicle": "Ice Cream Van", "target": 1, "description": "Keep the ice cream van"},
                    {"type": "stockpile", "resource": "water", "target": 15, "description": "Hold 15 water"},
                    {"type": "event", "event_id": "ice_cream_van", "target": 1, "description": "Meet the children"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "food", "amount": 10},
            {"type": "resource", "resource": "water", "amount": 6},
        ],
        "failure_conditions": [],
    },
    {
        "id": "strange_music",
        "title": "Strange Music",
        "description": "A few survivors swear they heard a calliope on the wind. Nobody believes them.",
        "prerequisites": ["reach_safe_haven"],
        "stages": [
            {
                "title": "Music on the Wind",
                "description": "Keep driving. If the music is real, it will come back.",
                "objectives": [
                    {"type": "destination", "min_axis": 310, "target": 1, "description": "Reach City 3 (or the road around it)"},
                    {"type": "event", "event_id": "distant_calliope", "target": 1, "description": "Hear the music"},
                ],
            },
            {
                "title": "Follow the Tune",
                "description": "Somewhere ahead the tune becomes a place.",
                "objectives": [
                    {"type": "travel", "target": 1, "description": "Complete another journey"},
                    {"type": "event", "event_id": "travelling_circus", "target": 1, "description": "Find the circus"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "food", "amount": 8},
            {"type": "resource", "resource": "scrap", "amount": 8},
        ],
        "failure_conditions": [],
    },
    {
        "id": "the_package",
        "title": "The Package",
        "description": "A man in a dark suit at a roadblock says there is someone who must reach the coast alive.",
        "prerequisites": ["long_haul"],
        "stages": [
            {
                "title": "A Man in a Dark Suit",
                "description": "Hear the stranger out.",
                "objectives": [
                    {"type": "event", "event_id": "presidential_envoy", "target": 1, "description": "Meet the envoy"},
                ],
            },
            {
                "title": "The Garage",
                "description": "The envoy's coordinates lead to a locked garage. Arm the convoy for what comes next.",
                "objectives": [
                    {"type": "stockpile", "resource": "fuel", "target": 25, "description": "Hold 25 fuel"},
                    {"type": "event", "event_id": "presidential_limo", "target": 1, "description": "Open the garage"},
                ],
                "rewards": [{"type": "resource", "resource": "scrap", "amount": 8}],
            },
            {
                "title": "Presidential Protection",
                "description": "Get the VIP to the next stop, then the next.",
                "objectives": [
                    {"type": "vehicle", "vehicle": "Presidential Limo", "target": 1, "description": "Keep the limousine"},
                    {"type": "travel", "vehicle": "Presidential Limo", "target": 2,
                     "description": "Complete 2 journeys with the limousine"},
                    {"type": "event", "event_id": "presidential_escort", "target": 1, "description": "Escort the VIP"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "fuel", "amount": 15},
            {"type": "resource", "resource": "scrap", "amount": 15},
            {"type": "survivors", "amount": 2},
        ],
        "failure_conditions": [],
    },
    {
        "id": "armour_up",
        "title": "Armoured Convoy",
        "description": "The military base still has a few working machines. One of them could carry the convoy to the coast.",
        "prerequisites": ["reach_safe_haven"],
        "stages": [
            {
                "title": "The Armoured Depot",
                "description": "Reach the Military Base and ask about the tank.",
                "objectives": [
                    {"type": "destination", "node_flag": "military_base", "target": 1,
                     "description": "Reach the Military Base"},
                    {"type": "event", "event_id": "tank_depot", "target": 1, "description": "Visit the armoured depot"},
                ],
                "rewards": [{"type": "resource", "resource": "scrap", "amount": 6}],
            },
            {
                "title": "Armoured Column",
                "description": "Drive the tank out. Raiders do not like what they see.",
                "objectives": [
                    {"type": "vehicle", "vehicle": "Tank", "target": 1, "description": "Keep the tank"},
                    {"type": "travel", "vehicle": "Tank", "target": 2, "description": "Complete 2 journeys with the tank"},
                    {"type": "event", "event_id": "armoured_checkpoint", "target": 1,
                     "description": "Break the barricade"},
                ],
            },
        ],
        "rewards": [
            {"type": "resource", "resource": "fuel", "amount": 15},
            {"type": "resource", "resource": "scrap", "amount": 12},
        ],
        "failure_conditions": [],
    },
]
