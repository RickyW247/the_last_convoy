
"""Sound effect management for THE LAST CONVOY."""

import random
from pathlib import Path

import pygame

from config import TYPING_SOUND_INTERVAL_MS
from platform_web import IS_WEB


# The sound-effect folder next to this file, so the audio works wherever the game is launched from.
_DEFAULT_SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sound_effects"


# ---------------------------------------------------------------------------------------------------------------
# WHICH CLICK SOUND PLAYS FOR WHICH BUTTON  (edit this list)
#
# One entry per sound file in assets/sound_effects: the file name, then the labels of the buttons that play it.
# Labels are the button texts, in capitals; a leading number ("1. PLAY AGAIN") is ignored, so write "PLAY AGAIN".
# A button that is in no list plays DEFAULT_CLICK. A label may only be listed once (the last entry wins).
# ---------------------------------------------------------------------------------------------------------------
BUTTON_CLICK_SOUNDS = {
    "click5.wav": [
        "SCAVENGE", "REPAIR", "TRAVEL", "MISSIONS", "SURVIVORS", "VEHICLES", "HISTORY",
    ],
    "click9.wav": [
        "PLAY", "LOAD GAME", "CONTINUE", "START GAME", "PLAY AGAIN", "SETTINGS", 
        "INSTRUCTIONS", "ACHIEVEMENTS", "SAVE / LOAD", "DIFFICULTY", "MUTE MUSIC", 
        "UNMUTE MUSIC", "RESTART GAME", "TITLE SCREEN", "QUIT GAME", "MENU", "CREDITS",
    ],
    "click11.wav": [
        "PREVIOUS", "NEXT", "PREVIOUS PAGE", "NEXT PAGE", "OPEN", "COMPLETED", 
        "NEWER", "OLDER",
    ],
    "click14.wav": [
        "RECOVER VEHICLE", "ABANDON VEHICLE", "CONFIRM ABANDON", 
        "UPGRADE VEHICLE", "INSTALL UPGRADE", "UNINSTALL UPGRADE",
        "ABANDON", "ACCEPT", "EVENT CHOICE", "MAP STOP", "<", ">", "-", "+",
    ],
    "click15.wav": [
        "YES", "OK", "BACK", "NO", "CANCEL",
        "SAVE", "LOAD", "DELETE", "CONFIRM",
        "EASY", "NORMAL", "HARD", "SANDBOX: ON", "SANDBOX: OFF",  "ON", "OFF", "TEXT SIZE",
    ],
}


DEFAULT_CLICK = "click14.wav"   # for every button that is in no list above

# The click sound files live in this folder inside the sound-effect folder (assets/sound_effects/button_clicks).
BUTTON_CLICK_FOLDER = "button_clicks"

# The typing sounds of the lore screen: keystroke sounds, one picked at random each time letters appear. They are the
# files keypress-001.wav ... keypress-032.wav in the keyboard_clicks folder inside the sound-effect folder. (The folder
# next to assets/sound_effects named assets/sound_effect is tried too.) Missing files are skipped; none means silence.
TYPING_SOUND_FOLDER = "keyboard_clicks"
TYPING_SOUND_PATTERN = "keypress-{:03d}.wav"
TYPING_SOUND_COUNT = 32

# Looping sounds, played by set_loop() while something is going on (not clicks): name -> (file name, gain). The gain
# scales the sound-effect volume, so a background bed such as the engine stays quieter than a click at the same setting.
LOOP_SOUNDS = {
    "engine": ("traffic-parisian-ring-road-cockpit-sfxjar.mp3", 0.6),   # the convoy on the road (main loop: set_loop("engine", game.travelling()))
}
LOOP_FADE_IN_MS = 200
LOOP_FADE_OUT_MS = 300


def _normal_label(label):
    """A button label as it is looked up in BUTTON_CLICK_SOUNDS: capitals, without a leading "1. " / "2. "."""
    text = str(label).strip()
    number, dot, rest = text.partition(". ")
    if dot and number.isdigit():
        text = rest
    return text.upper()


def _label_to_file():
    """The table above turned round: button label -> sound file name."""
    lookup = {}
    for filename, labels in BUTTON_CLICK_SOUNDS.items():
        for label in labels:
            lookup[_normal_label(label)] = filename
    return lookup


