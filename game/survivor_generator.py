# The Last Convoy
# Survivor identity generator

import random
import uuid

from .survivor_data import (
    MALE_FIRST_NAMES,
    FEMALE_FIRST_NAMES,
    LAST_NAMES,
    SPECIAL_SURVIVORS,
    SPECIAL_SERIES,
)

MIN_SURVIVOR_AGE = 18
MAX_SURVIVOR_AGE = 75

MIN_CHILD_AGE = 1
MAX_CHILD_AGE = 17


def _pick_first_name(gender, last_name):
    """Pick a first name that differs from the surname."""

    pool = MALE_FIRST_NAMES if gender == "Male" else FEMALE_FIRST_NAMES

    # Re-roll on a clash (e.g. "Gordon Gordon"). Safe because the
    # name pools are far larger than the overlap with LAST_NAMES.
    while True:
        first_name = random.choice(pool)
        if first_name != last_name:
            return first_name


def _build_person(first_name, last_name, age, gender,
                  is_special=False, series=None):
    """Build a person dict. Adults and children share identical keys."""

    is_child = age < MIN_SURVIVOR_AGE

    return {
        "id": str(uuid.uuid4()),
        "first_name": first_name,
        "last_name": last_name,
        "age": age,
        "gender": gender,
        "is_child": is_child,
        "can_drive": not is_child,
        "is_special": is_special,
        "series": series,
    }


def generate_survivor(last_name=None, age=None):
    """Generate one adult survivor with a random identity."""

    gender = random.choice(["Male", "Female"])

    if last_name is None:
        last_name = random.choice(LAST_NAMES)

    if age is None:
        age = random.randint(
            MIN_SURVIVOR_AGE,
            MAX_SURVIVOR_AGE
        )

    first_name = _pick_first_name(gender, last_name)

    return _build_person(first_name, last_name, age, gender)


def generate_child(last_name):
    """Generate one child as part of a family."""

    gender = random.choice(["Male", "Female"])

    age = random.randint(
        MIN_CHILD_AGE,
        MAX_CHILD_AGE
    )

    first_name = _pick_first_name(gender, last_name)

    return _build_person(first_name, last_name, age, gender)


def generate_family(size):
    """Generate a family containing adults and potentially children."""

    if size < 2:
        raise ValueError(
            "A family group must contain at least 2 people."
        )

    family_name = random.choice(LAST_NAMES)

    family = []

    # Every family must have at least one adult.
    family.append(
        generate_survivor(last_name=family_name)
    )

    # Generate the remaining family members.
    for _ in range(size - 1):

        # 40% chance of generating a child.
        if random.random() < 0.4:
            family.append(
                generate_child(last_name=family_name)
            )
        else:
            family.append(
                generate_survivor(last_name=family_name)
            )

    return family


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


def generate_special_survivor(key):
    """Generate a special survivor with a fixed identity.

    Not used by the normal generators; only called explicitly.
    """

    if key not in SPECIAL_SURVIVORS:
        raise ValueError(
            f"Unknown special survivor: {key}"
        )

    data = SPECIAL_SURVIVORS[key]

    return _build_person(
        data["first_name"],
        data["last_name"],
        data["age"],
        data["gender"],
        is_special=True,
        series=_series_of(key),
    )


def _series_of(key):
    """Return the series key a special survivor belongs to (or None)."""

    for series_key, series in SPECIAL_SERIES.items():
        if key in series["members"]:
            return series_key

    return None


def generate_special_family(series_key, exclude_keys=(), size=None):
    """Generate members of one series as a special family.

    Members whose keys are in exclude_keys are skipped (used by the
    manager to avoid duplicating characters already in the convoy).
    If size is given, that many of the remaining members are picked at
    random; otherwise every remaining member is generated.
    """

    if series_key not in SPECIAL_SERIES:
        raise ValueError(
            f"Unknown special series: {series_key}"
        )

    keys = [
        key
        for key in SPECIAL_SERIES[series_key]["members"]
        if key not in exclude_keys
    ]

    if size is not None:
        if size < 1:
            raise ValueError(
                "Family size must be at least 1."
            )

        if size > len(keys):
            raise ValueError(
                "Not enough remaining members in this series."
            )

        keys = random.sample(keys, size)

    return [
        generate_special_survivor(key)
        for key in keys
    ]
