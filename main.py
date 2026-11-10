"""THE LAST CONVOY — Prototype README
Version: 2.19

Development / versioning convention:
- For every update, increment the version number (e.g. 2.0 -> 2.1; the numbering went from 1.99 straight to 2.0).
- Keep this README-style summary at the top of main.py updated to reflect current capabilities.
- Add a brief version-history entry for the update; avoid changing gameplay unless requested.
- Keep this README concise: when it grows long, summarize capabilities and older version history
  a bit, while retaining the most important information. Do this on every update without being asked.

Current capabilities:
- Pygame survival prototype: drive a convoy along a branching highway map to the Pacific Coast. Flow: title screen
  (big PLAY and LOAD GAME, a small MENU button in the top right corner), lore screen (CONTINUE), background screen (START GAME). Reaching the coast starts the Pacific evacuation (below); escaping aboard the ship wins. The ending screen (win or
  loss) shows the reason, days survived, survivors left, stops visited, vehicles lost, distance and difficulty.
- Resizable window (min 640 x 480): every screen and popup is laid out in real window pixels (layout/ package); fonts
  and rows scale with the window and the text-size setting (textscale.py). Mouse positions are raw window coordinates.
- Map screen: info panel under the map, or in a column beside it whenever that shows a bigger map (a wide, low
  window), whatever the text size (layout/map.py). Map: one of five predefined layouts per run (map_data.LAYOUTS). All share Start, City 1-4 and the Pacific Coast on
  the main route; side cities 5-8, Riverside, Lakeside, the Mountain Pass and the bypass roads differ (Classic: Pass bypasses City 3).
  The Military Base (stop 11) is a dead end in every layout, holds the only military sites (Military Installation, Barracks, Motor Pool) and
  is the only place military vehicles can be recovered (Game.can_recover_type_here, convoy.is_military_vehicle). Every stop
  has three sites (29 site types, map_data.py). map_data._validate_geometry rejects layouts with crossing / touching roads. Stops lie on a 0-560 km line; travel time depends on road distance
  and the slowest vehicle; fuel use depends on road distance and the combined fuel_consumption of every vehicle
  (Game.trip_fuel, FUEL_USE_DIVISOR in config.py), and only travel uses fuel.
- Scenery: the convoy scene shows the highway background until the convoy is past the Mountain Pass, then the desert one
  (assets/backgrounds/convoy_background_desert.png). Every stop whose axis km lies beyond the pass is desert (map_data.scenery_for,
  so it works on all five layouts); Game.scenery() follows the stop, and on a journey switches to the destination's at half way.
  ui/convoy.py BACKGROUNDS lists each scenery's file, art block, loop mode and road height.
- Pacific evacuation (design doc 2.3 / 19.2; game/evacuation.py, config.EVACUATION_ENABLED / EVAC_BASE_BERTHS): arriving at the coast no longer
  wins at once. Three scripted events ("trigger": "evacuation" in event_data.py, opened by id in order) follow: The Port Gate, The Harbour
  Master's Quota, Loading Under Fire. The ship has EVAC_BASE_BERTHS (16) places; choices can add berths (new "berths" effect, shown as "+N ship berths"
  and "Ship berths +N" in the result), cost supplies / vehicles / health, and move the horde gap as usual (no extra timer). Then the convoy boards:
  a horde at gap 0 attacks once, min(survivors, berths) survivors escape (Game.survivors becomes that number; Game.survivors_left_behind
  is the rest) and the ending says how many were left on the dock. Nobody aboard = the run is lost. EVACUATION_ENABLED = False restores the old
  instant win (handy for tests).
- Horde: gap = convoy position - horde position (westward widens, eastward narrows, the horde advances daily).
  Danger levels Distant / Approaching / Close / Overrun show on the HUD (in words next to HORDE), event log and
  background; at gap 0 the horde attacks daily (kills survivors, wrecks vehicles); routes that would let it catch up show red / orange, on the map and minimap.
- HUD: title / location / day on the left, then a 3 x 2 grid of cells, each a label over a bar: FUEL, CONVOY HP, HORDE
  (gap in km + danger state) and, below, CARGO (two cells wide: ONE bar shared by FOOD, WATER and SCRAP against the cargo
  capacity, with their numbers) and SURVIVORS (seats). The label size is chosen for the widest text, so it does not
  change while the numbers change. The title follows the text-size setting like every heading; the location and day
  keep their size (the location wraps to a second line before it shrinks, the title gives way first).
- Vehicles: 59 types (vehicle_data.VEHICLE_SPECS; start: pickup truck, passenger van, school bus); recover them at stops with a Truck Stop,
  Repair Depot or Military Installation, or abandon them. For an owned vehicle the vehicles screen's RECOVER VEHICLE
  button is UPGRADE VEHICLE: it opens the upgrade screen (rows: Up / Down or click; INSTALL UPGRADE; BACK / ESC), where
  scrap buys the upgrades that fit the vehicle (upgrade_data.py: armour, defense, engine, fuel, cargo, passenger, trailer; every vehicle can
  take the general ones, the bikes only armour, bumper, engine, injectors and the extra tank), the table pages (PREVIOUS / NEXT, Left / Right, PgUp / PgDn, mouse wheel) when its rows do not fit,
  again only at stops with a Truck Stop, Repair Depot or Military Installation. An upgrade changes the vehicle's stats
  at once (the vehicle table, the card and the convoy totals show them), stays installed, and is kept if the vehicle
  is abandoned and recovered later. Trailers (Utility, Flatbed, Travel; the Semi-Truck's own Cargo Trailer): a vehicle tows ONE, so the installed one must be uninstalled
  first; every vehicle but the three bikes can tow the three; they are drawn behind the vehicle with their own dust (ui/vehicle_rendering.get_rig_sprite; size factors:
  upgrade_data.TRAILER_SCENE_SIZE), the Semi's replaces its sprite (semi_truck_trailer.png). Convoy health is the sum of vehicle health; ambushes hit
  every vehicle; REPAIR restores 25% of max health; special abilities (design doc section 6; vehicle_data.VEHICLE_ABILITIES / ABILITY_INFO, numbers in config.py): Ambulance Medical Care, Humvee Reinforced Protection, Tow Truck Recovery Support, shown on the vehicle card; each defense point cuts ambush damage by 1% (cap 60%). Vehicle
  sprites are drawn at whole-number scales (ui/common.whole_scale) so the pixel art keeps even pixels.
- SCAVENGE: pick a site in the popup, confirm with SCAVENGE (single-site stops search at once); a search takes a day
  and ends in a result popup; survivors can be found, and sometimes an abandoned vehicle that fits the site (the player chooses whether to take it). Cargo capacity limits food, water and scrap combined; fuel and
  passengers have their own capacities.
- Backgrounds (design doc section 21; numbers in background_data.py, rules in game/background_rules.py): Military: military vehicles cost
  1 scrap less to recover and to upgrade (Game.upgrade_price, shown on the upgrade screen) and heal 40% more per REPAIR; Police:
  "emergency" events cost half the horde-gap time; Government: a scavenge search may yield extra supplies; Corporate: REPAIR and
  recovery cost 1 scrap less; Civilian: every other REPAIR gives 1 scrap back; Criminal: stashes at Truck Stops / Depots / Garages /
  Warehouses / Hardware Stores, three Criminal-only events, but fewer people join (scavenging and event rescues) and "settlement"
  events are sometimes skipped. Event data: "emergency" / "settlement" flags and a "background" requirement.
- Survival: daily use is 1 food per 5 survivors and 1 water per 4 (rounded up). Each vehicle needs an adult driver; with
  more vehicles than adults a forced "ABANDON A VEHICLE" popup pauses the day / journey and the player ticks every
  vehicle to give up in that one popup (the least valuable ones start ticked and are marked "*" / SUGGESTED; ABANDON works
  once exactly Game.abandon_need() are ticked; Game.interactive_abandon, set by main.setup(); headless play drops them at
  once). Survivor conditions (conditions.py): a day without enough food / water moves survivors fed -> hungry -> starving
  (hydrated -> thirsty -> dehydrated) and starving / dehydrated ones leave, several per day; enough supplies restore
  everyone at once. Horde attacks and events ("injury" effect) injure survivors: injured -> critical -> dies, slow recovery,
  faster with an ambulance.
- Travel events: each day on the road may bring a weighted random event (event_data.py) offers 2-3 choices with declarative
  effects on resources, survivors, vehicle health or the horde gap; a result screen lists every change. A resource never
  goes below 0 and a loss takes only that resource. A choice marked "payment": True (a repair, rescue or trade the player
  pays for) is greyed out when the convoy cannot pay ("[need 3 scrap, have 1]"; if none is affordable all stay open); any
  other choice is a penalty ("[lose up to 12 water]"): always pickable, it takes what is available
  (effect_handler.is_payment / resource_costs / shortfalls / affordable_flags).
- Journeys are paced (config.TRAVEL_*_DELAY): after TRAVEL the convoy screen shows a TRAVELLING... banner (destination, day
  x of y); one day passes per second, an event's result is followed by a longer pause, and only the MENU button (O / ESC)
  works until the convoy arrives; holding SPACE speeds it up. A looping engine sound plays while on the road
  (sound_manager.LOOP_SOUNDS, assets/sound_effects/engine.wav). Game.animate_travel is on only in the real game (setup()).
- Special survivor events (special_event_data.py): eleven very rare events (weight 0.2), one per special series (The Walking Dead, its Telltale game, The Last of Us,
  Resident Evil, Shaun of the Dead, Zombieland, Dead Rising, World War Z, Dying Light, Warm Bodies, I Am Legend), built on its plot; a choice can bring special
  survivors aboard (fixed name, gender and age; never two copies at once).
- Event history: the whole RECENT EVENTS bar is a button with a "HISTORY [H]" tag (also H on any run screen) opening
  the EVENT HISTORY screen: every message of the run, newest first, under "Day 8 - <place>" headers (history_log.py;
  Game.history), scrolled with the wheel, PgUp / PgDn / Home / End, Up / Down or NEWER / OLDER; BACK / H / ESC return.
- Screens: convoy, vehicle table (paged), map, survivors and missions (paged), pause menu (SETTINGS, INSTRUCTIONS,
  SAVE / LOAD, MUTE MUSIC, then CREDITS (only in the menu opened from the title screen) or RESTART GAME and TITLE SCREEN
  (during a run), QUIT GAME), difficulty (Easy / Normal / Hard; opened from the settings), settings
  (music volume and sound-effect volume - / +, TEXT SIZE, FULLSCREEN and DIFFICULTY rows, HIGH CONTRAST and COLOUR-BLIND PALETTE; the
  accessibility options, fullscreen, text size, both volumes and music mute are saved in settings.json and restored at start-up), credits (licence / source lines are links; paged, nothing is dropped), instructions.
  RESTART GAME, TITLE SCREEN and QUIT GAME ask "Are you sure? Progress will not be saved." in a popup first;
  a confirmed RESTART GAME starts a fresh run on the lore screen (Game.restart_to_lore); CONTINUE then START GAME begin it.
  SANDBOX: ON / OFF (difficulty screen) gives infinite fuel, food, water and scrap, everything else stays normal.
  MUTE MUSIC / UNMUTE MUSIC mutes the music; the choice is saved and restored at start-up.
- Save / load (savegame.py): 3 slots (slot1..3.json beside settings.json: temporary folder for now, settings_store.USE_TEMP_FOLDER; written atomically, checked before loading);
  SAVE / LOAD page in the pause menu and LOAD GAME on the title screen; overwriting, loading over a run and DELETE ask CONFIRM.
- Achievements (design doc 20.5; achievement_data.py, achievements.py): ten achievements (Coast to Coast, Convoy Collector, Heavy Machinery,
  Broadcast from the End, Sweet Survival, One Last Laugh, Presidential Protection, Armoured Convoy, Nothing Left Behind, The Long Road Again)
  are completed through hooks in the rules (arrival, victory, resolved events, recovering vehicles, START GAME) and saved in achievements.json beside
  settings.json, so they survive RESTART GAME, TITLE SCREEN, loading and quitting (like settings.json, the folder is temporary while
  settings_store.USE_TEMP_FOLDER is True). Nothing is earned in SANDBOX MODE (config.ACHIEVEMENTS_IN_SANDBOX). Unlocks are logged
  ("Achievement unlocked: ..."). REWARDS ARE PLACEHOLDERS (achievements.apply_reward does nothing); so are the six achievements whose event / vehicle
  does not exist yet (COMING SOON, never awarded). ACHIEVEMENTS in the pause menu (also from the
  title screen's menu) opens the paged achievements screen: a card per achievement with status / progress, description, reward text and the
  date earned; secret ones show "???" until completed (layout/achievements.py, ui/achievements_screen.py; BACK / ESC return to the menu).
  RESET (bottom left) opens a YES / NO popup; YES erases all achievements and counters (Game.reset_achievements).
- Accessibility: high contrast and an Okabe-Ito colour-blind palette (theme.set_accessibility), with extra words / a
  selection ring where colour alone carried meaning.
- Browser build (pygbag / pygame-ce, GitHub Pages): main() is async and yields once per frame; platform_web.py holds IS_WEB and browser
  localStorage (settings and saves persist there); no QUIT GAME on the web; .mp3 music / sounds are played as .ogg (tools/convert_audio.py).
  Touch (touch.py): a tap is a click (held back until the finger lifts); a swipe becomes mouse-wheel scrolling / page turning, so it never
  presses a button; a long press while travelling fast-forwards (like SPACE). HOSTING.md explains the .github/workflows/pages.yml deployment.
  Closing the tab: the browser's "Leave site?" dialog freezes the page and made the music crackle, so the audio is suspended while it is
  open and resumed if the player stays (platform_web.install_leave_guard, called by setup()).
- Pixel-art PNG assets in assets/; hand cursor over every enabled button, map stop and vehicle-table row; headless tests (test_convoy.py, test_layouts.py).
- Pixel-art UI: panels, buttons, bars and focus rings are square with stepped corners, a dark outline and a bevel
  (widgets.draw_panel / draw_frame, PIX = 2 px); text is drawn without smoothing (theme.PIXEL_TEXT) and uses
  assets/fonts/pixel.ttf when that file exists. The background zombies stand on the looping background and scroll with it.
- The game/ package (rules) and config.py (balance constants) import no pygame code. Game(music=None, sound=None) builds the real
  audio managers (and reads settings.json) only when none are passed in; tests use Game(music=NullAudio(), sound=NullAudio()).

Controls (fully playable by keyboard; the mouse works everywhere):
- Tab / Shift+Tab (and the arrows where they have no other job) move the yellow focus outline; ENTER / SPACE press
  the focused button; ESC goes back one level; O or the MENU button opens the pause menu (it also opens by itself when the window loses focus or is minimized, headed PAUSED during a run); F11 toggles fullscreen (desktop-size, no video-mode change);
  ABANDON needs a second press; RESTART GAME, TITLE SCREEN and QUIT GAME open the confirmation popup (Y = yes, N / ESC =
  no; the focus starts on NO). Credits: Tab / ENTER open the links, PgUp / PgDn or the PREVIOUS / NEXT buttons turn the pages.
- Convoy: S scavenge, R repair, M map, V vehicles, P survivors, J missions, H event history; Up / Down move the focus above / below,
  Left / Right to the previous / next button. Map: Left / Right pick a destination.
  Vehicles and the upgrade screen: Up / Down pick a row (rows click when picked by mouse or keys); Left / Right, PgUp / PgDn (Home / End: first / last) or the mouse wheel flip the table's pages. Lists: Left / Right flip pages. Instructions: Up / Down turn pages (Left / Right move the
  focus), PgUp / PgDn / Home / End scroll. Credits: PgUp / PgDn / Home / End turn pages. The mouse wheel does both.
- Events: 1-4, or Tab / arrows + ENTER; the result is dismissed with ENTER / SPACE / ESC. SCAVENGE popup: 1-9 / ENTER
  pick a site, ENTER again searches. ABANDON A VEHICLE popup: 1-9 tick / untick, Tab / arrows + SPACE too, ENTER on ABANDON confirms (no cancel). Ending: Tab / Left / Right + ENTER; ESC goes to the title screen.

Project files:
- main.py: window (setup()), mouse handling and main loop (run this file; importing it opens nothing).   keys.py: keyboard play.   config.py: balance
  constants, difficulties.
- game/: the gameplay rules (`from game import Game, Vehicle, recovery_cost`); Game is assembled from mixins: state.py
  (reset, log, history), navigation.py (screens, menus, popups), audio.py, horde.py, survival.py (difficulty, days, defeat),
  convoy.py (totals, cargo, drivers, vehicle actions), travel.py, evacuation.py (the final evacuation), scavenge.py (sites, yields); vehicle.py (Vehicle), null_audio.py (silent audio for tests).
- music_manager.py / sound_manager.py: background music and button-click sound effects (assets/music, assets/sound_effects).
  Which click plays for which button is the editable list sound_manager.BUTTON_CLICK_SOUNDS (file -> button labels).
- theme.py: colours and fonts.   textscale.py: text-size setting and scale factor k.   settings_store.py: settings.json.   achievement_data.py / achievements.py: achievements (achievements.json; screen: layout/achievements.py, ui/achievements_screen.py).
  widgets.py: Button, text fitting / wrapping helpers.
- layout/: window-pixel geometry of every screen and popup (import from `layout`; layout/hud.py is the HUD grid).
  ui/: drawing only (import from `ui`; ui/hud.py draws the HUD, ui/credits.py, ui/confirm.py, ui/abandon.py and ui/travel_banner.py the
  credits screen, the confirmation popup and the "which vehicle to abandon?" popup).
  buttons.py: builds each screen's buttons.   paging.py: survivors / missions lists, clamp_pages, upgrade_page (the upgrade table's page).
  credits_items.py: where the credits lines (and links) go, page by page (the open page is kept there).
- map_data.py: stops, roads, pathfinding.   vehicle_data.py: specs and recovery costs.   upgrade_data.py: the upgrade catalogue (costs, effects, looks).   pixel_art.py: pixelate / whole_scale / cover_scale.   vehicle_rendering.py: loads the
  vehicle sprites (it stays outside ui/: it loads assets, it does not draw).   Map and minimap drawing is
  ui/map_system.py.
- event_data.py / event_manager.py / effect_handler.py: events, selection and effects.   game/background_rules.py: player background rules.   history_log.py: the event history
  (grouping, scroll clamp; layout/history.py and ui/history.py are its screen).   instructions_data.py,
  story_data.py, credits_data.py: text content (edit there).
- platform_web.py: IS_WEB, localStorage storage, viewport_size, fullscreen, open_url and the leave-site audio guard for the browser build.
- app/window.py: window creation helpers, DPI awareness, fullscreen and windowed-mode management.
- app/popups.py: popup selection, popup button construction and popup drawing coordination.
- app/rendering.py: screen drawing coordination; actual drawing remains in ui/.
- savegame.py: save slots (JSON files, validation, load).   test_savegame.py: save / load tests.   test_achievements.py: achievement tests.
- test_convoy.py: game tests.   test_backgrounds.py: background ability tests.   test_effects.py / test_history.py: event-effect and history logic tests.   test_event_data.py:
  EVENTS are valid (effect_handler.check_events).   test_missions.py: every destination mission is reachable on every map layout.
  test_headless_game.py: game/ runs without pygame, a display or settings.json.   test_layouts.py: headless layout tests (no overlaps at 640x480 ... 2560x1440).
  background_icons.py: loads the background icons (assets/icons).   assets/: vehicles, backgrounds, zombies, icons PNGs.

Setup: python -m pip install pygame | Run: python main.py | Test: python test_convoy.py

Version history (newest first; older entries are grouped):
- 2.19: Windows desktop build: DPI awareness is on again (window.enable_dpi_awareness, window.DPI_AWARE): the game draws in real pixels instead of
        Windows enlarging (and blurring) the window by 125 / 150 %, and the default window is opened at WIDTH x HEIGHT times the screen's scale factor
        (this is what made the window tiny when it was tried before). Text and art are sharp and no longer look oversized. Also the scene's vehicles are shrunk from the
        full PNG on desktop at 2x or more (ui/convoy._sharp_vehicle). The lore screen's story uses the 24 px font and more line spacing on desktop when it fits (ui/screens.draw_lore_screen) and the background screen's text gets more line and section spacing (ui/backgrounds). Browser build unchanged. Gameplay unchanged.
- 2.18: bigger text where there is room (the pixel font only has 8 px and 16 px sizes, and a lot of text sat at 8 px even in a big window):
        the vehicle name labels in the convoy scene (ui/convoy._label_font), the RECENT EVENTS log (long messages wrap instead of
        forcing 8 px: _wrapped_events), the right-hand CURRENT STOP column (stop name on two lines, descriptions and key hints
        at 16 px when the column fits: _info_flow) and the vehicles screen (table, headings, help and status lines, card details:
        _fit_best / _text_fonts; a long vehicle name is drawn in 8 px instead of deciding the whole table's size).
        Windows and layouts too small for the bigger text keep the 8 px text. Gameplay unchanged.
- 2.17: browser build: closing the tab no longer makes the music crackle. Chrome's "Leave site?" dialog blocks the page's main thread, which also
        mixes the audio; platform_web.install_leave_guard (called once in setup(), web only) suspends the audio context on beforeunload and
        resumes it if the player stays. Window caption check now says v2.17. Gameplay unchanged.
- 2.16: browser build fills the page: the drawing surface follows the viewport (window.fit_web_viewport, platform_web.viewport_size,
        stretch_canvas_to_page; whole-number zoom, nearest-neighbour), browser fullscreen on F11 / FULLSCREEN (platform_web.set_browser_fullscreen);
        convoy vehicles drawn 1.5x bigger (ui/convoy.VEHICLE_SCENE_H 80 -> 120). Desktop unchanged.
- 2.15: browser build: async main loop, platform_web.py, localStorage for settings / saves / achievements, touch.py (tap, swipe-to-scroll,
        long press = fast-forward), web branch in window.set_window_mode, no QUIT GAME on the web, .ogg audio fallback, GitHub Pages workflow.
- 2.14: background zombies no longer vanish before the scene's right edge on a widened scene: every repeat of the looping strip
        that fits the scene gets its zombies (ui/convoy.draw_background_zombies).
- 2.13: vehicles can be scavenged: a search may turn up an abandoned vehicle that fits the site (map_data.SITE_VEHICLES: police cars at the Police
        Station, ambulances at the Hospital, military vehicles only at the Military Base; none on the Open Highway or Mountain Pass); the player is
        asked (YES / NO popup) whether to take it; free, no day, needs a spare adult, joins damaged (config.VEHICLE_FIND_HEALTH), counts as recovered
        (scavenge._find_vehicle / take_found_vehicle; config.VEHICLE_SCAVENGE_ENABLED, VEHICLE_FIND_CHANCE_SCALE; Game.vehicle_scavenging set by setup()).
- 2.11-2.12: RESET button (with confirmation) on the achievements screen; eleven rare special survivor events (special_event_data.py,
        "special_survivor" effect, "special_absent" requirement, SurvivorManager.convert_to_special).
- 2.10: map overhaul: 14 stops per layout (new Military Base id 11, Riverside 12, Lakeside 13), 11 new sites (scrapyard replaces the military site
        in City 3 / 7), all five layouts redrawn so no roads cross or touch (map_data._validate_geometry, checked at import); the Military Base
        is always a dead end; military vehicles are recoverable only there (convoy.is_military_vehicle; sandbox mode exempt).
- 2.9: three trailers as upgrades (Utility 7 scrap, Flatbed 9, Travel 8; upgrade_data.py: "group": "trailer" = one per vehicle, Vehicle.blocking_upgrade,
        "Uninstall the X first" message in Game.upgrade_problem; "trailer" sprite drawn behind the vehicle: vehicle_rendering.get_rig_sprite /
        get_rig_source, trailer wheel dust TRAILER_DUST, size TRAILER_SCENE_SIZE; the upgrade card previews them). ALL_TYPES is now every
        vehicle (RACK_TYPES / SEAT_TYPES / TRAILER_TYPES; bikes take no racks, seats or trailers). The upgrade table pages when its rows do not
        fit (layout/upgrade.py per_page / pages / pager, paging.upgrade_page, PREVIOUS / NEXT, Left / Right, PgUp / PgDn, wheel; clicks and the
        hand cursor use the page). Assets: utility_trailer.png, flatbed_trailer.png, travel_trailer.png.
- 2.8: SANDBOX MODE: vehicles can be recovered / upgraded at any stop (Game.can_recover_here). Bonus vehicles are hidden on the vehicles
        screen until unlocked: achievement_data "unlocks_vehicle" (Convoy Collector -> Limousine, Nothing Left Behind -> Crane Truck; the
        other four are placeholders), AchievementTracker.unlocked_vehicles, Game.unlocked_bonus_vehicles / listed_vehicle_types; sandbox
        lists every bonus vehicle. Row hit-testing uses the real row count (vehicle_table_order).
- 2.7: Pacific evacuation finale: game/evacuation.py (EvacuationMixin: begin_evacuation / continue_evacuation / complete_evacuation, berths),
        three evacuation events in event_data.py, "berths" effect (effect_handler, ui/event_ui.py note), EventManager.start_event(id),
        Game.finish_victory(escaped, left), hooks in travel._arrive / dismiss_event_result and convoy.abandon_picked_vehicle,
        config.EVACUATION_ENABLED / EVAC_BASE_BERTHS. Tests that expected an instant win on reaching the coast must play the events
        or set EVACUATION_ENABLED = False.
- 2.4-2.6: background abilities and the Criminal trait are active (game/background_rules.py BackgroundMixin, constants in background_data.py;
        hooks in convoy / scavenge / event_manager / effect_handler; "emergency" / "settlement" event flags, Criminal events) and balanced by simulated
        runs (Civilian refunds scrap, Military upgrades cheaper: Game.upgrade_price). event_data.py lives in game/. Lore screen typing effect
        (config.LORE_TYPING_CPS; SPACE / ENTER skips; SoundManager.play_typing).
- 2.0-2.2: achievements (design doc 20.5, rewards PLACEHOLDER): achievement_data.py, achievements.py (AchievementTracker, achievements.json),
        hooks Game._achieve (travel.py, convoy.py, navigation.py), ACHIEVEMENTS pause-menu button and screen (layout/ui achievements_screen.py,
        paging, keys); achievements whose event / vehicle does not exist yet are COMING SOON placeholders. test_achievements.py.
- 2.3: background screen: the selected background's icon (assets/icons/<background>_icon.png, 512 x 512) is drawn on the right of the
        details box, the text on the left. background_icons.py loads / scales it; layout/backgrounds.py reserves the icon square and
        the text column (ICON_SHARE / ICON_MAX / ICON_MIN / TEXT_MIN): the icon shrinks, and is dropped before the text gets cramped.
        test_background_icons.py.
- 1.99: backgrounds give their own starting vehicles (background_data.starting_vehicles; stand-ins where a vehicle has no sprite yet);
        START GAME (Game.begin_game) rebuilds the run from the chosen background.
- 1.96-1.98: desert scenery beyond the Mountain Pass (map_data.scenery_for, Game.scenery, ui/convoy.py BACKGROUNDS; test_scenery.py);
        config.TRAVEL_ANIMATION_FAST_FORWARD (road animation speed while SPACE is held) and config.MAP_BG_PIXEL_ART; OVERRUN / RISKY
        labels get a dark backing; vehicles screen preview card reaches the bottom of the status text (layout/vehicles.py).
- 1.93-1.95: eight new vehicles (vehicle_data.py, upgrade_data.ALL_TYPES, vehicle_rendering._SPRITE_FILES) and a paged vehicle table
        (layout/vehicles.py per_page / pages, PREVIOUS / NEXT, Game.vehicle_page); SPACE also speeds up the road animation
        (ui/convoy.py set_animation_speed); vehicle special abilities (design doc section 6: vehicle_data.VEHICLE_ABILITIES, Game.has_ability /
        total_defense / repair_cost / recovery_price; test_abilities.py).
- 1.91: player backgrounds (design doc section 21): background screen after the lore screen (CONTINUE -> background -> START GAME), six
        cards; Game.background / select_background (kept across restarts); background_data.py, layout/backgrounds.py, ui/backgrounds.py.
- 1.83-1.90: vehicle upgrades (upgrade screen, upgrade_data.py; UPGRADE VEHICLE replaces RECOVER VEHICLE for owned vehicles), Game(music=None,
        sound=None) injected audio for tests, survivor conditions (game/conditions.py: hunger / thirst / injury counts; ambushes and
        horde attacks injure), three save slots (savegame.py; SAVE / LOAD page, LOAD GAME on the title screen, big PLAY / LOAD GAME with a
        small MENU button), "stockpile" missions (MissionManager.on_resources_changed).
- 1.82: paced journeys: TRAVELLING... banner, one day per second, a pause after every event, input locked except MENU (O / ESC), hold
        SPACE to fast-forward, engine sound loop. Game.animate_travel / update_travel / on_road; headless play and tests travel instantly.
- 1.79-1.81: the game pauses when the window loses focus or is minimized (Game.auto_pause); the road animation uses its own clock
        (ui/convoy.py animation_time / set_animation_paused); one click sound for every TEXT SIZE label; the ending screen's buttons are
        no longer numbered (1 / 2 keys gone).
- 1.72-1.78: EVENT HISTORY screen (H / RECENT EVENTS bar, history_log.py, layout/history.py, ui/history.py); unaffordable payment choices
        greyed out; HUD title and vehicle sprites follow the text-size setting; side-by-side map layout chosen by comparing map sizes
        (layout/map.py); vehicles screen: CONVOY TOTALS box, hover / click rows (keys.ROW_CLICK_LABEL), hand cursor over everything
        clickable (main.clickable_under_mouse); vehicle cards and convoy zombies use the original PNG shrunk smoothly
        (vehicle_rendering.get_vehicle_source, ui/convoy.py zombie_scale a continuous factor); the convoy scene keeps pixelated sprites.
- 1.66-1.71: app/ package (window.py, popups.py, rendering.py; behaviour unchanged); fullscreen is plain FULLSCREEN at the desktop size
        (checked, then borderless desktop-size window, then normal; saved setting applied before the first frame; leaving restores a
        clamped windowed size); the window opens at WIDTH x HEIGHT (maximize / DPI awareness tried and removed: tiny window, crash);
        wider convoy scene; settings Up / Down move between buttons.
- 1.63-1.65: ABANDON A VEHICLE multi-select popup when adults < vehicles (Game.abandon_need / abandon_marks, ui/abandon.py,
        keys.abandon_key; Game.interactive_abandon is False headless = automatic drop). Unaffordable event choices are greyed out
        ("[need 3 scrap, have 1]") and refused by EventManager.resolve_choice / can_choose.
- 1.41-1.62: journeys of several days with daily ambush / scrap rolls and events; fuel use from distance and combined fuel_consumption;
        the horde attacks daily at gap 0 (the run is lost only when no survivor is left); REPAIR only while stopped, takes a day; the map follows each
        run's layout and any stop can be selected (TRAVEL only for connected ones); keyboard focus on the convoy screen and SCAVENGE popup; RESTART GAME
        returns to the lore screen; per-button click sounds; text size / volumes / mute saved (settings_store.py); SANDBOX MODE (supplies topped up and
        never lowered, state._supply); LOW FUEL / NO FUEL on the HUD; pixel-art UI (widgets.draw_panel / draw_frame, un-smoothed text, optional
        assets/fonts/pixel.ttf); zombies on the looping background; robustness fixes.
- 1.1–1.40: core gameplay (vehicles, travel, hordes, scavenging, events); PNG and pixel art; multiple scavenging sites; title, lore, menu, settings, 
        credits and instructions screens; resizable layouts; keyboard-only controls; accessibility options; text scaling; organised layout/, ui/ and 
        game/ packages; 3×2 HUD; confirmation popups; fullscreen (F11); clickable credits; MENU button on all run screens; scrolling convoy with 
        navigation, bouncing vehicles and dust effects.
"""

