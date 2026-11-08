"""Rare events where a special survivor from a fictional series joins the convoy (merged into EVENTS by event_data.py).

One dedicated event per series in survivor_data.SPECIAL_SERIES, each built on that series' plot; the people who join
are the special survivors of survivor_data.SPECIAL_SURVIVORS (fixed name, gender and age), added by the
"special_survivor" effect. The events are drawn like ordinary travel events but with a very low weight
(SPECIAL_WEIGHT; the ordinary weights add up to about 110). Every event:
- "requires" enough free seats for the people it can bring and "special_absent" for them (an event whose join choice
  can bring a vehicle has no seat requirement, so it can still fire on a full convoy) (none of them is in the
  convoy right now; they can come back after they have left or died, like any special survivor);
- may bring a vehicle with them: a "vehicle_gain" effect with "special": [keys] (effect_handler.gain_crewed_vehicle) is
  one bundle, the vehicle with its own seats and its special survivors, so that choice needs neither free seats nor a
  spare driver (the special survivor drives). If the convoy already owns that vehicle type the same choice brings
  just the people (in free seats), with its "outcome_no_vehicle" text, so the event never disappears for that;
- belongs to the group SPECIAL_EVENTS_GROUP, which stays locked until the achievement "The Long Road Again" is completed
  (win a second time; effect_handler.event_unlocked, SANDBOX MODE unlocks it too);
- has a choice that brings them aboard, a choice that takes another reward without them and a choice that costs
  nothing.
"""

from config import SPECIAL_EVENTS_GROUP

SPECIAL_WEIGHT = 0.2


def _join_with_vehicle(vehicle, *keys, health=1.0):
    """One effect: `vehicle` arrives with these special survivors (and its own seats). The first adult drives."""
    return [{"type": "vehicle_gain", "vehicle": vehicle, "health": health, "special": list(keys)}]


def _join(*keys):
    return [{"type": "special_survivor", "key": key} for key in keys]


