
"""Sound effect management for THE LAST CONVOY."""

import random
from pathlib import Path

import pygame


class SoundManager:
    def __init__(self, sound_dir="assets/sound_effects", volume=0.5):
        self.sound_dir = Path(sound_dir)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.enabled = True
        self.sounds = {}
        self.initialized = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self.initialized = True

            # Different sounds can play simultaneously.
            pygame.mixer.set_num_channels(16)

            # Load your sound effects here.
            self.load_sounds({
                "button_click_1": "click1.wav",
                "button_click_2": "click2.wav",
                "button_click_3": "click3.wav",
            })

        except pygame.error as exc:
            print(f"Sound initialization failed: {exc}")

    def load_sound(self, name, filename):
        """Load one sound effect."""
        if not self.initialized:
            return False

        path = self.sound_dir / filename

        if not path.is_file():
            print(f"Sound file not found: {path}")
            return False

        try:
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(self.volume)
            self.sounds[name] = sound
            return True

        except pygame.error as exc:
            print(f"Could not load sound {filename}: {exc}")
            return False

    def load_sounds(self, sound_files):
        """Load multiple sounds from a name-to-filename dictionary."""
        for name, filename in sound_files.items():
            self.load_sound(name, filename)

    def play_sound(self, name):
        """Play a loaded sound effect."""
        if not self.initialized or not self.enabled:
            return False

        sound = self.sounds.get(name)
        if sound is None:
            return False

        sound.set_volume(self.volume)
        return sound.play() is not None

    def play_random(self, names):
        """Randomly play one of the available sound effects."""
        available = [name for name in names if name in self.sounds]

        if not available:
            return False

        return self.play_sound(random.choice(available))

    def play_button_click(self):
        """Play a random button click sound."""
        return self.play_random([
            "button_click_1",
            "button_click_2",
            "button_click_3",
        ])

    def set_volume(self, volume):
        """Set sound-effect volume between 0.0 and 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))

        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def toggle_sound(self):
        """Enable or disable sound effects."""
        self.enabled = not self.enabled
        return self.enabled

    def stop_all(self):
        """Stop currently playing sound effects."""
        if self.initialized:
            pygame.mixer.stop()

    def shutdown(self):
        """Stop sound effects and clear loaded sounds."""
        if self.initialized:
            self.stop_all()
            self.sounds.clear()
