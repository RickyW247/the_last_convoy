"""The Pacific Coast evacuation of THE LAST CONVOY: the final scripted sequence (design doc 2.3, 19.2).

Reaching the coast no longer wins the run by itself. The convoy has reached the port, but it still has to secure
passage on the last ship, and the ship has a limited number of berths (config.EVAC_BASE_BERTHS, raised by choices).

The sequence is three scripted events (event_data.py, "trigger": "evacuation", never drawn as ordinary or ambush
events), one after the other: the port gate, the harbour master's quota and boarding under fire. Their choices use the
usual effects plus "berths" (more places on the ship) and horde_gap (the same horde-distance system as everywhere
else; no separate timer). When the last result is dismissed the convoy boards: the horde attacks once if the gap is
0, then min(survivors, berths) survivors escape and the rest are left on the dock. Nobody aboard = the run is lost.

Pygame-free, like the rest of the game package.
"""
from config import EVAC_BASE_BERTHS, EVACUATION_ENABLED, people

EVACUATION_EVENTS = ("evac_gate", "evac_quota", "evac_boarding")   # event_data ids, in the order they are played


class EvacuationMixin:
    """The evacuation state ({"stage", "berths"} while it runs, None otherwise) and its steps."""
    evacuation = None             # reset() makes it None; begin_evacuation() fills it
    survivors_left_behind = 0     # survivors who did not fit on the ship (ending screen / log)

    def evacuating(self):
        """True while the final evacuation sequence is running."""
        return self.evacuation is not None and self.status == "playing"

    def berths(self):
        """Places left on the ship (0 when no evacuation is running)."""
        return self.evacuation["berths"] if self.evacuation else 0

    def add_berths(self, amount):
        """Change the ship's places (an event effect). Never below 0, only while evacuating. Returns the real change."""
        if not self.evacuation:
            return 0
        before = self.evacuation["berths"]
        self.evacuation["berths"] = max(0, before + int(amount))
        return self.evacuation["berths"] - before

    def begin_evacuation(self):
        """The convoy reached the coast: start the sequence (or win at once when config.EVACUATION_ENABLED is False)."""
        if not EVACUATION_ENABLED:
            self.finish_victory()
            return
        self.evacuation = {"stage": 0, "berths": EVAC_BASE_BERTHS}
        self.say(f"The Pacific port at last. One ship is still loading, with room for {EVAC_BASE_BERTHS} people.")
        self._next_evacuation_stage()

    def _next_evacuation_stage(self):
        """Open the next scripted event, or board the ship when they are all done."""
        if self.status != "playing" or not self.evacuation:
            return
        stage = self.evacuation["stage"]
        if stage >= len(EVACUATION_EVENTS):
            self.complete_evacuation()
            return
        self.evacuation["stage"] = stage + 1
        if not self.event_manager.start_event(self, EVACUATION_EVENTS[stage]):
            self._next_evacuation_stage()   # an event that is missing from the data is skipped, never a dead end

    def continue_evacuation(self):
        """Called when an event result is dismissed (or a vehicle pick is done): go on to the next stage."""
        if not self.evacuation or self.status != "playing":
            return
        if self.event_manager.active or self.event_manager.result or self.abandon_pick_needed():
            return
        self._next_evacuation_stage()

    def complete_evacuation(self):
        """Boarding: a horde at the gate attacks one last time, then as many survivors as there are berths escape."""
        if self.horde <= 0:
            self.horde_attack()          # the horde caught the convoy on the dock (may end the run if nobody is left)
            if self.status != "playing":
                self.evacuation = None
                return
        berths = self.berths()
        aboard = min(self.survivors, berths)
        left = self.survivors - aboard
        self.evacuation = None
        self.survivors_left_behind = left
        if aboard <= 0:
            self.end_run("lost", "The ship sailed without you. Nobody from the convoy made it aboard.")
            return
        self.survivors = aboard
        self.survivor_manager.sync_count(aboard)
        self.finish_victory(aboard, left)
