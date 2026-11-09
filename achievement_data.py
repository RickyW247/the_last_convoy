"""The achievement catalogue of THE LAST CONVOY (design doc section 20.5). Data only, no pygame.

Each achievement is a dict:
  id           stable key saved in achievements.json (never rename one once released)
  name, description   what the player sees
  placeholder  True: the event / vehicle it needs does not exist in the game yet. It is listed ("COMING SOON") but can
               never be completed. Remove the flag once the content exists (test_achievements.py checks that every
               achievement without the flag only names events and vehicles that exist).
  secret       True: the achievements screen shows it as "???" until it is completed
  condition    {"kind": ..., ...}, one of CONDITION_KINDS (how achievements.AchievementTracker decides):
                 wins                {"count": n}: the player has won n runs in total
                 vehicle_types_seen  {"count": n}: n different vehicle types have been in a convoy (all runs together)
                 run_stat            {"stat": Game attribute, "count": n}: that number reached n in the current run
                 event               {"events": (event ids,), optional "vehicle": type that must be owned}: one of
                                     those events was resolved
                 arrive_with_vehicle {"vehicle": type}: the convoy arrived at a stop while owning that vehicle
                 defeat              {}: a run was lost with no survivor left (Game.end_run, status "lost", survivors 0)
                 win_with_survivors  {"survivors": n}: the run was won with exactly n survivors left
                 win_within_days     {"days": n}: the run was won with Game.day at n or less (a speed run)
                 win_with_stat       {"stat": Game attribute, "count": n}: the run was won with that number at n or more
                 win_without_stat    {"stat": Game attribute, "max": n}: the run was won with that number at n or less
                 win_on_difficulty   {"difficulty": name}: the run was won on that difficulty (config.DIFFICULTIES)
                 win_with_convoy     {"vehicles": (types,), "upgrade": id}: the run was won with every one of those vehicle
                                     types in the convoy, and every vehicle in the convoy has that upgrade installed
                 lifetime_counter    {"counter": key in AchievementTracker.counters, "count": n}: that lifetime counter
                                     (kept in achievements.json, adds up over all runs) reached n. Counters: "wins",
                                     "vehicles_recovered" (RECOVER VEHICLE uses, see AchievementTracker.on_vehicle_recovered)
                 screens_visited     {"screens": (Game.screen values,)}: every one of those screens has been shown at least once
                                     (all runs together; AchievementTracker.screens_seen, kept in achievements.json)
  unlocks_vehicle  optional: the bonus vehicle (vehicle_data.BONUS_VEHICLES), or a tuple of them, completing it unlocks
               for the vehicles screen (AchievementTracker.unlocked_vehicles). Sandbox mode lists every bonus vehicle anyway.
  unlocks_events   optional: an event group name (event dicts carry "group"), completing it unlocks that group of events
               (AchievementTracker.unlocked_event_groups; effect_handler.event_available hides the group until then).
               Sandbox mode allows every group anyway.
  reward       PLACEHOLDER text. achievements.apply_reward does nothing yet; nothing is unlocked by it.
"""
from config import (COLLECTOR_VEHICLE_TYPES, RECOVERED_VEHICLES_TARGET, SPEED_RUN_DAYS, WINS_FOR_LONG_ROAD,
                    DIFFICULTY_ORDER, SPECIAL_EVENTS_GROUP, SCREENS_TO_VISIT)

CONDITION_KINDS = ("wins", "vehicle_types_seen", "run_stat", "event", "arrive_with_vehicle", "defeat",
                   "win_with_survivors", "win_with_stat", "win_without_stat", "lifetime_counter", "win_within_days",
                   "win_on_difficulty", "win_with_convoy", "screens_visited")

