"""Image-based pixel-art vehicle sprites for THE LAST CONVOY.

Sprites are authored as transparent PNG assets in assets/vehicles. The PNGs are enlarged pixel art (about 4 source
pixels per art pixel), so each is shrunk once on loading to its true low resolution (pixel_art.pixelate) and cached;
the screens then draw it at whole-number scales (nearest-neighbour), which keeps every art pixel the same size.
A second, coarser version (2 x 2 art pixels merged) exists for small scenes where whole-number scales of the fine one
leave too much room empty (pixel_art.choose_pixel_scale decides which to draw).

A sprite that cannot be loaded (missing or unreadable PNG) is replaced by a plain placeholder rectangle, so one bad
file never crashes the game; a warning is printed once.
"""
import os
import sys

import pygame

from vehicle_data import SPRITE_PLACEHOLDERS, VEHICLE_SCENE_SIZE
from upgrade_data import TRAILER_SCENE_SIZE   # the towed trailers' size factors live with the upgrades
from .pixel_art import ART_BLOCK, COARSE, pixelate

_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "vehicles",
)
_SPRITE_CACHE = {}   # vehicle type -> loaded (or placeholder) sprite
_COARSE_CACHE = {}
_SOURCE_CACHE = {}   # vehicle type -> the full-resolution PNG (bottom trimmed), or None when it cannot be loaded
_PLACEHOLDER_SIZE = (40, 20)   # in art pixels: about the size of a real sprite at its low resolution
_SPRITE_FILES = {
    "Pickup Truck": "pickup_truck.png",
    "Passenger Van": "passenger_van.png",
    "School Bus": "school_bus.png",
    "Semi-Truck": "semi_truck.png",
    "Fuel Tanker": "fuel_tanker.png",
    "Ambulance": "ambulance.png",
    "Military Humvee": "military_humvee.png",
    "Tow/Recovery Truck": "tow_recovery_truck.png",
    "Sedan": "sedan.png",
    "Civilian SUV": "civilian_suv.png",
    "Utility SUV": "offroad_suv.png",
    "Postal Van": "postal_van.png",
    "Box Truck": "box_truck.png",
    "City Bus": "city_bus.png",
    "Motorhome": "rv.png",
    "Fire Engine": "fire_engine.png",
    "Hatchback": "hatchback.png",
    "Coach Bus": "coach_bus.png",
    "Motorcycle": "motorcycle.png",
    "Dirt Bike": "dirt_bike.png",
    "Delivery Van": "delivery_van.png",
    "Flatbed Truck": "flatbed_truck.png",
    "Dump Truck": "dump_truck.png",
    "Military Cargo Truck": "military_cargo_truck.png",
    "Minivan": "minivan.png",
    "Police Sedan": "police_sedan.png",
    "Police SUV": "police_suv.png",
    "Prison Transport Bus": "prison_transport_bus.png",
    "Scooter": "scooter.png",
    "Sports Car": "sports_car.png",
    "Station Wagon": "station_wagon.png",
    "Taxi": "taxi.png",
    "Armored Personnel Carrier": "armored_personnel_carrier.png",
    "Bulldozer": "bulldozer.png",
    "Clown Car": "clown_car.png",
    "Excavator": "excavator.png",
    "Food Truck": "food_truck.png",
    "Garbage Truck": "garbage_truck.png",
    "Hearse": "hearse.png",
    "Ice Cream Van": "ice_cream_truck.png",
    "Limousine": "limo.png",
    "Tank": "military_tank.png",
    "Mobile Command Vehicle": "mobile_command_vehicle.png",
    "TV Broadcasting Van": "tv_news_van.png",
    "Presidential Limo": "presidential_limo.png",
    "Moving Truck": "moving_truck.png",
    "Utility Service Truck": "utility_service_truck.png",
    "Refrigerated Truck": "refrigerated_truck.png",
    "Landscaping Truck": "landscaping_truck.png",
    "Car Carrier Truck": "car_carrier_truck.png",
    "Road Maintenance Truck": "road_maintenance_truck.png",
    "Armored Cash Truck": "armored_cash_truck.png",
    "Crane Truck": "crane_truck.png",
    "Monster Truck": "monster_truck.png",
    "Tourist Bus": "tourist_bus.png",
    "Mobile Laboratory": "mobile_laboratory.png",
    "Vintage Police Car": "vintage_police_car.png",
    "Wrecking Ball Truck": "wrecking_ball_truck.png",
    "Prototype Military Vehicle": "prototype_military_vehicle.png",
    "Formula 1 Car": "formula_1_car.png",
    # Not a vehicle type: the look of the Semi-Truck once its cargo upgrade (the trailer) is installed (upgrade_data.py,
    # Vehicle.sprite_type). Nothing iterates this table; the convoy scene sizes itself from the real vehicle types only.
    "Semi-Truck Trailer": "semi_truck_trailer.png",
    # Towed trailers (upgrade_data.py, `trailer`): drawn behind a vehicle by get_rig_sprite / get_rig_source, never alone.
    "Utility Trailer": "utility_trailer.png",
    "Flatbed Trailer": "flatbed_trailer.png",
    "Travel Trailer": "travel_trailer.png",
}

