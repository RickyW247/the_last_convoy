"""The convoy of THE LAST CONVOY: vehicle totals, cargo capacity, gaining and trimming supplies, the driver and seat
rules, recovering / abandoning / repairing / upgrading vehicles and who rides in which vehicle.
"""
from config import (DEFENSE_REDUCTION_CAP, DEFENSE_REDUCTION_PER_POINT, RECOVERY_SITE_KEYS,
                    RECOVERY_SUPPORT_RECOVERY_DISCOUNT, RECOVERY_SUPPORT_REPAIR_DISCOUNT, REINFORCED_PROTECTION_BONUS,
                    REPAIR_FRACTION, REPAIR_SCRAP_COST)
from map_data import NODES, SITES, is_military_base
from upgrade_data import get_upgrade, upgrades_for
from vehicle_data import BONUS_VEHICLES, MILITARY_VEHICLES, STANDARD_VEHICLES, VEHICLE_ABILITIES, VEHICLE_SPECS

from .vehicle import Vehicle, recovery_cost


_unknown_sites = [key for key in RECOVERY_SITE_KEYS if key not in SITES]
if _unknown_sites:
    raise ValueError(f"config.RECOVERY_SITE_KEYS names sites that are not in map_data.SITES: {_unknown_sites}")

# Military vehicles can only be recovered at the Military Base (map_data.MILITARY_BASE, a dead end in every layout).
# The list is vehicle_data.MILITARY_VEHICLES (exact vehicle type names).


def is_military_vehicle(vehicle_type):
    """True for the vehicles that can only be recovered at the Military Base (APC, Humvee, ...)."""
    return vehicle_type in MILITARY_VEHICLES


# How much each kind of capacity counts when the convoy has to give up a vehicle nobody can drive (see
# ConvoyMixin._vehicle_value): seats count double, because losing seats means losing survivors.
VEHICLE_VALUE_WEIGHTS = {"passengers": 2, "cargo": 1, "defense": 1, "fuel_capacity": 1}


