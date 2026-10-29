"""Image-based pixel-art vehicle sprites for THE LAST CONVOY.

Sprites are authored as transparent PNG assets in assets/vehicles and loaded once
into the existing cache. Nearest-neighbour scaling preserves the pixel clusters.
"""
import os

import pygame

from vehicles import SPRITE_CACHE

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets", "vehicles")
_SPRITE_FILES = {
    "Pickup Truck": "pickup_truck.png",
    "Passenger Van": "passenger_van.png",
    "School Bus": "school_bus.png",
    "Semi-Truck": "semi_truck.png",
    "Fuel Tanker": "fuel_tanker.png",
    "Ambulance": "ambulance.png",
    "Military Humvee": "military_humvee.png",
    "Tow/Recovery Truck": "tow_recovery_truck.png",
}

def _trim_empty_bottom(sprite):
    """Cut the fully transparent rows off the bottom of a sprite.

    Vehicles are placed by the bottom edge of their image, so those rows would make a vehicle float above the
    road by a different amount for each PNG. The other three sides are left as they are.
    """
    bottom = sprite.get_bounding_rect().bottom
    if 0 < bottom < sprite.get_height():
        return sprite.subsurface((0, 0, sprite.get_width(), bottom)).copy()
    return sprite


def get_vehicle_sprite(vehicle_type):
    """Return a cached transparent pixel-art sprite facing left (west)."""
    if vehicle_type in SPRITE_CACHE:
        return SPRITE_CACHE[vehicle_type]
    filename = _SPRITE_FILES.get(vehicle_type)
    if filename is None:
        raise KeyError(f"Unknown vehicle type: {vehicle_type}")
    path = os.path.join(_ASSET_DIR, filename)
    try:
        sprite = _trim_empty_bottom(pygame.image.load(path).convert_alpha())
    except (pygame.error, FileNotFoundError) as exc:
        raise RuntimeError(f"Could not load vehicle sprite {path!r}: {exc}") from exc
    SPRITE_CACHE[vehicle_type] = sprite
    return sprite
