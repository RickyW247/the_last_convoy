"""Scavenging of THE LAST CONVOY: the sites of a stop, the SCAVENGE popup, what each kind of site yields and the
survivors that can be found.
"""
import random

from config import (VEHICLE_FIND_CHANCE_SCALE, VEHICLE_FIND_HEALTH, VEHICLE_SCAVENGE_ENABLED, people)
from .event_manager import changes, snapshot
from map_data import RARE_FUEL, SITE_VEHICLES, SITES, SURVIVOR_FINDS
from vehicle_data import BONUS_VEHICLES
from .vehicle import Vehicle


class ScavengeMixin:
    """A stop can hold several sites; the convoy searches one chosen site at a time (one day per search)."""
    # Vehicle finds (map_data.SITE_VEHICLES) only happen when this is True: main.setup() switches it on, because the
    # player is asked whether to take the vehicle (a popup); headless play and tests leave it off.
    vehicle_scavenging = False
    found_vehicle = None   # (vehicle type, site key) found by the search that is running, offered once it is over

    def _find_vehicle(self, kind):
        """Maybe turn up an abandoned vehicle at this site (map_data.SITE_VEHICLES). Only types the convoy does not
        own, and only when there is a spare adult to drive it. It is offered to the player after the search
        (_offer_found_vehicle), never added by itself."""
        self.found_vehicle = None
        if not (self.vehicle_scavenging and VEHICLE_SCAVENGE_ENABLED) or kind not in SITE_VEHICLES:
            return
        chance, types = SITE_VEHICLES[kind]
        if random.random() >= chance * VEHICLE_FIND_CHANCE_SCALE * self.diff()["scavenge"]:
            return
        owned = self.owned_vehicle_types()
        # A bonus vehicle (vehicle_data.BONUS_VEHICLES) can only turn up once an achievement has unlocked it
        # (sandbox mode lists every bonus vehicle anyway, as the vehicles screen does).
        unlocked = self.achievements.unlocked_vehicles()
        sandbox = getattr(self, "sandbox", False)
        options = [t for t in types if t not in owned and (t not in BONUS_VEHICLES or sandbox or t in unlocked)]
        if not options:
            return
        vehicle_type = random.choice(options)
        site = SITES[kind]["name"].lower()
        if self.adult_count() <= len(self.vehicles):
            self.say(f"Found a {vehicle_type} at the {site}, but there is no spare adult to drive it.")
            return
        self.found_vehicle = (vehicle_type, kind)
        self.say(f"Found an abandoned {vehicle_type} at the {site}!")

    def _offer_found_vehicle(self):
        """Ask whether to take the vehicle the search found (YES / NO popup, the same one the day-cost question uses)."""
        if not self.found_vehicle or self.status != "playing":
            self.found_vehicle = None
            return
        vehicle_type, _kind = self.found_vehicle
        self.found_vehicle = None
        self.day_warning = None
        self.day_cost_pending = {
            "mark": ("vehicle", self.day, vehicle_type), "retry": lambda: self.take_found_vehicle(vehicle_type),
            "text": f"You found an abandoned {vehicle_type}. It is free and takes no time, "
                    f"but it needs a driver and its upkeep uses more fuel. Take it?"}
        self.ask_confirm("daycost")

    def take_found_vehicle(self, vehicle_type):
        """YES: the scavenged vehicle joins the convoy for free (damaged, with the upgrades it once had). Counts as a
        recovered vehicle. NO does nothing: the vehicle is left behind."""
        if self.status != "playing" or vehicle_type in self.owned_vehicle_types():
            return False
        if self.adult_count() <= len(self.vehicles):
            self.say(f"No spare adult survivor to drive the {vehicle_type}: it was left behind.")
            return False
        vehicle = Vehicle(vehicle_type, self.vehicle_upgrades.get(vehicle_type, ()))
        low, high = VEHICLE_FIND_HEALTH
        vehicle.health = max(1, int(vehicle.stats["health"] * random.uniform(low, high)))
        self.vehicles.append(vehicle)
        self.vehicles_recovered += 1
        self.selected_vehicle_type = vehicle_type
        self.assign_survivors_to_vehicles()
        self.say(f"The {vehicle_type} joined the convoy.")
        self._achieve("on_vehicle_recovered")
        return True

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

    def find_survivors(self, chance, smallest, largest):
        """Maybe find a group of survivors. Returns True if a group was found."""
        if random.random() >= chance * self.recruit_chance_factor():   # Untrusted Reputation (background_rules.py)
            return False
        group = random.randint(smallest, largest)
        joined = self.recruit_survivors(group)   # seats, survivor records, vehicle assignment, mission credit
        left = group - joined

        if joined and left:
            self.say(
                f"{people(joined)} joined; {left} more had to be "
                "left behind: no free seats."
            )
        elif joined:
            self.say(f"{people(joined)} joined the convoy!")
        else:
            self.say(
                f"A group of {people(group)} wanted to join, "
                "but the convoy has no free seats."
            )

        return True

    def start_scavenge(self):
        """SCAVENGE button / S key: with several sites at this stop, open the popup (pick a site, then confirm with
        its SCAVENGE button); with one site there is nothing to choose, so it is searched at once."""
        if self.status != "playing" or self.current_site() is None:
            return
        if len(self.current_sites()) > 1:
            self.site_picker = True
        else:
            self.scavenge()

    def select_site(self, index):
        """Pick a site in the popup (no time passes); the popup's SCAVENGE button searches it."""
        if 0 <= index < len(self.current_sites()):
            self.selected_site = index

    def scavenge_site(self, index):
        """Close the popup and search the site with this index (see current_sites)."""
        self.site_picker = False
        if 0 <= index < len(self.current_sites()):
            self.selected_site = index
            self.scavenge()

    def close_site_picker(self):
        self.site_picker = False

    def _capture(self, func, *args):
        """Run func(*args) and return the log lines it said (they still go to the log as well)."""
        self._outcome_lines = []
        try:
            func(*args)
        finally:
            lines, self._outcome_lines = self._outcome_lines, None
        return lines

    def scavenge(self):
        """Search the selected site: one day passes, then the finds. Ends in the same result popup as an event
        choice (what was found first, then the day's upkeep, then every change); the log gets the same lines."""
        if self.status != "playing":
            return
        # Scavenging searches the chosen site of the stop the convoy is actually at, not the one selected on the map.
        kind = self.current_site()
        if kind is None:
            self.say(f"There is nothing to scavenge at {self.current_location}.")
            return
        before = snapshot(self)
        found = self._capture(self._search_site, kind)
        upkeep = self._capture(self.advance_time, 1)
        if self.status != "playing":
            return   # the horde caught the convoy (or everyone left): the ending popup says why
        name = SITES.get(kind, {}).get("name", "the site")
        self.event_manager.show_result(f"Scavenged: {name}", "", " ".join(found + upkeep) or "Nothing was found.",
                                       changes(before, self))
        self._offer_found_vehicle()   # a vehicle turned up: ask the player whether to take it

    def _rare_fuel(self, kind):
        """The small chance of fuel at a site that mostly gives something else (map_data.RARE_FUEL); says so when it
        happens. Returns the units that did not fit in the tank."""
        if kind not in RARE_FUEL:
            return 0
        chance, smallest, largest = RARE_FUEL[kind]
        if random.random() >= chance:
            return 0
        amount = self.scaled_yield(random.randint(smallest, largest))
        if amount <= 0:
            return 0
        self.say("Found a little spare fuel.")
        return self.gain("fuel", amount)

    def _search_site(self, kind):
        """The finds of one search of a site of this kind (what each site yields is in map_data.SITES); says what happened."""
        site = SITES.get(kind)
        if site is None:
            # A site key with no data is a typo (or a new site nobody wrote data for): fail loudly.
            raise ValueError(f"No scavenging data for site key {kind!r}")
        rand = random.randint
        scaled = self.scaled_yield
        finds = site["finds"]
        left_behind = 0
        fuel = scaled(rand(*finds["fuel"])) if "fuel" in finds else 0
        cargo = {resource: scaled(rand(*span)) for resource, span in finds.items() if resource != "fuel"}
        fuel, cargo = self.background_scavenge_bonus(fuel, cargo, kind)   # Resource Coordination / Underworld Connections
        if fuel > 0:
            left_behind += self.gain("fuel", fuel)
        if cargo:
            left_behind += self.gain_cargo(cargo)
        if site.get("message"):
            self.say(site["message"])
        left_behind += self._rare_fuel(kind)
        if left_behind > 0:
            self.say(f"Convoy is full: {left_behind} units left behind.")
        found_group = kind in SURVIVOR_FINDS and self.find_survivors(*SURVIVOR_FINDS[kind])
        if not found_group and site.get("no_survivors"):
            self.say(site["no_survivors"])
        self._find_vehicle(kind)
        # Check the stock counts ("Well Fed", "Scrap Baron") now, before the day's upkeep eats into it; the unlock
        # message is then part of this search's result popup.
        self._achieve("check")
