"""Survival rules of THE LAST CONVOY: difficulty, daily food and water use, the passing of days and defeat.
(Hunger, thirst and injury stages live in conditions.py; upkeep() calls them each day.)
"""
import random

from config import DIFFICULTIES, SURVIVORS_PER_FOOD, SURVIVORS_PER_WATER


class SurvivalMixin:
    """Days pass here: the horde moves, supplies are used and a run can be lost."""
    def diff(self):
        return DIFFICULTIES[self.difficulty]

    def set_difficulty(self, name):
        if name in DIFFICULTIES:
            self.difficulty = name
            if self.day == 1 and not self.journey:   # run not begun yet: the starting gap follows the difficulty
                self.apply_horde_start()
            self.say(f"Difficulty set to {name}.")

    def scaled_yield(self, amount):
        """Scale a scavenged amount by the difficulty (never rounds a real find down to nothing)."""
        if amount <= 0:
            return 0
        return max(1, int(amount * self.diff()["scavenge"] + 0.5))

    def daily_use(self, survivors=None):
        """Whole-number food and water the convoy uses per day.

        Base use follows the survivor count (1 food per 5 survivors, 1 water per 4, rounded up); the
        difficulty multiplier is then applied and the result rounded, with a minimum of 1. `survivors` (default: the
        convoy's own) lets a forecast ask what the use would be with another count.
        """
        people = self.survivors if survivors is None else survivors
        mult = self.diff()["consumption"]
        base_food = -(-people // SURVIVORS_PER_FOOD)
        base_water = -(-people // SURVIVORS_PER_WATER)
        return max(1, int(base_food * mult + 0.5)), max(1, int(base_water * mult + 0.5))

    def supply_forecast(self, days, extra_vehicles=0):
        """Replay upkeep() for `days` days on today's stock: would survivors leave because food or water runs out?

        Each day the daily use (daily_use) comes off. A day is short when the stock cannot feed everyone; then, in the
        worst case, every survivor moves one stage on (fed -> hungry -> starving) and every starving / dehydrated
        survivor leaves. A day with enough supplies puts everyone back to normal. Fewer adults than vehicles then
        loses vehicles: this assumes the worst, that every survivor who leaves is an adult. `extra_vehicles` counts a
        vehicle about to be added. Supplies found on the way, events and horde attacks are not foreseen.

        Returns None when nobody would leave, else a dict: short ("food", "water" or "food and water"), leave
        (survivors who would leave) and vehicles (vehicles that could be lost).
        """
        self.sync_conditions()
        food, water, people = self.food, self.water, self.survivors
        # [mild, severe] counts now, per need (worst-case simulation, so they are only ever pushed one way)
        stage = {"food": [self.conditions["hungry"], self.conditions["starving"]],
                 "water": [self.conditions["thirsty"], self.conditions["dehydrated"]]}
        empty, left = set(), 0
        for _ in range(days):
            if people <= 0:
                break
            use_food, use_water = self.daily_use(people)
            short = {"food": food < use_food, "water": water < use_water}
            food, water = max(0, food - use_food), max(0, water - use_water)
            leaving = 0
            for name, counts in stage.items():
                if not short[name]:
                    counts[:] = [0, 0]
                    continue
                empty.add(name)
                mild, severe = counts
                leaving += severe
                counts[:] = [max(0, people - mild - severe), mild]   # everyone else moves one stage on
            leaving = min(leaving, people)
            people -= leaving
            left += leaving
            for counts in stage.values():
                counts[:] = [min(counts[0], people), min(counts[1], people)]
        if left == 0:
            return None
        vehicles = max(0, len(self.vehicles) + extra_vehicles - max(0, self.adult_count() - left))
        return {"short": " and ".join(name for name in ("food", "water") if name in empty), "leave": left,
                "vehicles": vehicles}

    def confirm_day_cost(self, action, label, extra_vehicles=0, retry=None):
        """For an action that takes a day (repair, recovering a vehicle): True to go ahead.

        When that day would cost a survivor (not enough food or water, see supply_forecast) the action does not go
        ahead yet and False is returned. With `retry` (a no-argument function that does the same action again) an
        "are you sure?" popup opens (ask_confirm("daycost"), the text is in day_cost_pending["text"]); YES runs `retry`,
        which now goes ahead, NO does nothing. Without `retry` the old behaviour stays: the first press only warns in
        the log and pressing the same button again with nothing changed in between goes ahead. Any change (a day
        passing, supplies, survivors) asks again, so an old warning never counts.
        """
        forecast = self.supply_forecast(1, extra_vehicles)
        if forecast is None:
            self.day_warning = None
            return True
        mark = (action, self.day, self.food, self.water, self.survivors)
        if getattr(self, "day_warning", None) == mark:
            self.day_warning = None
            return True
        lost = " and a vehicle could be lost with them" if forecast["vehicles"] else ""
        who = "a survivor would leave" if forecast["leave"] == 1 else f"{forecast['leave']} survivors would leave"
        if retry is not None:
            self.day_warning = None
            self.day_cost_pending = {
                "mark": mark, "retry": retry,
                "text": f"This takes a day and the {forecast['short']} will run out: {who}{lost}. "
                        f"Go ahead anyway?"}
            self.ask_confirm("daycost")
            return False
        self.day_warning = mark
        self.say(f"Warning: this takes a day and the {forecast['short']} will run out: {who}{lost}. "
                 f"Press {label} again to go ahead anyway.")
        return False

    def upkeep(self):
        food_used, water_used = self.daily_use()
        food_short = self.food < food_used      # not enough to feed everyone today
        water_short = self.water < water_used
        self.food = max(0, self.food - food_used)
        self.water = max(0, self.water - water_used)
        # Hunger / thirst stages, injuries and the survivors who leave or die of them (conditions.py).
        self.update_conditions(food_short, water_short)

    def advance_time(self, amount=1):
        """Let days pass, one at a time: each day the horde moves toward the convoy (it can never get past it),
        supplies are used and a horde at gap 0 attacks. Stops early if the run ends."""
        for _ in range(amount):
            if self.status != "playing":
                break
            self.day += 1
            low, high = self.horde_daily_range()
            self.horde_km = min(self.horde_km + random.randint(low, high), self.convoy_km)
            self.upkeep()
            self.check_horde_state()
            if self.horde <= 0 and self.status == "playing":
                self.horde_attack()   # no instant loss: the run ends when every survivor is dead (check_defeat)
                if self.status == "playing" and self.survivors > 0:
                    self._achieve("check")   # survived another day overrun: "Hold the Line" counts horde_attack_streak
            else:
                self.horde_attack_streak = 0   # the convoy got clear of the horde: the attacks start from the beginning

    def check_defeat(self):
        if self.status != "playing":
            return
        if self.survivors <= 0:
            self.end_run("lost", "Every survivor has left. The convoy is empty.")
        elif not self.vehicles:
            self.end_run("lost", "The convoy has no vehicles left.")
        elif self.convoy_stats()["health"] <= 0:
            self.end_run("lost", "The convoy has broken down.")
