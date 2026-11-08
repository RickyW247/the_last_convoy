"""Reusable, validated effect application for travel events, and the cost rules of event choices (what a choice
spends, what the convoy is short of, which choices can be picked)."""

import math
import random
from operator import ge, lt

from background_data import BACKGROUNDS
from vehicle_data import VEHICLE_SPECS
from .survivor_data import SPECIAL_SURVIVORS
from .survivor_generator import MIN_SURVIVOR_AGE
from .vehicle import Vehicle

RESOURCE_FIELDS = {"fuel", "food", "water", "scrap"}
# Stats a "requires" condition can test (see requirements_met).
REQUIREMENT_STATS = {"fuel", "food", "water", "scrap", "survivors", "horde", "health", "vehicles", "free_seats"}
# Vehicle attributes that may hold a vehicle's type name (the keys of vehicle_data.VEHICLE_SPECS); first string found counts.
VEHICLE_NAME_ATTRS = ("vehicle_type", "name")


def resource_costs(choice):
    """What a choice spends: {resource: units}, the sum of its negative resource effects (fuel, food, water, scrap).
    Empty when the choice costs nothing."""
    costs = {}
    for effect in choice.get("effects", []) or []:
        if effect.get("type") != "resource" or effect.get("resource") not in RESOURCE_FIELDS:
            continue
        amount = int(effect.get("amount", 0))
        if amount < 0:
            field = effect["resource"]
            costs[field] = costs.get(field, 0) - amount
    return costs


def is_payment(choice):
    """True for a choice that is a service the player pays for (repair, rescue, trade): it needs its full cost.
    Every other choice is a penalty that simply takes what the convoy has (never below 0)."""
    return bool(choice.get("payment"))


def shortfalls(game, choice):
    """[(resource, needed, have)] for every resource the convoy cannot pay a PAYMENT choice's cost in (empty:
    affordable). A penalty choice is never short: it takes whatever is available."""
    if not is_payment(choice):
        return []
    return [(field, need, getattr(game, field, 0)) for field, need in resource_costs(choice).items()
            if getattr(game, field, 0) < need]


def _stat(game, name):
    if name == "health":
        return game.convoy_health_pct()
    if name == "vehicles":
        return len(game.vehicles)
    if name == "free_seats":
        return free_seats(game)
    return getattr(game, name, 0)          # fuel, food, water, scrap, survivors, horde (the gap in km)


def free_seats(game):
    """Passenger seats not taken by a survivor yet (what a rescue can still fit)."""
    return max(0, game.convoy_stats().get("passengers", 0) - game.survivors)


def owned_vehicle_names(game):
    """Lower-case type names of the vehicles the convoy owns right now (e.g. {"ambulance", "truck"})."""
    names = set()
    for vehicle in getattr(game, "vehicles", None) or []:
        for attr in VEHICLE_NAME_ATTRS:
            value = getattr(vehicle, attr, None)
            if isinstance(value, str):
                names.add(value.strip().lower())
                break
    return names


def special_name(key):
    """Display name of a special survivor key (survivor_data.SPECIAL_SURVIVORS), e.g. "Rick Grimes"."""
    data = SPECIAL_SURVIVORS.get(key)
    return f"{data['first_name']} {data['last_name']}" if data else str(key)


def special_keys_absent(game, keys):
    """True when none of these special survivors is in the convoy right now (SurvivorManager rules: one of each at a
    time; one who left or died can come back)."""
    manager = getattr(game, "survivor_manager", None)
    if manager is None:
        return False
    return set(keys) <= set(manager.get_available_special_keys())


def recruit_special(game, key):
    """Bring the special survivor `key` into the convoy. Returns a short note ("" when nothing happened).
    The ordinary recruit path does the seats, vehicle assignment and mission credit (Game.recruit_survivors); the new
    record is then turned into the special survivor (SurvivorManager.convert_to_special: fixed name, gender and age
    from survivor_generator.generate_special_survivor), so the survivor count and the records stay in step, and the
    survivor is removable like anybody else. Needs one free seat."""
    manager = getattr(game, "survivor_manager", None)
    if manager is None or key not in SPECIAL_SURVIVORS or key not in manager.get_available_special_keys():
        return ""
    name = special_name(key)
    if free_seats(game) < 1:
        return f"No seat free for {name}"
    before = {survivor["id"] for survivor in manager.survivors}
    if not game.recruit_survivors(1):
        return f"{name} could not join"
    fresh = [survivor for survivor in manager.survivors if survivor["id"] not in before]
    if not fresh or manager.convert_to_special(fresh[0]["id"], key) is None:
        return ""   # an ordinary survivor joined instead
    game.assign_survivors_to_vehicles()   # a child cannot drive: drivers and seats are re-checked
    return f"{name} joined the convoy"


