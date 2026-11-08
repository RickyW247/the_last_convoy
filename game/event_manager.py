"""Weighted random event selection and event lifecycle management."""
import random
from .event_data import EVENTS
from .effect_handler import (affordable_flags, apply_effects, event_available, fitted_effects, roll_choice,
                             vehicle_fallback)


def snapshot(game):
    """The numbers an event choice can change, taken before and after it is applied."""
    return {"fuel": game.fuel, "food": game.food, "water": game.water, "scrap": game.scrap,
            "survivors": game.survivors, "injured": game.injured_count(), "vehicles": len(game.vehicles),
            "health": game.convoy_health_pct(), "horde": game.horde, "day": game.day, "berths": getattr(game, "berths", lambda: 0)()}


def changes(before, game):
    """What changed since `before`, as [(text, is_good)] lines for the result screen."""
    now = snapshot(game)
    lines = []
    for key, label, unit in (("fuel", "Fuel", ""), ("food", "Food", ""), ("water", "Water", ""),
                             ("scrap", "Scrap", ""), ("survivors", "Survivors", ""), ("injured", "Injured", ""),
                             ("vehicles", "Vehicles", ""), ("health", "Convoy health", "%"),
                             ("horde", "Horde gap", " km"), ("berths", "Ship berths", "")):
        delta = now[key] - before[key]
        if delta:
            good = delta < 0 if key == "injured" else delta > 0   # more injured survivors is bad news
            lines.append((f"{label} {delta:+d}{unit}", good))
    if now["day"] != before["day"]:
        lines.append((f"{now['day'] - before['day']} day(s) pass", False))
    return lines



class EventManager:
    def __init__(self):
        self.current_event = None
        self.last_event_ids = []
        # What the last choice did, kept until the player dismisses the result screen:
        # {"title", "choice", "outcome", "changes"} or None.
        self.result = None
        self.last_failed = False   # True when the last risky choice failed its roll (see effect_handler.roll_choice)

    @property
    def active(self):
        return self.current_event is not None

    def start_for_arrival(self, game, trigger=None):
        """Select a weighted event; avoid immediate repeats. `trigger` picks the pool: None is the ordinary travel
        events, "ambush" the events of a road ambush (events carry "trigger": "ambush"). Returns the event or None."""
        if self.active or not EVENTS or game.status != "playing":
            return None
        # Only events that fit the situation (their "requires") and that the convoy can act on (at least one choice it
        # can pay for / is allowed to pick).
        candidates = [event for event in EVENTS
                      if event.get("weight", 1) > 0 and event.get("trigger") == trigger
                      and event_available(game, event) and not game.settlement_refuses(event)]
        if not candidates:
            return None
        fresh = [event for event in candidates if event.get("id") not in self.last_event_ids]
        pool = fresh or candidates
        selected = random.choices(pool, weights=[event.get("weight", 1) for event in pool], k=1)[0]
        self.current_event = selected
        self.last_event_ids.append(selected.get("id"))
        self.last_event_ids = self.last_event_ids[-2:]
        game.say(f"Road ambush: {selected['title']}." if trigger == "ambush"
                 else f"Unexpected situation: {selected['title']}.")
        return selected

    def start_event(self, game, event_id, announce="Evacuation"):
        """Open one particular event by its id (the scripted events of the Pacific evacuation, evacuation.py). Returns
        the event, or None when one is open already, the run is over or the id is unknown."""
        if self.active or game.status != "playing":
            return None
        event = next((e for e in EVENTS if e.get("id") == event_id), None)
        if event is None:
            return None
        self.current_event = event
        game.say(f"{announce}: {event['title']}.")
        return event

    def can_choose(self, game, choice_index):
        """True if the open event has this choice and the convoy can pay for it (effect_handler.affordable_flags).
        The popup greys out the others; resolve_choice refuses them too, so no key or click can get one through."""
        if not self.active:
            return False
        choices = self.current_event.get("choices", [])
        if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
            return False
        return affordable_flags(game, choices)[choice_index]

    def resolve_choice(self, game, choice_index):
        if not self.can_choose(game, choice_index):
            return None
        choices = self.current_event.get("choices", [])
        choice, self.last_failed = roll_choice(game, choices[choice_index])   # risky choices can go wrong
        before = snapshot(game)
        no_car = vehicle_fallback(game, choice)   # the people come without their vehicle: the convoy owns it already
        effects, fit_note = fitted_effects(game, choice)   # a rescue that does not fit costs only what actually came
        effects, background_note = game.adjust_event_effects(self.current_event, effects)   # Emergency Response (Police)
        if background_note:
            fit_note = (fit_note + " " + background_note).strip()
        notes = apply_effects(game, effects)
        outcome = (choice.get("outcome_no_vehicle") if no_car else None) or choice.get("outcome", "The convoy moves on.")
        if fit_note:
            outcome += " " + fit_note
        self.show_result(self.current_event.get("title", "Event"), choice.get("label", ""),
                         outcome,                     # the result screen lists the changes separately
                         changes(before, game))
        if notes:
            outcome += " (" + "; ".join(notes) + ")"  # the event log keeps the short notes
        self.current_event = None
        return outcome

    def show_result(self, title, choice, outcome, change_lines):
        """Open the result popup. Used by event choices and by scavenging, so both end in the same screen.
        `choice` may be "" (no "You chose" line); `change_lines` is [(text, is_good)] (see changes())."""
        self.result = {"title": title, "choice": choice, "outcome": outcome, "changes": change_lines}

    def clear_result(self):
        self.result = None
