"""Validated reward application for completed missions."""

from .effect_handler import RESOURCE_FIELDS, apply_effects


def apply_rewards(game, rewards):
    """Validate and apply mission rewards; return readable reward notes."""
    notes = []

    for reward in rewards or []:
        if not isinstance(reward, dict):
            continue

        kind = reward.get("type")
        amount = reward.get("amount", 0)

        if not isinstance(amount, int) or isinstance(amount, bool):
            continue

        if amount < 0:
            continue

        if kind == "resource":
            if reward.get("resource") not in RESOURCE_FIELDS:
                continue

        elif kind == "survivors":
            pass

        else:
            continue

        notes.extend(apply_effects(game, [reward]))

    return notes