import asyncio   # the browser (pygbag) needs an async main loop that yields once per frame

import pygame

from platform_web import IS_WEB, fullscreen_state, install_leave_guard
import touch
from config import TRAVEL_ANIMATION_FAST_FORWARD, TRAVEL_FAST_FORWARD
from credits_items import reset_credits_page, turn_credits_page
from buttons import (make_abandon_buttons, make_buttons, make_confirm_buttons, make_end_buttons,
                     make_site_buttons)
from paging import clamp_pages, turn_upgrade_page, upgrade_page
import settings_store
import textscale
from game import Game
from keys import ROW_CLICK_LABEL, KeyNav, play_click, press_button
from layout import (FPS, HEIGHT, WIDTH, calculate_layout, menu_layout, node_at, vehicle_row_at, vehicles_layout,
                    settings_layout)
from layout.upgrade import upgrade_row_at
from theme import BG
from ui.travel_banner import draw_travel_banner
from ui.convoy import set_animation_paused, set_animation_speed
from ui.screens import draw_brand
from ui import (SCROLL_STEP, clamp_history, scroll_instructions, reset_instructions_scroll,
                handle_event_click, handle_result_click, make_event_buttons)
from ui.vehicles_screen import vehicle_table_order
from app import window, popups, rendering

BRAND_SCREENS = ("menu", "difficulty", "settings", "credits", "instructions", "achievements")   # pause-menu pages (no HUD before a run)
REPEAT_KEYS = (pygame.K_TAB, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_PAGEUP,
               pygame.K_PAGEDOWN)   # the keys that may repeat

