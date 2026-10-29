
"""Situation-based music management for THE LAST CONVOY."""

from pathlib import Path
import pygame


class MusicManager:
    def __init__(self, music_dir="assets/music", volume=0.35):
        self.music_dir = Path(music_dir)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.enabled = True
        self.current_track = None
        self.initialized = False

        self.tracks = {
            "menu": "After The Disaster Pt. 2.mp3",
            "game": "After The Disaster Pt. 6 Loopable.mp3",
            "victory": "A New Page.mp3",
            "defeat": "After The Disaster Pt. 8-Menu Theme.mp3",
        }

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.set_volume(self.volume)
            self.initialized = True

        except pygame.error as exc:
            print(f"Audio initialization failed: {exc}")

    def play_music(self, situation, loop=None):
        """Play the music assigned to a game situation."""
        if not self.initialized or not self.enabled:
            return False

        filename = self.tracks.get(situation)

        if filename is None:
            print(f"Unknown music situation: {situation}")
            return False

        # Keep the current track playing without restarting it.
        if (
            self.current_track == situation
            and pygame.mixer.music.get_busy()
        ):
            return True

        path = self.music_dir / filename

        if not path.is_file():
            print(f"Music file not found: {path}")
            return False

        # Loop gameplay and menu music; play victory/defeat once.
        if loop is None:
            loop = situation in ("menu", "game")

        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1 if loop else 0)
            self.current_track = situation
            return True

        except pygame.error as exc:
            print(f"Could not play {filename}: {exc}")
            self.current_track = None
            return False

    def stop_music(self):
        """Stop the current music."""
        if self.initialized:
            pygame.mixer.music.stop()

        self.current_track = None

    def pause_music(self):
        """Pause the current music."""
        if self.initialized:
            pygame.mixer.music.pause()

    def resume_music(self):
        """Resume music if audio is enabled."""
        if self.initialized and self.enabled:
            pygame.mixer.music.unpause()

    def set_volume(self, volume):
        """Set music volume between 0.0 and 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))

        if self.initialized:
            pygame.mixer.music.set_volume(self.volume)

    def toggle_music(self):
        """Toggle music on or off."""
        self.enabled = not self.enabled

        if not self.enabled:
            self.pause_music()
        elif self.initialized:
            if self.current_track is None:
                self.play_music("menu")
            else:
                pygame.mixer.music.unpause()

        return self.enabled

    def shutdown(self):
        """Stop playback and release the audio mixer."""
        if self.initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.initialized = False
