"""Headless layout tests for THE LAST CONVOY (no pygame, no display, no fonts needed).

Every window-pixel layout (title, lore, menu, vehicles, instructions, survivors, missions, map and the popups) must
never put a rectangle outside the window or its panel, never overlap two rectangles that should be separate, and its
click geometry must match what is drawn. Text widths are an estimate (CHAR_W px per TINY character); the real fonts
are measured by the drawing code.
"""
import itertools
import unittest

import layout
import map_data
import vehicle_data
from layout import (
    instructions_layout, lore_layout, menu_card_layout, menu_layout, rect_bottom, rect_inside, rect_right,
    rects_overlap, screen_frame, table_columns, table_pad, title_layout, vehicle_card_layout, vehicle_row_at,
    vehicles_layout, VEHICLE_ROWS,
)

from layout.menus import MENU_CARD_MIN_H, credits_layout, difficulty_layout, saves_layout, settings_layout
from layout.vehicles import MIN_PAGE_ROWS, MIN_ROW_H, vehicles_buttons

from tests.helpers import LayoutTestCase

BASE_SIZES = [(640, 480), (1000, 680), (1920, 1080), (800, 600), (1366, 768), (1280, 1024), (2560, 1440)]
# Unusual shapes (narrow, short, very wide). Remove this line from SIZES if you only care about the usual windows.
EXTRA_SIZES = [(1280, 720), (1600, 900), (640, 900), (1500, 500), (900, 480)]
SIZES = BASE_SIZES + EXTRA_SIZES
CHAR_W = 8   # TINY (13 px Consolas) is about 7.2 px per character; 8 is the safe estimate

HUD_SCREENS = {"menu": menu_layout, "vehicles": vehicles_layout, "instructions": instructions_layout}
NO_HUD_SCREENS = {"title": title_layout, "lore": lore_layout}


class LayoutChecks:
    """Mixin: the one checker every layout goes through."""

    @staticmethod
    def window_of(size, g):
        width, height = g.get("size") or (max(640, size[0]), max(480, size[1]))
        return (0, 0, width, height)

    def check_layout(self, name, size, g, container=None):
        """Leaves are non-empty, inside the window (and `container`), and do not overlap; nested rectangles sit
        inside their parents; rectangles in the same group do not overlap; the HUD and panel never overlap."""
        label = f"{name} at {size[0]}x{size[1]}"
        window = self.window_of(size, g)
        leaves = g["leaves"]
        for leaf_name, rect in leaves:
            self.assertTrue(rect[2] > 0 and rect[3] > 0, f"{label}: {leaf_name} is empty {rect}")
            self.assertTrue(rect_inside(rect, window), f"{label}: {leaf_name} {rect} leaves the window {window}")
            if container is not None:
                self.assertTrue(rect_inside(rect, container), f"{label}: {leaf_name} {rect} leaves its panel")
        for (a_name, a), (b_name, b) in itertools.combinations(leaves, 2):
            self.assertFalse(rects_overlap(a, b), f"{label}: {a_name} {a} overlaps {b_name} {b}")
        for child_name, child, parent in g.get("inside", []):
            self.assertTrue(child[2] > 0 and child[3] > 0, f"{label}: {child_name} is empty {child}")
            self.assertTrue(rect_inside(child, parent), f"{label}: {child_name} {child} is outside {parent}")
        for group, rects in g.get("groups", []):
            for (a_name, a), (b_name, b) in itertools.combinations(rects, 2):
                self.assertFalse(rects_overlap(a, b), f"{label}: {group}: {a_name} {a} overlaps {b_name} {b}")
        if "hud" in g and "panel" in g:
            self.assertFalse(rects_overlap(g["hud"], g["panel"]), f"{label}: the panel overlaps the HUD")