# Importing this module opens no window and creates no game: setup() (called by main()) does that, so tests can import
# main. Until setup() has run, SCREEN, CLOCK and game are None.
SCREEN = None
CLOCK = None
game = None

_cursor_shape = None              # the mouse cursor last set, so set_cursor is only called when it changes


def clamp_screens(game, size):
    """Keep the paged / scrolled screens valid for this window size: the survivors / missions pages and the event
    history's scroll position (each changes with the rows that fit)."""
    clamp_pages(game, size)
    if game.screen == "history":
        clamp_history(game, size)


def setup():
    """Start pygame, open the window, load the saved settings and create the Game. Called once by main()."""
    global SCREEN, CLOCK, game
    # v2.19: DPI awareness is on again for the Windows desktop build (window.enable_dpi_awareness): the default window size is
    # multiplied by the screen's scale factor, which fixes the tiny window it used to give. window.DPI_AWARE = False undoes it.
    dpi = window.enable_dpi_awareness()   # Windows: real pixels instead of an OS-enlarged (blurry) window; 1.0 elsewhere
    start = (round(WIDTH * dpi), round(HEIGHT * dpi))   # the default window is as big on screen as before, just sharp
    window.initialize_windowed_size(*start)
    if IS_WEB:
        # In the browser the audio is mixed on the same thread as the game, so a slow frame can starve a small buffer
        # and crackle. A bigger buffer rides those out (a little more delay on sound effects, which is fine here).
        pygame.mixer.pre_init(44100, -16, 2, 4096)
    pygame.init()
    if IS_WEB:
        install_leave_guard()   # the "Leave site?" dialog freezes the page: silence the audio while it is open
    SCREEN = pygame.display.set_mode(
        start, pygame.RESIZABLE
    )
    pygame.display.set_caption("The Last Convoy — Prototype")
    SCREEN = window.fit_web_viewport(SCREEN)   # browser: start at the page's size, not the default WIDTH x HEIGHT
    CLOCK = pygame.time.Clock()
    pygame.key.set_repeat(400, 60)   # holding Tab / an arrow key keeps moving; main() ignores repeats of every other key

    settings_store.apply_saved()   # the saved accessibility palette (settings.json), before anything is drawn

    # The saved text size comes from a file, so it is only ever used as a plain name looked up in the known levels
    # (never in eval, a path or the like). An unknown name is ignored and the default size stays. (apply_saved already
    # does the same check; repeating it here keeps main.py safe even if that function changes. set_text_level is a
    # no-op when the level is already the current one.)
    saved_level = settings_store.saved_text_level()
    if isinstance(saved_level, str) and saved_level in dict(textscale.TEXT_LEVELS):
        textscale.set_text_level(saved_level)

    game = Game()
    game.animate_travel = True        # journeys run day by day on a timer (Game.update_travel), not all at once
    game.interactive_abandon = True   # a convoy without enough adult drivers asks which vehicle to give up (popup)
    game.vehicle_scavenging = True    # a search can find a vehicle; a YES / NO popup asks whether to take it
    game.fullscreen = settings_store.load_display()["fullscreen"]   # the wanted window mode
    if game.fullscreen:
        # Switch before the first frame, so the game never draws into the small start-up window first.
        SCREEN, window.window_fullscreen = window.set_window_mode(SCREEN, True)
        _cursor_shape = None
        game.fullscreen = window.window_fullscreen   # stays windowed if the switch failed