def requirements_met(game, requires):
    """True when the convoy is in the situation a "requires" dict asks for (empty / missing: always true).
    Every entry must hold. Entries:
      "<stat>_below": N      stat < N        "<stat>_at_least": N   stat >= N
          stat is one of fuel, food, water, scrap, survivors, horde (gap in km), health (convoy %), vehicles (count),
          free_seats (passenger seats nobody sits in: "free_seats_at_least": 1 on a choice that takes people aboard)
      "vehicle": "Ambulance" or ["Ambulance", "School Bus"]    the convoy owns at least one of these vehicle types
      "vehicle_absent": "Minivan" or ["Minivan", "Sedan"]   the convoy owns none of these vehicle types (a vehicle that
                             arrives WITH its own driver and crew, vehicle_gain "crew" / "special", can hide an
                             event that is only about the vehicle; a crewed gain of a type already owned simply
                             brings its people without it, so events usually do not need this)
      "vehicle_slot": True   the convoy could take another vehicle: an adult left over to drive it and a vehicle type
                             it does not own yet (the game allows one vehicle of each type)
      "background": "Criminal" or ["Military", "Police"]   the player's background is one of these (background_data.py)
      "special_absent": "rick_grimes" or ["joel_miller", "ellie_williams"]   none of these special survivors (keys of
                             survivor_data.SPECIAL_SURVIVORS) is in the convoy right now
    An unknown key is never met, so a typo hides the event instead of crashing the game."""
    for key, value in (requires or {}).items():
        if key == "vehicle_slot":
            if bool(value) != can_take_vehicle(game):
                return False
            continue
        if key == "vehicle_absent":
            unwanted = [value] if isinstance(value, str) else list(value)
            owned = owned_vehicle_names(game)
            if any(name.strip().lower() in owned for name in unwanted):
                return False
            continue
        if key == "background":
            if not game.is_background(value):
                return False
            continue
        if key == "special_absent":
            if not special_keys_absent(game, [value] if isinstance(value, str) else list(value)):
                return False
            continue
        if key == "vehicle":
            wanted = [value] if isinstance(value, str) else list(value)
            owned = owned_vehicle_names(game)
            if not any(name.strip().lower() in owned for name in wanted):
                return False
            continue
        for suffix, compare in (("_below", lt), ("_at_least", ge)):
            if key.endswith(suffix):
                stat = key[:-len(suffix)]
                if stat not in REQUIREMENT_STATS or not compare(_stat(game, stat), value):
                    return False
                break
        else:
            return False
    return True


def choice_available(game, choice):
    """A choice can be picked when its own "requires" holds (e.g. an option that needs a tow truck) and the convoy
    can pay for it if it is a payment."""
    return requirements_met(game, choice.get("requires")) and not shortfalls(game, choice) and not no_seat_for_fallback(game, choice)


def event_unlocked(game, event):
    """False for an event of a locked group (event["group"], unlocked by an achievement's "unlocks_events", e.g. the
    special survivor events by "The Long Road Again"). Events without a group are always unlocked, and SANDBOX MODE
    unlocks every group (like it lists every bonus vehicle)."""
    group = event.get("group")
    if not group or getattr(game, "sandbox", False):
        return True
    tracker = getattr(game, "achievements", None)
    return tracker is not None and group in tracker.unlocked_event_groups()


def event_available(game, event):
    """Can this event fire now? It must be unlocked (event_unlocked), its "requires" must hold AND at least one choice
    must be pickable: an event whose options the convoy can pay for none of is never shown."""
    if not event_unlocked(game, event) or not requirements_met(game, event.get("requires")):
        return False
    return any(choice_available(game, choice) for choice in event.get("choices", []))


def affordable_flags(game, choices):
    """One bool per choice: can it be picked (requirements met, cost payable)? If none can, every choice stays open (a
    player must never be stuck in an event), so the result is never all False. EventManager only opens events that
    pass event_available, so this is a safety net."""
    flags = [choice_available(game, choice) for choice in choices]
    return flags if any(flags) else [True] * len(choices)


def _vehicle_label(vehicle):
    return getattr(vehicle, "vehicle_type", None) or getattr(vehicle, "name", "vehicle")


def unowned_vehicle_types(game):
    """Vehicle types (vehicle_data.VEHICLE_SPECS keys) the convoy does not own yet: the game allows one of each."""
    owned = {v.vehicle_type for v in game.vehicles}
    return [name for name in VEHICLE_SPECS if name not in owned]