class SoundManager:
    def __init__(self, sound_dir=None, volume=0.5):
        self.sound_dir = _DEFAULT_SOUND_DIR if sound_dir is None else Path(sound_dir)
        self.volume = max(0.0, min(1.0, float(volume)))
        self.enabled = True
        self.sounds = {}
        self.loops = {}                        # LOOP_SOUNDS name -> loaded Sound
        self.loop_channels = {}                # LOOP_SOUNDS name -> the channel it plays on
        self.initialized = False
        self._last_typing = -10_000           # time (ms) of the last typing sound
        self.typing_sounds = []               # the loaded keypress sounds (TYPING_SOUND_PATTERN)
        self._last_typing_index = -1          # which one played last, so the same one never plays twice in a row
        self.click_files = _label_to_file()   # button label -> sound file (BUTTON_CLICK_SOUNDS)
        self.pending_label = None             # the label of the button just pressed (see note_button)

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self.initialized = True

            # Different sounds can play simultaneously.
            pygame.mixer.set_num_channels(16)

            # Every file named in BUTTON_CLICK_SOUNDS (and the default click) is loaded once from the button_clicks
            # folder. The sound is stored under its plain file name ("click5.wav"), which is what click_sound_for() returns.
            files = set(BUTTON_CLICK_SOUNDS) | {DEFAULT_CLICK}
            self.load_sounds({filename: f"{BUTTON_CLICK_FOLDER}/{filename}" for filename in sorted(files)})
            self.load_loops()
            self.load_typing_sounds()

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

    def load_loops(self):
        """Load every file of LOOP_SOUNDS (kept apart from the click sounds). A missing file only means silence."""
        for name, (filename, _gain) in LOOP_SOUNDS.items():
            path = self.sound_dir / filename
            if IS_WEB and path.suffix.lower() == ".mp3":
                path = path.with_suffix(".ogg")   # see tools/convert_audio.py
            try:
                self.loops[name] = pygame.mixer.Sound(str(path))
            except (pygame.error, FileNotFoundError, OSError) as exc:
                print(f"Could not load looping sound {path}: {exc}")

    def set_loop(self, name, active):
        """Keep a looping sound (LOOP_SOUNDS) playing while `active` and fade it out when not. Cheap enough to call every
        frame with the current state; it follows the sound-effect volume and the enabled switch."""
        sound = self.loops.get(name)
        if not self.initialized or sound is None:
            return
        channel = self.loop_channels.get(name)
        playing = channel is not None and channel.get_busy()
        if not (active and self.enabled):
            if playing:
                channel.fadeout(LOOP_FADE_OUT_MS)
            return
        sound.set_volume(self.volume * LOOP_SOUNDS[name][1])
        if not playing:
            self.loop_channels[name] = sound.play(loops=-1, fade_ms=LOOP_FADE_IN_MS)

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

    def load_typing_sounds(self):
        """Load keypress-001.wav ... keypress-032.wav from the keyboard_clicks folder. Files that are missing or cannot be
        read are skipped, so a few gaps only mean less variety."""
        folders = [self.sound_dir / TYPING_SOUND_FOLDER,
                   self.sound_dir.parent / "sound_effect" / TYPING_SOUND_FOLDER]
        folder = next((f for f in folders if f.is_dir()), None)
        if folder is None:
            print(f"Typing sound folder not found: {folders[0]}")
            return
        for number in range(1, TYPING_SOUND_COUNT + 1):
            path = folder / TYPING_SOUND_PATTERN.format(number)
            try:
                self.typing_sounds.append(pygame.mixer.Sound(str(path)))
            except (pygame.error, FileNotFoundError, OSError) as exc:
                print(f"Could not load typing sound {path}: {exc}")

    def play_typing(self):
        """One keystroke of the lore screen's typing effect: a random keypress sound (never the one that just played),
        at most one per TYPING_SOUND_INTERVAL_MS."""
        if not self.initialized or not self.enabled or not self.typing_sounds:
            return False
        now = pygame.time.get_ticks()
        if now - self._last_typing < TYPING_SOUND_INTERVAL_MS:
            return False
        self._last_typing = now
        choices = [i for i in range(len(self.typing_sounds)) if i != self._last_typing_index] or [0]
        index = random.choice(choices)
        self._last_typing_index = index
        sound = self.typing_sounds[index]
        sound.set_volume(self.volume)
        return sound.play() is not None

    def play_random(self, names):
        """Randomly play one of the available sound effects."""
        available = [name for name in names if name in self.sounds]

        if not available:
            return False

        return self.play_sound(random.choice(available))

    def note_button(self, label):
        """Remember which button is being pressed; the next play_button_click() uses its sound. (buttons.py calls
        this from every button's action, so the click that main.py / keys.py play afterwards fits the button.)"""
        self.pending_label = label

    def click_sound_for(self, label=None):
        """The sound name for a button label (its entry in BUTTON_CLICK_SOUNDS, else DEFAULT_CLICK)."""
        if label is None:
            return DEFAULT_CLICK
        return self.click_files.get(_normal_label(label), DEFAULT_CLICK)

    def play_button_click(self, label=None):
        """Play the click sound of a button: `label` if given, else the button noted by note_button (used once), else
        the default click."""
        if label is None:
            label = self.pending_label
        self.pending_label = None
        return self.play_sound(self.click_sound_for(label))

    def set_volume(self, volume):
        """Set sound-effect volume between 0.0 and 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))

        for sound in self.sounds.values():
            sound.set_volume(self.volume)
        for sound in self.typing_sounds:
            sound.set_volume(self.volume)
        for name, sound in self.loops.items():
            sound.set_volume(self.volume * LOOP_SOUNDS[name][1])

    def decrease_volume(self):
        """Decrease the sound-effect volume by 5%."""
        self.set_volume(self.volume - 0.05)

    def increase_volume(self):
        """Increase the sound-effect volume by 5%."""
        self.set_volume(self.volume + 0.05)

    def set_enabled(self, enabled):
        """Switch sound effects on or off (off also cuts any that are playing)."""
        self.enabled = bool(enabled)
        if not self.enabled:
            self.stop_all()
        return self.enabled

    def toggle_sound(self):
        """Enable or disable sound effects."""
        return self.set_enabled(not self.enabled)

    def stop_all(self):
        """Stop currently playing sound effects."""
        if self.initialized:
            pygame.mixer.stop()

    def shutdown(self):
        """Stop sound effects and clear loaded sounds."""
        if self.initialized:
            self.stop_all()
            self.sounds.clear()
            self.typing_sounds.clear()
            self.loops.clear()
            self.loop_channels.clear()
