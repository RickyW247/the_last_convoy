"""Which missions / survivors the list screens show, and keeping their page numbers valid (no pygame).

buttons.py and the drawing code only read from here; clamp_pages is the one place that writes the page numbers, and
main.py calls it once per frame (after events, so a resize or a new list never leaves the page past the end).
"""
from achievement_data import ACHIEVEMENTS
from layout import missions_layout, page_count, survivors_layout, vehicles_layout
from layout.achievements import achievements_layout
from layout.upgrade import upgrade_layout
from vehicle_data import VEHICLE_SPECS


def filtered_missions(game):
    """[(mission id, state)] of the missions the missions screen lists: the completed ones, or all the others.
    Read-only: the mission manager refreshes which missions are available when one is completed and whenever the
    missions screen is opened (Game.screen)."""
    manager = getattr(game, "mission_manager", None)
    if manager is None:
        return []
    wanted = game.mission_filter == "Completed"
    return [(mid, state) for mid, state in manager.missions.items() if (state["status"] == "Completed") == wanted]


def survivor_total(game):
    manager = getattr(game, "survivor_manager", None)
    return len(manager.get_survivors()) if manager is not None else 0


def clamp_pages(game, size):
    """Keep the survivors and missions page numbers valid for this window size (the pages hold as many rows as fit
    the window, so a resize can leave the current page past the end)."""
    if game.screen == "survivors":
        pages = page_count(survivor_total(game), survivors_layout(int(size[0]), int(size[1]))["per_page"])
        game.survivor_page = max(0, min(game.survivor_page, pages - 1))
    elif game.screen == "vehicles":
        total = len(VEHICLE_SPECS)
        pages = page_count(total, vehicles_layout(int(size[0]), int(size[1]), total)["per_page"])
        game.vehicle_page = max(0, min(getattr(game, "vehicle_page", 0), pages - 1))
    elif game.screen == "missions":
        pages = page_count(len(filtered_missions(game)), missions_layout(int(size[0]), int(size[1]))["per_page"])
        game.mission_page = max(0, min(game.mission_page, pages - 1))
    elif game.screen == "achievements":
        pages = page_count(len(ACHIEVEMENTS), achievements_layout(int(size[0]), int(size[1]))["per_page"])
        game.achievement_page = max(0, min(getattr(game, "achievement_page", 0), pages - 1))


def upgrade_page(game, size):
    """The page of the upgrade table that is showing. After the player turns the page it stays; as soon as another upgrade
    or vehicle is selected (a click, Up / Down, opening the screen) the table follows the selection to its page."""
    ids = [upgrade["id"] for upgrade in game.available_upgrades()]
    g = upgrade_layout(int(size[0]), int(size[1]), len(ids))
    key = (game.selected_vehicle_type, game.selected_upgrade_id())
    turned = getattr(game, "upgrade_turned", None)   # (key, page) of the last page turn
    if turned is not None and turned[0] == key:
        page = turned[1]
    else:
        chosen = key[1]
        page = ids.index(chosen) // g["per_page"] if chosen in ids else 0
    return max(0, min(page, g["pages"] - 1))


def turn_upgrade_page(game, size, page):
    """Show page `page` of the upgrade table (kept inside the pages that exist) until another upgrade is selected."""
    count = len(game.available_upgrades())
    pages = upgrade_layout(int(size[0]), int(size[1]), count)["pages"]
    game.upgrade_turned = ((game.selected_vehicle_type, game.selected_upgrade_id()), max(0, min(page, pages - 1)))