def has_spare_driver(game):
    """True when an adult is left over to drive one more vehicle (every vehicle needs its own adult driver)."""
    return game.adult_count() > len(game.vehicles)


def can_take_vehicle(game):
    """Same rules as Game.recover_vehicle: an adult spare to drive it, and a type not owned yet."""
    return has_spare_driver(game) and bool(unowned_vehicle_types(game))


def _add_vehicle(game, kind, health):
    """Put a new vehicle of the exact type `kind` into the convoy at `health` (a share of its maximum)."""
    vehicle = Vehicle(kind)
    vehicle.health = max(1, int(vehicle.stats["health"] * min(1.0, max(0.0, health))))
    game.vehicles.append(vehicle)
    game.vehicles_gained = getattr(game, "vehicles_gained", 0) + 1   # for the ending screen's "vehicles lost"
    return vehicle


def gain_vehicle(game, kind=None, health=1.0):
    """Add a vehicle: the named type (any capitalisation) or a random type the convoy lacks, at `health` (a share of
    its maximum; recovered vehicles come at 0.7). Returns the new vehicle, or None when the convoy cannot take it (no
    spare adult driver, type already owned or unknown); nothing changes then."""
    if not has_spare_driver(game):
        return None
    free = unowned_vehicle_types(game)
    if kind:
        kind = next((name for name in free if name.lower() == str(kind).strip().lower()), None)
    elif free:
        kind = random.choice(free)
    if kind is None:
        return None
    return _add_vehicle(game, kind, health)


def crew_of(effect):
    """(people, special_keys) a vehicle_gain effect brings with it: "crew" ordinary people (two or more arrive as a
    family) and the special survivors listed under "special". (0, []) for a plain vehicle_gain."""
    return max(0, int(effect.get("crew", 0) or 0)), list(effect.get("special") or [])


def crewed_vehicle_type(game, effect):
    """The exact vehicle type name a CREWED vehicle_gain (one with "crew" and / or "special") would add right now, or
    None when the effect is not a crewed gain or the convoy already owns that type (the effect then does nothing)."""
    if effect.get("type") != "vehicle_gain":
        return None
    crew, special = crew_of(effect)
    if crew + len(special) <= 0:
        return None
    wanted = str(effect.get("vehicle") or "").strip().lower()
    return next((name for name in unowned_vehicle_types(game) if name.lower() == wanted), None)


def without_vehicle(effect):
    """The plain effects a crewed vehicle_gain turns into when its vehicle is not added (the convoy owns that type
    already): the same people join, but in the convoy's own seats."""
    crew, special = crew_of(effect)
    return ([{"type": "survivors", "amount": crew}] if crew > 0 else []) + \
           [{"type": "special_survivor", "key": key} for key in special]


def vehicle_fallback(game, choice):
    """True when a choice has a crewed vehicle_gain whose vehicle the convoy owns already, so those people join
    without it (a choice may then give "outcome_no_vehicle" for its text)."""
    return any(effect.get("type") == "vehicle_gain" and crew_of(effect) != (0, []) and crewed_vehicle_type(game, effect) is None
               for effect in choice.get("effects", []) or [])


def no_seat_for_fallback(game, choice):
    """True when a choice's crewed vehicle would not come (the convoy owns that type already) so its people would need
    seats of their own, and there is not a single free seat: the choice is locked instead of doing nothing."""
    return vehicle_fallback(game, choice) and free_seats(game) < 1


def gain_crewed_vehicle(game, kind, health, crew, special):
    """A vehicle that arrives WITH its people (a family and their minivan, a special survivor on a motorcycle): no spare
    driver is needed, because the crew brings one. The vehicle is added first so its own seats take the crew; then the
    crew joins through Game.recruit_survivors (so seats, the family record and rescue-mission credit work as for any
    rescue) and the special survivors through recruit_special, adults first so the vehicle never stands without a
    driver. Returns (vehicle or None, [notes]); None (nothing changes) when the type is owned already or unknown."""
    kind = crewed_vehicle_type(game, {"type": "vehicle_gain", "vehicle": kind, "crew": crew, "special": special})
    if kind is None:
        return None, []
    vehicle = _add_vehicle(game, kind, health)
    notes = []
    joined = game.recruit_survivors(crew) if crew > 0 else 0
    if joined:
        notes.append(f"Survivors +{joined}")
    for key in sorted(special, key=lambda k: -SPECIAL_SURVIVORS.get(k, {}).get("age", 0)):
        note = recruit_special(game, key)
        if note:
            notes.append(note)
    game.assign_survivors_to_vehicles()   # drivers and seats; drops the vehicle again only if nobody arrived to drive it
    return vehicle, notes


