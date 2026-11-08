"""Vehicles of THE LAST CONVOY: the owned-vehicle class and the scrap cost of recovering one."""
from config import DEFAULT_RECOVERY_COST
from upgrade_data import apply_effects, conflicting_upgrade, fits, get_upgrade, look_for, trailer_for
from vehicle_data import RECOVERY_COSTS, VEHICLE_SPECS


def recovery_cost(vehicle_type):
    """Scrap needed to recover a vehicle of this type."""
    return RECOVERY_COSTS.get(vehicle_type, DEFAULT_RECOVERY_COST)


class Vehicle:
    """An owned vehicle instance: a copy of its baseline specifications plus the upgrades installed on it.

    `stats` always holds the current numbers (baseline + every installed upgrade), so the convoy totals and the screens
    just read it. `upgrades` lists the installed upgrade ids in the order they were installed (upgrade_data.py).
    """
    def __init__(self, vehicle_type, upgrades=()):
        self.vehicle_type = vehicle_type
        self.stats = dict(VEHICLE_SPECS[vehicle_type])
        self.upgrades = []
        for upgrade_id in upgrades:   # a vehicle recovered with the upgrades it had (Game.vehicle_upgrades)
            self._apply(upgrade_id)
        self.health = self.stats["health"]

    @property
    def name(self):
        return self.vehicle_type

    @property
    def sprite_type(self):
        """The name of the sprite this vehicle is drawn with: its own type, or the look of an installed upgrade."""
        return look_for(self.vehicle_type, self.upgrades)

    @property
    def trailer(self):
        """The name of the trailer sprite this vehicle tows (drawn behind it), or None."""
        return trailer_for(self.upgrades)

    def has_upgrade(self, upgrade_id):
        return upgrade_id in self.upgrades

    def blocking_upgrade(self, upgrade_id):
        """The installed upgrade that stops `upgrade_id` from being installed (a vehicle tows only one trailer), or None."""
        upgrade = get_upgrade(upgrade_id)
        if upgrade is None or not fits(upgrade, self.vehicle_type):
            return None
        return conflicting_upgrade(upgrade, self.upgrades)

    def can_install(self, upgrade_id):
        upgrade = get_upgrade(upgrade_id)
        return (upgrade is not None and fits(upgrade, self.vehicle_type) and upgrade_id not in self.upgrades
                and conflicting_upgrade(upgrade, self.upgrades) is None)

    def _apply(self, upgrade_id):
        """Add the upgrade's effects to the stats. Returns False (changing nothing) for an unknown, unfitting or already
        installed upgrade."""
        if not self.can_install(upgrade_id):
            return False
        self.stats = apply_effects(self.stats, get_upgrade(upgrade_id)["effects"])
        self.upgrades.append(upgrade_id)
        return True

    def stats_without(self, upgrade_id):
        """The stats this vehicle would have with `upgrade_id` removed (nothing is changed), or None when it is not installed."""
        if upgrade_id not in self.upgrades:
            return None
        stats = dict(VEHICLE_SPECS[self.vehicle_type])
        for other in self.upgrades:
            if other != upgrade_id:
                stats = apply_effects(stats, get_upgrade(other)["effects"])
        return stats

    def uninstall_upgrade(self, upgrade_id):
        """Remove an installed upgrade (Game.uninstall_upgrade asks first; it costs nothing and takes no time). The stats
        are rebuilt from the baseline plus the upgrades that stay. Maximum health that goes away takes the same amount of
        current health with it (what install_upgrade added), so uninstalling armour never heals the vehicle and
        reinstalling it gives back exactly what was lost. Returns True when it was removed."""
        stats = self.stats_without(upgrade_id)
        if stats is None:
            return False
        lost = self.stats["health"] - stats["health"]
        self.stats = stats
        self.upgrades.remove(upgrade_id)
        if lost > 0:
            self.health -= lost
        self.health = max(1, min(self.health, self.stats["health"]))
        return True

    def install_upgrade(self, upgrade_id):
        """Install an upgrade (the scrap is charged by Game.install_upgrade). Extra maximum health arrives as extra
        current health too, so armour is not a repair bill. Returns True when it was installed."""
        old_max = self.stats["health"]
        if not self._apply(upgrade_id):
            return False
        gained = self.stats["health"] - old_max
        if gained > 0:
            self.health += gained
        self.health = min(self.health, self.stats["health"])
        return True
