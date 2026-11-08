
"""Player instructions text for THE LAST CONVOY.

Four pages:
1. Your Mission
2. Keyboard Controls
3. How to Play
4. Survival Guide
"""

MISSION_TITLE = "1. Your Mission"
MISSION = [
    "The world has fallen to a zombie apocalypse. You lead a convoy of survivors trying to escape the horde and reach the Pacific Coast, where you can escape by ship.",
    "Your mission is to travel west, gather supplies, keep your vehicles running, protect your survivors, and stay ahead of the approaching zombie horde.",
    "You win by reaching the Pacific Coast alive.",
    "You lose if the horde catches your convoy, all survivors leave, all your vehicles are lost, or your convoy's total health reaches zero.",
]

CONTROLS_TITLE = "2. Keyboard Controls"

CONTROLS_LEFT = [
    ("TAB", "Focus next button."),
    ("SHIFT+TAB", "Focus previous button."),
    ("UP / DOWN", "Turn instructions pages, select vehicles, or move focus."),
    ("LEFT / RIGHT", "Change map destinations, flip survivors / missions pages, or move focus."),
    ("ENTER / SPACE", "Activate the focused button."),
    ("ESC", "Go back one level. On the convoy screen it opens the pause menu. Press twice on the title screen to quit."),
    ("O", "Open or close the pause menu from any screen (the same as the MENU button)."),
]

CONTROLS_RIGHT = [
    ("M", "Open the map or return to the convoy."),
    ("S", "Open the scavenge site picker."),
    ("R", "Repair vehicles using scrap."),
    ("V", "Open the vehicles screen."),
    ("P", "Open the survivors screen."),
    ("J", "Open the missions screen."),
    ("PGUP / PGDN", "Scroll the instructions (HOME / END: top / bottom). Turn the credits pages."),
]

CONTROLS_NOTE = (
    "The focused button has a yellow outline. All screens can be operated "
    "without a mouse. Press ENTER or SPACE to activate buttons. When a page is too long for the window, "
    "use PGUP / PGDN (or the mouse wheel) to read the rest."
)

HOW_TO_PLAY_TITLE = "3. How to Play"

HOW_TO_PLAY_INTRO = (
    "Lead your convoy across the highway map towards the Pacific Coast. "
    "Choose destinations carefully, manage your resources, and make decisions "
    "that keep your survivors alive."
)

HOW_TO_PLAY = [
    ("Travel", "Use LEFT / RIGHT on the map to select your destination. Press ENTER or SPACE on TRAVEL to move."),
    ("Scavenge", "Press S on the convoy screen to open the site picker. Use keys 1-9, TAB, or the arrow keys to choose a site, then press ENTER or SPACE on SCAVENGE to search it. Press ESC to cancel. At a single-site stop, S searches at once. Each search takes one day and ends with a result screen."),
    ("Resources", "Keep an eye on your fuel, food, water, and scrap. Your convoy has limited storage, and supplies are essential for survival."),
    ("Vehicles", "Press V to inspect your vehicles. Use UP / DOWN to select a vehicle. Press R on the convoy screen to repair vehicles using scrap."),
]

SURVIVAL_TITLE = "4. Survival Guide"

SURVIVAL_INTRO = (
    "Reaching the coast is not just about travelling west. "
    "You must manage your people, vehicles, supplies, and the dangers along the way."
)

SURVIVAL_GUIDE = [
    ("The Horde", "Time passes as you travel and scavenge. Keep track of the horde's distance and danger warnings. Think carefully before taking risky routes."),
    ("Survivors", "Press P to inspect your survivors. Keep your people alive and pay attention to their needs."),
    ("Missions", "Press J to view your missions. Check your objectives and track your progress."),
    ("Locations", "Different cities offer different scavenging sites. Decide which locations are worth visiting and which routes best suit your situation."),
    ("Events", "After arrivals, events may present difficult choices. Press 1-4 to select an option, or use TAB / arrow keys and ENTER / SPACE. Read the result, then press ENTER, SPACE or ESC to continue."),
    ("Pause Menu", "Press O or click MENU on any screen. The menu has SETTINGS (accessibility options and text size), INSTRUCTIONS, DIFFICULTY, MUTE MUSIC, RESTART GAME, TITLE SCREEN and QUIT GAME. RESTART GAME, TITLE SCREEN, QUIT GAME and ABANDON VEHICLE need a second press to confirm. BACK or ESC returns you to where you were. CREDITS is on the title screen."),
]

SURVIVAL_CONTINUED_TITLE = "5. Final Advice"

SURVIVAL_OUTRO = [
    "The HUD, map, minimap, and event log provide information to help you make decisions. Pay attention to warnings and adapt your strategy as the situation changes.",
    "Your objective is simple: keep the convoy alive and reach the Pacific Coast before the horde catches you.",
    "When the game ends, press 1 for PLAY AGAIN or 2 for TITLE SCREEN. You can also navigate the buttons and confirm with ENTER or SPACE.",
]

PAGE_COUNT = 5