def vehicle_to_lose(game):
    """The vehicle a vehicle_loss effect would give up: the most damaged (lowest share of its maximum health), on a tie
    the least valuable. None when there is only one vehicle (the last one is never given up) or no game."""
    if game is None or len(getattr(game, "vehicles", None) or []) < 2:
        return None
    value = getattr(game, "_vehicle_value", lambda v: 0)
    return min(game.vehicles, key=lambda v: (v.health / max(1, v.stats.get("health", v.health)), value(v)))


def lose_vehicle(game):
    """Abandon vehicle_to_lose through Game.abandon_vehicle, which logs it and re-checks drivers, seats and supplies.
    Never the last vehicle. Returns the lost vehicle or None."""
    vehicle = vehicle_to_lose(game)
    if vehicle is None:
        return None
    game.abandon_vehicle(vehicle.vehicle_type)
    return vehicle if vehicle not in game.vehicles else None


def _defended(game, amount, effect):
    """A loss `amount` (>= 0) cut by the convoy's defense when the effect has "defense": True (like an ambush)."""
    if effect.get("defense") and hasattr(game, "defense_reduction"):
        return int(amount * (100 - game.defense_reduction()) / 100 + 0.5)
    return amount


defended_loss = _defended   # public name: the event popup shows the same numbers the effects will apply


def requirement_text(key, value):
    """A short reading of one "requires" entry for a locked choice, e.g. "needs 2+ vehicles"."""
    if key == "vehicle":
        names = [value] if isinstance(value, str) else list(value)
        return "needs " + " or ".join(names)
    if key == "vehicle_slot":
        return "needs a spare driver"
    if key == "vehicle_absent":
        names = [value] if isinstance(value, str) else list(value)
        return "only while you have no " + " or ".join(names)
    if key == "background":
        names = [value] if isinstance(value, str) else list(value)
        return "only for " + " or ".join(names) + " backgrounds"
    if key == "special_absent":
        names = [value] if isinstance(value, str) else list(value)
        return "only while " + " and ".join(special_name(k) for k in names) + " are not aboard"
    if key == "free_seats_at_least":
        return "needs a free seat" if value == 1 else f"needs {value}+ free seats"
    if key.endswith("_at_least"):
        return f"needs {value}+ {key[:-len('_at_least')]}"
    if key.endswith("_below"):
        return f"only if {key[:-len('_below')]} is under {value}"
    return "not available"


def unmet_requirement_notes(game, choice):
    """[text] for every entry of the choice's "requires" the convoy does not meet (empty: nothing is missing)."""
    notes = [requirement_text(key, value) for key, value in (choice.get("requires") or {}).items()
             if not requirements_met(game, {key: value})]
    if no_seat_for_fallback(game, choice):
        notes.append("needs a free seat (you already have their vehicle)")
    return notes


def _people_offered(effect):
    """How many people one effect takes aboard: a "survivors" gain, or one for a "special_survivor"."""
    kind = effect.get("type")
    if kind == "survivors":
        return max(0, int(effect.get("amount", 0)))
    return 1 if kind == "special_survivor" else 0


