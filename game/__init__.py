"""Game rules for THE LAST CONVOY (package): the Vehicle and Game classes.

This package must stay free of pygame (it imports only config.py, vehicle_data.py, event_manager.py, the managers and the
map data / pathfinding from map_data.py), so the rules can be imported and tested without a display. main.py owns the
window, input and drawing.

`Game` (core.py) is assembled from mixins, one per area of the rules, so `from game import Game, Vehicle,
recovery_cost` works as it did when this was a single game.py:

  vehicle.py     Vehicle, recovery_cost
  null_audio.py  NullAudio: silent music / sound managers for tests, Game(music=NullAudio(), sound=NullAudio())
  state.py       __init__, reset, run statistics, say (the event log), end_run
  navigation.py  the screen property, pause menu, credits, instructions, "are you sure?" popup, fullscreen
  audio.py       music per screen / game state, mute
  horde.py       the horde's position, the gap, danger states, zombie count
  survival.py    difficulty, daily food and water use, advance_time, defeat
  conditions.py  survivor hunger, thirst and injury stages (counts, daily update, who leaves or dies)
  convoy.py      vehicle totals, cargo and fuel capacity, gain / trim supplies, drivers and seats, recover /
                 abandon / repair vehicles, who rides where
  travel.py      destination, plan_trip, travel danger, ambushes, arriving, events, victory
  evacuation.py  the Pacific Coast evacuation: three scripted events, ship berths, who escapes
  scavenge.py    the sites of a stop, the SCAVENGE popup, site yields, finding survivors

A new rule goes in the mixin of its area; a method may call methods of the other mixins through self.
"""
import random   # noqa: F401  (old code and tests reach the random module as game.random)

from map_data import NODES, SITES, START, SURVIVOR_FINDS, shortest_path   # noqa: F401  (names game.py used to have)
from vehicle_data import RECOVERY_COSTS, VEHICLE_SPECS   # noqa: F401

from .core import Game
from .vehicle import Vehicle, recovery_cost

__all__ = ["Game", "Vehicle", "recovery_cost"]
