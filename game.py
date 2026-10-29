"""Game rules for THE LAST CONVOY: the Vehicle and Game classes.

This module must stay free of pygame (it imports only config.py, vehicles.py, event_manager.py and the
map data/pathfinding from map_data.py), so the rules can be imported and tested without a display.
main.py owns the window, input and drawing.
"""
import random

from config import (AMBUSH_CHANCE, APPROACHING_MIN_KM, DEFAULT_RECOVERY_COST, DEFENSE_REDUCTION_CAP,
                    DEFENSE_REDUCTION_PER_POINT, DIFFICULTIES, DISTANT_MIN_KM, FUEL_BASE_COST, FUEL_KM_PER_UNIT,
                    HORDE_DAILY_ADVANCE_KM, HORDE_START_KM, HORDE_STATES, KM_PER_SPEED_DAY, RECOVERY_SITES,
                    REPAIR_FRACTION, REPAIR_SCRAP_COST, SCRAP_FIND_CHANCE, SURVIVORS_PER_FOOD,
                    SURVIVORS_PER_WATER, people)
from event_manager import EventManager
from instructions_data import PAGE_COUNT
from map_data import SITES, SURVIVOR_FINDS, NODES, START, shortest_path
from vehicles import VEHICLE_SPECS, RECOVERY_COSTS


def recovery_cost(vehicle_type):
    """Scrap needed to recover a vehicle of this type."""
    return RECOVERY_COSTS.get(vehicle_type, DEFAULT_RECOVERY_COST)


class Vehicle:
    """An owned vehicle instance with a copy of its baseline specifications."""
    def __init__(self, vehicle_type):
        self.vehicle_type = vehicle_type
        self.stats = dict(VEHICLE_SPECS[vehicle_type])
        self.health = self.stats["health"]

    @property
    def name(self):
        return self.vehicle_type