class ScreenLayoutTests(LayoutChecks, unittest.TestCase):
    """Title, lore, menu, vehicles and instructions screens."""

    def test_hud_screens_have_no_overlap_or_overflow(self):
        for size in SIZES:
            for name, make in HUD_SCREENS.items():
                g = make(*size)
                self.check_layout(name, size, g, container=g["panel"])
                self.assertTrue(rect_inside(g["panel"], self.window_of(size, g)), f"{name} panel leaves the window")

    def test_title_and_lore_have_no_overlap_or_overflow(self):
        for size in SIZES:
            for name, make in NO_HUD_SCREENS.items():
                g = make(*size)
                self.check_layout(name, size, g)
                if "panel" in g:   # the lore panel holds everything except its hint line, which sits below it
                    for leaf_name, rect in g["leaves"]:
                        if leaf_name != "hint":
                            self.assertTrue(rect_inside(rect, g["panel"]),
                                            f"{name} {leaf_name} leaves its panel at {size}")

    def test_window_below_minimum_is_clamped(self):
        g = menu_layout(300, 200)
        self.assertEqual(g["size"], (640, 480))
        self.check_layout("menu", (300, 200), g, container=g["panel"])

    def test_frame_follows_the_convoy_layout_margins(self):
        for size in SIZES:
            f = screen_frame(*size)
            base = layout.calculate_layout(*size)
            self.assertEqual(f["panel"][0], base["margin"])
            self.assertEqual(rect_right(f["panel"]), base["width"] - base["margin"])
            self.assertEqual(rect_bottom(f["panel"]), base["height"] - base["margin"])
            self.assertEqual(f["panel"][1] - rect_bottom(f["hud"]), base["gap"])

    def test_pause_menu_pages_have_no_overlap_or_overflow(self):
        """The pause menu's pages (difficulty, SAVE / LOAD, settings, credits) moved into layout/menus.py."""
        pages = {"difficulty": difficulty_layout, "saves": saves_layout, "settings": settings_layout,
                 "credits": credits_layout}
        for size in SIZES:
            for name, make in pages.items():
                g = make(*size)
                self.check_layout(name, size, g, container=g["panel"])

    def test_menu_buttons_follow_the_run_state(self):
        for size in SIZES:
            in_run, from_title = menu_layout(*size, True), menu_layout(*size, False)
            self.assertIn("restart", in_run)
            self.assertNotIn("achievements", in_run)
            self.assertIn("achievements", from_title)
            self.assertNotIn("restart", from_title)
            self.assertEqual(len(in_run["items"]), 8)
            self.assertEqual(len(from_title["items"]), 7)

    def test_difficulty_cards_and_notes(self):
        for size in SIZES:
            g = difficulty_layout(*size)
            self.assertEqual(len(g["cards"]), 3)
            for card in g["cards"]:
                sub = menu_card_layout(card, g["k"])
                for part in ("name", "body", "button"):
                    self.assertTrue(rect_inside(sub[part], card), f"{part} outside its card at {size}")
                self.assertFalse(rects_overlap(sub["name"], sub["body"]))
                self.assertFalse(rects_overlap(sub["body"], sub["button"]))
                self.assertFalse(rects_overlap(sub["name"], sub["button"]))
                self.assertGreater(sub["body"][3], 48, f"no room for the stats lines at {size}")

    def test_vehicle_table_geometry(self):
        for size in SIZES:
            g = vehicles_layout(*size)
            table = g["table"]
            shown = g["per_page"]            # a table with more vehicles than fit is paged: one page of rows is drawn
            self.assertEqual(rect_bottom(table), g["rows_top"] + shown * g["row_h"])
            self.assertEqual(g["rows"], VEHICLE_ROWS)
            self.assertEqual(g["paged"], shown < g["rows"])
            self.assertEqual(g["pages"], -(-g["rows"] // shown))
            self.assertGreaterEqual(g["row_h"], int(MIN_ROW_H * g["k"]) - 1)
            columns = g["columns"]
            self.assertEqual(len(columns), 9)
            self.assertGreaterEqual(columns[0][0], table[0])
            self.assertLessEqual(columns[-1][0] + columns[-1][1], rect_right(table))
            for (x, w), (nx, _nw) in zip(columns, columns[1:]):
                self.assertGreater(w, 0)
                self.assertEqual(x + w, nx, "columns must tile the table without gaps or overlap")
            self.assertEqual(columns, table_columns(table[0], table[2], g["compact"]))

    def test_table_headings_and_numbers_fit_their_columns(self):
        """Nothing but the vehicle name may be cut short."""
        for size in SIZES:
            g = vehicles_layout(*size)
            pad = table_pad(g["compact"])
            heads = (("VEHICLE", "OWN", "SPD", "HP", "PASS", "CARGO", "DEF", "FCAP", "FUSE") if g["compact"]
                     else ("VEHICLE", "STATUS", "SPD", "HP", "PASS", "CARGO", "DEF", "FCAP", "FUSE"))
            worst = (None, "OWNED" if g["compact"] else "NOT OWNED", "99", "999/999", "99", "99", "99", "99", "99")
            for (_x, w), head, cell in zip(g["columns"], heads, worst):
                room = w - 2 * pad
                self.assertLessEqual(len(head) * CHAR_W, room, f"heading {head} is cut at {size} (room {room}px)")
                if cell:
                    self.assertLessEqual(len(cell) * CHAR_W, room, f"value {cell!r} is cut at {size} (room {room}px)")

    def test_vehicle_row_hit_testing_uses_the_drawn_rows(self):
        for size in SIZES:
            g = vehicles_layout(*size)
            tx, _ty, tw, _th = g["table"]
            for page in range(g["pages"]):
                first = page * g["per_page"]
                on_page = min(g["per_page"], g["rows"] - first)
                for index in range(on_page):
                    top = g["rows_top"] + index * g["row_h"]
                    for y in (top, top + g["row_h"] // 2, top + g["row_h"] - 1):
                        self.assertEqual(vehicle_row_at(size[0], size[1], (tx + tw // 2, y), page=page), first + index)
                below = g["rows_top"] + on_page * g["row_h"]
                self.assertIsNone(vehicle_row_at(size[0], size[1], (tx + 5, below), page=page))
            self.assertIsNone(vehicle_row_at(size[0], size[1], (tx - 1, g["rows_top"] + 1)))
            self.assertIsNone(vehicle_row_at(size[0], size[1], (tx + tw, g["rows_top"] + 1)))
            self.assertIsNone(vehicle_row_at(size[0], size[1], (tx + 5, g["rows_top"] - 1)))

    def test_the_full_roster_is_paged_and_still_fits(self):
        """The game has far more vehicle types than the table can show at once (VEHICLE_ROWS is only the default)."""
        roster = len(vehicle_data.VEHICLE_SPECS)
        for size in SIZES:
            g = vehicles_layout(size[0], size[1], roster)
            self.check_layout("vehicles (full roster)", size, g, container=g["panel"])
            self.assertTrue(g["paged"], size)
            self.assertGreaterEqual(g["per_page"], MIN_PAGE_ROWS)
            self.assertEqual(g["pages"], -(-roster // g["per_page"]))
            self.assertIsNotNone(g["prev_page"])
            self.assertIsNotNone(g["next_page"])
            tx, _ty, tw, _th = g["table"]
            last = g["pages"] - 1
            self.assertEqual(vehicle_row_at(size[0], size[1], (tx + tw // 2, g["rows_top"] + 1), roster, last),
                             last * g["per_page"])

    def test_sandbox_recover_all_button_sits_at_the_left(self):
        """The row with RECOVER ALL: RECOVER ALL at the left, then ABANDON, RECOVER, BACK right-aligned as before, inside the button
        row and without overlaps; without it the row is the one vehicles_layout draws."""
        for size in SIZES:
            g = vehicles_layout(*size)
            row = screen_frame(*size)["button_row"]
            plain = vehicles_buttons(size[0], size[1])
            self.assertEqual((plain["abandon"], plain["recover"], plain["back"]), (g["abandon"], g["recover"], g["back"]), size)
            rects = vehicles_buttons(size[0], size[1], True)
            self.assertEqual(list(rects), ["recover_all", "abandon", "recover", "back"])
            ordered = list(rects.values())
            for name, rect in rects.items():
                self.assertTrue(rect[2] > 0 and rect[3] > 0, f"{name} is empty at {size}")
                self.assertTrue(rect_inside(rect, row), f"{name} {rect} leaves the button row {row} at {size}")
            for (a_name, a), (b_name, b) in itertools.combinations(rects.items(), 2):
                self.assertFalse(rects_overlap(a, b), f"{a_name} overlaps {b_name} at {size}")
            for left, right in zip(ordered, ordered[1:]):
                self.assertLessEqual(rect_right(left), right[0], size)
            self.assertLess(rect_right(rects["recover_all"]), rects["abandon"][0], size)
            self.assertEqual(rect_right(rects["back"]), rect_right(g["back"]), size)
            self.assertEqual(rects["recover_all"][0], row[0], size)

    def test_vehicle_card_parts_do_not_overlap(self):
        for size in SIZES:
            g = vehicles_layout(*size)
            card = g["card"]
            for ability_lines in (0, 1, 2):          # no special ability, or one that needs 1 / 2 lines of effect text
                parts = vehicle_card_layout(card, g["k"], ability_lines)
                self.assertEqual(parts["ability"] is None, ability_lines == 0)
                named = [(n, r) for n, r in parts.items() if r is not None]
                for n, r in named:
                    self.assertTrue(rect_inside(r, card), f"card part {n} outside the card at {size} ({ability_lines})")
                for (a_name, a), (b_name, b) in itertools.combinations(named, 2):
                    self.assertFalse(rects_overlap(a, b), f"card parts {a_name}/{b_name} overlap at {size} ({ability_lines})")
            self.assertGreaterEqual(vehicle_card_layout(card, g["k"])["picture"][3], 40,
                                    f"vehicle picture too small at {size}")

    def test_instruction_columns_fit_the_body(self):
        for size in SIZES:
            g = instructions_layout(*size)
            (lx, lw), (rx, rw) = g["columns"]
            self.assertGreater(lw, 100)
            self.assertGreater(rw, 100)
            self.assertLessEqual(lx + lw, rx)
            self.assertLessEqual(rx + rw, rect_right(g["body"]))

    def test_secondary_sections_are_dropped_only_when_tight(self):
        # Roomy windows keep everything: both help lines, the summary as a grid, no paging.
        for size in ((1000, 680), (1920, 1080)):
            g = vehicles_layout(*size)
            self.assertEqual((g["subtitle_lines"], g["summary_shape"]), (2, "grid"), size)
            self.assertIsNotNone(g["subtitle"])
            self.assertIsNotNone(g["summary"])
        self.assertFalse(vehicles_layout(1920, 1080)["paged"])
        # Whatever the window, the order of giving way holds: the help text goes before the summary does, and the
        # short layouts ("row" / "side" summaries, one help line) are only used when something had to give.
        for size in SIZES:
            g = vehicles_layout(*size)
            self.assertEqual(g["subtitle"] is None, g["subtitle_lines"] == 0, size)
            self.assertEqual(g["summary"] is None, g["summary_shape"] is None, size)
            if g["summary"] is None:
                self.assertIsNone(g["subtitle"], f"the summary was dropped before the help text at {size}")
        # The difficulty notes are left out only when the cards would otherwise get too short.
        self.assertIsNotNone(difficulty_layout(1000, 680)["notes"])
        for size in SIZES:
            g = difficulty_layout(*size)
            if g["notes"] is not None:
                self.assertGreaterEqual(g["cards"][0][3], int(MENU_CARD_MIN_H * g["k"]) - 1, size)


class ListScreenLayoutTests(LayoutChecks, LayoutTestCase):
    """Survivors, missions, map and the popups (on the pinned map layout, because the map tests index stops)."""

    @staticmethod
    def new_layouts(w, h):
        yield "survivors", layout.survivors_layout(w, h)
        yield "missions", layout.missions_layout(w, h)
        yield "map", layout.map_layout(w, h)
        for count in (2, 3, 4):
            yield f"event{count}", layout.popup_layout(w, h, "event", count)
        yield "result", layout.popup_layout(w, h, "result")
        yield "end", layout.popup_layout(w, h, "end", layout.END_STAT_ROWS)

    def test_new_layouts_do_not_overlap_or_leave_the_window(self):
        for w, h in SIZES:
            for name, g in self.new_layouts(w, h):
                self.check_layout(name, (w, h), g)

    def test_popup_is_centred_and_sized_from_the_window(self):
        for w, h in SIZES:
            w2, h2 = max(640, w), max(480, h)
            for kind in ("event", "result", "end"):
                g = layout.popup_layout(w, h, kind, 3 if kind == "event" else layout.END_STAT_ROWS)
                x, y, pw, ph = g["panel"]
                self.assertTrue(abs((x + pw / 2) - w2 / 2) <= 1 and abs((y + ph / 2) - h2 / 2) <= 1,
                                f"{kind} {w}x{h} not centred")
        small = layout.popup_layout(640, 480, "result")["panel"]
        big = layout.popup_layout(1920, 1080, "result")["panel"]
        self.assertTrue(big[2] > small[2] and big[3] > small[3], "popup does not grow with the window")

    def test_event_buttons_come_from_the_layout(self):
        for count in (1, 2, 3, 4):
            g = layout.popup_layout(1000, 680, "event", count)
            self.assertEqual(len(g["buttons"]), count)
            for button in g["buttons"]:
                self.assertTrue(rect_inside(button, g["panel"]))

    def test_rows_per_page(self):
        for w, h in SIZES:
            self.assertGreaterEqual(layout.survivors_per_page(w, h), 1)
            self.assertGreaterEqual(layout.missions_per_page(w, h), 1)
            s = layout.survivors_layout(w, h)
            self.assertEqual(layout.survivors_per_page(w, h), s["per_page"])
            self.assertEqual(layout.missions_per_page(w, h), len(layout.missions_layout(w, h)["cards"]))
            rows = (s["rows"][0], s["rows_top"], s["rows"][2], s["row_h"] * s["per_page"])
            self.assertTrue(rect_inside(rows, s["list"]))
        self.assertGreater(layout.survivors_per_page(1920, 1080), layout.survivors_per_page(640, 480))
        self.assertGreater(layout.missions_per_page(1920, 1080), layout.missions_per_page(640, 480))

    def test_pages_clamp(self):
        page_count = layout.page_count
        self.assertEqual((page_count(0, 8), page_count(8, 8), page_count(9, 8), page_count(5, 0)), (1, 1, 2, 5))
        # a page that is valid in a small window can be past the end in a big one: the clamp keeps it valid
        total = 30
        small = page_count(total, layout.survivors_per_page(640, 480))
        big = page_count(total, layout.survivors_per_page(1920, 1080))
        self.assertLess(big, small)
        self.assertEqual(max(0, min(small - 1, big - 1)), big - 1)

    def test_survivor_columns_fill_the_list_and_fit_their_headings(self):
        for w, h in SIZES:
            s = layout.survivors_layout(w, h)
            columns, (hx, _hy, hw, _hh) = s["columns"], s["heading"]
            self.assertEqual(columns[0][0], hx)
            self.assertEqual(columns[-1][0] + columns[-1][1], hx + hw)
            for (x0, w0), (x1, _w1) in zip(columns, columns[1:]):
                self.assertEqual(x0 + w0, x1, "columns leave a gap or overlap")
            for (_x, cw), head in zip(columns, ("NAME", "GENDER", "AGE", "VEHICLE")):
                self.assertGreaterEqual(cw - 8, len(head) * CHAR_W, f"{w}x{h}: column {head} ({cw}px) too narrow")

    def test_mission_card_parts_do_not_overlap_and_show_a_line(self):
        for w, h in SIZES:
            m = layout.missions_layout(w, h)
            for card, parts in zip(m["cards"], m["card_parts"]):
                self.assertGreaterEqual(card[3], 90)
                self.assertGreaterEqual(parts["lines"], 1, f"{w}x{h}: a mission card has no room for an objective line")
                self.assertTrue(parts["button"][2] >= 90 and parts["button"][3] >= 24)
                for a, b in itertools.combinations(("title", "status", "objectives", "footer", "button"), 2):
                    self.assertFalse(rects_overlap(parts[a], parts[b]), f"{w}x{h}: card {a} overlaps {b}")

    def test_map_positions_and_node_at(self):
        nodes = map_data.NODES
        for w, h in SIZES:
            g = layout.map_layout(w, h)
            _mx, _my, mw, mh = g["map"]
            self.assertLess(abs(mw / mh - 964 / 345), 0.03, "the map lost its aspect ratio")
            positions, radius = g["positions"], g["radius"]
            self.assertEqual(len(positions), len(nodes))
            for (i, a), (j, b) in itertools.combinations(enumerate(positions), 2):
                self.assertGreaterEqual((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2, (2 * radius + 4) ** 2,
                                        f"{w}x{h}: stops {i} and {j} touch")
            for i, p in enumerate(positions):
                self.assertEqual(layout.node_at(w, h, p), i, f"{w}x{h}: node_at does not find stop {i}")
                self.assertEqual(layout.map_point(w, h, nodes[i]["pos"]), p)
            self.assertIsNone(layout.node_at(w, h, (0, 0)))
        # relative positions follow the nodes: the coast is west (left) of the start, City 5 is north of City 1
        positions = layout.map_layout(1000, 680)["positions"]
        self.assertLess(positions[5][0], positions[0][0])
        self.assertLess(positions[6][1], positions[1][1])

    def test_map_scales_with_the_window(self):
        small, big = layout.map_layout(640, 480), layout.map_layout(1920, 1080)
        self.assertGreater(big["map"][2], 2 * small["map"][2])
        self.assertGreater(big["radius"], small["radius"])
