"""Survivor conditions of THE LAST CONVOY: hunger, thirst and injury (design doc section 12.3).

Population-based: the game keeps a COUNT of survivors in each stage, never per-person health. Each condition
progresses on its own, so one survivor can be hungry and injured; the counts need not add up to the population.

    hunger:  fed -> hungry -> starving -> leaves the convoy
    thirst:  hydrated -> thirsty -> dehydrated -> leaves the convoy
    injury:  healthy -> injured -> critical -> dies

Daily (update_conditions, called from upkeep after the day's food and water are used):
  * not enough food / water for the day -> each survivor may move one stage on (fed -> hungry -> starving), and
    starving / dehydrated survivors may leave. Several can leave on the same day.
  * enough food / water -> nobody gets worse, and hungry / starving (thirsty / dehydrated) survivors recover
    gradually: each may move one stage back a day (starving -> hungry -> fed), so a neglected convoy stays hungry
    for a few days after the resupply.
  * injuries never appear on their own: injure() is called by horde attacks and events. Untreated, injured
    survivors can turn critical and critical ones can die; both recover slowly, and faster with a Medical Care
    vehicle (the ambulance). The ambulance does not help hunger or thirst.

Pygame-free, like the rest of the game package. The rates are in config.py (Survivor conditions).
"""
import random

from config import (AMBUSH_INJURY_FRACTION, HORDE_ATTACK_INJURY_FRACTION, INJURY_DEATH_RATE, INJURY_RECOVER_RATE, INJURY_WORSEN_RATE,
                    MEDICAL_RECOVER_RATE, NEED_RECOVER_RATES, SHORTAGE_RATES, people)
from vehicle_data import VEHICLE_ABILITIES

STAGES = {"hunger": ("hungry", "starving"), "thirst": ("thirsty", "dehydrated"), "injury": ("injured", "critical")}
CONDITION_KEYS = tuple(key for stages in STAGES.values() for key in stages)
LEAVE_REASON = {"hunger": "starving", "thirst": "dehydrated"}


def _roll(count, rate):
    """How many of `count` survivors an event of probability `rate` hits (each is rolled once)."""
    return sum(1 for _ in range(max(0, count)) if random.random() < rate)


