"""The horde of THE LAST CONVOY: its position, the gap to the convoy, the danger states and the zombies shown.
"""
import math
import random

from config import (HORDE_START_KM, people, APPROACHING_MIN_KM, DISTANT_MIN_KM, HORDE_ATTACK_ESCALATION, HORDE_ATTACK_MIN_FRACTION,
                    HORDE_ATTACK_SURVIVOR_KILLS, HORDE_ATTACK_VEHICLE_DAMAGE_PCT, HORDE_DAILY_ADVANCE_KM, HORDE_STATES)
from map_data import NODES

    


class HordeMixin:
    """The horde and the convoy are on the same straight line: gap = convoy position - horde position."""
    @property
    def convoy_km(self):
        """The convoy's place on the line; between two stops it moves a little each travel day."""
        here = NODES[self.position]["axis"]
        journey = getattr(self, "journey", None)
        if not journey:
            return here
        return int(round(here + (journey["axis_to"] - here) * journey["day"] / journey["days"]))   # whole km

    def horde_attack(self):
        """The horde is on the convoy: it kills survivors and wrecks every vehicle (the run ends only when no
        survivor is left). Called once per day while the gap is 0."""
        mult = self.diff()["horde"]
        streak = getattr(self, "horde_attack_streak", 0)   # days in a row the convoy has been under attack
        kills = int((random.randint(*HORDE_ATTACK_SURVIVOR_KILLS) + streak * HORDE_ATTACK_ESCALATION) * mult + 0.5)
        kills = max(1, kills, math.ceil(self.survivors * HORDE_ATTACK_MIN_FRACTION * mult))
        self.horde_attack_streak = streak + 1
        pct = max(1, int(random.randint(*HORDE_ATTACK_VEHICLE_DAMAGE_PCT) * mult + 0.5))
        reduction = self.defense_reduction()
        pct = max(1, int(pct * (100 - reduction) / 100 + 0.5))
        kills = min(kills, self.survivors)
        # Wrecks are removed (the last vehicle is kept running at 1 health); this method reports them and re-checks the
        # convoy itself, once the survivors are gone too.
        wrecked = len(self.damage_vehicles(pct, keep_one=True, quiet=True))
        self.survivors -= kills
        hurt = self.injure_after_attack(reduction)   # survivors the attack wounded but did not kill (conditions.py)
        text = f"The horde is attacking! {people(kills)} killed, vehicles took {pct}% damage."
        if hurt:
            text += f" {hurt} injured."
        if wrecked:
            text += f" {wrecked} vehicle(s) destroyed."
        self.say(text)
        self.enforce_limits()

    @property
    def horde(self):
        """The gap in km between the convoy and the horde (never below 0)."""
        return max(0, int(round(self.convoy_km - self.horde_km)))

    @horde.setter
    def horde(self, gap):
        self.horde_km = self.convoy_km - gap

    def horde_state(self, gap=None):
        gap = self.horde if gap is None else gap
        if gap <= 0:
            return "Overrun"
        if gap < APPROACHING_MIN_KM:
            return "Close"
        if gap < DISTANT_MIN_KM:
            return "Approaching"
        return "Distant"

    def check_horde_state(self):
        """Announce in the log when the horde's danger state changes."""
        new, old = self.horde_state(), self.last_horde_state
        if new == old:
            return
        if HORDE_STATES.index(new) > HORDE_STATES.index(old):
            self.say(f"Horde warning: the horde is now {new}!")
        else:
            self.say(f"You are pulling ahead: the horde is now {new}.")
        self.last_horde_state = new

    def zombie_count(self):
        """How many zombies to show in the convoy screen's background; follows the real gap."""
        gap = self.horde
        if gap >= DISTANT_MIN_KM:
            return 0
        if gap <= 0:
            return 18
        if gap < APPROACHING_MIN_KM:
            return 6 + int((APPROACHING_MIN_KM - gap) / APPROACHING_MIN_KM * 7)
        return 2 + int((DISTANT_MIN_KM - gap) / (DISTANT_MIN_KM - APPROACHING_MIN_KM) * 4)

    def horde_daily_range(self):
        mult = self.diff()["horde"]
        low, high = HORDE_DAILY_ADVANCE_KM
        return max(1, int(low * mult + 0.5)), max(1, int(high * mult + 0.5))

    def horde_start_km(self):
        """The starting gap in km for the current difficulty."""
        return self.diff().get("horde_start_km", HORDE_START_KM)

    def apply_horde_start(self):
        """Put the horde at the starting gap behind the convoy and sync the announced danger state to it."""
        start = self.horde_start_km()
        self.horde_km = NODES[self.position]["axis"] - start
        self.last_horde_state = self.horde_state(start)
