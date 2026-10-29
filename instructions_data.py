"""Player instructions text for THE LAST CONVOY (pygame-free data; ui.py draws it on the instructions screen).

Page 1 holds the mission and the controls, page 2 holds how to play. Edit the text here.
"""

MISSION_TITLE = "1. Your Mission"
MISSION = [
    "The world has fallen to a zombie apocalypse. You lead a convoy of survivors trying to escape the horde and "
    "reach the Pacific Coast, where you can escape by ship.",
    "Your mission is to travel west, gather supplies, keep your vehicles running, protect your survivors, and stay "
    "ahead of the approaching zombie horde.",
    "You win by reaching the Pacific Coast alive.",
    "You lose if the horde catches your convoy, all survivors leave, all your vehicles are lost, or your convoy's "
    "total health reaches zero.",
]

CONTROLS_TITLE = "2. Controls"
CONTROLS = [
    ("Left / Right", "Select the next destination west / east of the convoy on the map."),
    ("ENTER", "Travel to the selected destination."),
    ("M", "Switch between the highway map and convoy screen."),
    ("S", "Scavenge the chosen site at your current stop."),
    ("TAB", "Choose which site to scavenge (convoy screen)."),
    ("R", "Repair your vehicles using scrap (or restart after a win or loss)."),
    ("O", "Open the menu."),
    ("ESC", "Go back, or quit from the convoy screen."),
    ("1 - 4", "Choose an option during an event. Then click OK or press ENTER to continue."),
    ("Mouse click", "Select stops, click buttons, and interact with the vehicle screen."),
]
CONTROLS_NOTE = ("Note: the arrow keys cycle through every stop, including the side cities and the Mountain Pass. "
                 "You can also click any stop on the map.")

HOW_TO_PLAY_TITLE = "3. How to Play"
HOW_TO_PLAY_INTRO = ("Lead your convoy across the highway map towards the Pacific Coast. Choose your destinations "
                     "carefully, manage your resources, and make decisions that keep your survivors alive.")
HOW_TO_PLAY = [
    ("Travel", "Select a destination on the map, check the route, and press ENTER or click TRAVEL to move."),
    ("Scavenge", "Each city has several sites (gas station, farm, diner...). Choose one with the SITE button or TAB, "
                 "then press S or click SCAVENGE. You can search as often as you like; each search takes a day."),
    ("Manage resources", "Keep an eye on your fuel, food, water, and scrap. Your convoy has limited storage, "
                         "and supplies are essential for survival."),
    ("Maintain vehicles", "Press R or click REPAIR to restore vehicle health using scrap. Visit the VEHICLES "
                          "screen to inspect, recover, or abandon vehicles."),
    ("Watch the horde", "Time passes as you travel and scavenge. Keep track of the horde's distance and danger "
                        "warnings, and think carefully before taking risky routes."),
    ("Explore", "Different cities offer different sites. Decide which locations are worth visiting and which "
                "routes best suit your situation."),
    ("Events", "Something may happen after each arrival. Choose an option and read the result before moving on."),
]
HOW_TO_PLAY_OUTRO = [
    "The HUD, map, minimap, and event log provide information to help you make decisions. Pay attention to "
    "warnings and adapt your strategy as the situation changes.",
    "Your objective is simple: keep the convoy alive and reach the Pacific Coast before the horde catches you.",
]

PAGE_COUNT = 2
