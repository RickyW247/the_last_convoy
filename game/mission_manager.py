
"""Mission activation, objective tracking, stages, and lifecycle management.

A mission with a "stages" list (mission_data.py) plays one stage at a time. state["data"] is then a view of the mission
(_stage_view) whose "objectives" and "description" are the CURRENT stage's, so every screen that already reads
state["data"]["objectives"] and state["progress"] shows the stage in progress without knowing about stages.
state["stage"] is the index of that stage (savegame.py must keep it, next to "status" and "progress").
"""

from map_data import NODES
from .effect_handler import owned_vehicle_names
from .event_data import EVENTS
from .mission_data import MISSIONS
from .mission_handler import apply_rewards

# Objective types that are a LEVEL (what the convoy holds right now) instead of a running total.
LEVEL_TYPES = ("stockpile", "vehicle")


def _stage_view(mission, index):
    """The mission dict as the screens should see it while stage `index` is current (a plain mission: itself)."""
    stages = mission.get("stages")
    if not stages:
        return mission
    stage = stages[index]
    view = dict(mission)
    view["objectives"] = stage.get("objectives", [])
    view["description"] = stage.get("description") or mission.get("description", "")
    view["stage"] = index + 1
    view["stage_count"] = len(stages)
    view["stage_title"] = stage.get("title", "")
    return view


def _all_objectives(mission):
    """Every objective of a mission, whatever shape it has (flat or staged)."""
    if mission.get("stages"):
        return [o for stage in mission["stages"] for o in stage.get("objectives", [])]
    return list(mission.get("objectives", []))


def validate_mission(mission):
    """[problem] for one mission definition (empty: fine). Checked when the manager loads, so a typo fails loudly."""
    problems = []
    name = mission.get("id", "?")
    if mission.get("stages") and mission.get("objectives"):
        problems.append(f"mission {name}: give either objectives or stages, not both")
    if "stages" in mission and not mission["stages"]:
        problems.append(f"mission {name}: stages is empty")
    mission_events = {e.get("id"): e for e in EVENTS}
    for objective in _all_objectives(mission):
        if objective.get("type") == "event":
            event = mission_events.get(objective.get("event_id"))
            if event is None:
                problems.append(f"mission {name}: unknown event {objective.get('event_id')!r}")
            elif event.get("trigger") != "mission":
                problems.append(f"mission {name}: event {objective.get('event_id')!r} needs \"trigger\": \"mission\"")
    return problems