class ConvoyMixin:
    """Cargo caps food + water + scrap together; fuel and passengers have their own capacities."""
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

    def unlocked_bonus_vehicles(self):
        """Bonus vehicles the vehicles screen lists: all of them in SANDBOX MODE, otherwise the ones unlocked by
        completed achievements (achievement_data "unlocks_vehicle") plus any the convoy currently owns."""
        if getattr(self, "sandbox", False):
            return set(BONUS_VEHICLES)
        tracker = getattr(self, "achievements", None)
        unlocked = tracker.unlocked_vehicles() if tracker is not None else set()
        return (unlocked | self.owned_vehicle_types()) & BONUS_VEHICLES

    def listed_vehicle_types(self):
        """Every vehicle type the vehicles screen lists: the standard roster plus the unlocked bonus vehicles, in
        VEHICLE_SPECS order."""
        unlocked = self.unlocked_bonus_vehicles()
        return [name for name in VEHICLE_SPECS if name in STANDARD_VEHICLES or name in unlocked]

    def adult_count(self):
        """How many survivors can drive (their "can_drive" flag). Only they can drive, so this, not the number of
        survivors, is how many vehicles the convoy can run (enforce_limits, recover_vehicle, the vehicles screen and its
        buttons). Reads the manager's own list without copying it: the journey clock calls this every frame."""
        return sum(1 for survivor in self.survivor_manager.survivors if survivor["can_drive"])

    def _vehicle_value(self, vehicle):
        """How much the convoy would miss `vehicle`: its share of the convoy's seats, cargo space, defense and fuel
        capacity (weighted by VEHICLE_VALUE_WEIGHTS), counted for less the more damaged it is (a wreck at 0% health
        counts half)."""
        totals = self.convoy_stats()
        value = sum(
            weight * vehicle.stats[stat] / totals[stat]
            for stat, weight in VEHICLE_VALUE_WEIGHTS.items() if totals[stat] > 0
        )
        health = vehicle.health / max(1, vehicle.stats["health"])
        return value * (0.5 + 0.5 * min(1.0, health))

    interactive_abandon = False   # main.py sets it True: the player then picks the vehicle to give up (popup); False
                                  # (headless, tests): the least valuable vehicle is dropped at once
    abandon_marks = None          # indices of the vehicles ticked in the popup (None: the suggested ones)

    def abandon_pick_needed(self):
        """True while the player has to choose a vehicle to abandon: a UI is attached, the run is on, and there are
        more vehicles than adults to drive them (with one vehicle left there is nothing to choose). Derived from the
        state, so it can never get stale: the popup (main.py), the journey pause (travel.py) and the drop all read it."""
        return (self.interactive_abandon and self.status == "playing" and self.survivors > 0
                and len(self.vehicles) > 1 and self.adult_count() < len(self.vehicles))

    def abandon_need(self):
        """How many vehicles the convoy must give up at once: one for every vehicle without an adult driver (at least
        one, and never all of them: one vehicle always stays for the player to choose around)."""
        return max(1, min(len(self.vehicles) - 1, len(self.vehicles) - self.adult_count()))

    def suggested_abandon_indices(self):
        """Indices in self.vehicles of the abandon_need() vehicles the automatic rule would drop (the least valuable;
        on a tie the ones furthest back). The popup starts with these ticked."""
        order = sorted(range(len(self.vehicles) - 1, -1, -1), key=lambda i: self._vehicle_value(self.vehicles[i]))
        return sorted(order[:self.abandon_need()])

    def suggested_abandon_index(self):
        """Index in self.vehicles of the single vehicle the automatic rule would drop first."""
        lost = min(reversed(self.vehicles), key=self._vehicle_value)
        return self.vehicles.index(lost)

    def abandon_marked_indices(self):
        """The ticked rows of the popup: the player's ticks, or the suggested vehicles until they tick one. (A stale or
        too long selection falls back to the suggested ones.) May hold fewer than abandon_need() while the player is
        still choosing."""
        marks = self.abandon_marks
        if marks is None or len(marks) > self.abandon_need() or any(not 0 <= i < len(self.vehicles) for i in marks):
            return self.suggested_abandon_indices() if self.vehicles else []
        return list(marks)

    def abandon_pick_index(self):
        """The first ticked row (kept for older callers)."""
        marked = self.abandon_marked_indices()
        return marked[0] if marked else 0

    def abandon_ready(self):
        """True when exactly as many vehicles are ticked as must go: only then does ABANDON work."""
        return self.abandon_pick_needed() and len(self.abandon_marked_indices()) == self.abandon_need()

    def select_abandon(self, index):
        """Tick / untick a vehicle in the popup (nothing is abandoned until abandon_picked_vehicle). Ticking one more
        than must go drops the oldest tick, so with a single vehicle to give up a click simply moves the tick."""
        if not 0 <= index < len(self.vehicles):
            return
        marks = self.abandon_marked_indices()
        if index in marks:
            marks.remove(index)
        else:
            marks.append(index)
            while len(marks) > self.abandon_need():
                marks.pop(0)
        self.abandon_marks = marks

    def abandon_picked_vehicle(self):
        """The popup's ABANDON button: give up every ticked vehicle at once, re-check the convoy and carry on with a
        journey that was paused for the choice. Does nothing until the right number of vehicles is ticked."""
        if not self.abandon_ready():
            return
        lost = [self.vehicles[i] for i in self.abandon_marked_indices()]
        self.abandon_marks = None
        for vehicle in lost:
            self.vehicles.remove(vehicle)
            self.say(f"The {vehicle.vehicle_type} was abandoned: no one left to drive it.")
        self.enforce_limits()
        if self.journey and self.status == "playing" and not self.abandon_pick_needed():
            self.continue_journey()
        elif self.evacuation and self.status == "playing":
            self.continue_evacuation()

    def _drop_undriven_vehicle(self):
        """Give up a vehicle because there is no adult left to drive it. Returns True when one was dropped: the least
        valuable (see _vehicle_value; on a tie the one furthest back in the list). Returns False, dropping nothing,
        when the player has to choose (abandon_pick_needed): the callers stop and the popup takes over."""
        if self.abandon_pick_needed():
            return False
        lost = min(reversed(self.vehicles), key=self._vehicle_value)
        self.vehicles.remove(lost)
        self.say(f"The {lost.vehicle_type} was abandoned: no one left to drive it.")
        return True

    def convoy_health_pct(self):
        """Convoy health is simply the combined health of the vehicles, as a percentage of their maximum."""
        stats = self.convoy_stats()
        if stats["max_health"] <= 0:
            return 0
        pct = int(100 * stats["health"] / stats["max_health"] + 0.5)
        return max(1, pct) if stats["health"] > 0 else 0

    def needs_repair(self):
        return any(vehicle.health < vehicle.stats["health"] for vehicle in self.vehicles)

    # ---- Special abilities (vehicle_data.VEHICLE_ABILITIES; the numbers are in config.py) ----
    def has_ability(self, ability):
        """True while a vehicle with this special ability key ("medical_care", "reinforced_protection",
        "recovery_support") is in the convoy."""
        return any(VEHICLE_ABILITIES.get(vehicle.vehicle_type) == ability for vehicle in self.vehicles)

    def total_defense(self):
        """The convoy's defense: its vehicles' defense stats plus the Reinforced Protection bonus (the Humvee). This, not
        convoy_stats()["defense"] (the plain sum the vehicle table's numbers add up to), is what absorbs damage."""
        bonus = REINFORCED_PROTECTION_BONUS if self.has_ability("reinforced_protection") else 0
        return self.convoy_stats()["defense"] + bonus

    def repair_cost(self):
        """Scrap one REPAIR costs: REPAIR_SCRAP_COST, less with Recovery Support (the Tow/Recovery Truck) and with the
        Corporate / Civilian background (background_rules.py), never below 1."""
        discount = RECOVERY_SUPPORT_REPAIR_DISCOUNT if self.has_ability("recovery_support") else 0
        discount += self.background_repair_discount()
        return max(1, REPAIR_SCRAP_COST - discount)

    def recovery_price(self, vehicle_type):
        """Scrap recovering this vehicle type costs right now: recovery_cost(type), less with Recovery Support and with the
        Corporate background (or the Military one for a military vehicle), never below 1."""
        discount = RECOVERY_SUPPORT_RECOVERY_DISCOUNT if self.has_ability("recovery_support") else 0
        discount += self.background_recovery_discount(vehicle_type)
        return max(1, recovery_cost(vehicle_type) - discount)

    def defense_reduction(self):
        """Percent of ambush damage absorbed by the convoy's total defense (total_defense: includes the Humvee's bonus)."""
        return min(DEFENSE_REDUCTION_CAP, self.total_defense() * DEFENSE_REDUCTION_PER_POINT)

    def current_stop(self):
        """The stop the convoy is at right now."""
        return NODES[self.position]

    def can_recover_here(self):
        """Vehicles can be recovered at stops with a Truck Stop, Repair Depot or Military Installation (compared by site
        key, config.RECOVERY_SITE_KEYS, so renaming a site's display name changes nothing here). In SANDBOX MODE
        vehicles can be recovered and upgraded at any stop."""
        if getattr(self, "sandbox", False):
            return True
        return any(site in RECOVERY_SITE_KEYS for site in self.current_sites())

    def at_military_base(self):
        """True while the convoy is at the Military Base."""
        return is_military_base(self.position)

    def can_recover_type_here(self, vehicle_type):
        """True when this vehicle type can be recovered at the current stop: any stop where recovery is possible for an
        ordinary vehicle, but military vehicles only at the Military Base. SANDBOX MODE recovers anything anywhere."""
        if getattr(self, "sandbox", False):
            return True
        if not self.can_recover_here():
            return False
        return not is_military_vehicle(vehicle_type) or self.at_military_base()

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

        # Update mission progress using the amount actually collected.
        manager = getattr(self, "mission_manager", None)

        if manager and added > 0:
            manager.on_resource_collected(self, resource, added)
            manager.on_resources_changed(self)   # a "hold X" (stockpile) mission may now be met

        return amount - added

    def gain_cargo(self, found):
        """Add several cargo items, sharing limited space fairly.
        Returns the number of units that did not fit.
        """
        found = {
            resource: amount
            for resource, amount in found.items()
            if amount > 0
        }

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

            want = {
                resource: found[resource] - alloc[resource]
                for resource in found
            }

            want_total = sum(want.values())

            if want_total > 0:
                takes = {
                    resource: remaining * want[resource] // want_total
                    for resource in found
                }

                for resource in found:
                    alloc[resource] += takes[resource]

                leftover = remaining - sum(takes.values())

                for resource in sorted(
                    found,
                    key=lambda r: found[r] - alloc[r],
                    reverse=True
                ):
                    if leftover <= 0:
                        break

                    if alloc[resource] < found[resource]:
                        alloc[resource] += 1
                        leftover -= 1

        # Award resources and update mission progress.
        manager = getattr(self, "mission_manager", None)

        for resource, amount in alloc.items():
            setattr(
                self,
                resource,
                getattr(self, resource) + amount
            )

            if manager and amount > 0:
                manager.on_resource_collected(
                    self, resource, amount
                )

        if manager and any(amount > 0 for amount in alloc.values()):
            manager.on_resources_changed(self)   # once, after every resource is in: a "hold X" mission may be met

        return total - sum(alloc.values())

    def trim_supplies(self):
        """Leave behind supplies and fuel that no longer fit after the convoy's capacity shrank. Sandbox mode keeps
        everything (its supplies are deliberately far above capacity and never lowered), so nothing is trimmed or said."""
        if getattr(self, "sandbox", False):
            return
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

    def enforce_limits(self):
        """Keep the convoy consistent: a driver per vehicle, supplies within capacity, a seat per survivor."""

        for _ in range(50):
            if self.status != "playing" or self.survivors <= 0:
                break

            self.survivor_manager.sync_count(self.survivors)

            # Abandon vehicles when there aren't enough adult survivors to drive them (adults are never more than
            # the survivors, so this also covers having fewer survivors than vehicles).
            if self.vehicles and self.adult_count() < len(self.vehicles):
                if self._drop_undriven_vehicle():
                    continue
                return   # the player is choosing which vehicle to give up; abandon_picked_vehicle calls this again

            self.trim_supplies()

            # Check available passenger seats.
            seats = self.convoy_stats()["passengers"]

            if self.survivors > seats:
                extra = self.survivors - seats
                self.survivors -= extra

                self.say(
                    f"{extra} survivor(s) left: "
                    "not enough seats for everyone."
                )
                continue

            break

        # Synchronize survivor records with the game population.
        self.survivor_manager.sync_count(self.survivors)

        if self.survivors <= 0 or not self.vehicles:
            self.check_defeat()   # nobody left to assign
            return

        # Update vehicle assignments.
        self.assign_survivors_to_vehicles()

        self.check_defeat()

    def recover_vehicle(self, vehicle_type):
        """Recover one unowned vehicle at a Truck Stop, Repair Depot or Military Installation. It takes a day: when
        that day would cost a survivor (not enough food or water) the player is asked first (confirm_day_cost)."""
        if self.status != "playing":
            return
        if self.journey:
            self.say("Can't recover a vehicle on the road: wait until the convoy has stopped.")
            return
        if not self.can_recover_here():
            self.say("Vehicle recovery is only possible where there is a Truck Stop, Repair Depot or Military Installation.")
            return
        if vehicle_type not in VEHICLE_SPECS:
            self.say("Unknown vehicle type.")
            return
        if not self.can_recover_type_here(vehicle_type):
            self.say(f"The {vehicle_type} is a military vehicle: it can only be recovered at the Military Base.")
            return
        if vehicle_type in self.owned_vehicle_types():
            self.say(f"Your convoy already has a {vehicle_type}.")
            return
        if self.adult_count() <= len(self.vehicles):
            self.say("No spare adult survivor to drive another vehicle.")
            return

        cost = self.recovery_price(vehicle_type)
        if self.scrap < cost:
            self.say(f"Need {cost} scrap to recover the {vehicle_type}.")
            return

        # Every check above must pass first: YES in the popup runs this method again from the top.
        if not self.confirm_day_cost("recover", "RECOVER VEHICLE", extra_vehicles=1,
                                     retry=lambda: self.recover_vehicle(vehicle_type)):
            return

        self.scrap -= cost
        # A vehicle that was given up earlier comes back with the upgrades it had (vehicle_upgrades).
        vehicle = Vehicle(vehicle_type, self.vehicle_upgrades.get(vehicle_type, ()))
        # Recovered vehicles are damaged and need maintenance, giving recovery a trade-off.
        vehicle.health = max(1, int(vehicle.stats["health"] * 0.7))
        self.vehicles.append(vehicle)
        self.vehicles_recovered += 1
        self.selected_vehicle_type = vehicle_type
        self.assign_survivors_to_vehicles()   # a driver (and seats) for the new vehicle
        self.say(f"Recovered a {vehicle_type} at {self.current_location} for {cost} scrap.")
        self._achieve("on_vehicle_recovered")   # lifetime count for "Salvage Legend" (also re-checks the other counts)
        self.advance_time(1)

    def sandbox_recoverable_types(self):
        """Vehicle types RECOVER ALL would bring in right now (sandbox mode only; empty otherwise): every listed type the
        convoy does not own. Missing adult drivers are spawned by recover_all_vehicles, so they do not limit this."""
        if not getattr(self, "sandbox", False) or self.status != "playing" or self.journey:
            return []
        owned = self.owned_vehicle_types()
        return [name for name in self.listed_vehicle_types() if name not in owned]

    def recover_all_vehicles(self):
        """SANDBOX MODE: recover every vehicle the vehicles screen lists that the convoy does not own, free and without
        spending a day, each at 70% health like a normal recovery (with the upgrades it had). Each vehicle needs an adult
        driver, so when there are not enough, new survivors are spawned until there are (children that turn up on the
        way stay as passengers). Returns how many vehicles were recovered."""
        if not getattr(self, "sandbox", False):
            return 0
        types = self.sandbox_recoverable_types()
        if not types:
            self.say("No vehicle to recover.")
            return 0
        for vehicle_type in types:
            vehicle = Vehicle(vehicle_type, self.vehicle_upgrades.get(vehicle_type, ()))
            vehicle.health = max(1, int(vehicle.stats["health"] * 0.7))
            self.vehicles.append(vehicle)
        self.vehicles_recovered += len(types)
        spawned = 0
        limit = 20 + 10 * len(self.vehicles)   # a safety stop: every spawn should be an adult sooner or later
        while self.adult_count() < len(self.vehicles) and spawned < limit:
            self.survivor_manager.add_survivors(1)
            self.survivors += 1
            spawned += 1
        self.assign_survivors_to_vehicles()
        self.say(f"Sandbox: recovered {len(types)} vehicle(s)."
                 + (f" {spawned} survivor(s) joined to drive them." if spawned else ""))
        return len(types)

    # ---- Upgrades (upgrade_data.py) ----
    UPGRADE_PLACE_MESSAGE = "Upgrades need a stop with a Truck Stop, Repair Depot or Military Installation."
    UPGRADE_ROAD_MESSAGE = "Can't change upgrades on the road: wait until the convoy has stopped."

    vehicle_upgrades = {}         # vehicle type -> installed upgrade ids; kept when the vehicle is lost (reset() makes it fresh)
    selected_upgrade = None       # id of the highlighted row on the upgrade screen (None: the first upgrade)

    def owned_vehicle(self, vehicle_type):
        """The owned vehicle of this type (the convoy holds at most one of each), or None."""
        return next((v for v in self.vehicles if v.vehicle_type == vehicle_type), None)

    def can_upgrade_here(self):
        """Upgrades are installed at the same stops vehicles are recovered at."""
        return self.can_recover_here()

    def available_upgrades(self, vehicle_type=None):
        """The upgrades that fit the vehicle type (default: the one selected on the vehicles screen), installed or not."""
        return upgrades_for(vehicle_type or self.selected_vehicle_type)

    def selected_upgrade_id(self):
        """The highlighted upgrade of the upgrade screen: the chosen one when it fits the selected vehicle, else the first."""
        upgrades = self.available_upgrades()
        if not upgrades:
            return None
        ids = [upgrade["id"] for upgrade in upgrades]
        return self.selected_upgrade if self.selected_upgrade in ids else ids[0]

    def select_upgrade(self, upgrade_id):
        """Highlight an upgrade on the upgrade screen (nothing is installed)."""
        if upgrade_id in [upgrade["id"] for upgrade in self.available_upgrades()]:
            self.selected_upgrade = upgrade_id

    def upgrade_problem(self, upgrade_id=None):
        """Why the upgrade (default: the highlighted one) cannot be installed right now, as a message, or "" when it can."""
        if self.status != "playing":
            return "The run is over."
        if self.journey:
            return self.UPGRADE_ROAD_MESSAGE
        vehicle = self.owned_vehicle(self.selected_vehicle_type)
        if vehicle is None:
            return f"You don't own a {self.selected_vehicle_type}."
        upgrade = get_upgrade(upgrade_id or self.selected_upgrade_id())
        if upgrade is None or not vehicle.can_install(upgrade["id"]):
            if upgrade and vehicle.has_upgrade(upgrade["id"]):
                return "Already installed."
            blocker = vehicle.blocking_upgrade(upgrade["id"]) if upgrade else None
            if blocker:   # one trailer per vehicle
                return f"Uninstall the {get_upgrade(blocker)['name']} first: one trailer per vehicle."
            return "That upgrade does not fit."
        if not self.can_upgrade_here():
            return self.UPGRADE_PLACE_MESSAGE
        price = self.upgrade_price(upgrade)
        if self.scrap < price:
            return f"Need {price} scrap for the {upgrade['name']}."
        return ""

    def install_upgrade(self, upgrade_id=None):
        """Install an upgrade (default: the highlighted one) on the selected vehicle for its scrap cost. It takes a day:
        when that day would cost a survivor (not enough food or water) the player is asked first (confirm_day_cost).
        The vehicle's stats, the convoy totals and (for a trailer) its picture change at once. The upgrade is remembered
        for the vehicle type, so a vehicle that is abandoned and recovered later keeps it. Returns True when installed."""
        upgrade_id = upgrade_id or self.selected_upgrade_id()
        problem = self.upgrade_problem(upgrade_id)
        if problem:
            self.say(problem)
            return False
        upgrade = get_upgrade(upgrade_id)
        vehicle = self.owned_vehicle(self.selected_vehicle_type)
        # Every check above must pass first: YES in the popup runs this method again from the top.
        if not self.confirm_day_cost("install", "INSTALL UPGRADE",
                                     retry=lambda: self.install_upgrade(upgrade_id)):
            return False
        price = self.upgrade_price(upgrade, vehicle.vehicle_type)   # Military Logistics: cheaper on military vehicles
        self.scrap -= price
        vehicle.install_upgrade(upgrade_id)
        self.vehicle_upgrades.setdefault(vehicle.vehicle_type, []).append(upgrade_id)
        self.assign_survivors_to_vehicles()   # more seats change who rides where
        self.say(f"Installed {upgrade['name']} on the {vehicle.vehicle_type} for {price} scrap.")
        self.advance_time(1)
        return True

    uninstall_pending = None      # (vehicle type, upgrade id) while the "uninstall?" popup is open

    def uninstall_problem(self, upgrade_id=None):
        """Why the upgrade (default: the highlighted one) cannot be uninstalled right now, or "" when it can."""
        if self.status != "playing":
            return "The run is over."
        if self.journey:
            return self.UPGRADE_ROAD_MESSAGE
        vehicle = self.owned_vehicle(self.selected_vehicle_type)
        if vehicle is None:
            return f"You don't own a {self.selected_vehicle_type}."
        upgrade_id = upgrade_id or self.selected_upgrade_id()
        if upgrade_id is None or not vehicle.has_upgrade(upgrade_id):
            return "Not installed."
        if not self.can_upgrade_here():
            return self.UPGRADE_PLACE_MESSAGE
        return ""

    def uninstall_losses(self, vehicle_type, upgrade_id):
        """What the convoy would have to leave behind if the upgrade came off: {"survivors": n, "supplies": n, "fuel": n}
        (zeros when nothing). The same rules enforce_limits applies, worked out in advance so the popup can warn."""
        out = {"survivors": 0, "supplies": 0, "fuel": 0}
        vehicle = self.owned_vehicle(vehicle_type)
        new = vehicle.stats_without(upgrade_id) if vehicle else None
        if new is None:
            return out
        caps = self.convoy_stats()
        old = vehicle.stats
        out["survivors"] = max(0, self.survivors - (caps["passengers"] - old["passengers"] + new["passengers"]))
        if not getattr(self, "sandbox", False):   # sandbox mode never trims supplies (trim_supplies)
            out["supplies"] = max(0, self.cargo_used() - (caps["cargo"] - old["cargo"] + new["cargo"]))
            out["fuel"] = max(0, self.fuel - (caps["fuel_capacity"] - old["fuel_capacity"] + new["fuel_capacity"]))
        return out

    def uninstall_text(self):
        """The message of the "uninstall?" popup: what comes off, that it is free, and anything that would be lost."""
        if not self.uninstall_pending:
            return "Uninstall this upgrade?"
        vehicle_type, upgrade_id = self.uninstall_pending
        upgrade = get_upgrade(upgrade_id)
        text = f"Remove the {upgrade['name']} from the {vehicle_type}? It costs nothing and takes no time. "
        lost = self.uninstall_losses(vehicle_type, upgrade_id)
        parts = []
        if lost["survivors"]:
            parts.append(f"{lost['survivors']} survivor(s) would leave (no seats)")
        if lost["supplies"]:
            parts.append(f"{lost['supplies']} supplies would be left behind")
        if lost["fuel"]:
            parts.append(f"{lost['fuel']} fuel would be left behind")
        if parts:
            text += "Warning: " + ", ".join(parts) + ". "
        return text + "You can install it again later."

    def request_uninstall(self, upgrade_id=None):
        """UNINSTALL UPGRADE: open the "are you sure?" popup (YES runs uninstall_upgrade, see confirm_yes)."""
        upgrade_id = upgrade_id or self.selected_upgrade_id()
        problem = self.uninstall_problem(upgrade_id)
        if problem:
            self.say(problem)
            return False
        self.uninstall_pending = (self.selected_vehicle_type, upgrade_id)
        self.ask_confirm("uninstall")
        return True

    def uninstall_upgrade(self, upgrade_id=None, vehicle_type=None):
        """Take an upgrade off a vehicle. No scrap is charged or refunded and no day passes. The upgrade is forgotten for
        the vehicle type too (vehicle_upgrades), and enforce_limits then leaves behind what no longer fits (seats, cargo,
        fuel). Reinstalling works as usual (install_upgrade). Returns True when removed."""
        if self.uninstall_pending and not upgrade_id:
            vehicle_type, upgrade_id = self.uninstall_pending
        self.uninstall_pending = None
        vehicle_type = vehicle_type or self.selected_vehicle_type
        vehicle = self.owned_vehicle(vehicle_type)
        if vehicle is None or not vehicle.has_upgrade(upgrade_id):
            return False
        upgrade = get_upgrade(upgrade_id)
        vehicle.uninstall_upgrade(upgrade_id)
        remembered = self.vehicle_upgrades.get(vehicle_type)
        if remembered and upgrade_id in remembered:
            remembered.remove(upgrade_id)
        self.say(f"Uninstalled {upgrade['name']} from the {vehicle_type}.")
        self.enforce_limits()
        return True

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

    def repair(self):
        """Repair the convoy: only while stopped at a destination, and it takes a day (the horde keeps coming). When
        that day would cost a survivor (not enough food or water) the player is asked first (confirm_day_cost)."""
        if self.status != "playing":
            return
        if self.journey:
            self.say("Can't repair on the road: wait until the convoy has stopped.")
            return
        cost = self.repair_cost()
        if self.scrap < cost:
            self.say(f"Need {cost} scrap to repair the convoy.")
            return
        if not self.needs_repair():
            self.say("The convoy is already in good condition.")
            return
        # Every check above must pass first: YES in the popup runs this method again from the top.
        if not self.confirm_day_cost("repair", "REPAIR", retry=self.repair):
            return
        self.scrap -= cost
        for vehicle in self.vehicles:
            maximum = vehicle.stats["health"]
            restored = int(maximum * REPAIR_FRACTION * self.repair_multiplier(vehicle) + 0.5)   # Military: more for its own
            vehicle.health = min(maximum, vehicle.health + restored)
        self.say(f"Used {cost} scrap to repair {int(REPAIR_FRACTION * 100)}% of every vehicle's health.")
        self.improvisation_refund()   # Civilian background: some repairs give a scrap back (background_rules.py)
        self.advance_time(1)

    def damage_vehicles(self, percent, keep_one=False, quiet=False):
        """Damage every vehicle by a percentage of its own maximum health, then remove the ones that are wrecked
        (remove_wrecks). Returns the vehicles that were removed. `keep_one` and `quiet` are passed on."""
        for vehicle in self.vehicles:
            hit = max(1, int(vehicle.stats["health"] * percent / 100 + 0.5))
            vehicle.health = max(0, vehicle.health - hit)
        return self.remove_wrecks(keep_one=keep_one, quiet=quiet)

    def remove_wrecks(self, keep_one=False, quiet=False):
        """Take the vehicles at 0 health out of the convoy (a wreck would still give seats, cargo, speed and a driver
        slot). Returns the removed vehicles.

        When EVERY vehicle is wrecked nothing is removed and check_defeat ends the run ("The convoy has broken down"),
        unless `keep_one` is set (the horde's attacks): then the most valuable wreck is kept running at 1 health, so
        the run ends only when no survivor is left. Unless `quiet`, each wreck is logged and the convoy is re-checked
        (enforce_limits: drivers, supplies, seats); a caller that does that itself passes quiet=True."""
        wrecked = [vehicle for vehicle in self.vehicles if vehicle.health <= 0]
        if not wrecked:
            return []
        if len(wrecked) == len(self.vehicles):
            if not keep_one:
                return []
            spared = max(wrecked, key=self._vehicle_value)
            spared.health = 1   # battered but still running
            wrecked.remove(spared)
        for vehicle in wrecked:
            self.vehicles.remove(vehicle)
            self.vehicles_wrecked = getattr(self, "vehicles_wrecked", 0) + 1   # destroyed, not abandoned: "Scorched Earth"
            if not quiet:
                self.say(f"The {vehicle.vehicle_type} was wrecked and left behind.")
        if wrecked and not quiet:
            self.enforce_limits()
        return wrecked

    def recruit_survivors(self, count):
        """Take up to `count` people aboard (scavenging finds and event rescues both come here). Only as many join as
        there are free seats; a group of two or more is added as a family. Re-assigns drivers and seats and credits
        rescue missions with the number who actually joined. Returns how many joined (0 when there is no room); the
        caller says what happened."""
        free_seats = max(0, self.convoy_stats()["passengers"] - self.survivors)
        joined = min(count, free_seats)
        if joined <= 0:
            return 0
        if joined >= 2:
            self.survivor_manager.add_family(joined)
        else:
            self.survivor_manager.add_survivors(joined)
        self.survivors += joined
        self.assign_survivors_to_vehicles()
        manager = getattr(self, "mission_manager", None)
        if manager:
            manager.on_survivors_recruited(self, joined)
        return joined

    def assign_survivors_to_vehicles(self):
        """Assign adult survivors as drivers and distribute remaining survivors as passengers."""

        survivors = self.survivor_manager.get_survivors()

        # Only survivors who can drive get a vehicle (the same rule as adult_count).
        adult_survivors = [
            survivor for survivor in survivors
            if survivor["can_drive"]
        ]

        if not survivors:
            # Nobody is left: the run is over (check_defeat says so); the vehicles are not dropped one by one.
            self.survivor_vehicles = {}
            self.check_defeat()
            return

        if self.vehicles and len(adult_survivors) < len(self.vehicles):
            # Not enough adults for every vehicle (children came along, or adults were lost): the vehicles nobody can
            # drive are abandoned, never an error. enforce_limits then also trims supplies and seats to what is left
            # and calls this again, which finds nothing more to drop.
            while self.vehicles and len(adult_survivors) < len(self.vehicles):
                if not self._drop_undriven_vehicle():
                    return   # the player picks the vehicle (popup); enforce_limits runs after the pick
            self.enforce_limits()
            return

        if not self.vehicles:
            self.survivor_vehicles = {}
            self.check_defeat()
            return

        self.survivor_vehicles = {}
        survivor_index = 0

        # Assign one adult driver to every vehicle.
        for vehicle in self.vehicles:
            survivor = adult_survivors[survivor_index]

            self.survivor_vehicles[survivor["id"]] = vehicle.vehicle_type
            survivor_index += 1

        # Collect everyone who hasn't been assigned yet.
        assigned_ids = set(self.survivor_vehicles)

        remaining_survivors = [
            survivor for survivor in survivors
            if survivor["id"] not in assigned_ids
        ]

        # Distribute remaining survivors into passenger seats.
        for vehicle in self.vehicles:
            capacity = max(0, vehicle.stats["passengers"] - 1)

            for _ in range(capacity):
                if not remaining_survivors:
                    break

                survivor = remaining_survivors.pop(0)

                self.survivor_vehicles[survivor["id"]] = vehicle.vehicle_type
