"""Travel of THE LAST CONVOY: choosing a destination, planning a trip, danger from the horde, road incidents,
journeys (one day at a time, with events), arriving and victory.
"""
import random

from config import (AMBUSH_CHANCE, AMBUSH_DAILY_FACTOR, AMBUSH_DAMAGE_PCT, AMBUSH_MIN_DAMAGE_PCT, FUEL_BASE_COST, FUEL_USE_DIVISOR, KM_PER_SPEED_DAY,
                    MIN_TRIP_DAYS, ROUTE_WEAR, SCRAP_FIND_CHANCE, TRAVEL_DAY_DELAY, TRAVEL_DAY_SCALE,
                    TRAVEL_EVENT_CHANCE, TRAVEL_EVENT_DELAY, TRAVEL_START_DELAY, people)
from achievements import event_id_of
from map_data import ADJACENT, NODES, scenery_for, shortest_path


class TravelMixin:
    """Trips follow map_data.NODES; the horde keeps advancing while the days of a trip pass."""
    # animate_travel: False (default, headless play and tests): travel() lives through the whole journey at once.
    # True (main.setup() switches it on): the journey is paced by update_travel(dt), one day per delay, so the player
    # sees "TRAVELLING..." and events never follow each other instantly. travel_delay = seconds until the next step.
    animate_travel = False
    travel_delay = 0.0

    def trip_fuel(self, km):
        """Fuel a trip of `km` road kilometres uses: a base cost plus the distance times the combined fuel_consumption
        of every vehicle in the convoy (so each vehicle you keep is an upkeep cost). Only travel uses fuel."""
        if km <= 0:
            return 0
        consumption = self.convoy_stats()["fuel_consumption"]
        return FUEL_BASE_COST + int(km * consumption / FUEL_USE_DIVISOR + 0.5)

    def route_wear(self, path):
        """Percent of every vehicle's maximum health the road itself costs on a trip along `path` (stop ids): the
        highest wear of any stop on it (a node's own wear=, else ROUTE_WEAR for its kind). It comes with the road, so it
        is charged on arrival whatever happened on the way, and defense does not reduce it."""
        return max((NODES[i].get("wear", ROUTE_WEAR.get(NODES[i]["kind"], 0)) for i in path), default=0)

    def scenery(self):
        """Which background the convoy scene shows right now: "highway" or "desert" (map_data.scenery_for). It follows the
        stop the convoy is at; on a journey it switches to the destination's scenery once the trip is half over, so
        driving over the Mountain Pass towards the desert changes the view part-way."""
        stop = self.position
        journey = self.journey
        if journey and journey["day"] * 2 >= journey["days"]:
            stop = journey["dest"]
        return scenery_for(stop)

    def neighbours(self):
        """Stop ids joined to the convoy's current stop by one road (the only places it can drive to)."""
        return [stop for stop, _km in ADJACENT[self.position]]

    def select_destination(self, stop):
        """Highlight any stop on the map to look at it. Only stops connected to the current one can be travelled to
        (travel() refuses the others), and the map shows which those are."""
        if isinstance(stop, int) and 0 <= stop < len(NODES):
            self.selected = stop
            return True
        return False

    def can_travel_now(self):
        """True if TRAVEL would set off: playing, not already on the road, and the selected stop is one road away.
        The TRAVEL button uses this to be disabled otherwise."""
        return self.status == "playing" and not self.journey and self.can_travel_to(self.selected)

    def can_travel_to(self, stop):
        """True if `stop` is one road away from the convoy's current stop."""
        return stop in self.neighbours()

    def default_destination(self):
        """The connected stop furthest west (the natural way on), used after arriving."""
        ids = self.neighbours()
        return max(ids, key=lambda i: (NODES[i]["axis"], -NODES[i]["pos"][0])) if ids else self.position

    def cycle_destination(self, direction):
        """Select the next stop west (direction -1, left arrow) or east (+1, right arrow) of the convoy, nearest first
        on the map screen: the stops one road away come first, then the rest (to look at; travel() only goes to
        connected stops). Repeated presses cycle and wrap; with none that way nothing changes."""
        convoy_x = NODES[self.position]["pos"][0]
        near = self.neighbours()
        if direction < 0:
            ids = [i for i, node in enumerate(NODES) if node["pos"][0] < convoy_x]
            ids.sort(key=lambda i: (i not in near, -NODES[i]["pos"][0]))
        else:
            ids = [i for i, node in enumerate(NODES) if node["pos"][0] > convoy_x]
            ids.sort(key=lambda i: (i not in near, NODES[i]["pos"][0]))
        if ids:
            self.selected = ids[(ids.index(self.selected) + 1) % len(ids)] if self.selected in ids else ids[0]

    def plan_trip(self, index=None):
        """Work out a trip from the convoy's current stop to a stop (default: the selected one).

        Returns a dict: path (stop ids), km (road distance), fuel, days, delta (axis km moved west; negative = east,
        0 = sideways detour), wear (% of every vehicle's health the road costs, see route_wear) and through (names of
        stops passed on the way).
        """
        dest = self.selected if index is None else index
        if dest == self.position:
            return {"path": [dest], "km": 0, "fuel": 0, "days": 0, "delta": 0, "wear": 0, "through": []}
        path, km = shortest_path(self.position, dest)
        km_per_day = max(1, int(self.convoy_stats()["speed"] * KM_PER_SPEED_DAY))
        days = max(MIN_TRIP_DAYS, -(-km // km_per_day) * TRAVEL_DAY_SCALE)
        return {
            "path": list(path),   # a copy: shortest_path returns the cached, immutable tuple
            "km": km,
            "fuel": self.trip_fuel(km),
            "days": days,
            "delta": NODES[dest]["axis"] - NODES[self.position]["axis"],
            "wear": self.route_wear(path),
            "through": [NODES[i]["name"] for i in path[1:-1]],
        }

    def travel_danger(self, index=None):
        """Would this trip let the horde catch the convoy (it then attacks every day)?

        Only trips that don't take the convoy west can be dangerous. Returns "overrun" if a trip back east is certain
        to hit a gap of zero (travel() refuses these), "risky" if the horde could catch (or already has) the convoy
        on a sideways trip or only might on a trip east, or None. Going west is never blocked, even from an overrun stop.
        Stops that are not connected to the current one are judged along the shortest route to them.
        """
        # A stop that is not one road away is judged too (the whole route there, as plan_trip works it out), so the map,
        # the minimap and the info panel can show it overrun / risky even though travel() will refuse to go there.
        trip = self.plan_trip(index)
        if trip["km"] == 0 or trip["delta"] > 0:
            return None
        low, high = self.horde_daily_range()
        gap_after_trip = self.horde + trip["delta"]
        if gap_after_trip - low * trip["days"] <= 0:
            # Only a trip back east (delta < 0) is ever blocked; a sideways trip is just risky, so a convoy the horde
            # caught on a dead-end spur can always drive back out.
            return "overrun" if trip["delta"] < 0 else "risky"
        if gap_after_trip - high * trip["days"] <= 0:
            return "risky"
        return None

    def supply_warning(self, index=None):
        """Would the convoy run out of food or water on this trip (default: to the selected stop)?

        The trip's days are replayed by survival.supply_forecast (see it for the rules and what is not foreseen).
        Only trips the convoy can make are judged.

        Returns None when nobody would leave, else a dict: days (trip days), short (what runs out: "food", "water" or
        "food and water"), days_short (days a survivor leaves), leave (survivors who would leave) and vehicles
        (vehicles that could be lost).
        """
        dest = self.selected if index is None else index
        if dest == self.position or dest not in self.neighbours():
            return None
        days = self.plan_trip(index)["days"]
        forecast = self.supply_forecast(days)
        if forecast is None:
            return None
        return {"days": days, "short": forecast["short"], "days_short": forecast["leave"],
                "leave": forecast["leave"], "vehicles": forecast["vehicles"]}

    def ambush(self):
        base = random.randint(*AMBUSH_DAMAGE_PCT)
        reduction = self.defense_reduction()
        damage = max(AMBUSH_MIN_DAMAGE_PCT, int(base * (100 - reduction) / 100 + 0.5))
        hurt = self.injure_in_ambush(reduction)   # survivors wounded in the attack (conditions.py)
        self.say(f"Road ambush! Defense absorbed {reduction}%. Convoy took {damage}% damage."
                 + (f" {hurt} injured." if hurt else ""))
        self.damage_vehicles(damage)   # after the message, so a wreck is logged below it

    def travel(self):
        """Set off for the selected stop (it must be connected to the current one). The journey then runs day by day
        (continue_journey), pausing at every event, and ends with the arrival."""
        if self.status != "playing" or self.journey:
            return
        dest_id = self.selected
        dest = NODES[dest_id]
        if dest_id == self.position:
            self.say(f"The convoy is already at {dest['name']}.")
            return
        if dest_id not in self.neighbours():
            self.say(f"{dest['name']} is not connected to {self.current_location}: you can only drive to a stop one road away.")
            return
        trip = self.plan_trip()
        warning = self.supply_warning()
        if self.travel_danger() == "overrun":
            self.say(f"Too dangerous: going back east to {dest['name']} would drive the convoy into the horde.")
            return
        if self.fuel < trip["fuel"]:
            self.say(f"Not enough fuel to reach {dest['name']} (need {trip['fuel']}).")
            return
        self.fuel -= trip["fuel"]
        self.journey = {"dest": dest_id, "km": trip["km"], "days": trip["days"], "day": 0,
                        "axis_to": dest["axis"], "delta": trip["delta"], "fuel": trip["fuel"], "wear": trip["wear"]}
        self.selected_site = 0
        self.say(f"Setting off for {dest['name']}: {trip['km']} km, about {trip['days']} days, {trip['fuel']} fuel"
                 + (f", rough road (about {trip['wear']}% wear)." if trip["wear"] else "."))
        if warning:
            self.say(f"Warning: the {warning['short']} will run out on this trip. Up to {warning['leave']} survivor(s) may "
                     f"leave" + (f" and up to {warning['vehicles']} vehicle(s) may be lost." if warning["vehicles"] else "."))
        self.current_location = f"On the road to {dest['name']}"
        if self.animate_travel:
            self.travel_delay = TRAVEL_START_DELAY   # update_travel() takes it from here
        else:
            self.continue_journey()

    def on_road(self):
        """True while a journey is under way on the convoy screen and the player may not act (animated travel only).
        The convoy screen then shows TRAVELLING... and only the MENU button (and O / ESC) work."""
        return bool(self.animate_travel and self.journey and self.status == "playing" and self.screen == "convoy")

    def travelling(self):
        """on_road() and nothing is waiting for the player: the journey clock runs only now."""
        return (self.on_road() and not self.event_manager.active and not self.event_manager.result
                and not self.abandon_pick_needed() and not getattr(self, "confirm_popup", None))

    def update_travel(self, dt):
        """Advance the animated journey by `dt` seconds (call once per frame). When the delay has run out one step is
        taken: a day on the road (_travel_day, which may open an event) or the arrival. Pauses by itself while a popup
        is open, and while another screen (the pause menu) is showing."""
        if not self.travelling():
            return
        self.travel_delay -= dt
        if self.travel_delay > 0:
            return
        if self.journey["day"] >= self.journey["days"]:
            self._arrive()
        else:
            self._travel_day()
        self.travel_delay = TRAVEL_DAY_DELAY

    def continue_journey(self):
        """The journey goes on (after an event result or a vehicle pick). Animated: after a pause, update_travel()
        lives the next day. Otherwise the days are lived through at once until an event needs the player, the run ends
        or the convoy arrives."""
        if self.animate_travel:
            if self.journey:
                self.travel_delay = max(self.travel_delay, TRAVEL_EVENT_DELAY)
            return
        self._run_journey()

    def _run_journey(self):
        """Live through the journey's days until an event needs the player, the run ends or the convoy arrives."""
        while (self.journey and self.status == "playing" and not self.event_manager.active
               and not self.event_manager.result and not self.abandon_pick_needed()):
            if self.journey["day"] >= self.journey["days"]:
                self._arrive()
                break
            self._travel_day()

    def _travel_day(self):
        """One day on the road: the convoy moves on, the horde and supplies follow the clock, then road incidents
        and maybe an event."""
        journey = self.journey
        journey["day"] += 1
        self.advance_time(1)
        if self.status != "playing":
            return
        factor = AMBUSH_DAILY_FACTOR
        ambush_chance = NODES[journey["dest"]].get("ambush", AMBUSH_CHANCE) * factor
        roll = random.random()
        if roll < ambush_chance:
            # An ambush is a decision (fight, flee or sacrifice a vehicle): a popup from the "ambush" events. Only when
            # none can be shown does the old automatic damage apply.
            if not self.event_manager.start_for_arrival(self, trigger="ambush"):
                self.ambush()
        elif roll < ambush_chance + SCRAP_FIND_CHANCE * factor:
            found = random.randint(2, 5)
            left = self.gain_cargo({"scrap": found})
            if left >= found:
                self.say("Found scrap beside the highway, but the convoy has no cargo space.")
            elif left > 0:
                self.say(f"Found {found} scrap beside the highway; only room for {found - left}.")
            else:
                self.say(f"Found {found} scrap beside the highway.")
        self.check_defeat()
        if self.status == "playing" and random.random() < TRAVEL_EVENT_CHANCE:
            self.event_manager.start_for_arrival(self)

    def _arrive(self):
        journey, self.journey = self.journey, None
        dest_id = journey["dest"]
        wear = journey.get("wear", 0)
        if wear and NODES[dest_id]["kind"] != "coast":
            self.damage_vehicles(wear)
            self.say(f"The rough road cost every vehicle {wear}% of its health.")
            self.check_defeat()
            if self.status != "playing":
                return
        dest = NODES[dest_id]
        self.position = dest_id
        self.current_location = dest["name"]
        self.selected_site = 0
        self.visited.add(dest_id)
        self.km_traveled += journey["km"]
        self.travel_count += 1
        self.scene_scroll += 1 if journey["delta"] >= 0 else -1
        manager = getattr(self, "mission_manager", None)
        if manager:
            manager.on_destination_reached(self, dest_id)
            manager.on_journey_completed(self)   # "travel" objectives (journeys with a given vehicle)
        if journey["delta"] > 0:
            direction = "west"
        elif journey["delta"] < 0:
            direction = "east (backwards)"
        else:
            direction = "on a detour"
        self.say(f"Reached {dest['name']} heading {direction} after {journey['days']} days.")
        self.selected = self.default_destination()
        self._achieve("on_arrival")
        if dest["kind"] == "coast":
            self.begin_evacuation()   # the final scripted events; they end in finish_victory (evacuation.py)
        elif manager and self.status == "playing":
            manager.open_stage_event(self)   # the dedicated event of a mission stage that is ready (mission_manager.py)

    def finish_victory(self, escaped=None, left=0):
        """The run is won. `escaped` / `left`: survivors who boarded the ship and who were left on the dock (the
        evacuation); without them the plain message is used."""
        if escaped is None:
            self.end_run("won", "You reached the Pacific Coast. The survivors escape by ship!")
        else:
            ending = f" {people(left)} left behind on the dock." if left else " Nobody was left behind."
            self.end_run("won", f"{people(escaped)} escaped aboard the last ship from the Pacific Coast!" + ending)
        self._achieve("on_victory")

    @property
    def event_result(self):
        """What the last event choice did (see EventManager.result); shown until the player clicks OK."""
        return self.event_manager.result

    def resolve_event_choice(self, choice_index):
        event = self.event_manager.current_event   # the event being answered (it is cleared once resolved)
        choices = (event or {}).get("choices", [])
        choice = choices[choice_index] if isinstance(choice_index, int) and 0 <= choice_index < len(choices) else {}
        outcome = self.event_manager.resolve_choice(self, choice_index)
        if outcome:
            self.say(outcome)
        if outcome or self.event_manager.result:   # a refused (unaffordable) choice resolves nothing
            manager = getattr(self, "mission_manager", None)
            if choice.get("declines_mission"):
                # "Not now" on a mission event: no achievement, no stage progress; it comes back at the next stop.
                self._achieve("check")
                if manager:
                    manager.on_event_declined(self, event_id_of(event))
            else:
                self._achieve("on_event", event_id_of(event))
                if manager:
                    manager.on_event_resolved(self, event_id_of(event))

    def dismiss_event_result(self):
        """The player clicked OK on the result screen: a journey that was waiting on the event goes on."""
        self.event_manager.clear_result()
        if self.journey and self.status == "playing":
            self.continue_journey()   # the journey goes on after the event
        elif self.evacuation and self.status == "playing":
            self.continue_evacuation()   # the next scripted event of the Pacific evacuation, or boarding
