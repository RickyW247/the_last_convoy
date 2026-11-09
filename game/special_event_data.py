"""Rare events where a special survivor from a fictional series joins the convoy (merged into EVENTS by event_data.py).

Dedicated events for the main / best-known characters of each series in survivor_data.SPECIAL_SERIES, each built on that
series' plot; the lesser-known characters travel together with a better-known one or with each other (one shared event
each, so nobody turns up alone and unexplained); the people who join are the special survivors of survivor_data.SPECIAL_SURVIVORS (fixed name, gender and age), added by the
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
from .survivor_data import SPECIAL_SURVIVORS

SPECIAL_WEIGHT = 0.2


def _join_with_vehicle(vehicle, *keys, health=1.0):
    """One effect: `vehicle` arrives with these special survivors (and its own seats). The first adult drives."""
    return [{"type": "vehicle_gain", "vehicle": vehicle, "health": health, "special": list(keys)}]


def _join(*keys):
    return [{"type": "special_survivor", "key": key} for key in keys]


def _res(**amounts):
    """Resource effects from keyword amounts, e.g. _res(food=-1, scrap=3)."""
    return [{"type": "resource", "resource": name, "amount": amount} for name, amount in amounts.items()]


def _injury(amount, defense=None):
    """Positive: wound that many survivors (defense can cut it); negative: treat that many injured survivors."""
    effect = {"type": "injury", "amount": amount}
    if amount > 0 and defense is not False:
        effect["defense"] = True
    return effect


def _horde(amount):
    return {"type": "horde_gap", "amount": amount}


def _paid(effects):
    """True when a choice spends resources (it is a payment: greyed out while the convoy cannot afford it)."""
    return any(e.get("type") == "resource" and e.get("amount", 0) < 0 for e in effects)


def _standard(event_id, title, description, keys, join, reward, leave, emergency=False, also_absent=()):
    """One special survivor event of the usual shape: join / take a reward without them / drive on.

    keys: the special survivors the join choice brings (one seat each, so the event needs that many free seats).
    join, reward: (label, outcome, effects) - the join effects get the special_survivor effects added.
    leave: (label, outcome).
    """
    join_label, join_outcome, join_effects = join
    reward_label, reward_outcome, reward_effects = reward
    event = {
        "id": event_id,
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": len(keys), "special_absent": list(keys) + list(also_absent)},
        "title": title,
        "description": description,
        "choices": [
            {"label": join_label, "outcome": join_outcome, "effects": list(join_effects) + _join(*keys)},
            {"label": reward_label, "outcome": reward_outcome, "effects": list(reward_effects)},
            {"label": leave[0], "outcome": leave[1], "effects": []},
        ],
    }
    if emergency:
        event["emergency"] = True
    for choice in event["choices"][:2]:
        if _paid(choice["effects"]):
            choice["payment"] = True
    return event


SPECIAL_EVENTS = [
    {
        "id": "special_walking_dead",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"free_seats_at_least": 1, "special_absent": ["rick_grimes"]},
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
        "id": "special_telltale_lee",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"free_seats_at_least": 2, "special_absent": ["lee_everett", "clementine"]},
        "title": "The Girl in the Treehouse",
        "description": "A police cruiser lies wrecked against a tree at the edge of a quiet suburban street, its back door hanging open. A man in handcuffs is limping up the driveway of the nearest house, rubbing his wrists, when a walkie-talkie crackles somewhere in the garden. In a treehouse behind the house an eight-year-old girl in a cap shouts down that her parents are away in Savannah and she is not supposed to talk to strangers.",
        "choices": [
            {"label": "Take them both aboard", "payment": True,
             "outcome": "You find the key in the cruiser and free his wrists. He gives his name as Lee Everett and does not mention why he was in the back of it. The girl, Clementine, climbs down from the treehouse with her walkie-talkie and does not leave his side.",
             "effects": [{"type": "resource", "resource": "food", "amount": -2},
                         {"type": "resource", "resource": "water", "amount": -1}] + _join("lee_everett", "clementine")},
            {"label": "Search the wrecked cruiser",
             "outcome": "There is scrap in the trunk, but the officer in the front seat is not as dead as he looked.",
             "effects": [{"type": "resource", "resource": "scrap", "amount": 3},
                         {"type": "injury", "amount": 1, "defense": True},
                         {"type": "horde_gap", "amount": -6}]},
            {"label": "Drive on", "outcome": "The walkie-talkie crackles from the garden behind you until the signal fades.", "effects": []},
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
        "requires": {"special_absent": ["claire_redfield"]},   # the seat is needed only by the choice that takes her without the motorcycle
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
        "requires": {"free_seats_at_least": 1, "special_absent": ["shaun_riley"]},
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
        "requires": {"free_seats_at_least": 1, "special_absent": ["frank_west"]},
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
        "requires": {"special_absent": ["gerry_lane", "karin_lane", "rachel_lane", "constance_lane"]},
        "title": "Gridlock",
        "description": "A family car sits in a gridlocked highway as sirens wail and the first crowds run between the cars. A man is pointing at a map on the dashboard while his wife and two daughters wait in the back. He is a former UN investigator named Gerry Lane, and he thinks he knows where the plague started.",
        "choices": [
            {"label": "Bring the whole Lane family aboard", "payment": True,
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
        "requires": {"free_seats_at_least": 1, "special_absent": ["kyle_crane"]},
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
        "requires": {"special_absent": ["robert_neville", "anna_legend", "ethan_legend"]},
        "title": "Noon Broadcast",
        "description": "Every day at noon an AM radio carries the same message: a man's voice, calm and tired, asking anyone alive to come to the pier. The signal leads to a barricaded house and an army scientist with a dog, hunting for a cure. The cellar door is bolted from the inside.",
        "choices": [
            {"label": "Ask him to join the convoy", "payment": True, "requires": {"free_seats_at_least": 1},
             "outcome": "Robert Neville has not spoken to a living person in a long time. He agrees, on one condition: that you lock the doors before dark. He has blood samples and field medicine, and he treats your wounded.",
             "effects": [{"type": "resource", "resource": "food", "amount": -1},
                         {"type": "injury", "amount": -2}] + _join("robert_neville")},
            {"label": "Take him and the family sheltering in his cellar", "payment": True,
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


# ---------------------------------------------------------------------------------------------------------------
# The rest of the roster: every fictional special survivor not brought by an event above gets one here, so each of
# them has a chance to join. Same shape everywhere: a choice that brings them aboard, a reward without them, drive on.
# ---------------------------------------------------------------------------------------------------------------
SPECIAL_EVENTS += [
    # --- The Walking Dead -------------------------------------------------------------------------------------
    {
        "id": "special_twd_daryl",
        "weight": SPECIAL_WEIGHT,
        "requires": {"special_absent": ["daryl_dixon"]},   # the seat is needed only by the choice that takes him without the chopper
        "title": "The Man With the Crossbow",
        "description": "A rider in a sleeveless vest crouches beside a chopper at the roadside, gutting a deer he just brought down with a crossbow. He studies the convoy without a word, then looks at the empty road behind it as if he were counting what could be following.",
        "choices": [
            {"label": "Offer him a place in the convoy",
             "outcome_no_vehicle": "Daryl Dixon shrugs, slings the crossbow and takes a seat without a word. He can track anything and kill most things quietly, and the deer comes with him.",
             "outcome": "Daryl Dixon wheels the chopper into the column, crossbow across his back. He says almost nothing, but the deer ends up in your supplies.",
             "effects": _res(food=2) + _join_with_vehicle("Motorcycle", "daryl_dixon", health=0.9)},
            {"label": "Trade scrap for his snares and a haunch of venison", "payment": True,
             "outcome": "He sets a few snares along the verge for you and cuts the best of the deer. Then he goes back to his fire.",
             "effects": _res(scrap=-2, food=4)},
            {"label": "Leave him to his deer", "outcome": "The chopper engine starts behind you and fades the other way.", "effects": []},
        ],
    },
    _standard("special_twd_michonne", "The Katana",
              "A woman in a ragged cloak stands on the hood of a wrecked taxi, a katana in her hands and a ring of fallen walkers around her. She has been alone for a long time, and she looks at the convoy like a bad idea she might still agree to.",
              ["michonne_hawthorne"],
              ("Offer her a seat", "Michonne Hawthorne gives her name and nothing else. By evening the walkers near the convoy seem to know to keep their distance from her.", _res(food=-1)),
              ("Let her clear the road ahead", "She cuts a path through the dead and comes back with a bruise and a nod. You learn more about how she fights than about who she is.",
               [_horde(8), _injury(1)]),
              ("Wave and drive on", "She watches the convoy go from the taxi's hood.")),
    _standard("special_twd_carol", "The Quiet Kitchen",
              "A gaunt woman in an apron steps out of a farmhouse with a pan of something warm in one hand and a pistol hidden under the dishcloth in the other. She says she can make a good stew out of whatever there is, and that she has learned the hard way not to be a burden.",
              ["carol_peletier"],
              ("Take her aboard", "Carol Peletier packs her pans and a few jars and climbs in. She is quiet, practical, and not nearly as meek as she looks.", _res(food=-1)),
              ("Share a meal and rest", "The stew is better than anything you have eaten in weeks. The wounded get a night in real beds, and the horde gets closer.",
               _res(water=-1) + [_injury(-2), _horde(-6)]),
              ("Thank her and drive on", "The smell of the stew follows you down the road.")),
    _standard("special_twd_glenn", "The Delivery",
              "A young man in a delivery jacket is hot-wiring a stalled car with a hand-drawn map of the whole district clamped between his teeth. He says he knows every alley, rooftop and back stair of the place, and that he can get in and out of anywhere.",
              ["glenn_rhee"],
              ("Take him aboard", "Glenn Rhee grins, folds the map into his pocket and climbs in. He is quick, cheerful and very good at not being seen.", _res(food=-1)),
              ("Send him ahead to scavenge", "He is back in twenty minutes with arms full of food and parts, and a story about how close it was.",
               _res(scrap=4, food=2) + [_horde(-6), _injury(1)]),
              ("Drive on", "He waves the map at the convoy until the stalled car hides him.")),
    _standard("special_twd_greene_farm", "The Vet's Barn",
              "An older farmer with white hair and a veterinarian's bag waves from the gate of a fenced farm. A young woman with a shotgun stands at his side, and on the porch a boy of thirteen in a sheriff's hat three sizes too big lies pale on a stretcher with a bandaged side. They have been treating strangers for weeks, and they ask if the convoy has room for three.",
              ["hershel_greene", "maggie_greene", "carl_grimes"],
              ("Take all three aboard", "Hershel Greene packs his bag and his Bible. His daughter Maggie, sharp and unsentimental, drives a hard bargain about where the shotgun rides. Carl Grimes tips the big hat from his stretcher, and Hershel patches your wounded before the convoy moves out.",
               _res(food=-3, water=-1) + [_injury(-2)]),
              ("Trade scrap for his medicine", "He opens the barn door on shelves of jars and bandages and tells you to take what you need.",
               _res(scrap=-2) + [_injury(-3)]),
              ("Wish them well", "The gate closes behind you, and you hear a bolt slide home.")),
    {
        "id": "special_twd_negan",
        "weight": SPECIAL_WEIGHT,
        "requires": {"free_seats_at_least": 1, "special_absent": ["negan_smith"]},
        "title": "The Toll",
        "description": "A man in a leather jacket stands alone in the road, a barbed-wire-wrapped bat on his shoulder, and grins like he has already won. He says this is a toll road, then adds, a little too cheerfully, that he is also looking for work.",
        "choices": [
            {"label": "Offer him a place in the convoy",
             "outcome": "Negan Smith loves the offer, and loves himself even more. He is brutal, charming, impossible to ignore and useful in a fight.",
             "effects": _join("negan_smith")},
            {"label": "Pay his toll", "payment": True,
             "outcome": "He counts the scrap twice, tips an imaginary hat and steps out of the road. For the price, he tells you which roads his people have already picked clean.",
             "effects": _res(scrap=-3) + [_horde(6)]},
            {"label": "Back away and find another road",
             "outcome": "He watches you reverse with a wide, disappointed grin, and the bat taps the tarmac in time with your engines until the road bends.",
             "effects": []},
        ],
    },

    # --- The Walking Dead (Telltale) --------------------------------------------------------------------------
    {
        "id": "special_telltale_kenny",
        "weight": SPECIAL_WEIGHT,
        "emergency": True,
        "requires": {"special_absent": ["kenny_russell", "katjaa_russell", "duck_russell"]},
        "title": "Down by the Docks",
        "description": "A man in a ball cap is trying to restart a stalled wagon outside a boarded-up bait shop. His wife, a vet's assistant, is bandaging a hurt dog on the hood, and their ten-year-old son is watching the road. He says they were headed for a boat, and that he will do anything for his family.",
        "choices": [
            {"label": "Take the whole Russell family aboard", "payment": True,
             "outcome_no_vehicle": "Kenny, Katjaa and Duck squeeze into the convoy. Katjaa checks your wounded before anyone has even sat down, and Kenny does not stop talking about the boat.",
             "outcome": "Kenny drives the family wagon into the column with Katjaa beside him and Duck in the back. Katjaa checks your wounded before anyone has sat still.",
             "effects": _res(food=-2, water=-1) + [_injury(-1)]
                        + _join_with_vehicle("Station Wagon", "kenny_russell", "katjaa_russell", "duck_russell", health=0.7)},
            {"label": "Pay Katjaa to patch up your wounded", "payment": True,
             "outcome": "She works quickly and does not ask for much. Kenny watches the road the whole time.",
             "effects": _res(food=-1) + [_injury(-2)]},
            {"label": "Drive on", "outcome": "In the mirror the boy is waving, and then the road bends.", "effects": []},
        ],
    },
    _standard("special_telltale_motor_inn", "The Camper",
              "An angry old man behind the wheel of a camper van is arguing at full volume with his daughter, who is hanging out of the passenger window waving a pistol at nobody in particular. A thin young man in a college jacket sits on the roof rack apologising quietly to the dead for something he did. They are headed somewhere, and they cannot agree where.",
              ["larry_caul", "lilly_caul", "ben_paul"],
              ("Take all three aboard", "Larry Caul grumbles through the whole transfer. Lilly Caul tells him to be quiet, and for the first time in an hour he is. Ben Paul thanks you three times and counts the exits every time he sits down.", _res(food=-3)),
              ("Trade scrap for what is in their cooler", "The camper is full of tinned food and a lot of opinions.",
               _res(scrap=-2, food=4)),
              ("Drive on", "The argument continues down the road behind you, and the young man waves apologetically from the roof.")),

    # --- The Last of Us ---------------------------------------------------------------------------------------
    _standard("special_last_of_us_sarah", "Midnight",
              "A twelve-year-old girl in a rumpled T-shirt stands under a streetlight, holding a cracked wristwatch and calling for her dad. She says he promised he would be back by midnight, and it is long past that now.",
              ["sarah_miller"],
              ("Take her aboard", "Sarah Miller climbs in with the watch ticking in her fist. She does not stop watching the road behind you.", _res(food=-1)),
              ("Search the neighbourhood with her", "You find food and parts, but not her father, and the search draws attention.",
               _res(scrap=2, food=2) + [_horde(-6), _injury(1)]),
              ("Leave her at the streetlight", "She is still calling when the convoy turns the corner.")),

    # --- Resident Evil ----------------------------------------------------------------------------------------
    _standard("special_re_leon_ashley", "The Detail",
              "A young officer in a leather jacket is walking a girl in a school cardigan through a ruined village, one hand on his pistol. She is clinging to his sleeve and flinching at every sound. He says he has to get her to a safe zone and that the village keeps trying to stop him.",
              ["leon_kennedy", "ashley_graham"],
              ("Take them both aboard", "Leon Kennedy accepts with weary relief. Ashley Graham, whose father is more important than he lets on, keeps a hand on his sleeve until she is sure the doors are shut.", _res(food=-2, water=-1)),
              ("Trade scrap for his intel on the road", "He knows which roads are blocked and where the others are going. You pay for it with scrap.",
               _res(scrap=-2) + [_horde(10)]),
              ("Wish them luck", "The girl looks back over her shoulder until the convoy is out of sight."),
              emergency=True),
    _standard("special_re_jill_carlos", "The Last Escape",
              "A woman with a handgun and a set of lockpicks and a mercenary in a bulletproof vest are backing out of a city street, trading shots with something that will not stay down. They shout that a train yard lies to the east and that the city is coming down at dawn.",
              ["jill_valentine", "carlos_oliveira"],
              ("Pull them in", "Jill Valentine and Carlos Oliveira pile in, breathless. Jill reloads. Carlos tells you what he is carrying and where he is carrying it.", _res(food=-2)),
              ("Cover them while they clear the street", "The street is full of supplies and of things that will not stay down. They leave you with plenty, and you leave with wounds.",
               _res(scrap=4, food=2) + [_horde(-8), _injury(2)]),
              ("Drive on", "The shooting fades behind the convoy. You do not look back.")),
    _standard("special_re_chris_rebecca", "Down From the Mountain",
              "A broad-shouldered officer and a very young medic come out of the treeline carrying packs and walking like people who have walked a long way. They say their team's helicopter left without them, and that the younger one can handle a medical kit better than anyone you will meet.",
              ["chris_redfield", "rebecca_chambers"],
              ("Take them both aboard", "Chris Redfield thanks you with a nod. Rebecca Chambers has already started checking your wounded.", _res(food=-1, water=-1) + [_injury(-2)]),
              ("Pay the medic for supplies", "She hands over what she can spare from the pack and tells you what to do with it.",
               _res(food=-1) + [_injury(-3)]),
              ("Drive on", "They watch the convoy go, then turn back toward the trees.")),
    _standard("special_re_ada", "The Woman in Red",
              "A woman in a red dress and a long coat stands on a quiet overpass with a grapple gun and a very good reason for being there. She smiles, says she is not working for anyone you know, and asks to borrow a seat.",
              ["ada_wong"],
              ("Offer her a seat", "Ada Wong takes the seat as if you had been waiting for her. She says the next stop will not be a problem. She does not say for whom.", _res(food=-1)),
              ("Pay her for a map of the next checkpoint", "She draws it from memory, which is more reliable than most of what you have seen.",
               _res(scrap=-2) + [_horde(8)]),
              ("Decline politely", "By the time you check the mirror, the overpass is empty.")),
    _standard("special_re_grace", "The Case Files",
              "A woman in a grey suit and sensible shoes waves from the lobby of a boarded-up hotel, a federal badge in one hand and a satchel of case files in the other. A twelve-year-old girl with a government badge pinned to her coat sits on the luggage beside her, clutching a locket. The woman says she is an analyst, that she is a long way from where she is supposed to be, and that they both need a ride.",
              ["grace_ashcroft", "sherry_birkin"],
              ("Take them both aboard", "Grace Ashcroft sorts the case files on her lap before she even sits down, quiet, thorough and braver than she thinks. Sherry Birkin gives you her name and nothing about where she has been, and does not let you see inside the locket.", _res(food=-2)),
              ("Trade scrap for her case notes", "She flips through the file and shows you where the infection came from, and which roads it travelled.",
               _res(scrap=-2) + [_horde(6)]),
              ("Drive on", "She is still holding the files when the hotel is gone from the mirror.")),

    # --- Zombieland -------------------------------------------------------------------------------------------
    _standard("special_zombieland_sisters", "The Con",
              "Two sisters in matching sunglasses are running a very bad con on an empty highway. The older one fakes an injury in the road while the younger one, about twelve, waits behind a car with a toy sheriff's badge. They say there is a theme park on the coast, and that it is open.",
              ["wichita", "little_rock"],
              ("Take them both aboard", "Wichita and Little Rock climb in as if it were their idea. Wichita watches your supplies and Little Rock watches everything else.", _res(food=-2)),
              ("Call their bluff and take what they stole", "The older sister is furious, and the younger one is delighted. Their stolen supplies are now yours.",
               _res(food=3, scrap=2) + [_injury(1)]),
              ("Drive on", "In the mirror the older sister is lying in the road again, and the younger one is not even looking.")),

    # --- Dead Rising ------------------------------------------------------------------------------------------
    _standard("special_dead_rising_chuck", "The Medicine Run",
              "A man in a battered motocross jacket crouches behind a wrecked car with a small girl in his arms, counting blister packs from a bag. The man says the girl needs medicine every day, and he has run out of places to look for it.",
              ["chuck_greene", "katey_greene"],
              ("Take them both aboard", "Chuck Greene thanks you without wasting words. His daughter Katey, seven, falls asleep before the convoy has gone a mile. Chuck promises he'll do whatever he can to help keep the convoy safe.", _res(food=-2, water=-1)),
              ("Trade food for his scavenged parts", "Chuck reluctantly hands over some of the scrap he has collected, but keeps every blister pack for Katey.",
               _res(food=-1, scrap=2)),
              ("Drive on", "Chuck holds Katey closer and watches the convoy disappear down the road."),
              emergency=True, also_absent=["annie_greene"]),
    _standard("special_dead_rising_3", "The Road Out",
              "A young mechanic stands beside a battered vehicle, arguing with a woman covered in grease and blood. An older man watches the road with a shotgun, while a teenage girl waits nearby. They look exhausted and could use a way out.",
              ["nick_ramos", "rhonda_kreske", "dick_baker", "annie_greene"],
              ("Take all four aboard", "Nick Ramos is relieved to find someone willing to help. Rhonda Kreske immediately starts inspecting the convoy's vehicles, Dick Baker settles in with his shotgun, and Annie Greene keeps mostly to herself.",
               _res(food=-4, water=-2)),
              ("Trade food for their mechanical supplies", "They hand over a collection of useful vehicle parts and eat well for the first time in days.",
               _res(food=-2, scrap=4)),
              ("Drive on", "They watch the convoy disappear down the road."),
              also_absent=["katey_greene"]),

    # --- World War Z ------------------------------------------------------------------------------------------
    _standard("special_world_war_z_sean", "The Satellite Phone",
              "A rangy man with a rolled map under one arm and a satellite phone in the other stands at a roadblock that no longer has anyone to guard it. He says a friend told him to look for a convoy heading west, and that he knows how the swarms move.",
              ["sean_collins"],
              ("Take him aboard", "Sean Collins settles in with the map across his knees. He talks about the swarms like a man who has watched them for a long time.", _res(food=-1)),
              ("Trade scrap for his phone numbers", "Most of them do not answer, but two of them do, and the answers are useful.",
               _res(scrap=-2) + [_horde(8)]),
              ("Drive on", "The phone rings once behind you, and then there is only road.")),

    # --- Dying Light ------------------------------------------------------------------------------------------
    _standard("special_dying_light_aldemirs", "Rooftops",
              "Four people stand on a rooftop beside the road with a coil of rope: a woman who fights like she has to, a charming man who talks like he does not, and two men in patched jackets and fingerless gloves. They say their tower is gone, that the roads are not safe after dark, and that they want out before sunset.",
              ["jade_aldemir", "rahim_aldemir", "allen_camden", "amir_ghoreyshi"],
              ("Take them all aboard", "They climb down the rope in half a minute. Jade looks at the convoy like a place to rest, and Rahim like a place to run. Allen Camden and Amir Ghoreyshi check the sky for the sun and promise to take the night watch.", _res(food=-4)),
              ("Trade scrap for their rooftop route", "They sketch a route that avoids the streets and takes the roofs, and tell you how long it will hold.",
               _res(scrap=-2) + [_horde(9)]),
              ("Drive on", "The rope sways on the empty roof behind you.")),
    _standard("special_dying_light_brecken_zere", "The Tower Radio",
              "Two men with the look of people used to giving orders stand beside a roadblock of overturned cars. One is grey and stern and holds a hand radio. The other has a clipboard, and he asks, politely, whether your convoy is organised.",
              ["harris_brecken", "imran_zere"],
              ("Take them both aboard", "Harris Brecken and Imran Zere take seats with clipped thanks. By evening they are quietly reorganising your night watch.", _res(food=-2)),
              ("Trade scrap for their radio frequencies", "The radio gives you three safe channels and one warning.",
               _res(scrap=-2) + [_horde(8)]),
              ("Drive on", "The radio crackles behind you, and a voice you do not know calls your convoy by name.")),

    # --- Warm Bodies ------------------------------------------------------------------------------------------
    _standard("special_warm_bodies_perry_nora", "Beyond the Wall",
              "Two teenagers in patched jackets sit on top of a concrete wall with a bag of scavenged things between them, arguing about whether they are allowed to be out here. Along the foot of the wall a stern man in a colonel's jacket leads a patrol, and he is plainly looking for them.",
              ["perry_kelvin", "nora_greene", "colonel_grigio"],
              ("Take all three aboard", "Perry Kelvin and Nora Greene agree to come before they can think better of it, jumpy and checking behind them. Colonel Grigio takes the offer as an order, sits very straight and does not intend to start trusting strangers.", _res(food=-3)),
              ("Trade for what is in their bag", "Mostly it is junk, but there is some good scrap and a tin of fruit.",
               _res(food=-1, scrap=3)),
              ("Drive on", "They are still arguing when the wall is gone."),
              emergency=True),
    _standard("special_warm_bodies_marcus", "The Loosened Tie",
              "A man in a rumpled office shirt and a loosened tie shuffles down the road in a straight line, trying to say something that comes out half a word at a time. He is not as slow as he looks, and he is clearly holding on to something.",
              ["marcus_corddry"],
              ("Take him aboard", "Marcus Corddry gets one word out, a thank you, then settles into the seat and watches the road with dull attention.", _res(food=-1)),
              ("Follow his shuffle to a quiet street", "He leads you in a slow, patient line to a street the dead have already left. You find supplies in the houses.",
               _res(scrap=2, food=2) + [_horde(-5)]),
              ("Drive on", "He stands in the middle of the road until he is out of sight.")),
]


def uncovered_special_survivors():
    """Keys of survivor_data.SPECIAL_SURVIVORS that no special event can bring aboard (empty: everyone has a chance).

    The two real-life entries are deliberately without a scripted event (see the note in event_data.py), so they are
    the only ones expected here until one is written.
    """
    covered = set()
    for event in SPECIAL_EVENTS:
        for choice in event.get("choices", []):
            for effect in choice.get("effects", []):
                if effect.get("type") == "special_survivor":
                    covered.add(effect.get("key"))
                covered.update(effect.get("special", []) or [])
    return [key for key in SPECIAL_SURVIVORS if key not in covered]


for _event in SPECIAL_EVENTS:   # locked until "The Long Road Again" is completed (achievement_data "unlocks_events")
    _event["group"] = SPECIAL_EVENTS_GROUP