class ConditionsMixin:
    """Hunger, thirst and injury counts for the convoy's survivors."""

    def reset_conditions(self):
        self.conditions = {key: 0 for key in CONDITION_KEYS}
        self.condition_losses = {"hunger": 0, "thirst": 0, "injury": 0}   # survivors lost to each, for the results screen

    # ---- questions ---------------------------------------------------------------------------------------------
    def has_medical_care(self):
        """True when a vehicle with the Medical Care ability (the ambulance) is in the convoy."""
        return any(VEHICLE_ABILITIES.get(v.vehicle_type) == "medical_care" for v in self.vehicles)

    def injured_count(self):
        """Survivors who are injured or critical (they overlap with hungry / thirsty ones)."""
        self.sync_conditions()
        return self.conditions["injured"] + self.conditions["critical"]

    def condition_report(self):
        """The total survivors plus the number in each stage, for the HUD / survivors screen."""
        self.sync_conditions()
        return {"survivors": self.survivors, **self.conditions}

    def sync_conditions(self):
        """Keep the counts valid when the survivor count changed for another reason (a horde attack, an event, someone
        joined). If a condition now covers more people than there are, the worse stage keeps its people first."""
        for stages in STAGES.values():
            room = max(0, self.survivors)
            for key in reversed(stages):
                self.conditions[key] = min(self.conditions[key], room)
                room -= self.conditions[key]

    # ---- injury sources and treatment ----------------------------------------------------------------------------
    def injure(self, amount):
        """Up to `amount` healthy survivors become injured. Returns how many did."""
        self.sync_conditions()
        healthy = self.survivors - self.conditions["injured"] - self.conditions["critical"]
        hurt = max(0, min(amount, healthy))
        self.conditions["injured"] += hurt
        return hurt

    def injure_share(self, fraction, defense_reduction=0, minimum=0):
        """A `fraction` of the survivors is hurt, cut by the convoy's defense and scaled by the difficulty's "horde"
        multiplier, rounded and at least `minimum`. Returns how many were injured."""
        if self.survivors <= 0:
            return 0
        share = fraction * (100 - defense_reduction) / 100 * self.diff()["horde"]
        return self.injure(max(minimum, int(self.survivors * share + 0.5)))

    def injure_after_attack(self, defense_reduction=0):
        """A horde attack wounds part of the survivors it did not kill (at least one). Returns how many."""
        return self.injure_share(HORDE_ATTACK_INJURY_FRACTION, defense_reduction, minimum=1)

    def injure_in_ambush(self, defense_reduction=0):
        """The automatic road ambush wounds part of the survivors (defense can spare them all). Returns how many."""
        return self.injure_share(AMBUSH_INJURY_FRACTION, defense_reduction)

    def heal_injuries(self, amount):
        """Treat up to `amount` injured survivors outright (an event); the critical ones first. Returns how many."""
        self.sync_conditions()
        c = self.conditions
        healed = 0
        for key in ("critical", "injured"):
            step = min(c[key], amount - healed)
            c[key] -= step
            healed += step
        return healed

    # ---- the daily update ----------------------------------------------------------------------------------------
    def _step_need(self, need, short):
        """One day of hunger or thirst. Returns how many survivors leave. `short`: the convoy could not feed everyone."""
        mild, severe = STAGES[need]
        c = self.conditions
        if not short:
            # Fed / watered: no one gets worse, and each survivor may recover one stage (starving -> hungry -> fed).
            # Both rolls use today's counts, so nobody skips a stage in a single day.
            rate = NEED_RECOVER_RATES[need]
            better_severe = _roll(c[severe], rate)
            better_mild = _roll(c[mild], rate)
            c[severe] -= better_severe
            c[mild] += better_severe - better_mild
            return 0
        to_mild_rate, to_severe_rate, leave_rate = SHORTAGE_RATES[need]
        leaving = _roll(c[severe], leave_rate)
        to_severe = _roll(c[mild], to_severe_rate)
        fine = self.survivors - c[mild] - c[severe]
        newly_mild = _roll(fine, to_mild_rate)
        c[severe] += to_severe - leaving
        c[mild] += newly_mild - to_severe
        return leaving

    def _step_injury(self):
        """One day of injuries. Returns how many survivors die."""
        c = self.conditions
        rate = MEDICAL_RECOVER_RATE if self.has_medical_care() else INJURY_RECOVER_RATE
        dying = _roll(c["critical"], INJURY_DEATH_RATE)
        stabilised = _roll(c["critical"] - dying, rate)
        worsened = _roll(c["injured"], INJURY_WORSEN_RATE)
        healed = _roll(c["injured"] - worsened, rate)
        c["critical"] += worsened - stabilised - dying
        c["injured"] += stabilised - worsened - healed
        return dying

    def update_conditions(self, food_short, water_short):
        """Run one day of condition changes, then remove the survivors who left or died. Call once per day from
        upkeep(), after the day's food and water were used. Several survivors can go in one day."""
        self.sync_conditions()
        gone = {"hunger": self._step_need("hunger", food_short),
                "thirst": self._step_need("thirst", water_short),
                "injury": self._step_injury()}
        total = min(sum(gone.values()), self.survivors)
        if total <= 0:
            self.sync_conditions()
            return
        self.survivors -= total
        for need, count in gone.items():
            self.condition_losses[need] += count
            if not count:
                continue
            if need == "injury":
                self.say(f"{people(count)} died of their injuries.")
            else:
                self.say(f"{people(count)} left the convoy: {LEAVE_REASON[need]}.")
        self.sync_conditions()
        self.enforce_limits()   # seats, drivers and records follow the lower survivor count (convoy.py)