def fitted_effects(game, choice):
    """(effects, note) to apply for a choice. A choice that takes people aboard (a "survivors" gain) can offer more
    than the free seats hold. Only the people who fit join, and the resource costs are scaled down to match (rounded up)
    instead of charging the full price for a partial rescue. Time and danger (horde gap, damage) are not scaled: the
    stop took as long either way. `note` says what happened (empty when everyone fits or nobody is taken aboard).

    A crewed vehicle_gain whose vehicle type the convoy owns already is turned into plain people first (without_vehicle):
    they join in free seats like any rescue, so an event never has to be hidden because the convoy has the car.

    A CREWED vehicle_gain (a vehicle that arrives with its own people, see gain_crewed_vehicle) brings its own seats, so
    its people always fit: it is moved to the front of the effects (its seats exist before anybody else is taken aboard)
    and the seats it has left over count for the other people the choice takes aboard.

    Untrusted Reputation (the Criminal background, background_rules.py) works the same way: each person who would fit
    only joins with some chance (Game.willing_recruits). The ones who refuse are taken out of the "survivors" effects,
    the costs and the wounds of the rescue (positive "injury" effects) scale down to the people who did join. A crewed
    vehicle is one group: one roll decides for all of it, and when it says no the group drives off with its vehicle."""
    effects = []
    for effect in choice.get("effects", []) or []:
        if effect.get("type") == "vehicle_gain" and crew_of(effect) != (0, []) and crewed_vehicle_type(game, effect) is None:
            effects.extend(without_vehicle(effect))   # the convoy owns that vehicle already: just the people come
        else:
            effects.append(effect)
    willing_for = getattr(game, "willing_recruits", None)
    groups = {}   # index of a crewed vehicle_gain -> (people it brings, seats its vehicle has)
    for index, effect in enumerate(effects):
        kind = crewed_vehicle_type(game, effect)
        if kind is not None:
            crew, special = crew_of(effect)
            groups[index] = (crew + len(special), VEHICLE_SPECS[kind]["passengers"])
    refused_groups = {i for i in groups if willing_for is not None and willing_for(1) < 1}
    taken = [i for i in groups if i not in refused_groups]
    offered_plain = sum(_people_offered(effect) for i, effect in enumerate(effects) if i not in groups)
    if offered_plain <= 0 and not groups:
        return effects, ""
    # The taken groups first (their seats exist before anyone else boards), refused groups dropped, the rest in order.
    kept = [effects[i] for i in taken] + [e for i, e in enumerate(effects) if i not in groups]
    bonus = sum(seats - people for people, seats in (groups[i] for i in taken))   # seats the new vehicles have left
    fits = min(offered_plain, free_seats(game) + bonus)
    joined_plain = fits if willing_for is None or fits <= 0 else willing_for(fits)
    offered = offered_plain + sum(people for people, _ in groups.values())
    joined = joined_plain + sum(groups[i][0] for i in taken)
    if joined >= offered:
        return kept, ""
    refused = joined_plain < fits or bool(refused_groups)   # people said no (as opposed to there being no seat for them)
    ratio = joined / offered
    scaled = []
    room = joined_plain   # how many people the "survivors" effects may still take aboard (only trimmed when someone refused)
    for effect in kept:
        kind, amount = effect.get("type"), int(effect.get("amount", 0))
        if kind == "resource" and amount < 0:
            effect = dict(effect, amount=-math.ceil(-amount * ratio))
        elif refused and kind == "survivors" and amount > 0:
            effect = dict(effect, amount=min(amount, room))
            room -= effect["amount"]
        elif refused and kind == "special_survivor":
            if room < 1:
                continue   # this person said no (Untrusted Reputation): they do not join
            room -= 1
        elif refused and kind == "injury" and amount > 0:
            effect = dict(effect, amount=int(amount * ratio + 0.5))
        scaled.append(effect)
    if refused:
        who = "Nobody" if joined == 0 else f"Only {joined} of {offered}"
        return scaled, f"{who} agreed to join: they do not trust you. The cost was scaled down."
    return scaled, f"Only {joined} of {offered} could fit aboard, so the cost was scaled down."


# ---------------------------------------------------------------------------
# Validation of event data (event_data.EVENTS). apply_effects does int(effect["amount"]) and ignores unknown effect
# types, and requirements_met treats an unknown "requires" key as never met, so a typo in the data would crash a run
# or silently hide / disable an effect. check_events(EVENTS) finds them all at once (test_event_data.py runs it).
# ---------------------------------------------------------------------------
# Effect types that need an integer "amount" (a missing one would silently mean 0).
# Risky choices: a choice with "success_chance" (0-1) is rolled when picked. On success it does its "effects" and
# "outcome"; on failure its "failure_effects" and "failure_outcome" instead (so a payment choice repeats its cost in
# "failure_effects": it is spent either way). "chance_bonus": [{"requires": {...}, "amount": 0.2}, ...] adds to the
# chance for every entry whose requirements the convoy meets. The final chance stays between CHANCE_MIN and CHANCE_MAX.
CHANCE_MIN = 0.05
CHANCE_MAX = 0.95


def success_chance(game, choice):
    """The chance (CHANCE_MIN..CHANCE_MAX) that a risky choice succeeds right now, or None for an ordinary choice."""
    base = choice.get("success_chance")
    if base is None:
        return None
    chance = base + sum(bonus.get("amount", 0) for bonus in choice.get("chance_bonus", []) or []
                        if requirements_met(game, bonus.get("requires")))
    return min(CHANCE_MAX, max(CHANCE_MIN, chance))