def update_mouse_cursor(buttons, over_clickable=False):
    """Hand cursor over everything clickable: an enabled button (Button.clicked is False for a disabled one), or something
    that is not a button (`over_clickable`: a map stop, a vehicle-table row). The cursor is only set when the shape
    changes, not on every frame."""
    global _cursor_shape
    mouse_pos = pygame.mouse.get_pos()
    hovering = over_clickable or any(button.clicked(mouse_pos) for button in buttons)

    wanted = pygame.SYSTEM_CURSOR_HAND if hovering else pygame.SYSTEM_CURSOR_ARROW
    if wanted != _cursor_shape:
        try:
            pygame.mouse.set_cursor(wanted)
        except Exception:   # some platforms (the browser) cannot change the cursor
            pass
        _cursor_shape = wanted


def clickable_under_mouse(game, layout, popup_open):
    """True when the mouse is over a clickable thing that is not a Button: a stop on the map screen or a row of the
    vehicle table (none while a popup is open on top, and none once the run has ended)."""
    if popup_open or game.status != "playing":
        return False
    pos = pygame.mouse.get_pos()
    if game.screen == "map":
        return node_at(layout["width"], layout["height"], pos) is not None
    if game.screen == "vehicles":
        return vehicle_row_at(layout["width"], layout["height"], pos, len(vehicle_table_order(game)),
                              getattr(game, "vehicle_page", 0)) is not None
    if game.screen == "upgrade":
        return upgrade_row_at(layout["width"], layout["height"], pos, len(game.available_upgrades()),
                              upgrade_page(game, (layout["width"], layout["height"]))) is not None
    return False