# Event ids and vehicle names must match event_data.EVENTS and vehicle_data.VEHICLE_SPECS. The six achievements that used
# to be "placeholder" (Heavy Machinery, Broadcast from the End, Sweet Survival, One Last Laugh, Presidential Protection,
# Armoured Convoy) are earned through the multi-stage missions (mission_data.py / mission_event_data.py).
ACHIEVEMENTS = (
    {"id": "coast_to_coast", "name": "Coast to Coast", "secret": False,
     "description": "Complete the main campaign: reach the Pacific Coast.",
     "condition": {"kind": "wins", "count": 1},
     "unlocks_vehicle": "Coach Bus",
     "reward": "Unlock the Coach Bus"},
    {"id": "convoy_collector", "name": "Convoy Collector", "secret": False,
     "description": f"Have {COLLECTOR_VEHICLE_TYPES} different vehicle types in your convoy (over all runs).",
     "condition": {"kind": "vehicle_types_seen", "count": COLLECTOR_VEHICLE_TYPES},
     "unlocks_vehicle": "Limousine",
     "reward": "Unlock the Limousine"},
    {"id": "heavy_machinery", "name": "Heavy Machinery", "secret": False,
     "description": "Complete the Heavy Machinery event.",
     "condition": {"kind": "event", "events": ("heavy_machinery",)},
     "unlocks_vehicle": ("Excavator", "Bulldozer",  "Crane Truck", "Wrecking Ball Truck"),
     "reward": "Unlock the Excavator, Bulldozer, Crane Truck", "Wrecking Ball Truck"},
    {"id": "broadcast_from_the_end", "name": "Broadcast from the End", "secret": False,
     "description": "Complete the television broadcasting event.",
     "condition": {"kind": "event", "events": ("tv_broadcast",)},
     "unlocks_vehicle": "TV Broadcasting Van",
     "reward": "Unlock the TV Broadcasting Van"},
    {"id": "sweet_survival", "name": "Sweet Survival", "secret": False,
     "description": "Complete the Ice Cream Van event.",
     "condition": {"kind": "event", "events": ("ice_cream_van",)},
     "unlocks_vehicle": "Ice Cream Van",
     "reward": "Unlock the Ice Cream Van"},
    {"id": "well_fed", "name": "Well Fed", "secret": False,
     "description": "Have 40 food in the convoy at once.",
     "condition": {"kind": "run_stat", "stat": "food", "count": 40},
     "unlocks_vehicle": "Food Truck",
     "reward": "Unlock the Food Truck"},
    {"id": "one_last_laugh", "name": "One Last Laugh", "secret": True,
     "description": "Discover the travelling circus event.",
     "condition": {"kind": "event", "events": ("travelling_circus",)},
     "unlocks_vehicle": "Clown Car",
     "reward": "Unlock the Clown Car"},
    {"id": "presidential_protection", "name": "Presidential Protection", "secret": True,
     "description": "Complete the Presidential Escort event.",
     "condition": {"kind": "event", "events": ("presidential_escort",)},
     "unlocks_vehicle": "Presidential Limo",
     "reward": "Unlock the Presidential Limo"},
    {"id": "armoured_convoy", "name": "Armoured Convoy", "secret": False,
     "description": "Reach the end of the road with the Humvee, Military Cargo Truck, Armored Personnel Carrier and "
                    "Tank in your convoy, every vehicle fitted with Armour Plating.",
     "condition": {"kind": "win_with_convoy",
                   "vehicles": ("Military Humvee", "Military Cargo Truck", "Armored Personnel Carrier", "Tank"),
                   "upgrade": "armor_plating"},
     "unlocks_vehicle": "Prototype Military Vehicle",
     "reward": "Unlock the Prototype Military Vehicle"},
    {"id": "hard_road", "name": "Hard Road", "secret": False,
     "description": f"Reach the end of the road on {DIFFICULTY_ORDER[-1]} difficulty.",
     "condition": {"kind": "win_on_difficulty", "difficulty": DIFFICULTY_ORDER[-1]},
     "unlocks_vehicle": "Road Maintenance Truck",
     "reward": "Unlock the Road Maintenance Truck"},
    {"id": "nothing_left_behind", "name": "Nothing Left Behind", "secret": False,
     "description": f"Recover {RECOVERED_VEHICLES_TARGET} vehicles in one run.",
     "condition": {"kind": "run_stat", "stat": "vehicles_recovered", "count": RECOVERED_VEHICLES_TARGET},
     "unlocks_vehicle": "Car Carrier Truck",
     "reward": "Unlock the Car Carrier Truck"},
    {"id": "salvage_legend", "name": "Salvage Legend", "secret": False,
     "description": "Recover 100 vehicles in total (over all runs).",
     "condition": {"kind": "lifetime_counter", "counter": "vehicles_recovered", "count": 100},
     "unlocks_vehicle": "Utility Service Truck",
     "reward": "Unlock the Utility Service Truck"},
    {"id": "hold_the_line", "name": "Hold the Line", "secret": False,
     "description": "Survive 7 days in a row while the horde has overrun your convoy.",
     "condition": {"kind": "run_stat", "stat": "horde_attack_streak", "count": 7},
     "unlocks_vehicle": "Tank",
     "reward": "Unlock the Tank"},
    {"id": "grand_tour", "name": "Grand Tour", "secret": False,
     "description": "Visit every stop on the map in a single run.",
     "condition": {"kind": "run_stat", "stat": "stops_visited_count", "count": 10},   # 11 stops in every layout, minus the start
     "unlocks_vehicle": "Tourist Bus",
     "reward": "Unlock the Tourist Bus"},
    {"id": "last_rites", "name": "Last Rites", "secret": False,
     "description": "Lose a run: every survivor is gone.",
     "condition": {"kind": "defeat"},
     "unlocks_vehicle": "Hearse",
     "reward": "Unlock the Hearse"},
    {"id": "solo_travelling", "name": "Solo Travelling", "secret": False,
     "description": "Reach the end of the road with only 1 survivor.",
     "condition": {"kind": "win_with_survivors", "survivors": 1},
     "unlocks_vehicle": ("Motorcycle", "Dirt Bike", "Scooter"),
     "reward": "Unlock the Motorcycle, Dirt Bike and Scooter"},
    {"id": "scrap_baron", "name": "Scrap Baron", "secret": False,
     "description": "Have 50 scrap in the convoy at once.",
     "condition": {"kind": "run_stat", "stat": "scrap", "count": 50},
     "unlocks_vehicle": "Armored Cash Truck",
     "reward": "Unlock the Armored Cash Truck"},
    {"id": "scorched_earth", "name": "Scorched Earth", "secret": False,
     "description": "Win a run after 5 of your vehicles have been destroyed.",
     "condition": {"kind": "win_with_stat", "stat": "vehicles_wrecked", "count": 5},
     "unlocks_vehicle": "Monster Truck",
     "reward": "Unlock the Monster Truck"},
    {"id": "chequered_flag", "name": "Chequered Flag", "secret": False,
     "description": f"Reach the end of the road within {SPEED_RUN_DAYS} days.",
     "condition": {"kind": "win_within_days", "days": SPEED_RUN_DAYS},
     "unlocks_vehicle": "Formula 1 Car",
     "reward": "Unlock the Formula 1 Car"},
    {"id": "old_school", "name": "Old School", "secret": False,
     "description": "Reach the end of the road without recovering any vehicle.",
     "condition": {"kind": "win_without_stat", "stat": "vehicles_recovered", "max": 0},
     "unlocks_vehicle": "Vintage Police Car",
     "reward": "Unlock the Vintage Police Car"},
    {"id": "rescue_brigade", "name": "Rescue Brigade", "secret": False,
     "description": "Have 30 survivors in the convoy at once.",
     "condition": {"kind": "run_stat", "stat": "survivors", "count": 30},
     "unlocks_vehicle": "Fire Engine",
     "reward": "Unlock the Fire Engine"},
    {"id": "flawless_command", "name": "Flawless Command", "secret": False,
     "description": "Reach the end of the road without losing a single survivor.",
     "condition": {"kind": "win_without_stat", "stat": "survivors_lost", "max": 0},
     "unlocks_vehicle": "Mobile Command Vehicle",
     "reward": "Unlock the Mobile Command Vehicle"},
    {"id": "the_long_road_again", "name": "The Long Road Again", "secret": False,
     "description": "Complete a subsequent playthrough: win a second time.",
     "condition": {"kind": "wins", "count": WINS_FOR_LONG_ROAD},
     "unlocks_events": SPECIAL_EVENTS_GROUP,
     "reward": "Unlock all the special survivor events"},
    {"id": "field_study", "name": "Field Study", "secret": True,
     "description": "Visit every screen of the game.",
     "condition": {"kind": "screens_visited", "screens": SCREENS_TO_VISIT},
     "unlocks_vehicle": "Mobile Laboratory",
     "reward": "Unlock the Mobile Laboratory"},
)

BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


def _check_catalogue():
    ids = [a["id"] for a in ACHIEVEMENTS]
    if len(set(ids)) != len(ids):
        raise ValueError("achievement_data.ACHIEVEMENTS has a duplicate id")
    for a in ACHIEVEMENTS:
        if a["condition"]["kind"] not in CONDITION_KINDS:
            raise ValueError(f"achievement {a['id']!r}: unknown condition kind {a['condition']['kind']!r}")


_check_catalogue()   # a typo fails loudly at import, like convoy.py's RECOVERY_SITE_KEYS check
