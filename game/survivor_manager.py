# The Last Convoy
# Survivor population manager

import random

from .survivor_data import SPECIAL_SURVIVORS, SPECIAL_SERIES
from .survivor_generator import (
    generate_survivor,
    generate_survivors,
    generate_family,
    generate_special_survivor,
    generate_special_family,
)


class SurvivorManager:

    def __init__(self, starting_count=0):
        """Initialize the survivor population."""

        if starting_count < 0:
            raise ValueError(
                "Starting count cannot be negative."
            )

        self.survivors = generate_survivors(starting_count)

    @property
    def count(self):
        """Return the current number of survivors."""

        return len(self.survivors)

    def add_survivors(self, amount):
        """Add newly recruited individual survivors."""

        if amount < 0:
            raise ValueError(
                "Amount cannot be negative."
            )

        new_survivors = generate_survivors(amount)
        self.survivors.extend(new_survivors)

        return new_survivors

    def add_family(self, size):
        """Add a family group sharing one surname."""

        family = generate_family(size)
        self.survivors.extend(family)

        return family

    def _present_special_keys(self):
        """Return keys of special survivors currently in the convoy."""

        present = {
            (s["first_name"], s["last_name"])
            for s in self.survivors
            if s.get("is_special")
        }

        return {
            key
            for key, data in SPECIAL_SURVIVORS.items()
            if (data["first_name"], data["last_name"]) in present
        }

    def get_available_special_keys(self):
        """Return keys of special survivors not currently in the convoy."""

        present = self._present_special_keys()

        return [key for key in SPECIAL_SURVIVORS if key not in present]

    def add_special_survivor(self, key=None):
        """Add a special survivor (random available one if no key given).

        Each special survivor can only be in the convoy once at a time.
        Returns the new survivor, or None if none are available.
        """

        available = self.get_available_special_keys()

        if key is None:
            if not available:
                return None
            key = random.choice(available)
        elif key not in available:
            return None

        survivor = generate_special_survivor(key)
        self.survivors.append(survivor)

        return survivor

    def convert_to_special(self, survivor_id, key):
        """Turn the survivor record with this id into the special survivor `key`.

        The fixed identity (name, gender, age, child / driver flags, series) comes from generate_special_survivor; the
        record keeps its own id and any extra fields other modules added to it (conditions). Used by the special
        survivor events, so the game's survivor count stays in step with the records. Returns the record, or None when
        the id is unknown or that special survivor is already in the convoy.
        """

        if key not in self.get_available_special_keys():
            return None

        record = self.get_survivor(survivor_id)

        if record is None:
            return None

        identity = generate_special_survivor(key)
        identity.pop("id")
        record.update(identity)

        return record

    def _remaining_in_series(self, series_key):
        """Return how many members of a series are not in the convoy."""

        present = self._present_special_keys()

        return sum(
            1
            for key in SPECIAL_SERIES[series_key]["members"]
            if key not in present
        )

    def get_available_special_series(self, size=1):
        """Return series keys with at least `size` members not aboard."""

        return [
            series_key
            for series_key in SPECIAL_SERIES
            if self._remaining_in_series(series_key) >= size
        ]

    def add_special_family(self, series_key=None, size=None):
        """Add members of one series as a group.

        series_key: which series (random eligible one if None).
        size: how many members to add (random picks from those not
              already aboard). If None, every remaining member is added.

        Members already in the convoy are never duplicated. The family
        is only added if the remaining members of the series are at
        least `size`. Returns the list of newly added survivors, or an
        empty list if the series is unknown or too few members remain.
        """

        if size is not None and size < 1:
            raise ValueError(
                "Family size must be at least 1."
            )

        needed = 1 if size is None else size
        available = self.get_available_special_series(needed)

        if series_key is None:
            if not available:
                return []
            series_key = random.choice(available)
        elif series_key not in available:
            return []

        family = generate_special_family(
            series_key,
            exclude_keys=self._present_special_keys(),
            size=size,
        )
        self.survivors.extend(family)

        return family

    def remove_survivors(self, amount):
        """Remove a random selection of survivors."""

        if amount < 0:
            raise ValueError(
                "Amount cannot be negative."
            )

        if amount > self.count:
            raise ValueError(
                "Cannot remove more survivors than exist."
            )

        removed = random.sample(
            self.survivors,
            amount
        )

        removed_ids = {
            survivor["id"] for survivor in removed
        }

        self.survivors = [
            survivor
            for survivor in self.survivors
            if survivor["id"] not in removed_ids
        ]

        return removed

    def sync_count(self, target_count):
        """Synchronize survivor records with the game's survivor count."""

        if target_count < 0:
            raise ValueError("Survivor count cannot be negative.")

        difference = target_count - self.count

        if difference > 0:
            self.add_survivors(difference)
        elif difference < 0:
            self.remove_survivors(-difference)

    def get_survivors(self):
        """Return a copy of the active survivor list."""

        return self.survivors.copy()

    def get_survivor(self, survivor_id):
        """Find a survivor by unique ID."""

        for survivor in self.survivors:
            if survivor["id"] == survivor_id:
                return survivor

        return None
