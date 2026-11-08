"""Player background rules of THE LAST CONVOY (design doc section 21): what each background's ability and trait does.

The text and the numbers are in background_data.py (BACKGROUNDS, the constants below it); this mixin only reads them, so
the rest of the game asks a question ("what does a repair cost?", "does this person join?") and never checks the
background's name. Pygame-free, like the rest of the game package.

    Military    Military Logistics      military vehicles are cheaper to recover and heal more per REPAIR
    Police      Emergency Response      "emergency" events cost less time (horde gap)
    Government  Resource Coordination   a scavenge search may yield extra supplies
    Corporate   Fleet Management        REPAIR and recovering a vehicle cost less scrap
    Criminal    Underworld Connections  some sites may hold a stash; events with "background": "Criminal" appear
                Untrusted Reputation    fewer people join; "settlement" events are sometimes skipped
    Civilian    Improvisation           every other REPAIR gives some scrap back
"""
import random

from background_data import (BACKGROUNDS, CIVILIAN_REFUND_EVERY, CIVILIAN_REPAIR_REFUND, CORPORATE_RECOVERY_DISCOUNT,
                             CORPORATE_REPAIR_DISCOUNT, CRIMINAL_RECRUIT_FACTOR, CRIMINAL_SETTLEMENT_REFUSAL_CHANCE,
                             CRIMINAL_STASH_CHANCE, CRIMINAL_STASH_FUEL, CRIMINAL_STASH_SCRAP, CRIMINAL_STASH_SITES,
                             DEFAULT_BACKGROUND, GOVERNMENT_SCAVENGE_CHANCE, GOVERNMENT_SCAVENGE_SHARE,
                             MILITARY_RECOVERY_DISCOUNT, MILITARY_REPAIR_BONUS, MILITARY_UPGRADE_DISCOUNT,
                             MILITARY_VEHICLE_TYPES, POLICE_EMERGENCY_TIME_FACTOR)