async def main():
    global SCREEN
    setup()
    running = True
    last_vehicle_order = ()   # the vehicle table's row order last frame (owned vehicles first), to follow a moved row
    last_screen = game.screen   # to reset the instructions scroll when that screen is left or opened
    last_menu_page = game.menu_page   # to restart the keyboard focus when the menu shows the save slots (or leaves them)
    nav = KeyNav()              # the keyboard focus (keys.py)
    held = set()                # keys currently down, to tell a held key's repeats from a fresh press
    away = False                # the window lost focus or is minimized: paused, music off
    minimized = False           # minimized: nothing is drawn either
    while running:
        dt = min(0.25, CLOCK.tick(5 if minimized else FPS) / 1000.0)   # seconds since the last frame

        if game.fullscreen != window.window_fullscreen:     # the settings toggle or F11 asked for the other
            SCREEN, window.window_fullscreen = window.set_window_mode(SCREEN, game.fullscreen)
            _cursor_shape = None
            game.fullscreen = window.window_fullscreen      # stays as it was if the switch failed
            settings_store.set_fullscreen(window.window_fullscreen)

        settings_store.set_music_muted(game.music_muted)   # remembers MUTE / UNMUTE MUSIC (writes only when it changed)

        if IS_WEB:
            SCREEN = window.fit_web_viewport(SCREEN)   # follow the browser page's size (no grey bars)
            real = fullscreen_state()                  # the browser's own fullscreen (F11 / FULLSCREEN setting / ESC)
            if real is not None and real != window.window_fullscreen:
                window.window_fullscreen = game.fullscreen = real

        # Recalculate geometry every frame so everything follows window resizing. The surface is always the one pygame
        # reports for the window (it can be replaced when the OS changes the window), so the picture fills the window.
        SCREEN = pygame.display.get_surface() or SCREEN
        size = SCREEN.get_size()
        layout = calculate_layout(*size)

        # (Pending confirmations end when their screen is left: Game.screen does that cleanup itself.)
        clamp_screens(game, size)   # survivors / missions pages and the history scroll stay valid when the window changes

        for event in touch.filter(pygame.event.get(), size):
            if event.type == pygame.KEYDOWN:
                repeated = event.key in held
                held.add(event.key)
                if repeated and event.key not in REPEAT_KEYS:
                    continue   # holding ENTER / SPACE / ESC / a letter must not press again and again
                if event.key == pygame.K_F11:
                    game.toggle_fullscreen()   # fullscreen on every screen and over every popup
                    continue
            elif event.type == pygame.KEYUP:
                held.discard(event.key)
            elif event.type in (getattr(pygame, "WINDOWFOCUSLOST", None), getattr(pygame, "WINDOWMINIMIZED", None)):
                held.clear()
                if event.type == getattr(pygame, "WINDOWMINIMIZED", None):
                    minimized = True
                if not away:
                    away = True
                    game.auto_pause()                  # to the pause menu (during a run)
                    game.music_manager.pause_music()   # after auto_pause, which switches to the menu track
            elif event.type in (getattr(pygame, "WINDOWFOCUSGAINED", None), getattr(pygame, "WINDOWRESTORED", None)):
                if event.type == getattr(pygame, "WINDOWRESTORED", None):
                    minimized = False
                if away:
                    away = False
                    game.update_music()   # like UNMUTE: the current screen's track, or silence while muted

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE and window.window_fullscreen:
                # The desktop-sized window stays as it is (set_mode would end fullscreen); only pick up the surface
                # pygame now reports, so drawing and window size can never disagree.
                SCREEN = pygame.display.get_surface() or SCREEN
                continue
            elif event.type == pygame.VIDEORESIZE:
                SCREEN = pygame.display.set_mode(
                    (max(window.MIN_SIZE[0], event.w), max(window.MIN_SIZE[1], event.h)),
                    pygame.RESIZABLE
                )
                size = SCREEN.get_size()
                layout = calculate_layout(*size)
                clamp_screens(game, size)
                continue
            elif event.type == pygame.MOUSEWHEEL and game.screen == "instructions" and not (
                    game.event_result or game.event_manager.active):
                scroll_instructions(game, SCREEN.get_size(), -event.y * SCROLL_STEP)
            elif event.type == pygame.MOUSEWHEEL and game.screen == "vehicles" and not (
                    game.confirm_popup or game.event_result or game.event_manager.active or game.abandon_pick_needed()):
                if event.y:   # wheel up: the page before; clamp_screens keeps it in range
                    game.vehicle_page = getattr(game, "vehicle_page", 0) + (-1 if event.y > 0 else 1)
            elif event.type == pygame.MOUSEWHEEL and game.screen == "upgrade" and not (
                    game.confirm_popup or game.event_result or game.event_manager.active or game.abandon_pick_needed()):
                if event.y:   # a paged upgrade table: wheel up is the page before (turn_upgrade_page keeps it in range)
                    turn_upgrade_page(game, SCREEN.get_size(),
                                      upgrade_page(game, SCREEN.get_size()) + (-1 if event.y > 0 else 1))
            elif event.type == pygame.MOUSEWHEEL and game.screen == "history" and not (
                    game.confirm_popup or game.event_result or game.event_manager.active):
                game.scroll_history(-event.y * 3)   # three rows a notch; clamp_screens keeps it in range
            elif event.type == pygame.MOUSEWHEEL and game.screen == "achievements" and not (
                    game.confirm_popup or game.event_result or game.event_manager.active):
                if event.y:   # wheel up: the page before; clamp_screens keeps it in range
                    game.achievement_page += -1 if event.y > 0 else 1
            elif event.type == pygame.MOUSEWHEEL and game.screen == "credits" and not (
                    game.confirm_popup or game.event_result or game.event_manager.active):
                if event.y:
                    turn_credits_page(SCREEN.get_size(), -1 if event.y > 0 else 1)   # wheel up: the page before
            elif game.abandon_pick_needed():
                # "Which vehicle to abandon?" is modal and cannot be cancelled: only it takes input (F11 and closing the
                # window still work).
                abandon_buttons = make_abandon_buttons(game, size)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in abandon_buttons:
                        if button.clicked(event.pos):
                            press_button(game, button)
                            break
                elif event.type == pygame.KEYDOWN:
                    nav.abandon_key(game, event, abandon_buttons)
            elif game.confirm_popup:
                # "Are you sure?" (RESTART GAME / TITLE SCREEN / QUIT GAME) is modal: only it takes input.
                confirm_buttons = make_confirm_buttons(game, size)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in confirm_buttons:
                        if button.clicked(event.pos):
                            button.action()
                            play_click(game)
                            break
                elif event.type == pygame.KEYDOWN:
                    nav.confirm_key(game, event, confirm_buttons)
            elif game.event_result:
                # The result of the chosen option: wait for OK (click, Enter, Space or ESC) before going on.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if handle_result_click(event.pos, game.event_result, size):
                        game.dismiss_event_result()
                        play_click(game, "OK")
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                                    pygame.K_SPACE, pygame.K_ESCAPE):
                    game.dismiss_event_result()
                    play_click(game, "OK")
            elif game.event_manager.active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    choice = handle_event_click(event.pos, game.event_manager.current_event, size, game)
                    if choice is not None:
                        play_click(game, "EVENT CHOICE")
                        game.resolve_event_choice(choice)
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    choice = event.key - pygame.K_1
                    if game.event_manager.can_choose(game, choice):   # not one the convoy cannot pay for
                        play_click(game, "EVENT CHOICE")
                        game.resolve_event_choice(choice)
                elif event.type == pygame.KEYDOWN:
                    # Tab / arrows move the focus outline; ENTER / SPACE select the focused choice (keys.py).
                    choice = nav.event_key(game, event, make_event_buttons(game.event_manager.current_event, size, game))
                    if choice is not None:
                        game.resolve_event_choice(choice)
            elif event.type == pygame.KEYDOWN:
                if game.on_road() and event.key not in (pygame.K_o, pygame.K_ESCAPE):
                    continue   # travelling: only the pause menu (O / ESC) takes keys
                # Keyboard play (keys.py): the focus moves through the buttons the keys act on, the screen's or the
                # ending popup's.
                kind = popups.popup_kind(game)
                keys_target = popups.popup_buttons(game, size) if kind in ("end", "sites") else make_buttons(game, layout)
                if not nav.handle_key(game, event, keys_target, kind, size) and not IS_WEB:
                    running = False   # (a web page cannot close itself, so the second ESC on the title screen does nothing there)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos   # raw window pixels on every screen
                if game.site_picker and game.status == "playing":
                    site_buttons = make_site_buttons(game, size)   # the SCAVENGE popup is modal
                    for i, button in enumerate(site_buttons):
                        if button.clicked(pos):
                            press_button(game, button)
                            nav.after_site_pick(site_buttons, i)   # a picked site: the focus moves to SCAVENGE
                            break
                elif game.status == "playing" or game.screen == "history":   # history is also clickable after the run ended
                    if game.screen == "vehicles":
                        # The same geometry the table is drawn with (layout.vehicles_layout).
                        index = vehicle_row_at(layout["width"], layout["height"], pos, len(vehicle_table_order(game)),
                                               getattr(game, "vehicle_page", 0))   # an index into all vehicles, whatever the page
                        vehicle_names = vehicle_table_order(game)   # owned vehicles first, as the table is drawn
                        if index is not None and 0 <= index < len(vehicle_names):
                            if vehicle_names[index] != game.selected_vehicle_type:
                                game.abandon_confirm = None  # picking another row cancels a pending abandon
                            game.selected_vehicle_type = vehicle_names[index]
                            play_click(game, ROW_CLICK_LABEL)   # the rows are not buttons, so they need their own click
                    if game.screen == "upgrade":
                        # The same geometry the upgrade table is drawn with (layout.upgrade.upgrade_layout).
                        upgrade_ids = [upgrade["id"] for upgrade in game.available_upgrades()]
                        index = upgrade_row_at(layout["width"], layout["height"], pos, len(upgrade_ids),
                                               upgrade_page(game, (layout["width"], layout["height"])))   # an index into all upgrades, whatever the page
                        if index is not None and 0 <= index < len(upgrade_ids):
                            game.select_upgrade(upgrade_ids[index])
                            play_click(game, ROW_CLICK_LABEL)   # the rows are not buttons, so they need their own click
                    if game.screen == "map":
                        # The same positions the map is drawn with (layout.map_layout).
                        stop = node_at(layout["width"], layout["height"], pos)
                        if stop is not None:
                            game.select_destination(stop)   # any stop to look at; travel() only goes to connected ones
                            play_click(game, "MAP STOP")   # the stops are not buttons, so they need their own click
                    # Built with the same layout the screen is drawn with, so clicks match the buttons on screen.
                    buttons = make_buttons(game, layout)
                    if game.on_road():
                        buttons = [b for b in buttons if b.label == "MENU"]   # travelling: only MENU is clickable
                    for button in buttons:
                        if button.clicked(pos):
                            press_button(game, button)
                            break
                else:
                    for button in make_end_buttons(game, size):   # victory / game over screen
                        if button.clicked(pos):
                            button.action()
                            play_click(game)
                            break

        if getattr(game, "quit_requested", False):   # the pause menu's QUIT GAME, after its confirmation
            if IS_WEB:
                game.quit_requested = False   # nothing to quit to in a browser tab
            else:
                running = False

        if minimized:
            await asyncio.sleep(0)   # keep the browser responsive
            continue   # nothing to draw while minimized

        # "Hold X" missions follow what the convoy holds right now, so spending supplies (travel, repairs, upkeep) must
        # show on the missions screen too: re-read it once a frame (a few comparisons).
        if game.status == "playing":
            game.mission_manager.on_resources_changed(game)
            game.mission_manager.open_stage_event(game)   # a ready mission stage opens its dedicated event at a stop

        # The journey clock: one day per delay, SPACE held = fast-forward. It pauses by itself while a popup or another
        # screen is open. The engine loop plays exactly while the clock runs.
        space_down = pygame.key.get_pressed()[pygame.K_SPACE] or touch.holding(game.on_road())   # a long finger press on the road = SPACE
        game.update_travel(dt * (TRAVEL_FAST_FORWARD if space_down else 1))
        if game.screen == "lore" and not away and game.update_lore(dt):   # the lore screen's typing effect
            game.sound_manager.play_typing()
        # the road animation (scroll, bounce, dust) speeds up too, by its own constant
        set_animation_speed(TRAVEL_ANIMATION_FAST_FORWARD if space_down and game.travelling() else 1)
        game.sound_manager.set_loop("engine", game.travelling())
        # The music dips while the engine runs (temporary; the settings volume is untouched), but not if sound effects are off.
        duck = getattr(game.music_manager, "set_ducking", None)   # the silent test audio has no ducking
        if duck is not None:
            duck(game.travelling() and game.sound_manager.enabled)

        # Drawn after the events above, so it matches the screen the game is now on.
        size = SCREEN.get_size()
        clamp_screens(game, size)

        # The instructions text starts at the top every time that screen is opened or left.
        if game.screen != last_screen:
            if last_screen == "menu":   # the SAVE / LOAD page is left with the menu
                game.menu_page, game.save_pending, game.save_message = "main", None, ""
            if game.screen == "vehicles":   # opened (or came back from the upgrade screen): show the selected vehicle's page
                names = vehicle_table_order(game)
                row = names.index(game.selected_vehicle_type) if game.selected_vehicle_type in names else 0
                game.vehicle_page = row // vehicles_layout(size[0], size[1], len(names))["per_page"]
                last_vehicle_order = tuple(names)
            if "instructions" in (game.screen, last_screen):
                reset_instructions_scroll()
            if "credits" in (game.screen, last_screen):
                reset_credits_page()
            last_screen = game.screen

        # Recovering or abandoning a vehicle moves its row (owned vehicles come first): follow the selected vehicle's row
        # to its new page. Paging with PREV / NEXT is left alone while the order stays the same.
        if game.screen == "vehicles":
            names = vehicle_table_order(game)
            if tuple(names) != last_vehicle_order:
                last_vehicle_order = tuple(names)
                row = names.index(game.selected_vehicle_type) if game.selected_vehicle_type in names else 0
                game.vehicle_page = row // vehicles_layout(size[0], size[1], len(names))["per_page"]

        # The button list is built once per frame and shared by the cursor check and the drawing.
        layout = calculate_layout(*size)
        screen_buttons = make_buttons(game, layout)
        if game.on_road():
            for button in screen_buttons:
                if button.label != "MENU":
                    button.enabled = False   # greyed out while travelling (no click, no focus, no hand cursor)
        popup = popups.popup_buttons(game, size)
        update_mouse_cursor(screen_buttons if popup is None else popup,
                            clickable_under_mouse(game, layout, popup is not None))

        # The keyboard focus outline goes on the open popup's buttons (event, result, ending, SCAVENGE), or on the
        # screen's buttons when no popup is open.
        kind = popups.popup_kind(game)
        focus_target = screen_buttons if kind is None else popup
        if game.menu_page != last_menu_page:   # the menu's buttons and the save slots are different lists: focus starts afresh
            nav.context = None
            last_menu_page = game.menu_page
        nav.sync(game, focus_target, kind)
        nav.apply(focus_target)

        # The road animation only runs while the scene can be seen: not in the pause menu or any other screen, and not
        # while the window is out of focus.
        set_animation_paused(away or game.screen not in ("title", "lore", "convoy"))

        SCREEN.fill(BG)
        if game.screen in rendering.WINDOW_SCREENS:
            rendering.draw_window_screen(
                SCREEN, game, layout, screen_buttons
            )
            if game.screen in BRAND_SCREENS and not game.started:
                # No run yet, so there is no HUD: the strip where it would be shows the logo and the game's name.
                draw_brand(SCREEN, menu_layout(*size)["hud"])
        else:
            rendering.draw_convoy_screen(
                SCREEN, game, layout, screen_buttons
            )
            if game.on_road():
                draw_travel_banner(SCREEN, game, layout)
        popups.draw_popups(SCREEN, game, popup)
        pygame.display.flip()
        await asyncio.sleep(0)   # hand control back to the browser once per frame (pygbag requirement)

    if not IS_WEB:
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
