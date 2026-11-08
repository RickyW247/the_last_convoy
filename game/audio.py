"""Background music of THE LAST CONVOY: which track plays on which screen, and the mute switch.
"""


class AudioMixin:
    """Music follows the game state (needs self.music_manager, self.music_muted, self.status and self.screen)."""
    def toggle_music_mute(self):
        """Toggle background music on or off."""

        self.music_muted = not self.music_muted

        if self.music_muted:
            self.music_manager.pause_music()
        else:
            self.update_music()

    def update_music(self):
        """Update background music according to the current game state."""

        # Never start music while muted.
        if self.music_muted:
            self.music_manager.pause_music()
            return

        if self.status == "won":
            self.music_manager.play_music("victory")

        elif self.status == "lost":
            self.music_manager.play_music("defeat")

        elif self.screen in ("title", "lore", "background", "menu", "difficulty", "settings", "credits", "instructions"):
            self.music_manager.play_music("menu")

        elif self.screen in ("convoy", "map", "vehicles", "missions", "survivors"):
            self.music_manager.play_music("game")