class Game:
    def __init__(self):
        self.difficulty = "Normal"  # not part of reset(): it stays the same across restarts
        self.started = False        # False until START GAME on the lore screen; restarts (reset) keep it True
        self.menu_return = "convoy"  # where the menu's BACK goes: "title" or "convoy"
        self.reset()
        self.screen = "title"       # title -> lore -> convoy

    def reset(self):
        self.fuel = 32
        self.food = 24
        self.water = 24
        self.scrap = 5
        self.survivors = 8
        # The starting convoy matches the three vehicles illustrated in the prototype.
        self.vehicles = [Vehicle("Pickup Truck"), Vehicle("Passenger Van"), Vehicle("School Bus")]
        self.position = START            # node id of the stop the convoy is at
        self.current_location = NODES[START]["name"]
        self.selected_site = 0           # index into the current stop's sites: the one SCAVENGE searches
        self.horde_km = -HORDE_START_KM  # the horde's position on the Start-to-Pacific line
        self.last_horde_state = "Distant"
        self.day = 1
        self.selected = 1                # the stop highlighted on the map (Gas Station)
        self.log = [
            "The convoy is heading west. The horde is behind you.",
            "Reach the Pacific Coast and escape by ship.",
        ]
        self.status = "playing"
        self.travel_count = 0
        self.scene_scroll = 0
        self.screen = "convoy"           # title, lore, convoy, map, vehicles, menu or instructions
        self.instructions_page = 0
        self.selected_vehicle_type = "Semi-Truck"
        self.abandon_confirm = None  # vehicle type waiting for a second click to confirm abandoning
        self.event_manager = EventManager()
        self.pending_victory = False
        # Run statistics for the ending screen.
        self.visited = {START}                 # node ids of the stops the convoy has reached
        self.km_traveled = 0
        self.vehicles_start = len(self.vehicles)
        self.vehicles_recovered = 0
        self.end_reason = ""                   # why the run ended (shown on the ending screen)

    def return_to_title(self):
        """From the ending screen: a fresh run, back to the title screen."""
        self.reset()
        self.started = False
        self.screen = "title"

    def stops_visited(self):
        """How many different stops the convoy has reached (not counting where it started)."""
        return len(self.visited - {START})

    def stops_total(self):
        return len(NODES) - 1

    def vehicles_lost(self):
        """Vehicles no longer in the convoy, however they were lost (abandoned, left without a driver, events)."""
        return max(0, self.vehicles_start + self.vehicles_recovered - len(self.vehicles))

    def end_run(self, status, message):
        self.status = status
        self.end_reason = message
        self.say(message)

    def show_lore(self):
        self.screen = "lore"

    def begin_game(self):
        self.started = True
        self.screen = "convoy"

    def open_menu(self):
        self.menu_return = "title" if self.screen == "title" else "convoy"
        self.screen = "menu"

    def close_menu(self):
        self.screen = self.menu_return

    def open_instructions(self):
        self.instructions_page = 0
        self.screen = "instructions"

    def turn_instructions_page(self, step):
        """Move to the next (+1) or previous (-1) instructions page, staying within the pages."""
        self.instructions_page = max(0, min(PAGE_COUNT - 1, self.instructions_page + step))

    def say(self, message):
        self.log.insert(0, message)
        self.log = self.log[:4]

    # ---- Horde: its position and the gap are on the same straight line ----
    @property
    def convoy_km(self):
        return NODES[self.position]["axis"]

    @property
    def horde(self):
        """The gap in km between the convoy and the horde (never below 0)."""
        return max(0, self.convoy_km - self.horde_km)

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

    # ---- Difficulty ----
    def diff(self):
        return DIFFICULTIES[self.difficulty]

    def set_difficulty(self, name):
        if name in DIFFICULTIES:
            self.difficulty = name
            self.say(f"Difficulty set to {name}.")

    def scaled_yield(self, amount):
        """Scale a scavenged amount by the difficulty (never rounds a real find down to nothing)."""
        if amount <= 0:
            return 0
        return max(1, int(amount * self.diff()["scavenge"] + 0.5))

    def horde_daily_range(self):
        mult = self.diff()["horde"]
        low, high = HORDE_DAILY_ADVANCE_KM
        return max(1, int(low * mult + 0.5)), max(1, int(high * mult + 0.5))

    def daily_use(self):
        """Whole-number food and water the convoy uses per day.

        Base use follows the survivor count (1 food per 5 survivors, 1 water per 4, rounded up); the
        difficulty multiplier is then applied and the result rounded, with a minimum of 1.
        """
        mult = self.diff()["consumption"]
        base_food = -(-self.survivors // SURVIVORS_PER_FOOD)
        base_water = -(-self.survivors // SURVIVORS_PER_WATER)
        return max(1, int(base_food * mult + 0.5)), max(1, int(base_water * mult + 0.5))

    # ---- Convoy and vehicle numbers ----
    def convoy_stats(self):
        """Return calculated convoy totals from currently owned vehicles."""
        if not self.vehicles:
            return {
                "speed": 0, "health": 0, "max_health": 0, "passengers": 0, "cargo": 0,
                "defense": 0, "fuel_capacity": 0, "fuel_consumption": 0,
            }
        return {
            # The slowest vehicle determines the convoy's travel speed.
            "speed": min(vehicle.stats["speed"] for vehicle in self.vehicles),
            "health": sum(vehicle.health for vehicle in self.vehicles),
            "max_health": sum(vehicle.stats["health"] for vehicle in self.vehicles),
            "passengers": sum(vehicle.stats["passengers"] for vehicle in self.vehicles),
            "cargo": sum(vehicle.stats["cargo"] for vehicle in self.vehicles),
            "defense": sum(vehicle.stats["defense"] for vehicle in self.vehicles),
            "fuel_capacity": sum(vehicle.stats["fuel_capacity"] for vehicle in self.vehicles),
            "fuel_consumption": sum(vehicle.stats["fuel_consumption"] for vehicle in self.vehicles),
        }

    def owned_vehicle_types(self):
        return {vehicle.vehicle_type for vehicle in self.vehicles}

    def convoy_health_pct(self):
        """Convoy health is simply the combined health of the vehicles, as a percentage of their maximum."""
        stats = self.convoy_stats()
        if stats["max_health"] <= 0:
            return 0
        pct = int(100 * stats["health"] / stats["max_health"] + 0.5)
        return max(1, pct) if stats["health"] > 0 else 0

    def needs_repair(self):
        return any(vehicle.health < vehicle.stats["health"] for vehicle in self.vehicles)

    def defense_reduction(self):
        """Percent of ambush damage absorbed by the convoy's total defense."""
        return min(DEFENSE_REDUCTION_CAP, self.convoy_stats()["defense"] * DEFENSE_REDUCTION_PER_POINT)

    def current_stop(self):
        """The stop the convoy is at right now."""
        return NODES[self.position]

    # ---- Sites: a stop can hold several; the convoy scavenges one chosen site at a time ----
    def current_sites(self):
        """Site keys (see map_data.SITES) available at the convoy's current stop."""
        return list(self.current_stop().get("sites", []))

    def current_site(self):
        """The site key SCAVENGE will search, or None if the stop has no sites."""
        sites = self.current_sites()
        return sites[self.selected_site % len(sites)] if sites else None

    def cycle_site(self):
        """Choose the next site at this stop (no time passes)."""
        sites = self.current_sites()
        if len(sites) > 1:
            self.selected_site = (self.selected_site + 1) % len(sites)

    def cycle_destination(self, direction):
        """Select the next destination west (direction -1, left arrow) or east (+1, right arrow) of the convoy.

        West and east follow the map screen: stops left or right of the convoy's stop, nearest first. Repeated
        presses cycle through them and wrap around; with none in that direction nothing changes.
        """
        convoy_x = NODES[self.position]["pos"][0]
        if direction < 0:
            ids = [i for i, node in enumerate(NODES) if node["pos"][0] < convoy_x]
            ids.sort(key=lambda i: -NODES[i]["pos"][0])
        else:
            ids = [i for i, node in enumerate(NODES) if node["pos"][0] > convoy_x]
            ids.sort(key=lambda i: NODES[i]["pos"][0])
        if ids:
            self.selected = ids[(ids.index(self.selected) + 1) % len(ids)] if self.selected in ids else ids[0]

    def can_recover_here(self):
        """Vehicles can be recovered at stops with a Truck Stop, Repair Depot or Military Installation."""
        return any(SITES[site]["name"] in RECOVERY_SITES for site in self.current_sites())

    # ---- Capacity helpers (cargo caps food + water + scrap; fuel and passengers have their own caps) ----
    def cargo_used(self):
        return self.food + self.water + self.scrap

    def cargo_free(self):
        return max(0, self.convoy_stats()["cargo"] - self.cargo_used())

    def gain(self, resource, amount):
        """Add one resource up to the convoy's capacity. Returns how much did not fit."""
        if amount <= 0:
            return 0
        if resource == "fuel":
            room = max(0, self.convoy_stats()["fuel_capacity"] - self.fuel)
        else:
            room = self.cargo_free()
        added = min(amount, room)
        setattr(self, resource, getattr(self, resource) + added)
        return amount - added

    def gain_cargo(self, found):
        """Add several cargo items (food, water, scrap) found together, sharing limited space fairly.

        If everything fits it is all added. Otherwise the free space is split in proportion to how much of
        each item was found, and every item gets at least one unit when there is room for that.
        Returns the number of units that did not fit.
        """
        found = {resource: amount for resource, amount in found.items() if amount > 0}
        total = sum(found.values())
        if total == 0:
            return 0
        free = self.cargo_free()
        if total <= free:
            alloc = dict(found)
        else:
            alloc = {resource: 0 for resource in found}
            remaining = free
            if remaining >= len(found):
                for resource in found:
                    alloc[resource] = 1
                remaining -= len(found)
            want = {resource: found[resource] - alloc[resource] for resource in found}
            want_total = sum(want.values())
            takes = {resource: remaining * want[resource] // want_total for resource in found}
            for resource in found:
                alloc[resource] += takes[resource]
            leftover = remaining - sum(takes.values())
            # Hand out any space left after rounding to the items with the biggest shortfall.
            for resource in sorted(found, key=lambda r: found[r] - alloc[r], reverse=True):
                if leftover <= 0:
                    break
                if alloc[resource] < found[resource]:
                    alloc[resource] += 1
                    leftover -= 1
        for resource, amount in alloc.items():
            setattr(self, resource, getattr(self, resource) + amount)
        return total - sum(alloc.values())

    def trim_supplies(self):
        """Leave behind supplies and fuel that no longer fit after the convoy's capacity shrank."""
        caps = self.convoy_stats()
        lost_cargo = 0
        excess = self.cargo_used() - caps["cargo"]
        while excess > 0:
            # Drop one unit at a time from the largest stock so no single resource is wiped out.
            resource = max(("food", "water", "scrap"), key=lambda r: getattr(self, r))
            setattr(self, resource, getattr(self, resource) - 1)
            excess -= 1
            lost_cargo += 1
        lost_fuel = max(0, self.fuel - caps["fuel_capacity"])
        self.fuel -= lost_fuel
        parts = []
        if lost_cargo:
            parts.append(f"{lost_cargo} supplies")
        if lost_fuel:
            parts.append(f"{lost_fuel} fuel")
        if parts:
            self.say("Not enough room: " + " and ".join(parts) + " left behind.")

    def check_defeat(self):
        if self.status != "playing":
            return
        if self.survivors <= 0:
            self.end_run("lost", "Every survivor has left. The convoy is empty.")
        elif not self.vehicles:
            self.end_run("lost", "The convoy has no vehicles left.")
        elif self.convoy_stats()["health"] <= 0:
            self.end_run("lost", "The convoy has broken down.")

    def enforce_limits(self):
        """Keep the convoy consistent: a driver per vehicle, supplies within capacity, a seat per survivor."""
        for _ in range(50):
            if self.status != "playing" or self.survivors <= 0:
                break
            if self.vehicles and self.survivors < len(self.vehicles):
                lost = self.vehicles.pop()  # the rearmost vehicle is abandoned
                self.say(f"The {lost.vehicle_type} was abandoned: no one left to drive it.")
                continue
            self.trim_supplies()
            seats = self.convoy_stats()["passengers"]
            if self.survivors > seats:
                extra = self.survivors - seats
                self.survivors -= extra
                self.say(f"{extra} survivor(s) left: not enough seats for everyone.")
                continue
            break
        self.check_defeat()

    # ---- Vehicle actions ----
    def recover_vehicle(self, vehicle_type):
        """Recover one unowned vehicle at a Truck Stop, Repair Depot or Military Installation."""
        if self.status != "playing":
            return
        if not self.can_recover_here():
            self.say("Vehicle recovery is only possible where there is a Truck Stop, Repair Depot or Military Installation.")
            return
        if vehicle_type not in VEHICLE_SPECS:
            self.say("Unknown vehicle type.")
            return
        if vehicle_type in self.owned_vehicle_types():
            self.say(f"Your convoy already has a {vehicle_type}.")
            return
        if self.survivors <= len(self.vehicles):
            self.say("No spare survivor to drive another vehicle.")
            return

        cost = recovery_cost(vehicle_type)
        if self.scrap < cost:
            self.say(f"Need {cost} scrap to recover the {vehicle_type}.")
            return

        self.scrap -= cost
        vehicle = Vehicle(vehicle_type)
        # Recovered vehicles are damaged and need maintenance, giving recovery a trade-off.
        vehicle.health = max(1, int(vehicle.stats["health"] * 0.7))
        self.vehicles.append(vehicle)
        self.vehicles_recovered += 1
        self.selected_vehicle_type = vehicle_type
        self.say(f"Recovered a {vehicle_type} at {self.current_location} for {cost} scrap.")
        self.advance_time(1)

    def request_abandon(self, vehicle_type):
        """First call asks for confirmation; a second call on the same vehicle abandons it."""
        if self.abandon_confirm == vehicle_type:
            self.abandon_confirm = None
            self.abandon_vehicle(vehicle_type)
        else:
            self.abandon_confirm = vehicle_type

    def abandon_vehicle(self, vehicle_type):
        """Give up an owned vehicle (anywhere, no time cost, no refund). It can be recovered again later."""
        if self.status != "playing":
            return
        vehicle = next((v for v in self.vehicles if v.vehicle_type == vehicle_type), None)
        if vehicle is None:
            self.say(f"You don't own a {vehicle_type}.")
            return
        if len(self.vehicles) <= 1:
            self.say("You can't abandon your last vehicle.")
            return
        self.vehicles.remove(vehicle)
        self.say(f"Abandoned the {vehicle_type}.")
        self.enforce_limits()

    # ---- Time ----
    def upkeep(self):
        food_used, water_used = self.daily_use()
        self.food = max(0, self.food - food_used)
        self.water = max(0, self.water - water_used)
        if self.food == 0 or self.water == 0:
            if self.food == 0 and self.water == 0:
                reason = "no food or water"
            elif self.food == 0:
                reason = "no food"
            else:
                reason = "no water"
            self.survivors = max(0, self.survivors - 1)
            self.say(f"A survivor left the convoy: {reason}.")
            self.enforce_limits()

    def advance_time(self, amount=1):
        """Let days pass: the horde moves toward the convoy (it can never get past it) and supplies are used."""
        self.day += amount
        low, high = self.horde_daily_range()
        self.horde_km = min(self.horde_km + random.randint(low, high) * amount, self.convoy_km)
        self.upkeep()
        self.check_horde_state()
        if self.horde <= 0 and self.status == "playing":
            self.end_run("lost", "The horde caught the convoy.")

    # ---- Travel and events ----
    def plan_trip(self, index=None):
        """Work out a trip from the convoy's current stop to a stop (default: the selected one).

        Returns a dict: path (stop ids), km (road distance), fuel, days, delta (km moved west along the
        straight line; negative = east, 0 = sideways detour) and through (names of stops passed on the way).
        """
        dest = self.selected if index is None else index
        if dest == self.position:
            return {"path": [dest], "km": 0, "fuel": 0, "days": 0, "delta": 0, "through": []}
        path, km = shortest_path(self.position, dest)
        km_per_day = max(1, int(self.convoy_stats()["speed"] * KM_PER_SPEED_DAY))
        return {
            "path": path,
            "km": km,
            "fuel": FUEL_BASE_COST + int(km / FUEL_KM_PER_UNIT + 0.5),
            "days": max(1, -(-km // km_per_day)),
            "delta": NODES[dest]["axis"] - NODES[self.position]["axis"],
            "through": [NODES[i]["name"] for i in path[1:-1]],
        }

    def travel_danger(self, index=None):
        """Would this trip let the horde reach the convoy?

        Only trips that don't take the convoy west can be dangerous. Returns "overrun" if the gap is
        certain to hit zero (the distance lost plus the horde's minimum advance over the trip's days already
        reaches it), "risky" if it only could (the horde's maximum advance would), or None.
        """
        trip = self.plan_trip(index)
        if trip["km"] == 0 or trip["delta"] > 0:
            return None
        low, high = self.horde_daily_range()
        gap_after_trip = self.horde + trip["delta"]
        if gap_after_trip - low * trip["days"] <= 0:
            return "overrun"
        if gap_after_trip - high * trip["days"] <= 0:
            return "risky"
        return None

    def damage_vehicles(self, percent):
        """Damage every vehicle by a percentage of its own maximum health."""
        for vehicle in self.vehicles:
            hit = max(1, int(vehicle.stats["health"] * percent / 100 + 0.5))
            vehicle.health = max(0, vehicle.health - hit)

    def ambush(self):
        base = random.randint(5, 13)
        reduction = self.defense_reduction()
        damage = max(1, int(base * (100 - reduction) / 100 + 0.5))
        self.damage_vehicles(damage)
        self.say(f"Road ambush! Defense absorbed {reduction}%. Convoy took {damage}% damage.")

    def travel(self):
        if self.status != "playing":
            return
        dest = NODES[self.selected]
        trip = self.plan_trip()
        if trip["km"] == 0:
            self.say(f"The convoy is already at {dest['name']}.")
            return
        if self.travel_danger() == "overrun":
            self.say(f"Too dangerous: going to {dest['name']} would let the horde overrun the convoy.")
            return
        if self.fuel < trip["fuel"]:
            self.say(f"Not enough fuel to reach {dest['name']} (need {trip['fuel']}).")
            return
        self.fuel -= trip["fuel"]
        self.position = self.selected
        self.current_location = dest["name"]
        self.selected_site = 0
        self.visited.add(self.selected)
        self.km_traveled += trip["km"]
        self.travel_count += 1
        self.scene_scroll += 1 if trip["delta"] >= 0 else -1
        # The convoy's position on the straight line has changed; the horde keeps coming while the days pass.
        self.advance_time(trip["days"])
        if self.status != "playing":
            return
        if trip["delta"] > 0:
            direction = "west"
        elif trip["delta"] < 0:
            direction = "east (backwards)"
        else:
            direction = "on a detour"
        self.say(f"Reached {dest['name']} heading {direction}. {trip['km']} km, {trip['fuel']} fuel.")
        reached_coast = dest["kind"] == "coast"
        if reached_coast:
            self.pending_victory = True
        # Road incident: the most dangerous stop on the route (excluding where you started) sets the ambush chance.
        ambush_chance = max(NODES[i].get("ambush", AMBUSH_CHANCE) for i in trip["path"][1:])
        roll = random.random()
        if roll < ambush_chance:
            self.ambush()
        elif roll < ambush_chance + SCRAP_FIND_CHANCE:
            found = random.randint(2, 5)
            left = self.gain_cargo({"scrap": found})
            if left >= found:
                self.say("Found scrap beside the highway, but the convoy has no cargo space.")
            elif left > 0:
                self.say(f"Found {found} scrap beside the highway; only room for {found - left}.")
            else:
                self.say(f"Found {found} scrap beside the highway.")
        self.check_defeat()
        if self.status == "playing":
            self.event_manager.start_for_arrival(self)
            # If no event opened, the victory completes now; otherwise it completes once the event is resolved.
            if self.pending_victory and not self.event_manager.active:
                self.finish_victory()

    def finish_victory(self):
        self.pending_victory = False
        self.end_run("won", "You reached the Pacific Coast. The survivors escape by ship!")

    @property
    def event_result(self):
        """What the last event choice did (see EventManager.result); shown until the player clicks OK."""
        return self.event_manager.result

    def resolve_event_choice(self, choice_index):
        outcome = self.event_manager.resolve_choice(self, choice_index)
        if outcome:
            self.say(outcome)

    def dismiss_event_result(self):
        """The player clicked OK on the result screen. A pending victory (coast reached) completes now."""
        self.event_manager.clear_result()
        if self.pending_victory and self.status == "playing":
            self.finish_victory()

    def find_survivors(self, chance, smallest, largest):
        """Maybe find a group of survivors. Returns True if a group was found."""
        if random.random() >= chance:
            return False
        group = random.randint(smallest, largest)
        free_seats = max(0, self.convoy_stats()["passengers"] - self.survivors)
        joined = min(group, free_seats)
        left = group - joined
        self.survivors += joined
        if joined and left:
            self.say(f"{people(joined)} joined; {left} more had to be left behind: no free seats.")
        elif joined:
            self.say(f"{people(joined)} joined the convoy!")
        else:
            self.say(f"A group of {people(group)} wanted to join, but the convoy has no free seats.")
        return True

    def scavenge(self):
        if self.status != "playing":
            return
        # Scavenging searches the chosen site of the stop the convoy is actually at, not the one selected on the map.
        kind = self.current_site()
        if kind is None:
            self.say(f"There is nothing to scavenge at {self.current_location}.")
            return
        self.advance_time(1)
        if self.status != "playing":
            return
        left_behind = 0
        rand = random.randint
        scaled = self.scaled_yield
        if kind == "start":
            # The open starting highway has no supplies, but stranded survivors can be found.
            if not self.find_survivors(*SURVIVOR_FINDS["start"]):
                self.say("No one was found along the highway.")
            return
        if kind == "fuel":
            left_behind += self.gain("fuel", scaled(rand(5, 12)))
            left_behind += self.gain_cargo({"food": scaled(rand(0, 3))})
            self.say("Scavenged fuel and a few supplies from the gas station.")
        elif kind == "food":
            left_behind += self.gain_cargo({"food": scaled(rand(6, 12)), "water": scaled(rand(2, 7))})
            self.say("Found canned food and bottled water in the supermarket.")
        elif kind == "repair":
            left_behind += self.gain_cargo({"scrap": scaled(rand(3, 7))})
            left_behind += self.gain("fuel", scaled(rand(0, 4)))
            self.say("Searched the repair depot for scrap and spare parts.")
        elif kind == "farm":
            left_behind += self.gain_cargo({"food": scaled(rand(10, 18)), "water": scaled(rand(5, 10))})
            self.say("Gathered plenty of food and fresh water at the farm.")
        elif kind == "hospital":
            left_behind += self.gain_cargo({"water": scaled(rand(2, 5)), "food": scaled(rand(0, 2))})
            self.say("Searched the hospital for supplies.")
        elif kind == "military":
            left_behind += self.gain_cargo({"scrap": scaled(rand(5, 10))})
            left_behind += self.gain("fuel", scaled(rand(3, 8)))
            self.say("Salvaged scrap and fuel from the military installation.")
        elif kind == "diner":
            left_behind += self.gain_cargo({"food": scaled(rand(4, 9)), "water": scaled(rand(2, 5))})
            self.say("Found meals and drinks in the diner's kitchen.")
        elif kind == "hardware":
            left_behind += self.gain_cargo({"scrap": scaled(rand(4, 8))})
            self.say("Hauled scrap and tools out of the hardware store.")
        elif kind == "pharmacy":
            left_behind += self.gain_cargo({"water": scaled(rand(1, 3)), "food": scaled(rand(0, 2))})
            self.say("Searched the pharmacy for water and a few supplies.")
        elif kind == "warehouse":
            left_behind += self.gain_cargo({"food": scaled(rand(3, 8)), "water": scaled(rand(1, 4)),
                                            "scrap": scaled(rand(2, 5))})
            self.say("Broke open crates in the warehouse.")
        elif kind == "water":
            left_behind += self.gain_cargo({"water": scaled(rand(7, 13))})
            self.say("Filled up on clean water at the water tower.")
        elif kind == "garage":
            left_behind += self.gain("fuel", scaled(rand(3, 8)))
            left_behind += self.gain_cargo({"scrap": scaled(rand(2, 5))})
            self.say("Drained fuel and stripped scrap at the auto garage.")
        elif kind == "shelter":
            left_behind += self.gain_cargo({"food": scaled(rand(0, 2)), "water": scaled(rand(0, 2))})
            self.say("Checked the survivor shelter.")
        elif kind == "police":
            left_behind += self.gain_cargo({"scrap": scaled(rand(3, 6))})
            left_behind += self.gain("fuel", scaled(rand(0, 3)))
            self.say("Searched the police station for scrap and fuel.")
        elif kind == "pass":
            left_behind += self.gain_cargo({"scrap": scaled(rand(1, 3))})
            self.say("Searched the roadside at the pass for scrap.")
        else:  # Truck Stop and Small Town: mixed supplies
            left_behind += self.gain_cargo({
                "food": scaled(rand(2, 6)),
                "water": scaled(rand(2, 6)),
                "scrap": scaled(rand(1, 4)),
            })
            self.say("Scavenging party returned with mixed supplies.")
        if left_behind > 0:
            self.say(f"Convoy is full: {left_behind} units left behind.")
        if kind in SURVIVOR_FINDS:
            self.find_survivors(*SURVIVOR_FINDS[kind])

    def repair(self):
        if self.status != "playing":
            return
        if self.scrap < REPAIR_SCRAP_COST:
            self.say(f"Need {REPAIR_SCRAP_COST} scrap to repair the convoy.")
            return
        if not self.needs_repair():
            self.say("The convoy is already in good condition.")
            return
        self.scrap -= REPAIR_SCRAP_COST
        for vehicle in self.vehicles:
            maximum = vehicle.stats["health"]
            vehicle.health = min(maximum, vehicle.health + int(maximum * REPAIR_FRACTION + 0.5))
        self.say(f"Used {REPAIR_SCRAP_COST} scrap to repair {int(REPAIR_FRACTION * 100)}% of every vehicle's health.")
