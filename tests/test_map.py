"""Tests for map_data.py and map_system.py: map data, sites, roads, pathfinding and drawing."""

import config
import layout
import map_data
import map_system

from tests.helpers import LayoutTestCase, make_game, surface


class MapTestCase(LayoutTestCase):
    """Runs on the pinned map layout; NODES always follows the active layout."""

    @property
    def NODES(self):
        return map_data.NODES


class MapSystemTests(MapTestCase):
    def test_start_and_destination(self):
        self.assertEqual(self.NODES[map_data.START]["kind"], "start")
        self.assertEqual(self.NODES[map_data.PACIFIC]["kind"], "coast")
        self.assertEqual(self.NODES[map_data.START]["axis"], 0)
        self.assertEqual(max(n["axis"] for n in self.NODES), self.NODES[map_data.PACIFIC]["axis"])

    def test_nodes_are_complete_and_unique(self):
        for node in self.NODES:
            for key in ("name", "kind", "axis", "pos", "tag", "label", "sites"):
                self.assertIn(key, node)
        for key in ("name", "tag"):
            values = [n[key] for n in self.NODES]
            self.assertEqual(len(values), len(set(values)), f"duplicate {key}")

    def test_map_labels_are_consistent(self):
        """Cities are numbered 1-8; the other stops have a letter: S start, C coast, P pass."""
        for node in self.NODES:
            self.assertEqual(len(node["tag"]), 1, node["name"])            # fits inside the marker
            if node["kind"] == "city":
                self.assertTrue(node["tag"].isdigit(), node["name"])
                self.assertEqual(node["name"], f"City {node['tag']}")
        city_tags = sorted(n["tag"] for n in self.NODES if n["kind"] == "city")
        self.assertEqual(city_tags, [str(number) for number in range(1, 9)])
        self.assertEqual(self.NODES[map_data.START]["tag"], "S")
        self.assertEqual(self.NODES[map_data.PACIFIC]["tag"], "C")
        self.assertEqual(next(n["tag"] for n in self.NODES if n["kind"] == "pass"), "P")

    def test_recovery_sites_exist_on_the_map(self):
        names = {map_data.SITES[key]["name"] for node in self.NODES for key in node["sites"]}
        for site in config.RECOVERY_SITES:
            self.assertIn(site, names)

    def test_roads_connect_real_stops_and_are_never_shorter_than_the_straight_line(self):
        for a, b, km, kind in map_data.ROAD_EDGES:
            self.assertIn(a, range(len(self.NODES)))
            self.assertIn(b, range(len(self.NODES)))
            self.assertGreaterEqual(km, abs(self.NODES[a]["axis"] - self.NODES[b]["axis"]), f"road {a}-{b}")
            self.assertIn(kind, ("main", "spur", "alt"))

    def test_adjacency_is_symmetric(self):
        for a, neighbours in map_data.ADJACENT.items():
            for b, km in neighbours:
                self.assertIn((a, km), map_data.ADJACENT[b])

    def test_every_stop_is_reachable_from_every_other(self):
        ids = range(len(self.NODES))
        for a in ids:
            for b in ids:
                path, km = map_data.shortest_path(a, b)
                self.assertEqual((path[0], path[-1]), (a, b), f"{a} -> {b}")
                self.assertEqual(km == 0, a == b)

    def test_shortest_path_is_symmetric_and_adds_up(self):
        ids = range(len(self.NODES))
        for a in ids:
            for b in ids:
                path, km = map_data.shortest_path(a, b)
                _back_path, back_km = map_data.shortest_path(b, a)
                self.assertEqual(km, back_km)      # (equally long alternative routes may differ, so only km is compared)
                total = 0
                for x, y in zip(path, path[1:]):
                    total += dict(map_data.ADJACENT[x])[y]
                self.assertEqual(total, km)

    def test_mountain_pass_bypasses_the_truck_stop(self):
        path, km = map_data.shortest_path(map_data.START, map_data.PACIFIC)
        truck_stop = next(i for i, n in enumerate(self.NODES) if n["name"] == "City 3")   # the bypassed city
        mountain_pass = next(i for i, n in enumerate(self.NODES) if n["name"] == "Mountain Pass")
        self.assertIn(mountain_pass, path)
        self.assertNotIn(truck_stop, path)
        main_road_km = sum(km for a, b, km, kind in map_data.ROAD_EDGES if kind == "main" and a < 5 and b <= 5)
        self.assertLess(km, main_road_km)

    def test_survivor_finds_are_valid(self):
        for kind, (chance, smallest, largest) in map_data.SURVIVOR_FINDS.items():
            self.assertIn(kind, map_data.SITES)
            self.assertTrue(0 < chance <= 1)
            self.assertTrue(1 <= smallest <= largest)
        self.assertIn("start", map_data.SURVIVOR_FINDS)

    def test_route_point_runs_along_the_main_road(self):
        self.assertEqual(map_system.route_point_for_axis(0), self.NODES[map_data.START]["pos"])
        self.assertEqual(map_system.route_point_for_axis(560), self.NODES[map_data.PACIFIC]["pos"])
        self.assertEqual(map_system.route_point_for_axis(9999), self.NODES[map_data.PACIFIC]["pos"])
        xs = [map_system.route_point_for_axis(axis)[0] for axis in range(0, 561, 20)]
        self.assertEqual(xs, sorted(xs, reverse=True))             # west is to the left
        self.assertGreaterEqual(map_system.route_point_for_axis(-200)[0], self.NODES[0]["pos"][0])

    def test_minimap_points_stay_inside_the_card(self):
        x0, y0, width, height = layout.MINI_CARD
        for node in self.NODES:
            x, y = map_system.mini_point(*node["pos"])
            self.assertTrue(x0 <= x <= x0 + width and y0 <= y <= y0 + height, node["name"])

    def test_danger_markers(self):
        g = make_game()
        g.position, g.current_location = 3, "City 3"
        g.horde = 30
        self.assertIsNone(g.travel_danger(3))                         # already here
        self.assertIsNone(g.travel_danger(5))                         # heading west is always safe
        self.assertEqual(g.travel_danger(1), "overrun")               # back east with the horde 30 km behind
        self.assertEqual(g.travel_danger(8), "risky")                 # sideways detour: the horde might arrive
        g.horde = 10
        self.assertEqual(g.travel_danger(8), "overrun")
        g.horde = 40
        self.assertIsNone(g.travel_danger(8))

    def test_map_info_names_the_sites_of_the_selected_city(self):
        """The info panel text for every stop is built from SITES; drawing each must not fail."""
        g = make_game()
        for selected in range(len(self.NODES)):
            g.selected = selected
            map_system.draw_map(surface(), g)

    def test_map_and_minimap_draw_for_every_selection(self):
        g = make_game()
        for position in range(len(self.NODES)):
            g.position, g.current_location = position, self.NODES[position]["name"]
            for selected in range(len(self.NODES)):
                g.selected = selected
                map_system.draw_map(surface(), g)
                map_system.draw_minimap(surface(), g)