def roll_choice(game, choice):
    """(choice to apply, failed). An ordinary choice, or a risky one that succeeds, comes back unchanged; a failed
    risky choice comes back as a copy that carries the failure effects and outcome."""
    chance = success_chance(game, choice)
    if chance is None or random.random() < chance:
        return choice, False
    outcome = choice.get("failure_outcome", "It goes badly wrong.")
    return dict(choice, effects=choice.get("failure_effects", []), outcome=outcome, outcome_no_vehicle=None), True


AMOUNT_EFFECTS = {"resource", "survivors", "injury", "vehicle_damage_pct", "vehicle_damage", "vehicle_repair", "horde_gap", "berths"}
EFFECT_TYPES = AMOUNT_EFFECTS | {"vehicle_gain", "vehicle_loss", "special_survivor"}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_effect(effect):
    """[problem] for one declarative effect dict (empty: it is fine)."""
    if not isinstance(effect, dict):
        return [f"effect is not a dict: {effect!r}"]
    kind = effect.get("type")
    if kind not in EFFECT_TYPES:
        return [f"unknown effect type {kind!r}"]
    problems = []
    if kind in AMOUNT_EFFECTS:
        amount = effect.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool):
            problems.append(f"{kind}: amount must be an integer, got {amount!r}")
    if kind == "resource" and effect.get("resource") not in RESOURCE_FIELDS:
        problems.append(f"resource: unknown resource {effect.get('resource')!r}")
    if kind == "special_survivor" and effect.get("key") not in SPECIAL_SURVIVORS:
        problems.append(f"special_survivor: unknown special survivor key {effect.get('key')!r}")
    if kind == "vehicle_gain":
        known = {name.lower() for name in VEHICLE_SPECS}
        vehicle = effect.get("vehicle")
        if vehicle is not None and (not isinstance(vehicle, str) or vehicle.strip().lower() not in known):
            problems.append(f"vehicle_gain: unknown vehicle {vehicle!r}")
        health = effect.get("health", 1.0)
        if not _is_number(health) or not 0 <= health <= 1:
            problems.append(f"vehicle_gain: health must be a number from 0 to 1, got {health!r}")
        crew, special = effect.get("crew", 0), effect.get("special", [])
        if not isinstance(crew, int) or isinstance(crew, bool) or crew < 0:
            problems.append(f"vehicle_gain: crew must be a whole number >= 0, got {crew!r}")
        elif not isinstance(special, (list, tuple)) or any(key not in SPECIAL_SURVIVORS for key in special):
            problems.append(f"vehicle_gain: special must be a list of special survivor keys, got {special!r}")
        elif crew + len(special) > 0:
            # A crewed vehicle must be named, must seat its crew and must arrive with someone who can drive it.
            specs = {name.lower(): spec for name, spec in VEHICLE_SPECS.items()}
            spec = specs.get(str(vehicle or "").strip().lower())
            if spec is None:
                problems.append("vehicle_gain: crew / special need a named \"vehicle\"")
            elif crew + len(special) > spec["passengers"]:
                problems.append(f"vehicle_gain: {crew + len(special)} people do not fit in a {vehicle} "
                                f"({spec['passengers']} seats)")
            if crew < 1 and not any(SPECIAL_SURVIVORS[key]["age"] >= MIN_SURVIVOR_AGE for key in special):
                problems.append("vehicle_gain: nobody who can drive comes with it (crew >= 1 or an adult in special)")
    return problems


def validate_requires(requires):
    """[problem] for a "requires" dict, using the same keys as requirements_met (empty: fine)."""
    if requires is None:
        return []
    if not isinstance(requires, dict):
        return [f"requires is not a dict: {requires!r}"]
    problems = []
    known_vehicles = {name.lower() for name in VEHICLE_SPECS}
    for key, value in requires.items():
        if key == "vehicle_slot":
            if not isinstance(value, bool):
                problems.append(f"requires vehicle_slot must be True / False, got {value!r}")
        elif key == "vehicle":
            names = [value] if isinstance(value, str) else value
            if not isinstance(names, (list, tuple)) or not names or not all(
                    isinstance(name, str) and name.strip().lower() in known_vehicles for name in names):
                problems.append(f"requires vehicle: unknown vehicle type in {value!r}")
        elif key == "vehicle_absent":
            names = [value] if isinstance(value, str) else value
            if not isinstance(names, (list, tuple)) or not names or not all(
                    isinstance(name, str) and name.strip().lower() in known_vehicles for name in names):
                problems.append(f"requires vehicle_absent: unknown vehicle type in {value!r}")
        elif key == "background":
            names = [value] if isinstance(value, str) else value
            if not isinstance(names, (list, tuple)) or not names or not all(name in BACKGROUNDS for name in names):
                problems.append(f"requires background: unknown background in {value!r}")
        elif key == "special_absent":
            names = [value] if isinstance(value, str) else value
            if not isinstance(names, (list, tuple)) or not names or not all(name in SPECIAL_SURVIVORS for name in names):
                problems.append(f"requires special_absent: unknown special survivor key in {value!r}")
        else:
            suffix = next((s for s in ("_below", "_at_least") if key.endswith(s)), None)
            if suffix is None or key[:-len(suffix)] not in REQUIREMENT_STATS:
                problems.append(f"requires: unknown key {key!r}")
            elif not _is_number(value):
                problems.append(f"requires {key}: value must be a number, got {value!r}")
    return problems


