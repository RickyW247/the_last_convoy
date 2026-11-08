"""A silent stand-in for MusicManager / SoundManager, for tests and headless runs: `Game(music=NullAudio(),
sound=NullAudio())` needs no display, no sound device and no settings.json. Every method call does nothing."""


class NullAudio:
    """Accepts any method call (play_music, pause_music, set_loop, play_click, ...) and ignores it."""

    volume = 0.0
    muted = False

    def __init__(self, *args, **kwargs):
        self.calls = []   # (method name, args), so a test can check what the game asked for

    def __getattr__(self, name):
        if name.startswith("__"):   # keep copy / pickle / repr protocols working
            raise AttributeError(name)

        def method(*args, **kwargs):
            self.calls.append((name, args))

        return method
