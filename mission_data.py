
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

Supported objective types:
- collection: Collect a specified amount of fuel, food, water, or scrap.
- destination: Reach a specific map stop.
- rescue: Recruit a specified number of survivors.
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
            "nearby. Reach the abandoned town and investigate."
        ),
        "prerequisites": ["fuel_run"],
        "objectives": [
            {
                "type": "destination",
                "stop_id": "abandoned_town",
                "target": 1,
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
            "moving and reach the next major checkpoint."
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
                "stop_id": "military_checkpoint",
                "target": 1,
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
]