def validate_events(events):
    """[readable problem] for every event in `events` (empty: the data is fine). Checks the event's and each
    choice's "requires" and every effect (type, amount, resource, vehicle name)."""
    problems = []
    for number, event in enumerate(events, start=1):
        name = next((str(event[k]) for k in ("id", "title", "name") if isinstance(event, dict) and k in event), "")
        where = f"event #{number}" + (f" ({name})" if name else "")
        if not isinstance(event, dict):
            problems.append(f"{where}: not a dict")
            continue
        problems += [f"{where}: {p}" for p in validate_requires(event.get("requires"))]
        problems += [f"{where}: {p}" for effect in event.get("effects") or [] for p in validate_effect(effect)]
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices:
            problems.append(f"{where}: needs a non-empty list of choices")
            continue
        for index, choice in enumerate(choices, start=1):
            label = f"{where}, choice {index}"
            if not isinstance(choice, dict):
                problems.append(f"{label}: not a dict")
                continue
            problems += [f"{label}: {p}" for p in validate_requires(choice.get("requires"))]
            problems += [f"{label}: {p}" for effect in choice.get("effects") or [] for p in validate_effect(effect)]
            problems += [f"{label}: failure_effects: {p}"
                         for effect in choice.get("failure_effects") or [] for p in validate_effect(effect)]
            chance = choice.get("success_chance")
            if chance is not None and (not _is_number(chance) or not 0 <= chance <= 1):
                problems.append(f"{label}: success_chance must be a number from 0 to 1, got {chance!r}")
            if chance is None and (choice.get("failure_effects") or choice.get("chance_bonus")):
                problems.append(f"{label}: failure_effects / chance_bonus need a success_chance")
            for bonus in choice.get("chance_bonus") or []:
                if not isinstance(bonus, dict) or not _is_number(bonus.get("amount")):
                    problems.append(f"{label}: chance_bonus entries need a numeric amount, got {bonus!r}")
                else:
                    problems += [f"{label}: chance_bonus: {p}" for p in validate_requires(bonus.get("requires"))]
    return problems


def check_events(events):
    """Raise ValueError listing every problem in `events` (nothing happens when the data is fine). Can also be
    called once at import time from event_data.py, like map_data._validate."""
    problems = validate_events(events)
    if problems:
        raise ValueError("bad event data:\n  " + "\n  ".join(problems))


