"""Pixel-art helpers for THE LAST CONVOY: shrinking the PNG art to its true low resolution and drawing it at whole-number
scales, so every art pixel is the same size on screen.

The PNGs in assets/ were drawn as small pixel art and then enlarged by a factor that is not a whole number, so one "art
pixel" is several source pixels wide (ART_BLOCK, measured from the edges of each image). Drawing such an image at a
fractional scale gives art pixels of uneven width. Instead each image is first shrunk once to its real low resolution
(pixelate) and then only ever enlarged by whole numbers (whole_scale / cover_scale).

Needs pygame (surfaces) but no window: it is safe to import before the display exists; call the functions after it does.
"""
import math

import pygame

# Source pixels per art pixel, measured with an autocorrelation of each image's edges (assets/): the vehicles are about
# 4, the zombie 8.5 (set to 10.6 on purpose: a smaller, about 43x42 sprite), the convoy background 5.3 and the map 10.75. Change a value here if the art is redrawn.
ART_BLOCK = {"vehicle": 4.0, "zombie": 10.6, "background": 5.3, "map": 10.75}

COARSE = 2   # the coarse vehicle sprite merges 2 x 2 art pixels: chunkier, but whole-number scales fill a small scene


def pixelate(surface, block):
    """`surface` shrunk to its true low resolution: its size divided by `block`, every new pixel the average of the
    source pixels it covers. A surface with transparency keeps hard edges: a pixel is either fully opaque or clear.

    The colour of a partly covered edge pixel is divided by its coverage, which assumes the transparent pixels of the
    PNG are black (the vehicle and zombie PNGs are); otherwise the edges come out slightly too light.
    """
    width, height = surface.get_size()
    size = (max(1, round(width / block)), max(1, round(height / block)))
    has_alpha = bool(surface.get_flags() & pygame.SRCALPHA)
    if surface.get_bitsize() in (24, 32):   # smoothscale needs 24 or 32 bit surfaces
        source = surface
    else:
        source = surface.convert_alpha() if has_alpha else surface.convert()
    small = pygame.transform.smoothscale(source, size)
    if not has_alpha:
        return small
    out = pygame.Surface(size, pygame.SRCALPHA)
    get, put = small.get_at, out.set_at
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = get((x, y))
            if a >= 128:
                put((x, y), (min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a), 255))
    return out


def whole_scale(fit, cap=None):
    """The scale to draw a pixel-art sprite at: `fit` (the biggest scale that still fits its box, at most `cap`)
    rounded down to a whole number, so every source pixel becomes the same number of screen pixels. The leftover room
    stays empty. Only when even 1x does not fit (fit < 1) is the fractional `fit` returned: shrinking is the one case
    where a whole number is not possible."""
    if cap is not None:
        fit = min(fit, cap)
    return int(fit) if fit >= 1 else fit


def cover_scale(size, box):
    """The smallest whole-number scale at which an image of `size` covers a `box` (w, h) completely. The caller crops
    what sticks out: a background has to fill its rectangle, so it is rounded up instead of down."""
    return max(1, math.ceil(max(box[0] / size[0], box[1] / size[1])))


def choose_vehicle_scale(heights, target, margin=0.1):
    """Fine or coarse sprites, and the whole-number scale, that bring the tallest sprite closest to `target` pixels high.

    `heights` = [fine, coarse] height of the tallest sprite at 1x. The error of a choice is how far its height is from
    the target as a fraction of the target (the scale is a whole number, at least 1x). The detailed
    sprite wins unless the coarse one is better by more than `margin`. Returns (index, scale), index 0 fine, 1 coarse.
    """
    errors = []
    for height in heights:
        # never fractional: the whole-number scale closest to the target, rounding down or up. Rounding only down made a
        # small drop in scene height (a larger text size shrinks the scene) cut the sprite to the next smaller scale,
        # up to half its size at once; a tiny scene still gets a sprite that is a little big (at least 1x).
        low = max(1, int(target / height))
        scale = min((low, low + 1), key=lambda s: abs(s * height - target))
        errors.append((abs(scale * height - target) / target, scale))
    if errors[0][0] - errors[1][0] > margin:
        return 1, errors[1][1]
    return 0, errors[0][1]


def choose_pixel_scale(variants, box, caps=(None, None), fill=0.7):
    """Which sprite variant to draw, and at which scale.

    `variants` is [(width, height), (width, height)]: the sprite group at 1x in its fine and its coarse version;
    `box` is the (width, height) room for it; `caps` the largest scale of each. The fine variant is used (more detail)
    unless it cannot reach 1x while the coarse one can, or it fills less than `fill` of the room while the coarse one
    fills more. Returns (index into variants, scale).
    """
    results = []
    for (width, height), cap in zip(variants, caps):
        scale = whole_scale(min(box[0] / width, box[1] / height), cap)
        results.append((scale, max(scale * width / box[0], scale * height / box[1])))
    (fine_scale, fine_fill), (coarse_scale, coarse_fill) = results
    if (fine_scale < 1 <= coarse_scale) or (fine_fill < fill and coarse_fill > fine_fill and coarse_scale >= 1):
        return 1, coarse_scale
    return 0, fine_scale
