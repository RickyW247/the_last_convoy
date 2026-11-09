
"""Credits text for THE LAST CONVOY (edit here).
Third-party licence text is taken from LICENSES.txt."""

CREDITS_TITLE = "CREDITS"


class Link(str):
    """A credits line that opens a web page when clicked (or ENTER on the keyboard): Link("text shown", "https://...").
    It is a str, so everything that handles plain lines handles a Link too; the address is its .url."""

    def __new__(cls, text, url):
        line = super().__new__(cls, text)
        line.url = url
        return line


# (heading, [lines]) blocks, drawn top to bottom.
# Keep individual lines short enough to fit the two-column layout. A line is a plain string or a Link(text, url).

CREDITS = [
    (
        "A game by",
        ["RW"]
    ),

    (
        "Design and programming",
        ["RW, Claude, GPT"]
    ),

    (
        "Art",
        ["GPT - DALL·E 3"]
    ),

    (
        "Music",
        [
            "After The Disaster Pt. 1 through 8",
            "by Ilker Yalciner (onemansymphony)",
            Link("Licence: CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
            Link("Source: OpenGameArt", "https://opengameart.org/content/after-the-disaster-pt-1-through-8"),
            "No changes were made to the original music.",
        ]
    ),

    (
        "Sound effects",
        [
            "87 Clickety Clips by OwlishMedia",
            Link("Licence: CC0 1.0 (public domain)", "https://creativecommons.org/publicdomain/zero/1.0/"),
            Link("Source: OpenGameArt", "https://opengameart.org/content/87-clickety-clips"),

            "Keyboard Soundpack #1 by unicaegames",
            Link("Licence: CC0 1.0 (public domain)", "https://creativecommons.org/publicdomain/zero/1.0/"),
            Link("Source: OpenGameArt", "https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes"),

            "Parisian Ring Road, Cockpit by Joseph SARDIN",
            Link("Licence: CC0 1.0 (public domain)", "https://creativecommons.org/publicdomain/zero/1.0/"),
            Link("Source: BigSoundBank", "https://bigsoundbank.com/parisian-ring-road-cockpit-s1079.html"),

            "No changes were made to any of the original sound effects.",
        ]
    ),

    (
        "Font",
        [
            "Press Start 2P by CodeMan38",
            "Copyright 2012 The Press Start 2P",
            "Project Authors",
            Link("Licence: SIL OFL 1.1", "https://openfontlicense.org/"),
            Link("Source: Google Fonts", "https://fonts.google.com/specimen/Press+Start+2P"),
            "No changes were made to the original font.",
        ]
    ),

    (
        "Special thanks",
        ["Earn to Die and Organ Trail"]
    ),

    (
        "Licence notice",
        [
            "Each third-party asset remains subject to its own licence.",
            "No ownership of third-party music, sound effects or fonts is claimed.",
            "See LICENSES.txt for the full text.",
        ]
    ),
]
