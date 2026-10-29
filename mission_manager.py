
"""Mission activation, objective tracking, and lifecycle management."""

from mission_data import MISSIONS
from mission_handler import apply_rewards


class MissionManager:
    def __init__(self):
        self.missions = {}
        self._load_missions()

    def _load_missions(self):
        """Load mission definitions and initialize their states."""
        for mission in MISSIONS:
            mission_id = mission["id"]

            if mission_id in self.missions:
                raise ValueError(f"Duplicate mission ID: {mission_id}")

            self.missions[mission_id] = {
                "data": mission,
                "status": "Locked" if mission.get("prerequisites") else "Available",
                "progress": [0] * len(mission.get("objectives", [])),
            }

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
        state["progress"] = [
            0
            for _ in state["data"].get("objectives", [])
        ]

        game.say(f"Mission accepted: {state['data']['title']}.")
        self._check_completion(game, mission_id)
        return True

    def on_resource_collected(self, game, resource, amount):
        """Track newly collected fuel, food, water, or scrap."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            return

        self._update_objectives(
            game,
            "collection",
            lambda objective: objective.get("resource") == resource,
            amount,
        )

    def on_destination_reached(self, game, stop_id):
        """Track arrival at a specific map stop."""
        self._update_objectives(
            game,
            "destination",
            lambda objective: objective.get("stop_id") == stop_id,
            1,
        )

    def on_survivors_recruited(self, game, amount=1):
        """Track newly recruited survivors."""
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

        if not all(
            state["progress"][index] >= objective.get("target", 1)
            for index, objective in enumerate(objectives)
        ):
            return False

        # Change state before applying rewards to prevent duplicate claims.
        state["status"] = "Completed"

        notes = apply_rewards(
            game, state["data"].get("rewards", [])
        )

        game.say(f"Mission completed: {state['data']['title']}!")

        if notes:
            game.say("Rewards: " + "; ".join(notes))

        self._refresh_availability()
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

        state["status"] = "Abandoned"
        game.say(f"Mission abandoned: {state['data']['title']}.")
        return True