class BackgroundMixin:
    """Questions and effects for the chosen player background (Game.background)."""

    # ---- which background ---------------------------------------------------------------------------------------
    def background_data(self):
        """The BACKGROUNDS entry of the chosen background (the default one if the name is unknown)."""
        return BACKGROUNDS.get(self.background) or BACKGROUNDS[DEFAULT_BACKGROUND]

    def has_background_ability(self, key):
        """True when the chosen background's ability has this "ability_key" (e.g. "fleet_management")."""
        return self.background_data().get("ability_key") == key

    def has_background_trait(self, key):
        """True when the chosen background's trait has this "trait_key" (e.g. "untrusted_reputation")."""
        return self.background_data().get("trait_key") == key

    def is_background(self, names):
        """True when the chosen background is this name or one of these names (an event's "background" requirement)."""
        names = [names] if isinstance(names, str) else list(names)
        return (self.background if self.background in BACKGROUNDS else DEFAULT_BACKGROUND) in names

    # ---- repairs and recovery (convoy.py) -----------------------------------------------------------------------
    def background_repair_discount(self):
        """Scrap less one REPAIR costs for the background (Fleet Management)."""
        return CORPORATE_REPAIR_DISCOUNT if self.has_background_ability("fleet_management") else 0

    def improvisation_refund(self):
        """Call once after every paid REPAIR. Improvisation (Civilian): every CIVILIAN_REFUND_EVERY-th repair of the run
        gives CIVILIAN_REPAIR_REFUND scrap back (and says so). Returns the scrap refunded (0 for other backgrounds)."""
        if not self.has_background_ability("improvisation"):
            return 0
        self.repairs_done = getattr(self, "repairs_done", 0) + 1
        if self.repairs_done % CIVILIAN_REFUND_EVERY:
            return 0
        self.scrap += CIVILIAN_REPAIR_REFUND
        self.say(f"Improvisation: spare parts made from scraps, {CIVILIAN_REPAIR_REFUND} scrap back.")
        return CIVILIAN_REPAIR_REFUND

    def upgrade_price(self, upgrade, vehicle_type=None):
        """Scrap installing this upgrade costs right now (upgrade_data cost; Military Logistics: less on a military
        vehicle), never below 1. vehicle_type defaults to the one selected on the vehicles screen."""
        vehicle_type = vehicle_type or self.selected_vehicle_type
        discount = MILITARY_UPGRADE_DISCOUNT if (self.has_background_ability("military_logistics")
                                                  and vehicle_type in MILITARY_VEHICLE_TYPES) else 0
        return max(1, upgrade["cost"] - discount)

    def background_recovery_discount(self, vehicle_type):
        """Scrap less recovering a vehicle of this type costs for the background (Fleet Management; Military
        Logistics for military vehicles)."""
        if self.has_background_ability("fleet_management"):
            return CORPORATE_RECOVERY_DISCOUNT
        if self.has_background_ability("military_logistics") and vehicle_type in MILITARY_VEHICLE_TYPES:
            return MILITARY_RECOVERY_DISCOUNT
        return 0

    def repair_multiplier(self, vehicle):
        """How much more health one REPAIR gives this vehicle (1.0 normally; Military Logistics: military vehicles)."""
        if self.has_background_ability("military_logistics") and vehicle.vehicle_type in MILITARY_VEHICLE_TYPES:
            return 1.0 + MILITARY_REPAIR_BONUS
        return 1.0

    # ---- scavenging (scavenge.py) -------------------------------------------------------------------------------
    def background_scavenge_bonus(self, fuel, cargo, site=None):
        """Add what the background's luck gives one scavenge search of the site with this key (map_data.SITES). `fuel`
        is the units of fuel found and `cargo` the {resource: units} found; returns the new (fuel, cargo) (the dict is a
        copy) and says what happened.

        Resource Coordination (Government): chance of a bonus of GOVERNMENT_SCAVENGE_SHARE of every find (at least 1 of
        each resource that was found). Underworld Connections (Criminal): at the CRIMINAL_STASH_SITES, a chance of a
        stash of fuel and scrap."""
        cargo = dict(cargo)
        if self.has_background_ability("resource_coordination") and random.random() < GOVERNMENT_SCAVENGE_CHANCE:
            extra = False
            if fuel > 0:
                fuel += max(1, int(fuel * GOVERNMENT_SCAVENGE_SHARE + 0.5))
                extra = True
            for resource, amount in list(cargo.items()):
                if amount > 0:
                    cargo[resource] = amount + max(1, int(amount * GOVERNMENT_SCAVENGE_SHARE + 0.5))
                    extra = True
            if extra:
                self.say("Resource Coordination: your contacts point you to extra supplies.")
        if (self.has_background_ability("underworld_connections") and site in CRIMINAL_STASH_SITES
                and random.random() < CRIMINAL_STASH_CHANCE):
            fuel += self.scaled_yield(random.randint(*CRIMINAL_STASH_FUEL))
            cargo["scrap"] = cargo.get("scrap", 0) + self.scaled_yield(random.randint(*CRIMINAL_STASH_SCRAP))
            self.say("Underworld Connections: an old contact had a stash hidden here.")
        return fuel, cargo

    # ---- recruiting (scavenge.py, effect_handler.fitted_effects) ------------------------------------------------
    def recruit_chance_factor(self):
        """Multiplier on the chance that a group of survivors is found (Untrusted Reputation: below 1)."""
        return CRIMINAL_RECRUIT_FACTOR if self.has_background_trait("untrusted_reputation") else 1.0

    def willing_recruits(self, count):
        """How many of `count` people who could join actually do: each one rolls recruit_chance_factor()."""
        factor = self.recruit_chance_factor()
        if factor >= 1.0:
            return max(0, count)
        return sum(1 for _ in range(max(0, count)) if random.random() < factor)

    # ---- events (event_manager.py) ------------------------------------------------------------------------------
    def settlement_refuses(self, event):
        """True when this event is a settlement ("settlement": True) that will not deal with the convoy this time
        (Untrusted Reputation). Rolled each time an event is drawn, so it is a chance, not a ban."""
        return bool(event.get("settlement")) and self.has_background_trait("untrusted_reputation") \
            and random.random() < CRIMINAL_SETTLEMENT_REFUSAL_CHANCE

    def adjust_event_effects(self, event, effects):
        """(effects, note) for an event choice after the background's say. Emergency Response (Police): in an event
        marked "emergency": True the horde-gap losses (negative "horde_gap" amounts) are cut by
        POLICE_EMERGENCY_TIME_FACTOR, never to less than 1 km. `note` is "" when nothing changed."""
        if not (event or {}).get("emergency") or not self.has_background_ability("emergency_response"):
            return effects, ""
        changed = False
        adjusted = []
        for effect in effects:
            amount = effect.get("amount", 0)
            if effect.get("type") == "horde_gap" and isinstance(amount, int) and amount < 0:
                cut = -max(1, int(-amount * POLICE_EMERGENCY_TIME_FACTOR + 0.5))
                if cut != amount:
                    effect = dict(effect, amount=cut)
                    changed = True
            adjusted.append(effect)
        return (adjusted, "Emergency Response: your training saved some time.") if changed else (effects, "")
