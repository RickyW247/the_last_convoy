"""Dedicated events of the multi-stage missions (mission_data.py) of THE LAST CONVOY. Data only.

These events carry "trigger": "mission": EventManager.start_for_arrival never draws them (it only draws trigger None and
"ambush"), and MissionManager.open_stage_event opens them by id when the stage that names them is ready
(objective {"type": "event", "event_id": ...}).

Two things are specific to mission events:
- "declines_mission": True on a choice means "not now". The event does NOT count as done (the stage stays where it is,
  the event comes back at the next stop the convoy reaches) and no achievement is awarded for it. Every mission event
  has one, so a convoy that cannot afford or fit anything is never stuck.
- The event "requires" is NOT checked when a mission opens an event (like the evacuation events), so a choice that
  needs a vehicle carries its own "requires" and is greyed out without it.

Event ids that achievement_data.py names (they unlock the bonus vehicles): heavy_machinery, tv_broadcast,
ice_cream_van, travelling_circus, presidential_escort.
"""

MISSION_EVENTS = [
    # ---- Clear the Road -------------------------------------------------------------------------------
    {
        "id": "heavy_machinery",
        "trigger": "mission",
        "weight": 0,
        "title": "A Wall of Wrecks",
        "description": "A collapsed overpass has buried the road under crushed trucks and concrete, and the horde is "
                       "behind you. The convoy has to cut a lane through it before the wreckage shifts again. "
                       "Heavy machinery would make it far safer, but any convoy can try.",
        "choices": [
            {
                "label": "Clear it by hand and winch (risky)",
                "success_chance": 0.35,
                "chance_bonus": [
                    {"requires": {"vehicle": "Excavator"}, "amount": 0.35},
                    {"requires": {"vehicle": "Bulldozer"}, "amount": 0.30},
                    {"requires": {"vehicle": "Tow/Recovery Truck"}, "amount": 0.10},
                    {"requires": {"survivors_at_least": 12}, "amount": 0.10},
                ],
                "outcome": "Chains, winches and a lot of sweat shift the wreckage a car at a time. A lane opens, and "
                           "the rubble gives up some scrap.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 10},
                    {"type": "vehicle_damage_pct", "amount": 3, "defense": True},
                    {"type": "horde_gap", "amount": -8},
                ],
                "failure_outcome": "A stack of crushed trucks gives way and buries the work crew. By the time the "
                                   "lane is finally clear, people are hurt, vehicles are scraped and the horde is closer.",
                "failure_effects": [
                    {"type": "survivors", "amount": -2, "defense": True},
                    {"type": "injury", "amount": 3, "defense": True},
                    {"type": "vehicle_damage_pct", "amount": 12, "defense": True},
                    {"type": "horde_gap", "amount": -14},
                ],
            },
            {
                "label": "Burn a lane with cutting torches (5 scrap, 3 fuel)",
                "payment": True,
                "success_chance": 0.60,
                "chance_bonus": [
                    {"requires": {"vehicle": ["Excavator", "Bulldozer"]}, "amount": 0.20},
                ],
                "outcome": "The torches cut the twisted steel into pieces small enough to drag aside. The road is "
                           "open, and the offcuts are worth keeping.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -5},
                    {"type": "resource", "resource": "fuel", "amount": -3},
                    {"type": "vehicle_damage_pct", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -6},
                ],
                "failure_outcome": "A fuel line in one of the wrecks catches. The fire costs the convoy hours, and "
                                   "the torches and fuel are gone by the time it is out.",
                "failure_effects": [
                    {"type": "resource", "resource": "scrap", "amount": -5},
                    {"type": "resource", "resource": "fuel", "amount": -3},
                    {"type": "survivors", "amount": -1, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "vehicle_damage_pct", "amount": 8, "defense": True},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Not now",
                "declines_mission": True,
                "outcome": "You back away to look for another way. The wreckage waits.",
                "effects": [{"type": "horde_gap", "amount": -4}],
            },
        ],
    },

    # ---- The Last Broadcast (TV Broadcasting Van) -----------------------------------------------------------------
    {
        "id": "news_van_signal",
        "trigger": "mission",
        "weight": 0,
        "title": "A Signal in the Static",
        "description": "A news van sits dead on the shoulder, its mast still raised and a red light blinking. The "
                       "generator inside works. Whoever drove it is long gone.",
        "choices": [
            {
                "label": "Take the van",
                "requires": {"vehicle_slot": True},
                "outcome": "The van's batteries are flat but the engine turns over. Its mast folds down for the road.",
                "effects": [
                    {"type": "vehicle_gain", "vehicle": "TV Broadcasting Van", "health": 0.7},
                    {"type": "horde_gap", "amount": -5},
                ],
            },
            {
                "label": "Not now",
                "declines_mission": True,
                "outcome": "You leave the van for later and drive on.",
                "effects": [],
            },
        ],
    },
    {
        "id": "tv_broadcast",
        "trigger": "mission",
        "weight": 0,
        "title": "Broadcast from the End",
        "description": "The van's transmitter finds a live frequency. Somewhere out there people are listening. A signal "
                       "this strong will also tell everything with ears where you are.",
        "choices": [
            {
                "label": "Broadcast a call to the survivors",
                "payment": True,
                "requires": {"vehicle": "TV Broadcasting Van", "free_seats_at_least": 1},
                "outcome": "Your voice goes out over the dead cities. Within hours people begin to arrive, and so does the horde.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -6},
                    {"type": "survivors", "amount": 4},
                    {"type": "horde_gap", "amount": -15},
                ],
            },
            {
                "label": "Send a short coded message",
                "payment": True,
                "requires": {"vehicle": "TV Broadcasting Van"},
                "outcome": "A short burst, then silence. A courier meets you at dawn with a crate of supplies.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -3},
                    {"type": "resource", "resource": "food", "amount": 5},
                    {"type": "resource", "resource": "water", "amount": 4},
                    {"type": "horde_gap", "amount": -6},
                ],
            },
            {
                "label": "Stay silent",
                "declines_mission": True,
                "outcome": "You switch the transmitter off. Another day, perhaps.",
                "effects": [],
            },
        ],
    },

    # ---- Sweet Survival (Ice Cream Van) ---------------------------------------------------------------------------
    {
        "id": "ice_cream_jingle",
        "trigger": "mission",
        "weight": 0,
        "title": "A Tinny Little Tune",
        "description": "A cheerful jingle drifts across the empty road. Around the bend, a pastel ice cream van is parked "
                       "with its music box still playing. Its freezer is warm but its engine is sound.",
        "choices": [
            {
                "label": "Take the ice cream van",
                "requires": {"vehicle_slot": True},
                "outcome": "You silence the music box. The van joins the convoy, and it is surprisingly comfortable inside.",
                "effects": [
                    {"type": "vehicle_gain", "vehicle": "Ice Cream Van", "health": 0.8},
                    {"type": "horde_gap", "amount": -5},
                ],
            },
            {
                "label": "Not now",
                "declines_mission": True,
                "outcome": "You drive past, the jingle fading behind you.",
                "effects": [],
            },
        ],
    },
    {
        "id": "ice_cream_van",
        "trigger": "mission",
        "weight": 0,
        "title": "Sweet Survival",
        "description": "A group of children huddles by the roadside, thin and exhausted. The ice cream van's old stock "
                       "has kept in its deep freezer. It is not nutrition, but it is something the world forgot.",
        "choices": [
            {
                "label": "Hand out the ice cream and take them aboard",
                "requires": {"free_seats_at_least": 1},
                "outcome": "For ten minutes it is an ordinary afternoon. The children climb aboard, laughing.",
                "effects": [
                    {"type": "survivors", "amount": 3},
                    {"type": "injury", "amount": -2},
                    {"type": "horde_gap", "amount": -6},
                ],
            },
            {
                "label": "Hand it out and share some supplies",
                "payment": True,
                "outcome": "They eat in silence, then smile. One of the older kids repays you with scavenged scrap.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "resource", "resource": "scrap", "amount": 6},
                    {"type": "injury", "amount": -1},
                    {"type": "horde_gap", "amount": -5},
                ],
            },
            {
                "label": "Save it for later",
                "declines_mission": True,
                "outcome": "You drive on. The children watch you go.",
                "effects": [],
            },
        ],
    },

    # ---- Strange Music (Clown Car; the circus achievement is secret) -----------------------------------------------
    {
        "id": "distant_calliope",
        "trigger": "mission",
        "weight": 0,
        "title": "Music on the Wind",
        "description": "A faint calliope melody drifts over the hills. It is impossible, and it is getting closer.",
        "choices": [
            {
                "label": "Follow the music",
                "outcome": "The tune leads along an old service road. Hand-painted arrows point the way.",
                "effects": [{"type": "horde_gap", "amount": -6}],
            },
            {
                "label": "Ignore it",
                "declines_mission": True,
                "outcome": "You turn up the engine noise until the tune is gone.",
                "effects": [],
            },
        ],
    },
    {
        "id": "travelling_circus",
        "trigger": "mission",
        "weight": 0,
        "title": "The Travelling Circus",
        "description": "Painted wagons ring a field of torn tents. A ringmaster in a threadbare coat bows to the convoy. "
                       "The troupe has survived by never stopping. They have one clown car left and no more room.",
        "choices": [
            {
                "label": "Trade supplies for the clown car",
                "payment": True,
                "requires": {"vehicle_slot": True},
                "outcome": "The ringmaster presses the keys into your hand. A dozen people clap as the tiny car rattles out.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -6},
                    {"type": "vehicle_gain", "vehicle": "Clown Car", "health": 0.9},
                    {"type": "injury", "amount": -1},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Take the show on the road with you",
                "requires": {"free_seats_at_least": 2, "vehicle_slot": True},
                "outcome": "The performers pile into the convoy and the clown car follows. For an hour it feels almost normal.",
                "effects": [
                    {"type": "survivors", "amount": 2},
                    {"type": "vehicle_gain", "vehicle": "Clown Car", "health": 0.7},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Leave quietly",
                "declines_mission": True,
                "outcome": "You back away. The music does not stop until you are miles down the road.",
                "effects": [],
            },
        ],
    },

    # ---- The Package (Presidential Limo) ----------------------------------------------------------------------------
    {
        "id": "presidential_envoy",
        "trigger": "mission",
        "weight": 0,
        "title": "A Man in a Dark Suit",
        "description": "A man in a dark suit steps out of a roadblock with his hands raised. He says there is a vehicle "
                       "in a garage nearby, and a passenger who needs to reach the coast alive. He does not say who.",
        "choices": [
            {
                "label": "Hear him out",
                "outcome": "He gives you coordinates and a handshake that lasts too long. You are being trusted with something.",
                "effects": [{"type": "horde_gap", "amount": -4}],
            },
            {
                "label": "Refuse",
                "declines_mission": True,
                "outcome": "You decline. He nods and lets you through.",
                "effects": [],
            },
        ],
    },
    {
        "id": "presidential_limo",
        "trigger": "mission",
        "weight": 0,
        "title": "The Garage",
        "description": "Behind a steel door, an armoured limousine with flags on its bonnet. Its driver died at the wheel "
                       "weeks ago. The back seat is empty, but the glove box holds sealed orders.",
        "choices": [
            {
                "label": "Take the limousine",
                "requires": {"vehicle_slot": True},
                "outcome": "The armoured limo starts at the first turn. The orders say to protect it at all costs.",
                "effects": [
                    {"type": "vehicle_gain", "vehicle": "Presidential Limo", "health": 1.0},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Not now",
                "declines_mission": True,
                "outcome": "You leave the garage door shut for now.",
                "effects": [],
            },
        ],
    },
    {
        "id": "presidential_escort",
        "trigger": "mission",
        "weight": 0,
        "title": "Presidential Protection",
        "description": "A figure in a long coat steps into the limousine at the roadside, flanked by two exhausted guards. "
                       "They say the convoy's route is the only one still open. Everything depends on you getting them to the coast.",
        "choices": [
            {
                "label": "Escort them under heavy guard",
                "payment": True,
                "requires": {"vehicle": "Presidential Limo", "free_seats_at_least": 2},
                "outcome": "The guards take the rear and the convoy tightens up. You deliver them safely and are well rewarded.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -5},
                    {"type": "survivors", "amount": 2},
                    {"type": "resource", "resource": "scrap", "amount": 10},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Run a decoy and take the limousine through",
                "requires": {"vehicle": "Presidential Limo"},
                "outcome": "A decoy draws the horde off. The limo slips through with the VIP aboard. It costs the convoy dearly.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 8, "defense": True},
                    {"type": "resource", "resource": "food", "amount": 8},
                    {"type": "resource", "resource": "water", "amount": 8},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
            {
                "label": "Not yet",
                "declines_mission": True,
                "outcome": "You ask them to wait while the convoy prepares.",
                "effects": [],
            },
        ],
    },

    # ---- Armoured Convoy (Tank) -------------------------------------------------------------------------------------
    {
        "id": "tank_depot",
        "trigger": "mission",
        "weight": 0,
        "title": "The Armoured Depot",
        "description": "Behind the base's motor pool a battle tank sits under a tarpaulin, its tracks cracked but whole. "
                       "A quartermaster says it can run again for the right price and the right driver.",
        "choices": [
            {
                "label": "Pay 15 scrap to recover the tank",
                "payment": True,
                "requires": {"vehicle_slot": True},
                "outcome": "Mechanics work through the night. By dawn the tank shudders to life and falls in behind the convoy.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -15},
                    {"type": "vehicle_gain", "vehicle": "Tank", "health": 0.7},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Not now",
                "declines_mission": True,
                "outcome": "You decline for now. The tank is not going anywhere.",
                "effects": [],
            },
        ],
    },
    {
        "id": "armoured_checkpoint",
        "trigger": "mission",
        "weight": 0,
        "title": "Armoured Column",
        "description": "A burning barricade seals the road. Raiders watch from the wrecks on either side. The tank's "
                       "engine idles behind you, a promise of what the convoy can do.",
        "choices": [
            {
                "label": "Lead with the tank",
                "requires": {"vehicle": "Tank"},
                "outcome": "The tank flattens the barricade and the raiders scatter. The convoy rolls through in its wake.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": 6},
                    {"type": "resource", "resource": "scrap", "amount": 8},
                    {"type": "vehicle_damage_pct", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -6},
                ],
            },
            {
                "label": "Hold back",
                "declines_mission": True,
                "outcome": "You wait it out. The barricade burns on.",
                "effects": [],
            },
        ],
    },
]
