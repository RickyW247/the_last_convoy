"""Weighted random event selection and event lifecycle management."""
import random
from event_data import EVENTS
from effect_handler import apply_effects


def _snapshot(game):
    """The numbers an event choice can change, taken before and after it is applied."""
    return {"fuel": game.fuel, "food": game.food, "water": game.water, "scrap": game.scrap,
            "survivors": game.survivors, "vehicles": len(game.vehicles),
            "health": game.convoy_health_pct(), "horde": game.horde, "day": game.day}


def _changes(before, game):
    """What changed since `before`, as [(text, is_good)] lines for the result screen."""
    now = _snapshot(game)
    lines = []
    for key, label, unit in (("fuel", "Fuel", ""), ("food", "Food", ""), ("water", "Water", ""),
                             ("scrap", "Scrap", ""), ("survivors", "Survivors", ""),
                             ("vehicles", "Vehicles", ""), ("health", "Convoy health", "%"),
                             ("horde", "Horde gap", " km")):
        delta = now[key] - before[key]
        if delta:
            lines.append((f"{label} {delta:+d}{unit}", delta > 0))
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

    @property
    def active(self):
        return self.current_event is not None

    def start_for_arrival(self, game):
        """Select a weighted event after a successful arrival; avoid immediate repeats."""
        if self.active or not EVENTS or game.status != "playing":
            return None
        candidates = [event for event in EVENTS if event.get("weight", 1) > 0]
        if not candidates:
            return None
        fresh = [event for event in candidates if event.get("id") not in self.last_event_ids]
        pool = fresh or candidates
        selected = random.choices(pool, weights=[event.get("weight", 1) for event in pool], k=1)[0]
        self.current_event = selected
        self.last_event_ids.append(selected.get("id"))
        self.last_event_ids = self.last_event_ids[-2:]
        game.say(f"Unexpected situation: {selected['title']}.")
        return selected

    def resolve_choice(self, game, choice_index):
        if not self.active:
            return None
        choices = self.current_event.get("choices", [])
        if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
            return None
        choice = choices[choice_index]
        before = _snapshot(game)
        notes = apply_effects(game, choice.get("effects", []))
        outcome = choice.get("outcome", "The convoy moves on.")
        self.result = {
            "title": self.current_event.get("title", "Event"),
            "choice": choice.get("label", ""),
            "outcome": outcome,                       # the result screen lists the changes separately
            "changes": _changes(before, game),
        }
        if notes:
            outcome += " (" + "; ".join(notes) + ")"  # the event log keeps the short notes
        self.current_event = None
        return outcome

    def clear_result(self):
        self.result = None