class MissionManager:
    def __init__(self):
        self.missions = {}
        self._applying_rewards = False
        self._declined = {}   # mission event id -> game.travel_count when the player said "not now" (see open_stage_event)
        self._load_missions()

    def _load_missions(self):
        """Load mission definitions and initialize their states."""
        for mission in MISSIONS:
            mission_id = mission["id"]

            if mission_id in self.missions:
                raise ValueError(f"Duplicate mission ID: {mission_id}")

            problems = validate_mission(mission)
            if problems:
                raise ValueError("bad mission data:\n  " + "\n  ".join(problems))

            view = _stage_view(mission, 0)
            self.missions[mission_id] = {
                "data": view,                 # the current stage's view (the mission itself when it has no stages)
                "mission": mission,           # the full definition
                "stage": 0,
                "status": "Locked" if mission.get("prerequisites") else "Available",
                "progress": [0] * len(view.get("objectives", [])),
            }

    def restore_stage(self, mission_id, index):
        """Put a mission back at stage `index` (loading a save). False (nothing changes) for an unknown mission, a plain
        mission or an index outside its stages."""
        state = self.missions.get(mission_id)
        stages = state["mission"].get("stages") if state else None
        if not stages or not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(stages):
            return False
        self._set_stage(state, index)
        return True

    def _set_stage(self, state, index):
        """Make stage `index` current: new view, fresh progress."""
        state["stage"] = index
        state["data"] = _stage_view(state["mission"], index)
        state["progress"] = [0 for _ in state["data"].get("objectives", [])]

    def _refresh_availability(self):
        """Unlock missions whose prerequisites have been completed."""
        for mission_id, state in self.missions.items():
            if state["status"] != "Locked":
                continue

            prerequisites = state["data"].get("prerequisites", [])

            if all(
                self.missions.get(pid, {}).get("status") == "Completed"
                for pid in prerequisites
            ):
                state["status"] = "Available"

    def get_available_missions(self):
        """Return missions that can currently be accepted."""
        self._refresh_availability()
        return [
            state["data"]
            for state in self.missions.values()
            if state["status"] == "Available"
        ]

    def get_active_missions(self):
        """Return missions currently being tracked."""
        return [
            state["data"]
            for state in self.missions.values()
            if state["status"] == "Active"
        ]

    def get_mission(self, mission_id):
        """Return mission data and runtime state."""
        return self.missions.get(mission_id)

    def accept_mission(self, game, mission_id):
        """Accept an available mission."""
        self._refresh_availability()
        state = self.missions.get(mission_id)

        if not state or state["status"] != "Available":
            return False

        state["status"] = "Active"
        self._set_stage(state, 0)

        game.say(f"Mission accepted: {state['data']['title']}.")
        # A stockpile objective may already be satisfied by what the convoy holds right now.
        self._refresh_stockpiles(game, state)
        # A destination can already be reached when the mission is accepted (the player stands at or beyond it), and no
        # arrival is coming to credit it. Collection missions are not back-filled: they count only what is collected
        # after acceptance.
        position = getattr(game, "position", None)
        if position is not None:
            self.on_destination_reached(game, position)
        self._check_completion(game, mission_id)
        return True

    def on_resource_collected(self, game, resource, amount):
        """Track newly collected fuel, food, water, or scrap."""
        if self._applying_rewards:
            return

        if not isinstance(amount, (int, float)) or amount <= 0:
            return

        self._update_objectives(
            game,
            "collection",
            lambda objective: objective.get("resource") == resource,
            amount,
        )

    @staticmethod
    def _refresh_stockpiles(game, state):
        """Set every level objective's progress to what the convoy holds now: "stockpile" (a resource, capped at the
        target) and "vehicle" (1 while the convoy owns that vehicle type).

        Unlike collection, this is a level, not a running total: it can go down again when the resource is spent or the
        vehicle is lost."""
        owned = None
        for index, objective in enumerate(state["data"].get("objectives", [])):
            if objective.get("type") == "vehicle":
                owned = owned_vehicle_names(game) if owned is None else owned
                wanted = str(objective.get("vehicle", "")).strip().lower()
                state["progress"][index] = 1 if wanted in owned else 0
                continue
            if objective.get("type") != "stockpile":
                continue
            held = getattr(game, objective.get("resource", ""), 0)
            if not isinstance(held, (int, float)) or isinstance(held, bool):
                held = 0
            state["progress"][index] = max(0, min(objective.get("target", 1), held))

    def on_resources_changed(self, game):
        """Re-read what the convoy holds: updates the progress of active stockpile missions and completes those that
        are met. Cheap, so it is safe to call often: Game.gain / gain_cargo and the fuel effect call it when supplies
        rise (so headless play completes missions), and main.py calls it every frame while playing (so the missions
        screen also shows a drop after supplies were spent)."""
        if self._applying_rewards:
            return

        for mission_id, state in list(self.missions.items()):
            if state["status"] != "Active":
                continue
            if any(o.get("type") in LEVEL_TYPES for o in state["data"].get("objectives", [])):
                self._check_completion(game, mission_id)

    def on_destination_reached(self, game, stop_id):
        """Track arrival at a specific map stop."""
        self._update_objectives(
            game,
            "destination",
            lambda objective: self._stop_matches(objective, stop_id),
            1,
        )

    @staticmethod
    def _stop_matches(objective, stop_id):
        """True if arriving at stop_id satisfies a destination objective."""
        if "node_flag" in objective:
            try:
                return bool(NODES[stop_id].get(objective["node_flag"]))
            except (IndexError, KeyError, TypeError, AttributeError):
                return False
        if "min_axis" in objective:
            try:
                return NODES[stop_id]["axis"] >= objective["min_axis"]
            except (IndexError, KeyError, TypeError):
                return False
        return stop_id in objective.get("stop_ids", [objective.get("stop_id")])

    def on_journey_completed(self, game):
        """The convoy arrived at a stop: counts for "travel" objectives (with "vehicle": only if that vehicle is owned)."""
        owned = owned_vehicle_names(game)

        def matches(objective):
            wanted = objective.get("vehicle")
            return wanted is None or str(wanted).strip().lower() in owned

        self._update_objectives(game, "travel", matches, 1)

    def on_event_resolved(self, game, event_id):
        """The player picked a choice of a mission event (not a "declines_mission" one): its "event" objective is done."""
        self._declined.pop(event_id, None)
        self._update_objectives(game, "event", lambda objective: objective.get("event_id") == event_id, 1)

    def on_event_declined(self, game, event_id):
        """The player said "not now" to a mission event: it does not count, and comes back at the next stop."""
        self._declined[event_id] = getattr(game, "travel_count", 0)

    def pending_event_ids(self, game):
        """Ids of the mission events that are ready: every other objective of the stage is met, the event is not."""
        ready = []
        for state in self.missions.values():
            if state["status"] != "Active":
                continue
            self._refresh_stockpiles(game, state)
            objectives = state["data"].get("objectives", [])
            progress = state["progress"]
            waiting = [i for i, o in enumerate(objectives)
                       if o.get("type") == "event" and progress[i] < o.get("target", 1)]
            others_met = all(progress[i] >= o.get("target", 1)
                             for i, o in enumerate(objectives) if o.get("type") != "event")
            if waiting and others_met:
                ready.append(objectives[waiting[0]]["event_id"])
        return ready

    def open_stage_event(self, game):
        """Open the dedicated event of a stage that is ready. Only at a stop on the convoy screen with nothing else
        open (never mid-journey). An event the player declined waits for the next arrival. Returns True if one opened.
        Call it after an arrival and once a frame while playing (main.py)."""
        manager = getattr(game, "event_manager", None)
        if (manager is None or game.status != "playing" or game.journey or getattr(game, "evacuation", None)
                or manager.active or manager.result or game.screen != "convoy"
                or getattr(game, "confirm_popup", None) or getattr(game, "site_picker", False)
                or game.abandon_pick_needed()):
            return False
        for event_id in self.pending_event_ids(game):
            if self._declined.get(event_id, -1) >= getattr(game, "travel_count", 0):
                continue
            if manager.start_event(game, event_id, announce="Mission"):
                return True
        return False

    def on_survivors_recruited(self, game, amount=1):
        """Track newly recruited survivors."""
        if self._applying_rewards:
            return

        if not isinstance(amount, (int, float)) or amount <= 0:
            return

        self._update_objectives(
            game,
            "rescue",
            lambda objective: True,
            amount,
        )

    def _update_objectives(
        self, game, objective_type, matches, amount
    ):
        """Update matching objectives across all active missions."""
        for mission_id, state in self.missions.items():
            if state["status"] != "Active":
                continue

            objectives = state["data"].get("objectives", [])

            for index, objective in enumerate(objectives):
                if objective.get("type") != objective_type:
                    continue

                if not matches(objective):
                    continue

                target = objective.get("target", 1)
                current = state["progress"][index]
                state["progress"][index] = min(
                    target, current + amount
                )

            self._check_completion(game, mission_id)

    def _check_completion(self, game, mission_id):
        """Complete a mission once all objectives are met."""
        state = self.missions[mission_id]

        if state["status"] != "Active":
            return False

        objectives = state["data"].get("objectives", [])

        # Stockpile objectives are levels: re-read them now so the check below never uses a stale amount.
        self._refresh_stockpiles(game, state)

        if not all(
            state["progress"][index] >= objective.get("target", 1)
            for index, objective in enumerate(objectives)
        ):
            return False

        stages = state["mission"].get("stages")
        if stages and state["stage"] < len(stages) - 1:
            return self._advance_stage(game, mission_id, state, stages)

        # Change state before applying rewards to prevent duplicate claims.
        state["status"] = "Completed"

        # Rewards are not progress: don't let them advance other missions.
        self._applying_rewards = True

        try:
            notes = apply_rewards(
                game, state["data"].get("rewards", [])
            )
        finally:
            self._applying_rewards = False

        game.say(f"Mission completed: {state['data']['title']}!")

        if notes:
            game.say("Rewards: " + "; ".join(notes))

        self._refresh_availability()
        # The rewards may have lifted a stockpile past another mission's target (rewards themselves are never progress,
        # but what they leave in the cargo hold is what the convoy holds). The status is already "Completed", so this
        # cannot loop.
        self.on_resources_changed(game)
        return True

    def _advance_stage(self, game, mission_id, state, stages):
        """The current stage is done: pay its rewards, move to the next one (which may already be met)."""
        finished = stages[state["stage"]]
        self._applying_rewards = True   # stage rewards are not progress either
        try:
            notes = apply_rewards(game, finished.get("rewards", []))
        finally:
            self._applying_rewards = False
        self._set_stage(state, state["stage"] + 1)
        game.say(f"Stage complete: {finished.get('title', 'Stage')}. Next: {state['data'].get('stage_title', '')}.")
        if notes:
            game.say("Rewards: " + "; ".join(notes))
        # Like accept_mission: a destination of the new stage may already be reached, and levels may already hold.
        position = getattr(game, "position", None)
        if position is not None:
            self.on_destination_reached(game, position)
        self._check_completion(game, mission_id)
        return True

    def fail_mission(self, game, mission_id, reason=""):
        """Fail an active mission."""
        state = self.missions.get(mission_id)

        if not state or state["status"] != "Active":
            return False

        state["status"] = "Failed"
        message = f"Mission failed: {state['data']['title']}."

        if reason:
            message += f" {reason}"

        game.say(message)
        return True

    def abandon_mission(self, game, mission_id):
        """Abandon an active mission."""
        state = self.missions.get(mission_id)

        if not state or state["status"] != "Active":
            return False

        # Abandoning returns the mission to the board so it can be accepted
        # again; a permanent status here would lock every mission that
        # lists it as a prerequisite.
        state["status"] = "Available"
        self._set_stage(state, 0)
        game.say(f"Mission abandoned: {state['data']['title']}.")
        return True