SPECIAL_EVENTS = [
    {
        "id": "special_walking_dead",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"free_seats_at_least": 1, "special_absent": "rick_grimes"},
        "title": "The Deputy Who Slept Through It",
        "description": "A sheriff's deputy in a hospital gown and borrowed boots staggers out of a gutted county hospital, revolver in hand. A chained door behind him is scrawled with a warning not to open it. He woke from a coma this morning and wants to know where everyone went.",
        "choices": [
            {"label": "Take him aboard", "payment": True,
             "outcome": "He says his name is Rick Grimes. He was shot on duty and slept through the end of the world. He only wants to find his wife and son, and he knows how to use a gun.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -2}] + _join("rick_grimes")},
            {"label": "Search the hospital behind the chained door",
             "outcome": "He warned you. The dead pour out of the basement, but the pharmacy and stockroom were worth it.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": 4},
                         {"type": "resource", "resource": "food", "amount": 3},
                         {"type": "injury", "amount": 2, "defense": True},
                         {"type": "horde_gap", "amount": -8}]},
            {"label": "Drive on", "outcome": "In the mirror he is a small figure in a gown, standing in the road.", "effects": []},
        ],
    },
    {
        "id": "special_walking_dead_telltale",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"free_seats_at_least": 2, "special_absent": ["lee_everett", "clementine"]},
        "title": "The Girl in the Treehouse",
        "description": "A police cruiser lies wrecked off the road, its back door hanging open. A man in handcuffs sits beside it, rubbing his wrists. In a treehouse nearby an eight-year-old girl with a walkie-talkie shouts that her parents are away in Savannah and she is not supposed to talk to strangers.",
        "choices": [
            {"label": "Take them both aboard", "payment": True,
             "outcome": "The man gives his name as Lee Everett and does not mention why he was in the cruiser. The girl, Clementine, climbs down with her walkie-talkie and a cap, and does not leave his side.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -1}] + _join("lee_everett", "clementine")},
            {"label": "Search the wrecked cruiser",
             "outcome": "There is scrap and a first aid kit in the trunk, but the officer in the front seat is not as dead as he looked.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": 3},
                         {"type": "injury", "amount": 1, "defense": True},
                         {"type": "horde_gap", "amount": -6}]},
            {"label": "Drive on", "outcome": "The walkie-talkie crackles behind you until the signal fades.", "effects": []},
        ],
    },
    {
        "id": "special_last_of_us",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"free_seats_at_least": 2, "special_absent": ["joel_miller", "ellie_williams"]},
        "title": "The Cargo",
        "description": "A hard-faced smuggler and a fourteen-year-old girl are walking west along the highway. She has a bite scar that never turned her. He says a militia called the Fireflies is waiting at the end of the road, and that he is bad at lying.",
        "choices": [
            {"label": "Offer them a ride west", "payment": True,
             "outcome": "Joel Miller agrees, grudgingly, with one hand on his rifle. Ellie wants to know what the ocean looks like. Neither of them is going to be easy to protect or to leave behind.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -2}] + _join("joel_miller", "ellie_williams")},
            {"label": "Trade supplies for his route knowledge", "payment": True,
             "outcome": "He sketches the safe stretches and the nests to avoid, then they walk on, together.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "horde_gap", "amount": 10}]},
            {"label": "Tell them to keep walking", "outcome": "The girl looks back at the convoy until it is out of sight.", "effects": []},
        ],
    },
    {
        "id": "special_resident_evil",
        "weight": SPECIAL_WEIGHT,
        "requires": {"special_absent": "claire_redfield"},   # the seat is needed only by the choice that takes her without the motorcycle
        "title": "Looking for Chris",
        "description": "A young woman in a red jacket stands beside a motorcycle at an abandoned toll booth. Her brother Chris is a police special-forces officer who stopped answering her calls, and she is riding straight for the city that went dark behind the barricades.",
        "choices": [
            {"label": "Talk her out of it and take her with you", "payment": True,
             "outcome_no_vehicle": "Claire Redfield looks at the smoke on the horizon, then at the convoy. She still wants her brother, but she will not find him alone. She climbs aboard with a pistol and a stubborn jaw.",
             "outcome": "Claire Redfield looks at the smoke, then at the convoy, and wheels the motorcycle into the column and falls in behind the last vehicle. She still wants her brother, but it is easier to look for him with a convoy at her back.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1}]
                        + _join_with_vehicle("Motorcycle", "claire_redfield", health=0.9)},
            {"label": "Trade scrap for her hand-drawn map of the roadblocks", "payment": True,
             "outcome": "The map shows where the dead are thickest and which roads are still open. She rides on toward the city anyway.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": -2},
                         {"type": "horde_gap", "amount": 8}]},
            {"label": "Wish her luck", "outcome": "The motorcycle pulls away toward the smoke.", "effects": []},
        ],
    },
    {
        "id": "special_shaun_of_the_dead",
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": 1, "special_absent": "shaun_riley"},
        "title": "A Nice Cold Pint",
        "description": "A man in a rumpled shirt waves from the door of a boarded-up pub, a cricket bat on his shoulder. He has a plan: collect his mum, pick up his girlfriend, go to the pub, have a nice cold pint, and wait for all this to blow over.",
        "choices": [
            {"label": "Offer him a lift",
             "outcome": "Shaun Riley agrees to leave the pub only after a short, awkward argument with himself. He brings the bat, three records and no plan at all.",
             "effects": _join("shaun_riley")},
            {"label": "Stay for a pint", "payment": True,
             "outcome": "The convoy rests, the wounded get a seat and a bandage, and the horde gets closer.",
             "effects": [{"type": "resource", "resource": "water", "amount": -1},
                         {"type": "injury", "amount": -2},
                         {"type": "horde_gap", "amount": -10}]},
            {"label": "Drive on", "outcome": "Through the pub window you see someone raise a glass.", "effects": []},
        ],
    },
    {
        "id": "special_zombieland",
        "weight": SPECIAL_WEIGHT,
        "requires": {"special_absent": ["tallahassee", "columbus"]},
        "title": "The Last Snack Cake",
        "description": "A man in a cowboy hat is tearing through a roadside supermarket in search of the last snack cake on Earth, while a nervous kid shouts survival rules from the doorway. They say there is an amusement park on the Pacific coast, and they are headed there too.",
        "choices": [
            {"label": "Share food and offer them a ride", "payment": True,
             "outcome_no_vehicle": "Tallahassee takes the front seat and the food. Columbus recites the rules out loud, starting with cardio. The convoy suddenly has a lot more noise and a lot more firepower.",
             "outcome": "Tallahassee insists on driving. They have a dented SUV in the car park with a trunk full of weapons and snack-cake wrappers. Columbus rides shotgun, reciting the rules.",
             "effects": [{"type": "resource", "resource": "food", "amount": -3}]
                        + _join_with_vehicle("Utility SUV", "tallahassee", "columbus", health=0.8)},
            {"label": "Help them ransack the supermarket",
             "outcome": "You find the snack cake, plus plenty of ordinary food, but the dead heard the commotion.",
             "effects": [{"type": "resource", "resource": "food", "amount": 4},
                         {"type": "injury", "amount": 1, "defense": True},
                         {"type": "horde_gap", "amount": -8}]},
            {"label": "Move on", "outcome": "Behind you, a very happy man holds up a small packet.", "effects": []},
        ],
    },
    {
        "id": "special_dead_rising",
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": 1, "special_absent": "frank_west"},
        "title": "Seventy-Two Hours",
        "description": "A photojournalist with a heavy camera waves a flare from the roof of a looted shopping mall. His helicopter will not be back for three days, and he refuses to leave without the biggest story of his career: what really happened behind the quarantine line.",
        "choices": [
            {"label": "Pick him up", "payment": True,
             "outcome": "Frank West slings his camera, climbs down a fire escape and takes the seat as if it were his. He has an eye for a story and a talent for turning anything into a weapon.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1}] + _join("frank_west")},
            {"label": "Raid the mall with him",
             "outcome": "The mall is full of food, tools and the dead. You get out with plenty, but not unhurt.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": 5},
                         {"type": "resource", "resource": "food", "amount": 4},
                         {"type": "injury", "amount": 2, "defense": True},
                         {"type": "horde_gap", "amount": -10}]},
            {"label": "Leave him to his story", "outcome": "The flare burns out on the roof behind you.", "effects": []},
        ],
    },
    {
        "id": "special_world_war_z",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"special_absent": "gerry_lane"},
        "title": "Gridlock",
        "description": "A family car sits in a gridlocked highway as sirens wail and the first crowds run between the cars. A man is pointing at a map on the dashboard while his wife and two daughters wait in the back. He is a former UN investigator named Gerry Lane, and he thinks he knows where the plague started.",
        "choices": [
            {"label": "Bring the whole Lane family aboard", "payment": True,
             "requires": {"special_absent": ["karin_lane", "rachel_lane", "constance_lane"]},
             "outcome_no_vehicle": "Gerry, Karin, Rachel and Constance squeeze into the convoy. Gerry tells you how swarms move and when they tire, and does not let his family out of his sight.",
             "outcome": "Gerry drives out of the gridlock through a gap you make for him, with Karin and the girls in the back. The family wagon falls in behind the convoy. Gerry says it is the first time in days nobody is looking over their shoulder.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -2},
                         {"type": "horde_gap", "amount": 10}]
                        + _join_with_vehicle("Station Wagon", "gerry_lane", "karin_lane", "rachel_lane",
                                             "constance_lane", health=0.8)},
            {"label": "Take only Gerry; his family is evacuated by air", "requires": {"free_seats_at_least": 1},
             "outcome": "Gerry kisses his family goodbye as the helicopter lifts off, then takes the seat. He has a plague to trace and no time to waste.",
             "effects": [{"type": "horde_gap", "amount": 10}] + _join("gerry_lane")},
            {"label": "Drive on", "outcome": "Behind you the traffic jam dissolves into screaming.", "effects": []},
        ],
    },
    {
        "id": "special_dying_light",
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": 1, "special_absent": "kyle_crane"},
        "title": "The Night Is Coming",
        "description": "A man in a parachute harness picks his way out of the ruins of a quarantined city with a satchel of vials. He is an agent sent in undercover, and he warns that the infected become far faster and deadlier after dark. The vials hold the infection back.",
        "choices": [
            {"label": "Take him aboard", "payment": True,
             "outcome": "Kyle Crane treats the wounded with his vials and promises to hold the line after dark. He is not telling the whole story, but he is a good man to have around.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1},
                         {"type": "injury", "amount": -2}] + _join("kyle_crane")},
            {"label": "Trade scrap for a few vials", "payment": True,
             "outcome": "He hands over what he can spare and tells you to be somewhere safe before sunset. Then he goes back into the ruins.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": -3},
                         {"type": "injury", "amount": -3}]},
            {"label": "Drive on", "outcome": "The sun is already sinking behind the ruins.", "effects": []},
        ],
    },
    {
        "id": "special_warm_bodies",
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": 2, "special_absent": ["julie_grigio", "romeo_grigio"]},
        "title": "He Remembers",
        "description": "A teenage girl with a pistol stands between the convoy and a shambling grey figure carrying a suitcase of records. She shouts not to shoot: he is different, he remembers who he was, and he is trying to protect her.",
        "choices": [
            {"label": "Take them both aboard", "payment": True,
             "outcome": "Julie climbs in, and Romeo shuffles after her, silent and clutching his records. Some survivors do not like it, but he has not bitten anyone yet.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1}] + _join("julie_grigio", "romeo_grigio")},
            {"label": "Take only the girl",
             "outcome": "Julie refuses to leave him at first. In the end she climbs in, watching him shamble after the convoy until he is out of sight.",
             "effects": _join("julie_grigio")},
            {"label": "Drive on", "outcome": "She lowers the pistol. In the mirror the grey figure raises one hand.", "effects": []},
        ],
    },
    {
        "id": "special_i_am_legend",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"special_absent": "robert_neville"},
        "title": "Noon Broadcast",
        "description": "Every day at noon an AM radio carries the same message: a man's voice, calm and tired, asking anyone alive to come to the pier. The signal leads to a barricaded house and a lone army scientist with a dog, hunting for a cure.",
        "choices": [
            {"label": "Ask him to join the convoy", "payment": True, "requires": {"free_seats_at_least": 1},
             "outcome": "Robert Neville has not spoken to a living person in a long time. He agrees, on one condition: that you lock the doors before dark. He has blood samples and field medicine, and he treats your wounded.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1},
                         {"type": "injury", "amount": -2}] + _join("robert_neville")},
            {"label": "Take him and the family sheltering in his cellar", "payment": True,
             "requires": {"special_absent": ["anna_legend", "ethan_legend"]},
             "outcome_no_vehicle": "Anna and her son Ethan come up out of the cellar. They say a colony exists to the north, where survivors are safe. Robert treats your wounded before the convoy moves out.",
             "outcome": "Neville loads the SUV with sample cases and a dog bed, Anna and Ethan climb in behind him, and the vehicle falls in at the back of the column. He treats your wounded before the convoy moves on.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -2},
                         {"type": "injury", "amount": -2}]
                        + _join_with_vehicle("Civilian SUV", "robert_neville", "anna_legend", "ethan_legend",
                                             health=0.9)},
            {"label": "Let him treat your wounded and move on",
             "outcome": "He works fast, hands steady, and refuses to leave the city that is his lab.",
             "effects": [{"type": "injury", "amount": -2},
                         {"type": "horde_gap", "amount": -6}]},
        ],
    },
]


for _event in SPECIAL_EVENTS:   # locked until "The Long Road Again" is completed (achievement_data "unlocks_events")
    _event["group"] = SPECIAL_EVENTS_GROUP
