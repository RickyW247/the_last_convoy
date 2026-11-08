"""Headless test: which stops show the desert scenery on every map layout (no pygame needed)."""
import map_data


def test_scenery_follows_the_mountain_pass():
    for index, layout in enumerate(map_data.LAYOUTS):
        map_data.load_layout(index)
        pass_id = next(i for i, node in enumerate(map_data.NODES) if node["kind"] == "pass")
        pass_axis = map_data.NODES[pass_id]["axis"]
        assert map_data.scenery_for(map_data.START) == "highway", layout["name"]
        assert map_data.scenery_for(pass_id) == "highway", layout["name"]
        assert map_data.scenery_for(map_data.PACIFIC) == "desert", layout["name"]
        for stop, node in enumerate(map_data.NODES):
            expected = "desert" if node["axis"] > pass_axis else "highway"
            assert map_data.scenery_for(stop) == expected, (layout["name"], node["name"])
    map_data.load_layout(0)


if __name__ == "__main__":
    test_scenery_follows_the_mountain_pass()
    print("scenery tests passed")
