"""Reusable, validated effect application for travel events."""

RESOURCE_FIELDS = {"fuel", "food", "water", "scrap"}


def apply_effects(game, effects):
    """Apply a list of declarative effects; return human-readable effect notes."""
    notes = []
    for effect in effects or []:
        kind = effect.get("type")
        amount = int(effect.get("amount", 0))
        if kind == "resource":
            field = effect.get("resource")
            if field not in RESOURCE_FIELDS:
                continue
            before = getattr(game, field, 0)
            if field == "fuel":
                cap = game.convoy_stats().get("fuel_capacity", before)
                after = max(0, min(cap, before + amount))
            elif field in ("food", "water", "scrap"):
                if amount > 0 and hasattr(game, "gain_cargo"):
                    remainder = game.gain_cargo({field: amount})
                    after = getattr(game, field, before)
                    actual = after - before
                    if actual:
                        notes.append(f"{field.title()} {actual:+d}")
                    if remainder:
                        notes.append(f"Cargo full: {remainder} {field} could not fit")
                    continue
                after = max(0, before + amount)
            setattr(game, field, after)
            actual = after - before
            if actual:
                notes.append(f"{field.title()} {actual:+d}")
        elif kind == "survivors":
            before = game.survivors
            if amount > 0:
                capacity = game.convoy_stats().get("passengers", before)
                game.survivors = min(capacity, before + amount)
            else:
                game.survivors = max(0, before + amount)
            if game.survivors != before:
                notes.append(f"Survivors {game.survivors - before:+d}")
        elif kind == "vehicle_damage":
            for vehicle in game.vehicles:
                vehicle.health = max(0, vehicle.health - amount)
            notes.append(f"Each vehicle took {amount} damage")
            if hasattr(game, "check_defeat"):
                game.check_defeat()
        elif kind == "vehicle_repair":
            remaining = amount
            repaired = 0
            for vehicle in game.vehicles:
                maximum = vehicle.stats.get("health", vehicle.health)
                add = min(remaining, max(0, maximum - vehicle.health))
                vehicle.health += add
                repaired += add
                remaining -= add
                if remaining <= 0:
                    break
            if repaired:
                notes.append(f"Vehicle repairs +{repaired} health")
        elif kind == "horde_gap":
            game.horde = max(0, game.horde + amount)
            notes.append(f"Horde gap {amount:+d} km")
    return notes
