
# The Last Convoy
# Survivor population manager

import random

from survivor_generator import (
    generate_survivor,
    generate_survivors,
    generate_family,
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

    def get_survivors(self):
        """Return a copy of the active survivor list."""

        return self.survivors.copy()

    def get_survivor(self, survivor_id):
        """Find a survivor by unique ID."""

        for survivor in self.survivors:
            if survivor["id"] == survivor_id:
                return survivor

        return None
