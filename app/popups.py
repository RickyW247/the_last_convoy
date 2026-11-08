"""Popup management: determines which popup is active, builds its buttons and
coordinates the drawing of popups, confirmations, events and ending screens."""

from buttons import (
    make_abandon_buttons,
    make_confirm_buttons,
    make_end_buttons,
    make_site_buttons,
)

from widgets import draw_dim

from ui import (
    draw_abandon_popup,
    draw_confirm_popup,
    draw_end_overlay,
    draw_event_overlay,
    draw_event_result_overlay,
    draw_site_popup,
    make_event_buttons,
    make_result_buttons,
)


def popup_kind(game):
    """Which popup is open: "abandon" (which vehicle to give up), "confirm" (are you sure?), "result", "event", "end"
    (victory / game over), "sites" (SCAVENGE) or None."""
    if game.abandon_pick_needed():
        return "abandon"
    if game.confirm_popup:
        return "confirm"
    if game.event_result:
        return "result"
    if game.event_manager.active:
        return "event"
    if game.status != "playing" and game.screen != "history":   # the history screen (opened from the ending) has no popup over it
        return "end"
    return "sites" if game.site_picker else None


def popup_buttons(game, size):
    """The buttons of the popup that is open (abandon, confirm, result, event, ending or SCAVENGE), or None when none is."""
    if game.abandon_pick_needed():
        return make_abandon_buttons(game, size)
    if game.confirm_popup:
        return make_confirm_buttons(game, size)
    if game.event_result:
        return make_result_buttons(game.event_result, size)
    if game.event_manager.active:
        return make_event_buttons(game.event_manager.current_event, size, game)
    if game.status != "playing" and game.screen != "history":
        return make_end_buttons(game, size)
    if game.site_picker:
        return make_site_buttons(game, size)
    return None


def draw_popups(surface, game, popup):
    """Event, result and ending popups: dim the whole window, then draw the popup straight onto it.

    popup is the frame's popup button list (popup_buttons), reused for the ending popup's buttons.
    """
    kind = popup_kind(game)
    if kind == "abandon":
        draw_dim(surface)
        draw_abandon_popup(surface, game, popup)
        return
    if kind == "confirm":
        draw_dim(surface)
        draw_confirm_popup(surface, game, popup)
        return
    if kind == "sites":
        draw_dim(surface)
        draw_site_popup(surface, game, popup)
        return
    show_end = game.status != "playing" and not game.event_result and game.screen != "history"   # a win or loss caused by an event shows after its result screen
    if not (game.event_result or game.event_manager.active or show_end):
        return
    draw_dim(surface)
    if game.event_result:
        draw_event_result_overlay(surface, game.event_result, popup)
    elif game.event_manager.active:
        draw_event_overlay(surface, game.event_manager.current_event, popup)
    if show_end:
        # popup holds the ending's buttons unless an event popup is also open (then it holds that popup's).
        end_buttons = popup if not game.event_manager.active else make_end_buttons(game, surface.get_size())
        draw_end_overlay(surface, game, end_buttons)