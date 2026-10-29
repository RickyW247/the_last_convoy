"""
Data-driven definitions for travel events in THE LAST CONVOY.

How to add an event:
- Append a new dictionary to the EVENTS list.
- Give it a unique "id", a selection "weight", a "title",
  a "description", and a list of "choices".
- Each choice needs a "label", an "outcome", and an "effects" list.
- Effects are optional. Use an empty list [] if a choice has no effects.
- Events and effects are defined here; effect_handler.py applies the effects.
  Adding a new effect type requires updating effect_handler.py.

Supported effect types:
- resource: Change fuel, food, water, or scrap.
  Requires "resource" and "amount". Positive amounts gain resources;
  negative amounts consume resources.
- survivors: Add or remove survivors using "amount".
- vehicle_repair: Repair vehicle health using "amount".
- vehicle_damage: Damage every vehicle using "amount".
- horde_gap: Change the distance to the horde in kilometres using "amount".
  Positive amounts increase the gap; negative amounts decrease it.

The "weight" controls how likely an event is to be selected relative
to other events. Higher weights make an event more likely to appear.

Keep event content and choices self-contained. The event generator
does not need to be changed when adding events that use existing
fields and supported effect types.

EVENT QUICK REFERENCE
- roadside_cache: Search a roadside crate for food, water, or scrap.
- stranded_traveller: Help a stranded person in exchange for supplies or repairs.
- blocked_highway: Clear wreckage, force through, or take a detour.
- abandoned_gas_station: Risk a stop to collect fuel or shop supplies.
- overturned_delivery_truck: Salvage cargo or parts from a crashed truck.
- small_town_survivors: Recruit a resident, trade for supplies, or move on.
- makeshift_repair_stop: Spend scrap for repairs or collect spare parts.
- zombies_on_the_road: Push through, sneak around, or distract a zombie cluster.
- rural_farmstead: Search a farmhouse or outbuildings for useful supplies.
- damaged_bridge: Reinforce a damaged bridge, cross carefully, or detour.
- engine_fire: Extinguish a fire or risk further vehicle damage.
- contaminated_supplies: Discard spoiled supplies or risk further losses.
- highway_ambush: Ram through attackers or retreat from the highway.
- broken_axle: Repair a broken axle or risk further damage.
- desperate_rescue: Rescue trapped survivors or leave them behind.
"""

