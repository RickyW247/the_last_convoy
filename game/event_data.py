"""
Data-driven definitions for travel events in THE LAST CONVOY.

How to add an event:
- Append a new dictionary to the EVENTS list.
- Give it a unique "id", a selection "weight", a "title",
  a "description", and a list of "choices".
- Each choice needs a "label", an "outcome", and an "effects" list.
- A choice that is a service the player pays for (a repair, a rescue, a trade) has "payment": True: it is greyed
  out while the convoy cannot afford its cost. Any other choice is a penalty (a robber, a horde, an ambush): it
  can always be picked and takes whatever the convoy has, down to zero, never below.
- An optional "requires" dict on an EVENT makes it fire only in that situation, and on a CHOICE makes the option
  selectable only then (greyed out otherwise). Every entry must hold:
    "fuel_below": 15, "food_below", "water_below", "scrap_below", "survivors_below", "horde_below", "health_below",
    "vehicles_below"          -> the stat is lower than the number
    "scrap_at_least": 8 (same stats)  -> the stat is at least the number
    "vehicle": "Ambulance" or ["Ambulance", "School Bus"]  -> the convoy owns one of these vehicle types (the
                                      names in vehicle_data.VEHICLE_SPECS, any capitalisation)
    "vehicle_slot": True   -> a spare adult could drive another vehicle and there is a type not owned yet
    "free_seats_at_least": 1  -> that many passenger seats are free. Put it on every choice that takes survivors
                                 aboard. If fewer people fit than the choice offers, only those join and its resource
                                 costs are scaled down to match (effect_handler.fitted_effects).
    "background": "Criminal" or ["Military", "Police"]   -> the player's background is one of these (background_data.py)
    "special_absent": "rick_grimes" or ["joel_miller", "ellie_williams"]  -> none of these special survivors (keys of
                                      survivor_data.SPECIAL_SURVIVORS) is in the convoy right now
  "horde" is the gap in km, "health" the convoy health in %. An unknown key means the event never fires.
- Optional event flags that player backgrounds read (game/background_rules.py): "emergency": True (a rescue or
  emergency: the Police background's Emergency Response cuts the horde-gap losses of its choices) and "settlement":
  True (a town or camp: the Criminal background's Untrusted Reputation makes it sometimes not appear).
- An event is also skipped when the convoy can pick none of its choices (all are payments it cannot afford).
- An optional "trigger": "ambush" keeps an event out of the ordinary travel events: it is drawn only when a road
  ambush happens (travel._travel_day), and takes the place of the old automatic ambush damage. Give an ambush event
  a fight / flee / sacrifice style choice set, and always one choice that needs nothing (a penalty), so it can be shown.
- Effects are optional. Use an empty list [] if a choice has no effects.
- Events and effects are defined here; effect_handler.py applies the effects.
  Adding a new effect type requires updating effect_handler.py.

Supported effect types:
- resource: Change fuel, food, water, or scrap.
  Requires "resource" and "amount". Positive amounts gain resources;
  negative amounts consume resources.
- survivors: Add or remove survivors using "amount".
- vehicle_damage_pct: Damage every vehicle by "amount" percent of its own maximum health (what an ambush does).
  Every event that hurts vehicles uses this, so damage scales with each vehicle and defense can absorb it.
- Add "defense": True to a vehicle_damage_pct effect, or to a survivors LOSS (negative amount), to let the convoy's
  defense absorb part of it (Game.defense_reduction(), up to 60%).
- vehicle_repair: Repair vehicle health using "amount".
- injury: Positive amounts injure that many healthy survivors (injured -> critical -> dies if untreated, see
  game/conditions.py); add "defense": True to let the convoy's defense cut the number (it can spare everyone). Negative
  amounts treat that many injured survivors (the critical ones first). Put it after a "survivors" gain to wound the
  people just taken aboard. Put a sentence about it in the choice's "outcome": the result screen lists "Injured +n".
- vehicle_damage: Old name of vehicle_damage_pct with "defense" always on (kept so old data still works); write
  vehicle_damage_pct in new events.
- special_survivor: A special survivor (key of survivor_data.SPECIAL_SURVIVORS: fixed name, gender and age) joins the
  convoy. Needs "key" and one free seat per person. Give the event "requires": {"free_seats_at_least": N,
  "special_absent": [...]} and use it only in rare events (see special_event_data.py). effect_handler.recruit_special
  recruits an ordinary survivor and turns the new record into the special one (SurvivorManager.convert_to_special).
- vehicle_gain: Add a vehicle to the convoy. Optional "vehicle": a type name from vehicle_data.VEHICLE_SPECS (without it
  a random type the convoy lacks) and "health": share of max health (default 1.0; recovered vehicles are 0.7). Needs a
  spare adult driver and an unowned type, so give the event "requires": {"vehicle_slot": True}. Only for very rare
  events (weight well under 1).
  A vehicle that arrives WITH its people (a family and their minivan): add "vehicle" (required), "crew": N (ordinary
  people; two or more come as a family) and / or "special": [keys] (special survivors; at least one adult must
  come, the vehicle needs a driver). The crew brings its own driver and the vehicle its own seats, so such an event
  needs neither a spare driver nor free seats. If the convoy already owns that vehicle type, the people still come
  (in free seats, like any rescue) and only the vehicle stays behind: the event is never hidden for that, and a choice
  can give "outcome_no_vehicle" for its text then. N plus the special survivors may not exceed the vehicle's passenger seats (check_events tests it).
  The result screen lists "Vehicles +1" and "Survivors +N". Under Untrusted Reputation (Criminal) the whole group
  agrees or drives off together (one roll), see effect_handler.fitted_effects.
- vehicle_loss: Abandon the most damaged vehicle through Game.abandon_vehicle (never the last one; seats and
  drivers are re-checked, so survivors may leave). Pair it with a "requires" of
  {"vehicles_at_least": 2} or more.
- horde_gap: Change the distance to the horde in kilometres using "amount".
  Positive amounts increase the gap; negative amounts decrease it.
- berths: Change the places left on the Pacific evacuation ship by "amount" (only meaningful in the evacuation events;
  elsewhere it does nothing). The choice button shows "+N ship berths".
- An optional "trigger": "mission" marks the dedicated events of the multi-stage missions (mission_event_data.py, appended
  to EVENTS at the bottom of this file). They are never drawn as ordinary or ambush events: MissionManager opens them by
  id. A choice with "declines_mission": True is "not now" (the event comes back at the next stop, no achievement).
- An optional "trigger": "evacuation" marks the three scripted events of the final Pacific evacuation (game/evacuation.py).
  They are never drawn as ordinary or ambush events: the evacuation opens them by id, in order.

The "weight" controls how likely an event is to be selected relative
to other events. Higher weights make an event more likely to appear. Weights may be fractions: the vehicle
gain / loss events use 0.3 (about 0.3% each while the other weights add up to about 110).

Horde gap scale: endless_traffic_jam (-5 / -15 / -20) is the reference. A quick, cheap stop costs about -4, a
search or detour -8 to -12, a big time sink -15 or more. Gains (positive amounts) are separate.

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
- abandoned_medical_clinic: Search a clinic for supplies or scrap.
- stranded_fuel_tanker: Recover fuel or salvage tanker parts.
- rainwater_collection: Collect and filter rainwater for supplies.
- family_in_need: Recruit a family, share supplies, or move on.
- emergency_radio_transmission: Follow a distress signal, respond, or ignore it.
- the_bottleneck: Block a pass, speed ahead, or take a quiet route.
- endless_traffic_jam: Force through traffic, detour, or wait.
SITUATIONAL EVENTS (need a "requires")
- running_on_fumes: [fuel low] Trade for fuel, siphon wrecks, or press on.
- dry_wells: [water low] Fix a farm pump, boil pond water, or move on.
- horde_close_call: [horde gap small] Barricade, sprint, or fight a rearguard.
- scrap_trader: [plenty of scrap] Trade scrap for supplies or fuel.
- family_minivan: A family with a minivan asks to join: take them in, trade for fuel, or drive on.
- retired_couple_motorhome: A retired couple offers their motorhome and company, or a trade.
- church_group_bus: A church group with a city bus wants safety in numbers.
- ambulance_callout: [own an ambulance] Answer a medic call for new survivors.
- ambulance_checkpoint: [own an ambulance] A checkpoint waves the red cross through.
- tow_truck_wreck: [own a Tow/Recovery Truck] Haul a wreck aside and strip it.
BACKGROUND EVENTS (need a "requires" with "background")
- underworld_fence: [Criminal] Buy fuel off the books or call in a favour.
- smugglers_stash: [Criminal] Crack a smugglers' cache quietly or strip it by force.
- toll_gang: [Criminal] Face down a rival crew's toll, pay it, or detour.
AMBUSH EVENTS ("trigger": "ambush"; shown when a road ambush happens, never as ordinary events)
- ambush_raiders: Fight the raiders, floor it, or sacrifice a vehicle as a decoy.
- ambush_swarm: Cut through a zombie swarm, reverse out, or abandon a vehicle as bait.
- highway_ambush: Ram through a barricade, retreat, or sacrifice a vehicle (the big one).
MISSION EVENTS (defined in mission_event_data.py; "trigger": "mission")
- heavy_machinery (Clear the Road), news_van_signal / tv_broadcast (The Last Broadcast),
  ice_cream_jingle / ice_cream_van (A Little Sweetness), distant_calliope / travelling_circus (Strange Music),
  presidential_envoy / presidential_limo / presidential_escort (The Package), tank_depot / armoured_checkpoint (Armoured Convoy).
EVACUATION EVENTS ("trigger": "evacuation"; the final scripted sequence at the Pacific port, played in this order)
- evac_gate: The port gate: pay the garrison, show the ambulance (extra berths), ram the wall, or talk your way in.
- evac_quota: The harbour master's quota: trade supplies, clear the ramp, hand over a vehicle (extra berths) or accept the quota.
- evac_boarding: Loading under fire: hold the gate, lure the horde with fuel, barricade with scrap, or run for the gangway.
SPECIAL SURVIVOR EVENTS (special_event_data.py, weight 0.2 each; every fictional special survivor in
survivor_data.SPECIAL_SURVIVORS is brought by at least one event, built on the plot of their series; the best-known
characters have their own event, the lesser-known ones arrive together with a better-known one or with each other)
- The Walking Dead: special_walking_dead (Rick), special_twd_daryl (Daryl, with his chopper), special_twd_michonne,
  special_twd_carol, special_twd_glenn, special_twd_negan, special_twd_greene_farm (Hershel, Maggie and Carl).
- The Walking Dead (Telltale): special_walking_dead_telltale (Lee and Clementine), special_telltale_kenny (the Russell
  family, with a Station Wagon), special_telltale_motor_inn (Larry, Lilly and Ben).
- The Last of Us: special_last_of_us (Joel and Ellie), special_last_of_us_sarah.
- Resident Evil: special_resident_evil (Claire, with her motorcycle), special_re_leon_ashley, special_re_jill_carlos,
  special_re_chris_rebecca, special_re_ada, special_re_grace (Grace and Sherry).
- Zombieland: special_zombieland (Tallahassee and Columbus, with an SUV), special_zombieland_sisters (Wichita and Little Rock).
- Dead Rising: special_dead_rising (Frank), special_dead_rising_chuck (Chuck, Katey and Nick).
- World War Z: special_world_war_z (Gerry, or the whole Lane family), special_world_war_z_sean.
- Dying Light: special_dying_light (Kyle), special_dying_light_aldemirs (Jade, Rahim, Allen and Amir),
  special_dying_light_brecken_zere (Harris and Imran).
- Warm Bodies: special_warm_bodies (Julie and Romeo), special_warm_bodies_perry_nora (Perry, Nora and the Colonel),
  special_warm_bodies_marcus.
- Others: special_shaun_of_the_dead (Shaun), special_i_am_legend (Robert Neville, and Anna and Ethan).
- Not scripted yet: the two real-life entries (donald_trump, elon_musk). special_event_data.uncovered_special_survivors()
  lists whoever has no event, so a test can assert it returns only those two.
VERY RARE VEHICLE EVENTS (weight 0.3)
- rare_intact_vehicle: [spare driver, unowned type] Patch up an intact vehicle and take it, strip it, or leave it.
- rare_stranded_driver: [spare driver, unowned type] A dying driver gives you their vehicle for company and supplies.
- rare_beyond_repair: [2+ vehicles, poor convoy health] Pay to keep the worst vehicle going or abandon it.
- rare_warlord_toll: [3+ vehicles] Hand over a vehicle for supplies, pay in supplies, or run the gauntlet.
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
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Take only the scrap",
                "outcome": "You strip the crate quickly and get back on the road.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -4},
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
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 2,
        "title": "A Stranded Traveller",
        "description": "A weary traveller flags down the convoy. They offer to help, but ask for supplies in return.",
        "choices": [
            {
                "label": "Share food and water",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "The traveller joins the convoy, grateful for the help.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "resource", "resource": "water", "amount": -2},
                    {"type": "survivors", "amount": 1},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Ask them to repair a vehicle",
                "outcome": "They trade a little scrap for a quick repair job.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 1},
                    {"type": "vehicle_repair", "amount": 8},
                    {"type": "horde_gap", "amount": -4},
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
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Force through the wreckage",
                "outcome": "The convoy pushes through the debris and several vehicles take damage. Someone may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 5, "defense": True},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Take a longer detour",
                "outcome": "You avoid the wreckage, but the detour lets the horde close in.",
                "effects": [{"type": "horde_gap", "amount": -8}],
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
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Search the shop",
                "outcome": "The shelves yield a little food and water, but the search takes time.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 2},
                    {"type": "resource", "resource": "water", "amount": 2},
                    {"type": "horde_gap", "amount": -8},
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
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Strip useful parts",
                "outcome": "The crew removes a few reusable parts without searching the cargo.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
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
        "settlement": True,   # Criminal: Untrusted Reputation, the town sometimes will not deal with the convoy
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 2,
        "title": "Survivors in a Small Town",
        "description": "A few residents wave from a boarded-up shop. They have supplies, but are afraid the horde will reach the town soon.",
        "choices": [
            {
                "label": "Bring one person aboard",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "One resident joins the convoy after a quick exchange of supplies.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -1},
                    {"type": "resource", "resource": "water", "amount": -1},
                    {"type": "survivors", "amount": 1},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Trade for supplies",
                "payment": True,
                "outcome": "You trade scrap for the residents' spare food and water.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -1},
                    {"type": "resource", "resource": "food", "amount": 2},
                    {"type": "resource", "resource": "water", "amount": 2},
                    {"type": "horde_gap", "amount": -4},
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
                "payment": True,
                "outcome": "The mechanic uses spare parts to restore some convoy health.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -2},
                    {"type": "vehicle_repair", "amount": 12},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Ask for spare parts only",
                "outcome": "You trade time for a small bundle of reusable scrap.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -4},
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
                "outcome": "The convoy breaks through the cluster, but vehicles are battered in the process. Someone may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 8, "defense": True},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Move quietly around them",
                "outcome": "The convoy avoids the worst of the danger, losing time on a cautious route.",
                "effects": [{"type": "horde_gap", "amount": -8}],
            },
            {
                "label": "Use supplies to distract them",
                "payment": True,
                "outcome": "You sacrifice food to draw the zombies away from the road.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "horde_gap", "amount": -4},
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
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Collect scrap from the outbuildings",
                "outcome": "You recover a few useful metal parts from abandoned equipment.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -4},
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
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Reinforce the bridge first",
                "payment": True,
                "outcome": "The crew uses scrap to brace the weakest section before crossing, costing time but reducing the risk.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -2},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Take the river road detour",
                "outcome": "The convoy avoids the bridge, but the rough detour damages the vehicles and costs time.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 4, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
        ],
    },
    {
        "id": "engine_fire",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 2,
        "title": "Engine Fire",
        "description": "Smoke pours from an engine. Flames spread as the horde approaches.",
        "choices": [
            {
                "label": "Stop and fight the fire",
                "payment": True,
                "outcome": "You extinguish the flames, but repairs cost precious supplies and time.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -12},
                    {"type": "resource", "resource": "water", "amount": -6},
                    {"type": "horde_gap", "amount": -10}
                ]
            },
            {
                "label": "Keep driving",
                "outcome": "The fire spreads through the engine compartment. Some survivors may be burned.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 30, "defense": True},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -12}
                ]
            }
        ]
    },
    {
        "id": "contaminated_supplies",
        "weight": 3,
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
                "outcome": "The survivors consume the questionable provisions. One survivor becomes seriously ill and is unable to continue travelling, but the remaining supplies are preserved.",                
                "effects": [
                    {"type": "survivors", "amount": -1},
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "resource", "resource": "food", "amount": -5},
                    {"type": "horde_gap", "amount": -8}
                ]
            }
        ]
    },
    {
        "id": "highway_ambush",
        "trigger": "ambush",
        "weight": 2,
        "title": "Highway Ambush",
        "description": "Hostile scavengers attack from behind wrecked cars as zombies close in.",
        "choices": [
            {
                "label": "Ram through the barricade",
                "outcome": "You escape under fire, smashing vehicles and wasting fuel. Some survivors may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 25, "defense": True},
                    {"type": "resource", "resource": "fuel", "amount": -12},
                    {"type": "injury", "amount": 2, "defense": True},
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
            },
            {
                "label": "Sacrifice a vehicle as a decoy",
                "requires": {"vehicles_at_least": 2},
                "outcome": "The attackers fall on the abandoned wreck while the rest of the convoy slips through.",
                "effects": [
                    {"type": "vehicle_loss"},
                ],
            },
        ]
    },
    {
        "id": "broken_axle",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 3,
        "title": "Broken Axle",
        "description": "A loaded vehicle suffers a catastrophic axle failure on the highway.",
        "choices": [
            {
                "label": "Repair it with scrap",
                "payment": True,
                "outcome": "The improvised repair gets you moving, but supplies are depleted.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -15},
                    {"type": "horde_gap", "amount": -12},
                    {"type": "vehicle_repair", "amount": 10}
                ]
            },
            {
                "label": "Keep moving regardless",
                "outcome": "Metal grinds against the road as the damaged vehicles deteriorate. Someone may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 25, "defense": True},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -10}
                ]
            }
        ]
    },
    {
        "id": "desperate_rescue",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 2,
        "title": "Desperate Rescue",
        "description": "Three survivors are trapped on a car roof surrounded by zombies.",
        "choices": [
            {
                "label": "Rescue them",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "You save three people, but the rescue drains supplies and damages the convoy. Some of the rescued are wounded.",
                "effects": [
                    {"type": "survivors", "amount": 3},
                    {"type": "resource", "resource": "food", "amount": -12},
                    {"type": "resource", "resource": "water", "amount": -12},
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "vehicle_damage_pct", "amount": 20, "defense": True},
                    {"type": "injury", "amount": 2},
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
    {
        "id": "abandoned_medical_clinic",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 4,
        "title": "An Abandoned Medical Clinic",
        "description": "The convoy spots an abandoned medical clinic beside the road. Its doors are partly open, and the shelves may still contain useful supplies. Searching the building could take valuable time.",
        "choices": [
            {
                "label": "Search the storage rooms",
                "outcome": "The crew searches the clinic and discovers some preserved food and bottled water. Anyone injured is treated with the clinic's supplies.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "water", "amount": 3},
                    {"type": "injury", "amount": -2},
                    {"type": "horde_gap", "amount": -8}
                ],
            },
            {
                "label": "Salvage equipment",
                "outcome": "You recover useful metal equipment and spare parts from the abandoned clinic.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -4}
                ],
            },
            {
                "label": "Leave the clinic",
                "outcome": "The convoy decides not to risk spending time inside the building.",
                "effects": [],
            },
        ],
    },
    {
        "id": "stranded_fuel_tanker",
        "weight": 3,
        "title": "A Stranded Fuel Tanker",
        "description": "A damaged fuel tanker sits abandoned on the roadside. Some fuel may remain inside, but the tanker looks unstable and the surrounding area is exposed.",
        "choices": [
            {
                "label": "Recover the remaining fuel",
                "outcome": "The crew carefully transfers some remaining fuel into the convoy's storage tanks.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": 10},
                    {"type": "horde_gap", "amount": -12}
                ],
            },
            {
                "label": "Salvage the tanker",
                "outcome": "You strip away useful metal components and leave the remaining fuel behind.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 4},
                    {"type": "horde_gap", "amount": -4}
                ],
            },
            {
                "label": "Avoid the tanker",
                "outcome": "The convoy keeps its distance from the unstable tanker and continues down the highway.",
                "effects": [],
            },
        ],
    },
    {
        "id": "rainwater_collection",
        "weight": 5,
        "title": "Rainwater Collection",
        "description": "After a night of heavy rain, the convoy discovers several large rainwater collection barrels beside an abandoned property. The water looks usable, but nobody knows how clean it really is.",
        "choices": [
            {
                "label": "Collect and filter the water",
                "outcome": "The crew spends time filtering the collected rainwater before filling the convoy's containers.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": 8},
                    {"type": "horde_gap", "amount": -8}
                ],
            },
            {
                "label": "Collect the water quickly",
                "outcome": "You gather the available water quickly, but the delay allows the horde to get closer.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": 5},
                    {"type": "horde_gap", "amount": -4}
                ],
            },
            {
                "label": "Leave the water behind",
                "outcome": "The crew decides the water is not worth the risk and continues travelling.",
                "effects": [],
            },
        ],
    },
    {
        "id": "family_in_need",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 3,
        "title": "A Family in Need",
        "description": "A family stands beside a broken-down car on the roadside. They have been travelling for days and are running out of supplies. They ask whether the convoy can help them.",
        "choices": [
            {
                "label": "Bring the family aboard",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "The family joins the convoy, grateful for the chance to survive. Your supplies will now need to stretch further.",
                "effects": [
                    {"type": "survivors", "amount": 3},
                    {"type": "resource", "resource": "food", "amount": -6},
                    {"type": "resource", "resource": "water", "amount": -6},
                    {"type": "horde_gap", "amount": -12}
                ],
            },
            {
                "label": "Give them some supplies",
                "payment": True,
                "outcome": "You share some provisions with the family and help them continue their journey.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -3},
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "horde_gap", "amount": -4}
                ],
            },
            {
                "label": "Continue without stopping",
                "outcome": "The convoy continues west, leaving the family behind.",
                "effects": [],
            },
        ],
    },
    {
        "id": "emergency_radio_transmission",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 4,
        "title": "Emergency Radio Transmission",
        "description": "Static crackles through the convoy's radio. A faint voice breaks through, repeating a desperate message asking for help. The signal appears to be coming from somewhere nearby, but its exact location is unclear.",
        "choices": [
            {
                "label": "Follow the signal",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "The convoy follows the transmission and discovers a small group of survivors hiding nearby. They agree to join you, although the detour costs valuable time and supplies.",
                "effects": [
                    {"type": "survivors", "amount": 2},
                    {"type": "resource", "resource": "food", "amount": -4},
                    {"type": "resource", "resource": "water", "amount": -4},
                    {"type": "horde_gap", "amount": -15}
                ],
            },
            {
                "label": "Respond over the radio",
                "outcome": "You respond without leaving the highway. The survivors provide useful information about a nearby supply location before the signal disappears.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -8}
                ],
            },
            {
                "label": "Ignore the transmission",
                "outcome": "The convoy switches off the radio and continues west. Whatever was broadcasting is left behind.",
                "effects": [],
            },
        ],
    },
    {
        "id": "the_bottleneck",
        "weight": 4,
        "title": "The Bottleneck",
        "description": "The convoy approaches a narrow mountain pass littered with abandoned vehicles. The road ahead offers an opportunity to slow the pursuing horde, but the crew will need to make a decision quickly.",
        "choices": [
            {
                "label": "Block the road behind you",
                "payment": True,
                "outcome": "The crew builds a makeshift barricade from abandoned vehicles and debris. The horde slows as it struggles through the obstruction.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -3},
                    {"type": "horde_gap", "amount": 12}
                ],
            },
            {
                "label": "Push the convoy to maximum speed",
                "outcome": "Engines roar as every driver pushes their vehicle to its limits. The convoy gains considerable distance, but burns through precious fuel.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -8},
                    {"type": "horde_gap", "amount": 8}
                ],
            },
            {
                "label": "Take a slow, quiet route",
                "outcome": "The convoy takes a longer, quieter route through the pass. Progress is slow, but the horde gradually falls further behind.",
                "effects": [
                    {"type": "horde_gap", "amount": 2}
                ],
            },
        ],
    },
    {
        "id": "endless_traffic_jam",
        "weight": 3,
        "title": "The Endless Traffic Jam",
        "description": "The convoy rounds a bend and encounters miles of abandoned vehicles packed tightly across the highway. With wreckage blocking every lane, the drivers struggle to find a way through. The noise of engines and crashing metal echoes across the landscape. Somewhere behind you, the horde is getting closer.",
        "choices": [
            {
                "label": "Force your way through",
                "outcome": "The convoy smashes through the gridlocked vehicles. Several vehicles suffer heavy damage, but the convoy makes reasonable progress. Someone may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 25, "defense": True},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -5}
                ],
            },
            {
                "label": "Search for a way around",
                "outcome": "The drivers take a rough alternative route around the traffic jam. The detour takes longer than expected, allowing the horde to close in further.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 10, "defense": True},
                    {"type": "horde_gap", "amount": -15}
                ],
            },
            {
                "label": "Wait for a gap and move carefully",
                "outcome": "The convoy waits too long for a clear passage. By the time everyone gets moving, the horde has closed a frightening amount of distance.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -20}
                ],
            },
        ],
    },
    {
        "id": "running_on_fumes",
        "weight": 6,
        "requires": {"fuel_below": 15},
        "title": "Running on Fumes",
        "description": "Every gauge in the convoy is hovering near empty. Smoke rises from a camp just off the road, and a line of rusting wrecks sits in a lay-by ahead.",
        "choices": [
            {
                "label": "Trade scrap for fuel",
                "payment": True,
                "outcome": "The camp's mechanic weighs your scrap and fills a few cans in return.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -4},
                    {"type": "resource", "resource": "fuel", "amount": 6},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Siphon the wrecks",
                "outcome": "It is slow, dirty work, but the tanks are not all dry.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": 3},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
            {
                "label": "Press on and hope",
                "outcome": "The convoy keeps its lead and its fingers crossed.",
                "effects": [],
            },
        ],
    },
    {
        "id": "dry_wells",
        "weight": 6,
        "requires": {"water_below": 6},
        "title": "Dry Wells",
        "description": "The water cans are nearly empty. A ruined farm ahead has an old hand pump in the yard, seized with rust, and a muddy pond behind the barn.",
        "choices": [
            {
                "label": "Fix the pump",
                "payment": True,
                "outcome": "A few scrap parts later, clean water runs again.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -2},
                    {"type": "resource", "resource": "water", "amount": 8},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Boil pond water",
                "outcome": "It tastes awful, but it is wet and it will not kill anyone.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Move on",
                "outcome": "Nobody wants to spend the time. The convoy rolls on thirsty.",
                "effects": [],
            },
        ],
    },
    {
        "id": "horde_close_call",
        "weight": 5,
        "requires": {"horde_below": 15},
        "title": "Too Close for Comfort",
        "description": "Dust rises on the horizon behind the convoy. The horde is much closer than anyone would like, and the drivers want orders now.",
        "choices": [
            {
                "label": "Drop scrap as a barricade",
                "payment": True,
                "outcome": "Piles of scrap and a dragged-out wreck slow the leading zombies.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -3},
                    {"type": "horde_gap", "amount": 8},
                ],
            },
            {
                "label": "Burn fuel in a flat-out sprint",
                "payment": True,
                "outcome": "Engines scream and the gap widens, along with the fuel bill.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -5},
                    {"type": "horde_gap", "amount": 6},
                ],
            },
            {
                "label": "Fight a rearguard action",
                "outcome": "The rear vehicles hold the road, but they take a beating. Some survivors may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 6, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": 4},
                ],
            },
        ],
    },
    {
        "id": "scrap_trader",
        "weight": 4,
        "requires": {"scrap_at_least": 8},
        "title": "A Roadside Trader",
        "description": "A lone trader with a laden handcart spots the convoy's stacked scrap and waves you down. He wants metal, and he has food, water and fuel to give for it.",
        "choices": [
            {
                "label": "Scrap for food and water",
                "payment": True,
                "outcome": "He counts the scrap twice, then hands over sealed rations and jugs of water.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -6},
                    {"type": "resource", "resource": "food", "amount": 5},
                    {"type": "resource", "resource": "water", "amount": 5},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Scrap for fuel",
                "payment": True,
                "outcome": "Two jerry cans change hands and the trader grins at his bargain.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -4},
                    {"type": "resource", "resource": "fuel", "amount": 5},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Decline politely",
                "outcome": "You keep your scrap and your schedule.",
                "effects": [],
            },
        ],
    },
    {
        "id": "ambulance_callout",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 5,
        "requires": {"vehicle": "Ambulance"},
        "title": "Medics Wanted",
        "description": "The ambulance's old radio crackles with a call for medics. Wounded survivors are sheltering in a collapsed overpass nearby. Without a vehicle that can carry stretchers, nobody else would stop.",
        "choices": [
            {
                "label": "Send the ambulance to treat and collect them",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "The ambulance crew patches up the worst of them and brings two survivors back to the convoy.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "survivors", "amount": 2},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
            {
                "label": "Treat the worst case and leave",
                "requires": {"free_seats_at_least": 1},   # nobody to take aboard with every seat full
                "payment": True,
                "outcome": "One badly hurt traveller is stabilised and climbs aboard. The others wave you on.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -2},
                    {"type": "survivors", "amount": 1},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Keep driving",
                "outcome": "The radio goes quiet behind you. Nobody talks for a while.",
                "effects": [],
            },
        ],
    },
    {
        "id": "ambulance_checkpoint",
        "weight": 3,
        "requires": {"vehicle": "Ambulance"},
        "title": "The Red Cross Checkpoint",
        "description": "A makeshift militia checkpoint blocks the road, but the guards stare at the ambulance at the head of your column. One of them has a cough that sounds bad.",
        "choices": [
            {
                "label": "Treat the guards",
                "payment": True,
                "outcome": "The guards are grateful. They send the convoy off with supplies and salvage from their stockpile.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -2},
                    {"type": "resource", "resource": "food", "amount": 4},
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Show the red cross and drive through",
                "outcome": "The barrier is lifted and the convoy passes without a word.",
                "effects": [
                    {"type": "horde_gap", "amount": 2},
                ],
            },
            {
                "label": "Turn around and take another road",
                "outcome": "You avoid the checkpoint, but the detour costs time.",
                "effects": [
                    {"type": "horde_gap", "amount": -12},
                ],
            },
        ],
    },
    {
        "id": "tow_truck_wreck",
        "weight": 4,
        "requires": {"vehicle": "Tow/Recovery Truck"},
        "title": "A Wreck Worth Hauling",
        "description": "A heavy wreck lies across both lanes, its hull full of salvage. Nobody else could shift it, but the tow truck could.",
        "choices": [
            {
                "label": "Haul it aside and strip it",
                "outcome": "The tow truck drags the wreck clear and the crew strips it of scrap and fuel.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 6},
                    {"type": "resource", "resource": "fuel", "amount": 3},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Tow it just enough to pass",
                "outcome": "A quick pull clears a gap and the convoy squeezes through.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
        ],
    },
    {
        "id": "family_minivan",
        "weight": 0.8,
        "emergency": True,
        "title": "A Family and Their Minivan",
        "description": "A minivan with a cracked windscreen idles on the shoulder, stickers still on the rear window. A father waves the convoy down; his wife and two kids watch from the back seats. They have a full tank of fumes and a map with no safe road marked on it, and they would rather travel with company.",
        "choices": [
            {
                "label": "Welcome the family aboard",
                "payment": True,
                "outcome_no_vehicle": "The family squeezes into the convoy and the father hands over his keys. Their minivan is the same as one you already have, so it stays behind. Four more mouths to feed.",
                "outcome": "The family pulls in behind the column. The minivan adds seats and room for luggage, and four more mouths to feed.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -4},
                    {"type": "resource", "resource": "water", "amount": -4},
                    {"type": "vehicle_gain", "vehicle": "Minivan", "health": 0.8, "crew": 4},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Trade supplies for their spare fuel",
                "payment": True,
                "outcome": "They hand over two jerry cans and keep the minivan. The father thanks you and turns the family south.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -2},
                    {"type": "resource", "resource": "fuel", "amount": 5},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Drive on",
                "outcome": "The minivan's headlights shrink in the mirror.",
                "effects": [],
            },
        ],
    },
    {
        "id": "retired_couple_motorhome",
        "weight": 0.5,
        "title": "The Retirees' Motorhome",
        "description": "A motorhome with a faded 'Grand Tour 2019' decal sits across two lanes. A retired couple sit on folding chairs beside it, a kettle on a camping stove. They have the stove, a freezer full of old stock and no plans except 'west'.",
        "choices": [
            {
                "label": "Let them join the convoy",
                "payment": True,
                "outcome_no_vehicle": "The couple leave their motorhome with its twin in the convoy and climb aboard with their kettle and a freezer bag of food. There is no room for the freezer itself.",
                "outcome": "They lock up the motorhome and pull in at the back. It is slow and a bit roomy, but it has beds and a working freezer.",
                "effects": [
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "vehicle_gain", "vehicle": "Motorhome", "health": 0.7, "crew": 2},
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Raid their freezer and move on",
                "outcome": "They hand over what they can spare, grumbling about the rudeness of the young.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 4},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Wave and keep driving",
                "outcome": "The kettle was still whistling when the road bent out of sight.",
                "effects": [],
            },
        ],
    },
    {
        "id": "church_group_bus",
        "weight": 0.4,
        "title": "A Bus Full of Hymns",
        "description": "A city bus is parked in a church lot, painted over in prayer slogans. A deacon steps out and says his congregation has driven for nine days on faith and one tank of diesel. They would like to travel with the convoy, if the convoy will have them.",
        "choices": [
            {
                "label": "Take the whole congregation aboard",
                "payment": True,
                "outcome_no_vehicle": "The congregation leaves its bus by the church and files into your column, singing. It is a lot of people, but also a lot of hands.",
                "outcome": "They file back onto the bus singing. It is a lot of people, but it is also a lot of hands, and the deacon knows how to fix an engine.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -8},
                    {"type": "resource", "resource": "water", "amount": -8},
                    {"type": "vehicle_gain", "vehicle": "City Bus", "health": 0.7, "crew": 10},
                    {"type": "horde_gap", "amount": -15},
                ],
            },
            {
                "label": "Share some provisions and send them on",
                "payment": True,
                "outcome": "The deacon blesses the convoy, and the bus rolls off in another direction.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -3},
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Decline politely",
                "outcome": "You tell the deacon there is not enough to go round. He says he understands.",
                "effects": [],
            },
        ],
    },
    {
        "id": "rare_intact_vehicle",
        "weight": 0.3,
        "requires": {"vehicle_slot": True},
        "title": "A Vehicle Left Behind",
        "description": "Beside a collapsed roadblock sits a vehicle that looks almost untouched, keys still in the ignition. Somebody left in a hurry, and a few scrap parts might be all it needs to run.",
        "choices": [
            {
                "label": "Patch it up and add it to the convoy",
                "payment": True,
                "outcome": "The crew spends hours coaxing the engine to life. The convoy has a new vehicle.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -6},
                    {"type": "vehicle_gain", "health": 0.7},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
            {
                "label": "Strip it for scrap",
                "outcome": "You take everything useful and leave the shell behind.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": 5},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Leave it",
                "outcome": "It could be a trap, and there is no driver to spare. The convoy rolls on.",
                "effects": [],
            },
        ],
    },
    {
        "id": "rare_stranded_driver",
        "weight": 0.3,
        "requires": {"vehicle_slot": True},
        "title": "A Driver's Last Gift",
        "description": "A weak, dehydrated driver flags down the convoy beside a vehicle that still runs fine. They cannot go on, and they offer you the keys if somebody will share food and water with them.",
        "choices": [
            {
                "label": "Share supplies and take the keys",
                "payment": True,
                "outcome": "The driver rests, presses the keys into your hand and wishes the convoy luck. You have a new vehicle.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -3},
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "vehicle_gain"},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Wish them luck",
                "outcome": "You cannot spare the supplies. The driver watches the convoy leave.",
                "effects": [],
            },
        ],
    },
    {
        "id": "rare_beyond_repair",
        "weight": 0.3,
        "requires": {"vehicles_at_least": 2, "health_below": 55},
        "title": "Beyond Repair",
        "description": "One vehicle is coughing smoke and shedding parts. The mechanics say it can be saved, but only with a lot of scrap, and only just. Otherwise it is slowing the whole column.",
        "choices": [
            {
                "label": "Spend scrap to keep it running",
                "payment": True,
                "outcome": "The crew rebuilds what they can. It will hold, for now.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -10},
                    {"type": "vehicle_repair", "amount": 25},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Strip it and abandon it",
                "outcome": "The most damaged vehicle is stripped for parts and left on the roadside.",
                "effects": [
                    {"type": "vehicle_loss"},
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
        ],
    },
    {
        "id": "rare_warlord_toll",
        "weight": 0.3,
        "requires": {"vehicles_at_least": 3},
        "title": "The Warlord's Toll",
        "description": "Armed riders block the road. Their leader says the road costs a vehicle, and points at the most battered one in your column. He is offering a share of his stockpile for it, or he will take what he wants.",
        "choices": [
            {
                "label": "Hand over a vehicle",
                "outcome": "The riders drive the vehicle away and leave crates of supplies behind.",
                "effects": [
                    {"type": "vehicle_loss"},
                    {"type": "resource", "resource": "food", "amount": 8},
                    {"type": "resource", "resource": "water", "amount": 8},
                    {"type": "resource", "resource": "scrap", "amount": 6},
                    {"type": "resource", "resource": "fuel", "amount": 6},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Pay in supplies",
                "payment": True,
                "outcome": "He takes food, water and scrap, and lets the column pass.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -6},
                    {"type": "resource", "resource": "water", "amount": -6},
                    {"type": "resource", "resource": "scrap", "amount": -6},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Run the gauntlet",
                "outcome": "Gunfire rakes the column as it speeds past. Every vehicle takes damage, but none are lost. Some survivors may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 12, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
        ],
    },
    {
        "id": "underworld_fence",
        "weight": 2,
        "requires": {"background": "Criminal"},
        "title": "A Friend of a Friend",
        "description": "A man you used to do business with waves the convoy down outside a chop shop that survived the outbreak. He still remembers your name, and he is happy to deal.",
        "choices": [
            {
                "label": "Buy fuel off the books",
                "payment": True,
                "outcome": "No questions asked. His drums of fuel are not clean, but they burn just the same.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -3},
                    {"type": "resource", "resource": "fuel", "amount": 10},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Call in an old favour",
                "outcome": "He grumbles, then loads a few crates into the nearest vehicle. You are even now.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "water", "amount": 3},
                    {"type": "resource", "resource": "scrap", "amount": 2},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Not now",
                "outcome": "You nod to him and keep driving.",
                "effects": [],
            },
        ],
    },
    {
        "id": "smugglers_stash",
        "weight": 1,
        "requires": {"background": "Criminal"},
        "title": "The Smugglers' Cache",
        "description": "You know the signs: a painted tyre, a loose slab behind a gas station. A smuggling crew hid a cache here before the roads closed, and nobody seems to be guarding it.",
        "choices": [
            {
                "label": "Crack it open quietly",
                "outcome": "The lock gives way and the convoy leaves with a decent haul before anyone notices.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": 3},
                    {"type": "resource", "resource": "water", "amount": 3},
                    {"type": "resource", "resource": "scrap", "amount": 3},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Take everything, whatever it costs",
                "outcome": "A watchman opens fire as you strip the place. The haul is big, and some survivors are hurt.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": 8},
                    {"type": "resource", "resource": "scrap", "amount": 8},
                    {"type": "resource", "resource": "food", "amount": 4},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -12},
                ],
            },
            {
                "label": "Leave it",
                "outcome": "Somebody will be back for it. You would rather not be here when they are.",
                "effects": [],
            },
        ],
    },
    {
        "id": "toll_gang",
        "weight": 2,
        "requires": {"background": "Criminal"},
        "title": "Another Crew's Road",
        "description": "A rival crew has parked a flatbed across the road and put up a hand-painted toll sign. They have not noticed who is driving the lead vehicle yet.",
        "choices": [
            {
                "label": "Remind them who you are",
                "outcome": "Word gets around. The flatbed rolls aside, though a warning shot clips the convoy as you pass.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 4, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Pay the toll",
                "payment": True,
                "outcome": "They count the scrap twice and wave you through.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -4},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Take the long way round",
                "outcome": "You would rather not start a war today. The detour costs time.",
                "effects": [
                    {"type": "horde_gap", "amount": -12},
                ],
            },
        ],
    },
    {
        "id": "ambush_raiders",
        "trigger": "ambush",
        "weight": 5,
        "title": "Raiders on the Road",
        "description": "Armed raiders block the road ahead and open fire from behind a pair of wrecks. The convoy has seconds to decide.",
        "choices": [
            {
                "label": "Fight them off",
                "outcome": "The convoy fights its way through. Defense soaks up part of the damage, people are hurt, and the raiders' stash is yours.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 15, "defense": True},
                    {"type": "survivors", "amount": -2, "defense": True},
                    {"type": "resource", "resource": "scrap", "amount": 4},
                    {"type": "injury", "amount": 3, "defense": True},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Floor it",
                "outcome": "The convoy bolts through a hail of bullets, burning fuel and shedding supplies. Some survivors may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 4, "defense": True},
                    {"type": "resource", "resource": "fuel", "amount": -5},
                    {"type": "resource", "resource": "food", "amount": -3},
                    {"type": "resource", "resource": "water", "amount": -3},
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Sacrifice a vehicle as a decoy",
                "requires": {"vehicles_at_least": 2},
                "outcome": "The raiders swarm the abandoned vehicle while the rest of the convoy slips away.",
                "effects": [
                    {"type": "vehicle_loss"},
                ],
            },
        ],
    },
    {
        "id": "ambush_swarm",
        "trigger": "ambush",
        "weight": 4,
        "title": "A Swarm on the Highway",
        "description": "A mass of zombies spills onto the road from a burning pile-up. The noise of the engines draws more every second.",
        "choices": [
            {
                "label": "Cut through them",
                "outcome": "The convoy ploughs through the swarm. Defense keeps the worst off the vehicles, but someone is dragged out of a window. Some survivors may be hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 12, "defense": True},
                    {"type": "survivors", "amount": -1, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -6},
                ],
            },
            {
                "label": "Reverse and find another way",
                "outcome": "The drivers back out and take a long loop around. It costs fuel and time, but nobody is hurt.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -6},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
            {
                "label": "Abandon a vehicle as bait",
                "requires": {"vehicles_at_least": 2},
                "outcome": "The swarm follows the noise of the abandoned vehicle while the rest of the convoy drives away.",
                "effects": [
                    {"type": "vehicle_loss"},
                    {"type": "horde_gap", "amount": 6},
                ],
            },
        ],
    },
    {
        "id": "evac_gate",
        "trigger": "evacuation",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 0,
        "title": "The Port Gate",
        "description": "The Pacific at last. Floodlights burn over a port walled in with shipping containers, and one ship rides at the quay with its engines turning. A militia garrison holds the gate and is turning most convoys away: the ship has room for only so many, and the guards decide who even reaches the dock.",
        "choices": [
            {
                "label": "Pay the garrison's entry toll",
                "payment": True,
                "outcome": "The captain counts the supplies twice, then waves the convoy through onto the quay.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -6},
                    {"type": "resource", "resource": "food", "amount": -4},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Show them the ambulance",
                "requires": {"vehicle": "Ambulance"},
                "outcome": "The garrison's medic recognises the red cross and the wounded are rushed to the front. The harbour master releases three more berths for the convoy.",
                "effects": [
                    {"type": "injury", "amount": -2},
                    {"type": "berths", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Ram through the container wall",
                "outcome": "The convoy smashes through. The guards scatter, but not before the vehicles are battered and some survivors are hurt.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 15, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Talk your way in",
                "outcome": "Hours of arguing at the gate finally earn a pass, and the horde gets hours closer.",
                "effects": [
                    {"type": "horde_gap", "amount": -8},
                ],
            },
        ],
    },
    {
        "id": "evac_quota",
        "trigger": "evacuation",
        "weight": 0,
        "title": "The Harbour Master's Quota",
        "description": "The ship is an old container carrier refitted for passengers, and the harbour master is rationing places with a clipboard. The convoy may have more people than the ship has room for. The quota is not up for debate, unless you can make it worth his while.",
        "choices": [
            {
                "label": "Trade supplies for extra berths",
                "payment": True,
                "outcome": "The harbour master takes the supplies and crosses out a few names on his list. There is room for four more.",
                "effects": [
                    {"type": "resource", "resource": "food", "amount": -6},
                    {"type": "resource", "resource": "water", "amount": -6},
                    {"type": "resource", "resource": "scrap", "amount": -4},
                    {"type": "berths", "amount": 4},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Clear the loading ramp of the infected",
                "outcome": "Your crews cut down the infected clogging the lower deck, taking knocks as they go. The harbour master grudgingly finds room for two more.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 8, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "berths", "amount": 2},
                    {"type": "horde_gap", "amount": -8},
                ],
            },
            {
                "label": "Hand over a vehicle",
                "requires": {"vehicles_at_least": 2},
                "outcome": "The harbour master takes the keys to the most battered vehicle and finds room for three more people.",
                "effects": [
                    {"type": "vehicle_loss"},
                    {"type": "berths", "amount": 3},
                    {"type": "horde_gap", "amount": -4},
                ],
            },
            {
                "label": "Accept the quota",
                "outcome": "You take the places you have been given and ask no more.",
                "effects": [],
            },
        ],
    },
    {
        "id": "evac_boarding",
        "trigger": "evacuation",
        "emergency": True,   # Police: Emergency Response cuts its horde-gap time penalties
        "weight": 0,
        "title": "Loading Under Fire",
        "description": "Boarding has barely begun when the sirens start: the horde has found the port. Dust and noise roll in from the east gate while the crew shout for the gangway to be cleared. Whoever is still on the quay when the ropes come off stays on the mainland.",
        "choices": [
            {
                "label": "Hold the gate with the convoy",
                "outcome": "The vehicles form a wall across the gate and take the brunt of it. People are hurt, but the front of the horde is held.",
                "effects": [
                    {"type": "vehicle_damage_pct", "amount": 20, "defense": True},
                    {"type": "injury", "amount": 2, "defense": True},
                    {"type": "horde_gap", "amount": 12},
                ],
            },
            {
                "label": "Burn fuel to lure them away",
                "payment": True,
                "outcome": "A burning fuel dump on the far side of the port draws the horde away from the gangway.",
                "effects": [
                    {"type": "resource", "resource": "fuel", "amount": -10},
                    {"type": "horde_gap", "amount": 15},
                ],
            },
            {
                "label": "Barricade the quay with scrap",
                "payment": True,
                "outcome": "Piles of scrap and dragged-out containers slow the leading zombies.",
                "effects": [
                    {"type": "resource", "resource": "scrap", "amount": -4},
                    {"type": "horde_gap", "amount": 10},
                ],
            },
            {
                "label": "Run for the gangway",
                "outcome": "Everyone sprints for the ship. Some trip, and the horde gains ground.",
                "effects": [
                    {"type": "injury", "amount": 1, "defense": True},
                    {"type": "horde_gap", "amount": -10},
                ],
            },
        ],
    },
]


from .mission_event_data import MISSION_EVENTS   # the dedicated events of the multi-stage missions

EVENTS.extend(MISSION_EVENTS)

from .special_event_data import SPECIAL_EVENTS   # rare events where a special survivor from a fictional series joins

EVENTS.extend(SPECIAL_EVENTS)