def apply_effects(game, effects):
    """Apply a list of declarative effects; return human-readable effect notes."""
    notes = []
    for effect in effects or []:
        kind = effect.get("type")
        amount = int(effect.get("amount", 0))
        if kind == "resource":
            field = effect.get("resource")
            if field not in RESOURCE_FIELDS:
                continue
            before = getattr(game, field, 0)
            # A loss takes at most what the convoy has of THAT resource: never below 0, never more than `amount`, and
            # never anything from another resource ("-12 water" with 1 water left takes 1 water and nothing else).
            if field == "fuel":
                if amount <= 0:
                    after = max(0, before + amount)
                else:
                    cap = game.convoy_stats().get("fuel_capacity", before)
                    after = max(before, min(cap, before + amount))   # a gain never lowers the fuel
            elif field in ("food", "water", "scrap"):
                if amount > 0 and hasattr(game, "gain_cargo"):
                    remainder = game.gain_cargo({field: amount})
                    after = getattr(game, field, before)
                    actual = after - before
                    if actual:
                        notes.append(f"{field.title()} {actual:+d}")
                    if remainder:
                        notes.append(f"Cargo full: {remainder} {field} could not fit")
                    continue
                after = max(0, before + amount)
            setattr(game, field, after)
            actual = after - before
            if actual:
                notes.append(f"{field.title()} {actual:+d}")

            manager = getattr(game, "mission_manager", None)

            if manager and field == "fuel" and actual > 0:
                manager.on_resource_collected(game, "fuel", actual)
                manager.on_resources_changed(game)   # a "hold X" (stockpile) mission may now be met
        elif kind == "survivors":
            before = game.survivors
            if amount < 0:
                amount = -_defended(game, -amount, effect)

            if amount > 0:
                # Seats, survivor records, vehicle assignment and rescue-mission credit: Game.recruit_survivors.
                change = game.recruit_survivors(amount)
            else:
                game.survivors = max(0, before + amount)
                game.survivor_manager.sync_count(game.survivors)
                change = game.survivors - before
                if change != 0:
                    game.assign_survivors_to_vehicles()

            if change != 0:
                notes.append(f"Survivors {change:+d}")
        elif kind == "injury":
            # +N: N survivors are hurt ("defense": True lets the convoy's defense cut it, like a survivors loss);
            # -N: N injured survivors are treated (the critical ones first).
            if amount > 0:
                hurt = game.injure(_defended(game, amount, effect))
                if hurt:
                    notes.append(f"Survivors injured +{hurt}")
            elif amount < 0:
                healed = game.heal_injuries(-amount)
                if healed:
                    notes.append(f"Survivors treated {healed}")
        elif kind in ("vehicle_damage_pct", "vehicle_damage"):
            # Percent of every vehicle's own maximum health (like an ambush); "defense": True lets defense absorb it.
            # "vehicle_damage" is the old flat-health effect: it now means the same thing, with defense always on, so
            # no event can hurt a big and a small vehicle alike or ignore the convoy's defense.
            if kind == "vehicle_damage":
                effect = dict(effect, defense=True)
            damage = _defended(game, amount, effect)
            if amount > 0:
                damage = max(1, damage)
            if damage > 0:
                wrecked = game.damage_vehicles(damage)
                notes.append(f"Convoy took {damage}% damage")
                notes.extend(f"{_vehicle_label(vehicle)} wrecked" for vehicle in wrecked)
                if hasattr(game, "check_defeat"):
                    game.check_defeat()
        elif kind == "vehicle_repair":
            remaining = amount
            repaired = 0
            # The most damaged vehicle first (lowest share of its maximum health), not whoever is first in the list.
            for vehicle in sorted(game.vehicles,
                                  key=lambda v: v.health / max(1, v.stats.get("health", v.health))):
                maximum = vehicle.stats.get("health", vehicle.health)
                add = min(remaining, max(0, maximum - vehicle.health))
                vehicle.health += add
                repaired += add
                remaining -= add
                if remaining <= 0:
                    break
            if repaired:
                notes.append(f"Vehicle repairs +{repaired} health")
        elif kind == "vehicle_gain" and crew_of(effect)[0] + len(crew_of(effect)[1]) > 0:
            # A vehicle with its own people (a family and their minivan): they bring the driver, so no spare adult is needed.
            vehicle, crew_notes = gain_crewed_vehicle(game, effect.get("vehicle"), float(effect.get("health", 1.0)),
                                                      *crew_of(effect))
            if vehicle is not None:
                notes.append(f"New vehicle: {_vehicle_label(vehicle)}")
                notes.extend(crew_notes)
            else:
                notes.append("No new vehicle could join the convoy")   # the type is owned already or unknown
        elif kind == "vehicle_gain":
            vehicle = gain_vehicle(game, effect.get("vehicle"), float(effect.get("health", 1.0)))
            if vehicle is not None:
                game.assign_survivors_to_vehicles()
                notes.append(f"New vehicle: {_vehicle_label(vehicle)}")
            elif not has_spare_driver(game):
                notes.append("No driver free for the new vehicle")
            else:
                notes.append("No new vehicle could join the convoy")   # the type is owned already or unknown
        elif kind == "special_survivor":
            note = recruit_special(game, effect.get("key"))
            if note:
                notes.append(note)
        elif kind == "vehicle_loss":
            vehicle = lose_vehicle(game)
            if vehicle is not None:
                game.assign_survivors_to_vehicles()
                notes.append(f"Vehicle abandoned: {_vehicle_label(vehicle)}")
        elif kind == "berths":
            # Places on the Pacific evacuation ship (evacuation.py); nothing happens outside the evacuation.
            added = game.add_berths(amount) if hasattr(game, "add_berths") else 0
            if added:
                notes.append(f"Ship berths {added:+d}")
        elif kind == "horde_gap":
            game.horde = max(0, game.horde + amount)
            notes.append(f"Horde gap {amount:+d} km")
            if hasattr(game, "check_horde_state"):
                game.check_horde_state()   # a new danger state is announced now, not on the next day
    return notes