# Vehicles that have no PNG yet borrow the file of a similar vehicle (vehicle_data.SPRITE_PLACEHOLDERS). setdefault, so a
# vehicle with its own entry in the table above always wins, even if its placeholder line has not been deleted yet.
for _type, _stand_in in SPRITE_PLACEHOLDERS.items():
    _SPRITE_FILES.setdefault(_type, _SPRITE_FILES[_stand_in])

# Sprites that are not drawn from the usual 4 px art pixels: source pixels per art pixel, measured for the sprite (instead of
# ART_BLOCK["vehicle"] / the scene size factor). The Semi-Truck + trailer PNG is the semi at about 1.7 times the size of
# semi_truck.png; 5.5 makes its tractor as big in the convoy scene as the plain semi's (4 / 1.25 x 1.7).
SPRITE_BLOCK = {"Semi-Truck Trailer": 5.5}
TRAILER_HITCH_OVERLAP = 0.06   # share of the trailer's width that sits under the vehicle's rear end (the hitch)
_RIG_CACHE = {}


def vehicle_scene_size(vehicle_type):
    """Size factor of this vehicle in the convoy scene (vehicles.VEHICLE_SCENE_SIZE; 1.0 when it has none)."""
    return TRAILER_SCENE_SIZE.get(vehicle_type) or VEHICLE_SCENE_SIZE.get(vehicle_type, 1.0)


def _trim_empty_bottom(sprite):
    """Cut the fully transparent rows off the bottom of a sprite.

    Vehicles are placed by the bottom edge of their image, so those rows would make a vehicle float above the
    road by a different amount for each PNG. The other three sides are left as they are.
    """
    bottom = sprite.get_bounding_rect().bottom
    if 0 < bottom < sprite.get_height():
        return sprite.subsurface((0, 0, sprite.get_width(), bottom)).copy()
    return sprite


