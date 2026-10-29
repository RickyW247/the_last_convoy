
# The Last Convoy
# Survivor identity generator

import random
import uuid

from survivor_data import (
    MALE_FIRST_NAMES,
    FEMALE_FIRST_NAMES,
    LAST_NAMES,
)

MIN_SURVIVOR_AGE = 1
MAX_SURVIVOR_AGE = 75


def generate_survivor(last_name=None, age=None):
    """Generate one survivor with a random identity."""

    gender = random.choice(["Male", "Female"])

    if gender == "Male":
        first_name = random.choice(MALE_FIRST_NAMES)
    else:
        first_name = random.choice(FEMALE_FIRST_NAMES)

    if last_name is None:
        last_name = random.choice(LAST_NAMES)

    if age is None:
        age = random.randint(
            MIN_SURVIVOR_AGE,
            MAX_SURVIVOR_AGE
        )

    return {
        "id": str(uuid.uuid4()),
        "first_name": first_name,
        "last_name": last_name,
        "age": age,
        "gender": gender,
    }


def generate_family(size):
    """Generate a group of survivors sharing one surname."""

    if size < 2:
        raise ValueError(
            "A family group must contain at least 2 people."
        )

    family_name = random.choice(LAST_NAMES)

    return [
        generate_survivor(last_name=family_name)
        for _ in range(size)
    ]


def generate_survivors(amount):
    """Generate a specified number of individual survivors."""

    if amount < 0:
        raise ValueError(
            "Amount cannot be negative."
        )

    return [
        generate_survivor()
        for _ in range(amount)
    ]
