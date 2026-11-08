"""Situation-based music management for THE LAST CONVOY."""

import time
from pathlib import Path

import pygame

from platform_web import IS_WEB


# The music folder next to this file, so the audio works wherever the game is launched from.
_DEFAULT_MUSIC_DIR = Path(__file__).resolve().parent / "assets" / "music"


class MusicManager:
    def __init__(self, music_dir=None, volume=0.35):
        self.music_dir = _DEFAULT_MUSIC_DIR if music_dir is None else Path(music_dir)

        # Master volume (controlled by settings screen)
        self.volume = max(0.0, min(1.0, float(volume)))

        # Individual track volume multipliers
        self.defeat_volume = 0.95
        self.victory_volume = 0.25
        self.game_volume = 0.50

        # Temporary "ducking" (e.g. while the engine loop plays). Separate from the settings volume.
        self.duck_factor = 0.4          # music plays at 40% of normal while ducked (lower = quieter music)
        self.duck_fade_seconds = 0.4    # time to go fully down or back up
        self.duck_level = 1.0           # current multiplier, eased towards 1.0 or duck_factor
        self._duck_time = time.monotonic()

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

            print("Audio mixer initialized:", pygame.mixer.get_init())

            self.initialized = True
            self.apply_volume()

        except pygame.error as exc:
            print(f"Audio initialization failed: {exc}")

    def apply_volume(self):
        """Apply master volume and individual track multiplier."""

        if not self.initialized:
            return

        if self.current_track == "defeat":
            track_volume = self.defeat_volume

        elif self.current_track == "victory":
            track_volume = self.victory_volume

        elif self.current_track == "game":
            track_volume = self.game_volume

        else:
            track_volume = 1.0

        final_volume = self.volume * track_volume * self.duck_level

        pygame.mixer.music.set_volume(
            max(0.0, min(1.0, final_volume))
        )

    def set_ducking(self, active):
        """Smoothly lower the music while `active` and restore it afterwards. Cheap enough to call every frame."""
        now = time.monotonic()
        dt = min(now - self._duck_time, 0.1)    # ignore long frame hitches
        self._duck_time = now

        goal = self.duck_factor if active else 1.0
        if self.duck_level == goal:
            return

        step = dt / self.duck_fade_seconds * (1.0 - self.duck_factor)
        if self.duck_level < goal:
            self.duck_level = min(goal, self.duck_level + step)
        else:
            self.duck_level = max(goal, self.duck_level - step)

        self.apply_volume()

    def play_music(self, situation, loop=None, fade_ms=1500):
        """Play music according to the game situation."""

        if not self.initialized or not self.enabled:
            return False

        filename = self.tracks.get(situation)

        if filename is None:
            return False

        # Avoid restarting the current track.
        if (
            self.current_track == situation
            and pygame.mixer.music.get_busy()
        ):
            return True

        path = self.music_dir / filename
        if IS_WEB and path.suffix.lower() == ".mp3":
            path = path.with_suffix(".ogg")   # browsers play .ogg reliably; tools/convert_audio.py makes these

        if not path.is_file():
            print(f"Music file not found: {path}")
            return False

        # All tracks loop automatically by default.
        if loop is None:
            loop = situation in ("menu", "game", "defeat", "victory")

        try:
            # Stop previous music.
            pygame.mixer.music.stop()

            # Load new track.
            pygame.mixer.music.load(str(path))

            # Set current situation before applying volume.
            self.current_track = situation
            self.apply_volume()

            # Victory and defeat play immediately.
            if situation in ("victory", "defeat"):
                pygame.mixer.music.play(-1 if loop else 0)

            # Menu and gameplay fade in.
            else:
                pygame.mixer.music.play(
                    -1 if loop else 0,
                    fade_ms=fade_ms
                )

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
        """Set master volume while preserving individual track multipliers."""

        self.volume = max(0.0, min(1.0, float(volume)))
        self.apply_volume()

    def toggle_music(self):
        """Toggle music on or off."""

        self.enabled = not self.enabled

        if not self.enabled:
            self.pause_music()

        elif self.initialized:
            if self.current_track is None:
                self.play_music("menu")
            else:
                self.apply_volume()
                pygame.mixer.music.unpause()

        return self.enabled

    def shutdown(self):
        """Stop playback and release the audio mixer."""

        if self.initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.initialized = False

    def decrease_volume(self):
        """Decrease master music volume by 5%."""
        self.set_volume(self.volume - 0.05)


    def increase_volume(self):
        """Increase master music volume by 5%."""
        self.set_volume(self.volume + 0.05)