def _placeholder_sprite():
    """A plain grey vehicle-shaped rectangle (cab window on the left, as the sprites face west), used when a PNG
    cannot be loaded. It is built at the same low resolution as a loaded sprite, so it is drawn the same way."""
    width, height = _PLACEHOLDER_SIZE
    sprite = pygame.Surface((width, height), pygame.SRCALPHA)
    sprite.fill((120, 120, 130))
    pygame.draw.rect(sprite, (60, 60, 70), sprite.get_rect(), 1)
    pygame.draw.rect(sprite, (170, 200, 220), (3, 3, width // 4, height // 3))
    return sprite


def get_vehicle_sprite(vehicle_type, coarse=False):
    """Return a cached transparent pixel-art sprite facing left (west), at its true low resolution (about 1/4 of the PNG; finer for a vehicle whose scene size factor is above 1).
    With coarse=True: the same sprite with 2 x 2 art pixels merged (about 1/8 of the PNG). Draw either at a whole-number
    scale (pixel_art.whole_scale)."""
    if coarse:
        if vehicle_type not in _COARSE_CACHE:
            _COARSE_CACHE[vehicle_type] = pixelate(get_vehicle_sprite(vehicle_type), COARSE)
        return _COARSE_CACHE[vehicle_type]
    if vehicle_type in _SPRITE_CACHE:
        return _SPRITE_CACHE[vehicle_type]
    filename = _SPRITE_FILES.get(vehicle_type)
    if filename is None:
        raise KeyError(f"Unknown vehicle type: {vehicle_type}")   # a programming error, not a missing file
    path = os.path.join(_ASSET_DIR, filename)
    try:
        # A vehicle drawn bigger (vehicle_scene_size > 1) is shrunk less, so it has more art pixels; it is still drawn at
        # the same whole-number scale as the rest, so every art pixel is the same size on screen.
        block = SPRITE_BLOCK.get(vehicle_type) or ART_BLOCK["vehicle"] / vehicle_scene_size(vehicle_type)
        sprite = pixelate(_trim_empty_bottom(pygame.image.load(path).convert_alpha()), block)
    except (pygame.error, OSError) as exc:   # OSError covers FileNotFoundError and unreadable files
        print(f"Warning: could not load vehicle sprite {path!r} ({exc}); drawing a placeholder.", file=sys.stderr)
        sprite = _placeholder_sprite()
    _SPRITE_CACHE[vehicle_type] = sprite   # the placeholder is cached too, so the file is not retried every frame
    return sprite


# Fine reference height (art pixels at size factor 1.0) of each vehicle type, so the convoy scene can size itself from
# the tallest vehicle without loading every PNG at launch. Measured once from the PNGs: when a PNG changes or a vehicle
# is added, run dump_reference_heights() (below) and paste its output here. A type missing from the table is measured
# from its PNG as before, so a stale table never breaks anything (it only costs launch time).
_REFERENCE_HEIGHTS = {
    'Pickup Truck': 71,
    'Passenger Van': 75,
    'School Bus': 66,
    'Semi-Truck': 80,
    'Fuel Tanker': 67,
    'Ambulance': 63,
    'Military Humvee': 62,
    'Tow/Recovery Truck': 62,
    'Sedan': 52,
    'Civilian SUV': 56,
    'Utility SUV': 59,
    'Postal Van': 66,
    'Box Truck': 71,
    'City Bus': 62,
    'Motorhome': 72,
    'Fire Engine': 70,
    'Hatchback': 56,
    'Taxi': 60,
    'Station Wagon': 59,
    'Minivan': 57,
    'Coach Bus': 70,
    'Sports Car': 50,
    'Motorcycle': 66,
    'Dirt Bike': 68,
    'Scooter': 66,
    'Delivery Van': 58,
    'Moving Truck': 67,
    'Utility Service Truck': 68,
    'Flatbed Truck': 64,
    'Refrigerated Truck': 64,
    'Dump Truck': 72,
    'Landscaping Truck': 66,
    'Garbage Truck': 65,
    'Car Carrier Truck': 70,
    'Police SUV': 63,
    'Police Sedan': 57,
    'Prison Transport Bus': 64,
    'Road Maintenance Truck': 82,
    'Military Cargo Truck': 66,
    'Armored Personnel Carrier': 69,
    'Mobile Command Vehicle': 72,
    'Hearse': 49,
    'Limousine': 46,
    'Presidential Limo': 49,
    'Ice Cream Van': 66,
    'TV Broadcasting Van': 65,
    'Clown Car': 67,
    'Tank': 66,
    'Excavator': 70,
    'Bulldozer': 61,
    'Crane Truck': 67,
    'Wrecking Ball Truck': 99,
    'Monster Truck': 94,
    'Armored Cash Truck': 74,
    'Vintage Police Car': 67,
    'Tourist Bus': 85,
    'Mobile Laboratory': 89,
    'Food Truck': 66,
    'Prototype Military Vehicle': 100,
    'Formula 1 Car': 59,
}


def dump_reference_heights():
    """Print the _REFERENCE_HEIGHTS table for every vehicle type, measured from the PNGs. Run from the project folder:
    python -c "from ui.vehicle_rendering import dump_reference_heights; dump_reference_heights()" """
    if pygame.display.get_surface() is None:   # convert_alpha needs a display
        pygame.display.init()
        pygame.display.set_mode((1, 1))
    from vehicle_data import VEHICLE_LOOKS
    print("_REFERENCE_HEIGHTS = {")
    for name in VEHICLE_LOOKS:
        source = get_vehicle_source(name)
        if source is not None:   # a type whose PNG cannot be loaded stays out of the table
            print(f"    {name!r}: {max(1, round(source.get_height() / ART_BLOCK['vehicle']))},")
    print("}")


def reference_sprite_height(vehicle_type, coarse=False):
    """Height in art pixels the sprite would have at size factor 1.0 (the convoy scene sizes its scale from the tallest
    of these, so enlarging a vehicle does not change the scale, and so the size, of all the others)."""
    fine = _REFERENCE_HEIGHTS.get(vehicle_type)
    if fine is not None:   # measured once from the PNGs (see _REFERENCE_HEIGHTS): no image has to be loaded for it
        return max(1, round(fine / COARSE)) if coarse else fine
    source = get_vehicle_source(vehicle_type)
    if source is None:   # the placeholder is never enlarged
        return get_vehicle_sprite(vehicle_type, coarse).get_height()
    fine = max(1, round(source.get_height() / ART_BLOCK["vehicle"]))
    return max(1, round(fine / COARSE)) if coarse else fine


def get_vehicle_source(vehicle_type):
    """The vehicle's full-resolution PNG (transparent rows trimmed off the bottom, facing left), cached, or None when the
    file cannot be loaded (the caller then falls back to get_vehicle_sprite). For big pictures such as the vehicles
    screen's card: the PNGs are not perfectly regular pixel art, so shrinking them to ART_BLOCK and enlarging that by
    3x / 4x makes them blurry; a smooth shrink of the original stays sharp."""
    if vehicle_type not in _SOURCE_CACHE:
        filename = _SPRITE_FILES.get(vehicle_type)
        if filename is None:
            raise KeyError(f"Unknown vehicle type: {vehicle_type}")
        try:
            _SOURCE_CACHE[vehicle_type] = _trim_empty_bottom(
                pygame.image.load(os.path.join(_ASSET_DIR, filename)).convert_alpha())
        except (pygame.error, OSError):   # already reported by get_vehicle_sprite
            _SOURCE_CACHE[vehicle_type] = None
    return _SOURCE_CACHE[vehicle_type]


def _block(name):
    """Source pixels per art pixel of this sprite (as get_vehicle_sprite works it out)."""
    return SPRITE_BLOCK.get(name) or ART_BLOCK["vehicle"] / vehicle_scene_size(name)


def _rig_overlap(trailer_width):
    return int(trailer_width * TRAILER_HITCH_OVERLAP)


def get_rig_sprite(vehicle_look, trailer, coarse=False):
    """The vehicle and the trailer it tows as ONE art-pixel sprite (vehicle in front on the left, trailer behind it on the
    right, wheels on the same road line, hitch overlapping a little). Without a trailer: the vehicle's own sprite."""
    sprite = get_vehicle_sprite(vehicle_look, coarse)
    if not trailer:
        return sprite
    key = (vehicle_look, trailer, coarse)
    if key not in _RIG_CACHE:
        tow = get_vehicle_sprite(trailer, coarse)
        overlap = _rig_overlap(tow.get_width())
        rig = pygame.Surface((sprite.get_width() + tow.get_width() - overlap, max(sprite.get_height(), tow.get_height())),
                             pygame.SRCALPHA)
        rig.blit(tow, (sprite.get_width() - overlap, rig.get_height() - tow.get_height()))   # behind: drawn first
        rig.blit(sprite, (0, rig.get_height() - sprite.get_height()))
        _RIG_CACHE[key] = rig
    return _RIG_CACHE[key]


def rig_dust_points(vehicle_look, trailer, vehicle_fractions, trailer_fractions, coarse=False):
    """Wheel dust points (fractions of the rig's width) of a vehicle and its trailer drawn by get_rig_sprite."""
    vw = get_vehicle_sprite(vehicle_look, coarse).get_width()
    tw = get_vehicle_sprite(trailer, coarse).get_width()
    total = vw + tw - _rig_overlap(tw)
    return tuple(f * vw / total for f in vehicle_fractions) + tuple((vw - _rig_overlap(tw) + f * tw) / total
                                                                    for f in trailer_fractions)


def get_rig_source(vehicle_look, trailer):
    """Full-resolution picture of a vehicle with its trailer (for the upgrade screen's card), or None when a PNG cannot be
    loaded. The trailer is resized so that it keeps the size relative to the vehicle it has in the convoy scene."""
    vehicle, tow = get_vehicle_source(vehicle_look), get_vehicle_source(trailer)
    if vehicle is None or tow is None:
        return None
    key = ("source", vehicle_look, trailer)
    if key not in _RIG_CACHE:
        ratio = _block(vehicle_look) / _block(trailer)
        tow = pygame.transform.smoothscale(tow, (max(1, round(tow.get_width() * ratio)), max(1, round(tow.get_height() * ratio))))
        overlap = _rig_overlap(tow.get_width())
        rig = pygame.Surface((vehicle.get_width() + tow.get_width() - overlap, max(vehicle.get_height(), tow.get_height())),
                             pygame.SRCALPHA)
        rig.blit(tow, (vehicle.get_width() - overlap, rig.get_height() - tow.get_height()))
        rig.blit(vehicle, (0, rig.get_height() - vehicle.get_height()))
        _RIG_CACHE[key] = rig
    return _RIG_CACHE[key]