class SiteDataTests(MapTestCase):
    def test_every_site_is_complete(self):
        for key, site in map_data.SITES.items():
            with self.subTest(site=key):
                self.assertTrue(site["name"])
                self.assertTrue(site["short"])
                self.assertLessEqual(len(site["short"]), 15, "too long for the SITE button")
                self.assertTrue(site["detail"])

    def test_every_stop_lists_known_sites_without_duplicates(self):
        for node in self.NODES:
            self.assertEqual(len(node["sites"]), len(set(node["sites"])), node["name"])
            for key in node["sites"]:
                self.assertIn(key, map_data.SITES, node["name"])

    def test_cities_have_three_sites_and_the_other_stops_follow_their_role(self):
        for node in self.NODES:
            if node["kind"] == "city":
                self.assertEqual(len(node["sites"]), 3, node["name"])
        self.assertEqual(self.NODES[map_data.START]["sites"], ["start"])
        self.assertEqual(self.NODES[map_data.PACIFIC]["sites"], [])
        self.assertEqual(next(n["sites"] for n in self.NODES if n["kind"] == "pass"), ["pass"])

    def test_every_site_is_used_somewhere(self):
        used = {key for node in self.NODES for key in node["sites"]}
        self.assertEqual(used, set(map_data.SITES))

    def test_some_sites_exist_in_several_cities(self):
        counts = {}
        for node in self.NODES:
            for key in node["sites"]:
                counts[key] = counts.get(key, 0) + 1
        self.assertTrue(any(count > 1 for count in counts.values()))

    def test_site_names_are_unique(self):
        names = [site["name"] for site in map_data.SITES.values()]
        self.assertEqual(len(names), len(set(names)))