EVENTS = [
    {
        "id": "roadside_cache",
        "weight": 5,
        "title": "A Roadside Cache",
        "description": "A half-hidden supply crate sits beside an abandoned car. It might be useful, but checking it will take time and care.",
        "choices": [
            {
                "label": "Search the crate",
                "outcome": "The crate held a few useful supplies.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "water", "amount": 2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Take only the scrap",
                "outcome": "You strip the crate quickly and get back on the road.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Leave it alone",
                "outcome": "The convoy moves on without risking a detour.",
                "effects": [],
            },
        ],
    },
    {
        "id": "stranded_traveller",
        "weight": 2,
        "title": "A Stranded Traveller",
        "description": "A weary traveller flags down the convoy. They offer to help, but ask for supplies in return.",
        "choices": [
            {
                "label": "Share food and water",
                "outcome": "The traveller joins the convoy, grateful for the help.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "resource", "resource": "water", "amount": -2},
                    {"type": "survivors", "amount": 1},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Ask them to repair a vehicle",
                "outcome": "They trade a little scrap for a quick repair job.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 1},
                    {"type": "vehicle_repair", "amount": 8},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Wish them luck and leave",
                "outcome": "You keep your supplies and continue west.",
                "effects": [],
            },
        ],
    },

    {
        "id": "blocked_highway",
        "weight": 3,
        "title": "A Blocked Highway",
        "description": "Wrecked cars and a collapsed barrier block the highway. Clearing a path could save fuel, but the noise may draw nearby zombies.",
        "choices": [
            {
                "label": "Clear a narrow path",
                "outcome": "The convoy squeezes through, but the work costs precious time.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 1},
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Force through the wreckage",
                "outcome": "The convoy pushes through the debris and several vehicles take damage.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 5},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Take a longer detour",
                "outcome": "You avoid the wreckage, but the detour lets the horde close in.",
                "effects": [{"type": "horde_gap", "amount": -2}],
            },
        ],
    },
    {
        "id": "abandoned_gas_station",
        "weight": 4,
        "title": "An Abandoned Gas Station",
        "description": "A roadside gas station stands silent, with a few pumps still intact. The forecourt looks exposed, but fuel is running low.",
        "choices": [
            {
                "label": "Drain the remaining fuel",
                "outcome": "You recover a small amount of fuel before getting back on the highway.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": 4},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Search the shop",
                "outcome": "The shelves yield a little food and water, but the search takes time.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 2},
                    {"type": "resource", "resource": "water", "amount": 2},
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Keep moving",
                "outcome": "You leave the station untouched and preserve your lead.",
                "effects": [],
            },
        ],
    },
    {
        "id": "overturned_delivery_truck",
        "weight": 3,
        "title": "An Overturned Delivery Truck",
        "description": "A delivery truck lies on its side beside the road. Its cargo may still be useful, but the wreck is unstable and exposed.",
        "choices": [
            {
                "label": "Salvage the cargo",
                "outcome": "You recover packaged food and water, though the search delays the convoy.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "water", "amount": 1},
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Strip useful parts",
                "outcome": "The crew removes a few reusable parts without searching the cargo.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Leave the wreck",
                "outcome": "You avoid the risk and continue west.",
                "effects": [],
            },
        ],
    },
    {
        "id": "small_town_survivors",
        "weight": 2,
        "title": "Survivors in a Small Town",
        "description": "A few residents wave from a boarded-up shop. They have supplies, but are afraid the horde will reach the town soon.",
        "choices": [
            {
                "label": "Bring one person aboard",
                "outcome": "One resident joins the convoy after a quick exchange of supplies.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -1},
                    {"type": "resource", "resource": "water", "amount": -1},
                    {"type": "survivors", "amount": 1},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Trade for supplies",
                "outcome": "You trade scrap for the residents' spare food and water.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -1},
                    {"type": "resource", "resource": "food", "amount": 2},
                    {"type": "resource", "resource": "water", "amount": 2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Do not stop",
                "outcome": "You signal that you cannot risk a stop and keep the convoy moving.",
                "effects": [],
            },
        ],
    },
    {
        "id": "makeshift_repair_stop",
        "weight": 3,
        "title": "A Makeshift Repair Stop",
        "description": "A mechanic has set up a temporary workshop in a roadside garage. They can help, but need parts and time to work.",
        "choices": [
            {
                "label": "Pay for a repair",
                "outcome": "The mechanic uses spare parts to restore some convoy health.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -2},
                    {"type": "vehicle_repair", "amount": 12},
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Ask for spare parts only",
                "outcome": "You trade time for a small bundle of reusable scrap.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Skip the workshop",
                "outcome": "You leave before the stop can slow the convoy down.",
                "effects": [],
            },
        ],
    },
    {
        "id": "zombies_on_the_road",
        "weight": 3,
        "title": "Zombies Across the Road",
        "description": "A cluster of zombies has gathered around abandoned vehicles ahead. The convoy must choose between speed, caution, and taking damage.",
        "choices": [
            {
                "label": "Push through quickly",
                "outcome": "The convoy breaks through the cluster, but vehicles are battered in the process.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 8},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Move quietly around them",
                "outcome": "The convoy avoids the worst of the danger, losing time on a cautious route.",
                "effects": [{"type": "horde_gap", "amount": -2}],
            },
            {
                "label": "Use supplies to distract them",
                "outcome": "You sacrifice food to draw the zombies away from the road.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
        ],
    },
    {
        "id": "rural_farmstead",
        "weight": 2,
        "title": "A Quiet Farmstead",
        "description": "A rural farmstead appears undisturbed. The fields may provide food, but the crew cannot be sure the buildings are safe.",
        "choices": [
            {
                "label": "Search the pantry",
                "outcome": "You find preserved food and bottled water inside the farmhouse.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 4},
                    {"type": "resource", "resource": "water", "amount": 1},
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Collect scrap from the outbuildings",
                "outcome": "You recover a few useful metal parts from abandoned equipment.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Avoid the property",
                "outcome": "You decide the risk is not worth taking and continue west.",
                "effects": [],
            },
        ],
    },
    {
        "id": "damaged_bridge",
        "weight": 3,
        "title": "A Damaged Bridge",
        "description": "A narrow bridge crosses a swollen river. Part of the railing is gone, and the convoy must decide whether to risk the crossing or find another route.",
        "choices": [
            {
                "label": "Cross carefully",
                "outcome": "The drivers guide the vehicles over one at a time. The crossing is slow, giving the horde time to close in.",
                "effects": [
                    {"type": "horde_gap", "amount": -2},
                ],
            },
            {
                "label": "Reinforce the bridge first",
                "outcome": "The crew uses scrap to brace the weakest section before crossing, costing time but reducing the risk.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -2},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
            {
                "label": "Take the river road detour",
                "outcome": "The convoy avoids the bridge, but the rough detour damages the vehicles and costs time.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 4},
                    {"type": "horde_gap", "amount": -1},
                ],
            },
        ],
    },
    {
        "id": "engine_fire",
        "weight": 4,
        "title": "Engine Fire",
        "description": "Smoke pours from an engine. Flames spread as the horde approaches.",
        "choices": [
            {
                "label": "Stop and fight the fire",
                "outcome": "You extinguish the flames, but repairs cost precious supplies and time.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -12},
                    {"type": "resource", "resource": "water", "amount": -6},
                    {"type": "horde_gap", "amount": -10}
                ]
            },
            {
                "label": "Keep driving",
                "outcome": "The fire spreads through the engine compartment.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 30},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "horde_gap", "amount": -12}
                ]
            }
        ]
    },
    {
        "id": "contaminated_supplies",
        "weight": 6,
        "title": "Contaminated Supplies",
        "description": "Your stored water smells foul. Some food may also be spoiled.",
        "choices": [
            {
                "label": "Discard everything suspicious",
                "outcome": "You eliminate the risk but lose vital supplies.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -15},
                    {"type": "resource", "resource": "food", "amount": -8}
                ]
            },
            {
                "label": "Keep the supplies",
                "outcome": "The survivors reluctantly accept the questionable provisions.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -5},
                    {"type": "resource", "resource": "food", "amount": -12},
                    {"type": "horde_gap", "amount": -8}
                ]
            }
        ]
    },
    {
        "id": "highway_ambush",
        "weight": 5,
        "title": "Highway Ambush",
        "description": "Hostile scavengers attack from behind wrecked cars as zombies close in.",
        "choices": [
            {
                "label": "Ram through the barricade",
                "outcome": "You escape under fire, smashing vehicles and wasting fuel.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 25},
                    {"type": "resource", "resource": "fuel", "amount": -12}
                ]
            },
            {
                "label": "Retreat and take a detour",
                "outcome": "The convoy escapes the ambush but loses valuable distance.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -18},
                    {"type": "resource", "resource": "food", "amount": -5},
                    {"type": "horde_gap", "amount": -20}
                ]
            }
        ]
    },
    {
        "id": "broken_axle",
        "weight": 7,
        "title": "Broken Axle",
        "description": "A loaded vehicle suffers a catastrophic axle failure on the highway.",
        "choices": [
            {
                "label": "Repair it with scrap",
                "outcome": "The improvised repair gets you moving, but supplies are depleted.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -15},
                    {"type": "horde_gap", "amount": -12},
                    {"type": "vehicle_repair", "amount": 10}
                ]
            },
            {
                "label": "Keep moving regardless",
                "outcome": "Metal grinds against the road as the damaged vehicles deteriorate.",
                "effects": [
                    {"type": "vehicle_damage", "amount": 25},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "horde_gap", "amount": -10}
                ]
            }
        ]
    },
    {
        "id": "desperate_rescue",
        "weight": 3,
        "title": "Desperate Rescue",
        "description": "Three survivors are trapped on a car roof surrounded by zombies.",
        "choices": [
            {
                "label": "Rescue them",
                "outcome": "You save three people, but the rescue drains supplies and damages the convoy.",
                "effects": [
                    {"type": "survivors", "amount": 3},
                    {"type": "resource", "resource": "food", "amount": -12},
                    {"type": "resource", "resource": "water", "amount": -12},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "vehicle_damage", "amount": 20},
                    {"type": "horde_gap", "amount": -15}
                ]
            },
            {
                "label": "Leave them behind",
                "outcome": "You escape safely, haunted by the screams fading behind you.",
                "effects": [
                    {"type": "horde_gap", "amount": 5}
                ]
            }
        ]
    },

]