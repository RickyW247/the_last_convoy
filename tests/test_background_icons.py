"""Headless tests for the icons on the background screen: the files are there (six 512 x 512 PNGs in assets/icons), and at every
window size and text-size level the icon is a square inside the details box, on the right, never overlapping the text column or the
note row, and never squeezing the text below TEXT_MIN (the icon is dropped first). Run: python test_background_icons.py"""
import struct
import unittest

import layout.backgrounds as lb
import textscale
from background_data import BACKGROUND_ORDER
from background_icons import icon_path
from layout.geometry import rect_inside, rects_overlap

SIZES = [(640, 480), (800, 600), (1000, 680), (1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440),
         (1000, 400), (640, 900), (900, 1600)]


def _png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", head[16:24])


def test_icon_files():
    if not icon_path(BACKGROUND_ORDER[0]).parent.is_dir():
        raise unittest.SkipTest("assets/icons folder not found")
    for name in BACKGROUND_ORDER:
        path = icon_path(name)
        assert path.exists(), f"missing {path}"
        assert _png_size(path) == (512, 512), f"{name}: icon is {_png_size(path)}, expected 512 x 512"
    try:
        import pygame
    except ImportError:
        return
    from background_icons import get_icon
    scaled = get_icon(BACKGROUND_ORDER[0], 100)
    assert scaled is not None and scaled.get_size() == (100, 100)


def test_icon_layout():
    start = textscale.text_level()
    shown = hidden = 0
    try:
        for level, _scale in textscale.TEXT_LEVELS:
            textscale.set_text_level(level)
            for w, h in SIZES:
                g = lb.background_layout(w, h, len(BACKGROUND_ORDER))
                k, detail, text, icon, note = g["k"], g["detail"], g["detail_text"], g["icon"], g["note"]
                where = (level, w, h)
                assert rect_inside(text, detail), (where, "text column outside the details box")
                if note:
                    assert rect_inside(note, detail), (where, "note row outside the details box")
                    assert not rects_overlap(note, text), (where, "note row overlaps the text column")
                if icon is None:
                    hidden += 1
                    continue
                shown += 1
                assert icon[2] == icon[3] >= lb.tpx(lb.ICON_MIN, k), (where, "icon too small or not square", icon)
                assert rect_inside(icon, detail), (where, "icon outside the details box", icon)
                assert not rects_overlap(icon, text), (where, "icon overlaps the text column")
                assert not (note and rects_overlap(icon, note)), (where, "icon overlaps the note row")
                assert icon[0] >= text[0] + text[2], (where, "icon is not on the right")
                assert text[2] >= lb.tpx(lb.TEXT_MIN, k), (where, "text column squeezed", text)
    finally:
        textscale.set_text_level(start)
    assert shown, "the icon never shows at any tested size"
    print(f"icon shown in {shown} and dropped in {hidden} of {shown + hidden} size / text-size combinations")


if __name__ == "__main__":
    test_icon_files()
    test_icon_layout()
    print("OK")
