# Dry Creek Duel

A quick-draw reaction game written in Python with Pygame. Wait for the bell, then draw before the gunslinger does. Draw early and you are dead.

Five opponents, each faster than the last, from Dusty Pete (450 ms) to The Marshal (200 ms). You have three bullets. Your fastest draw is saved between sessions.

## Run it

```
pip install -r requirements.txt
python main.py
```

Needs Python 3.9 or newer.

| Input | Action |
| --- | --- |
| Up / Down (or W / S), mouse hover | Move through the main menu |
| Enter, Space, or left click | Choose a menu option, draw, continue |
| Left / Right (or A / D) | Change the arena or sound setting on the menu |
| L or [ / ] | Cycle unlocked duel locations / arenas |
| M | Sound on or off (remembered between sessions) |
| Esc or P, or the pause button | Pause a duel (the clock freezes) |
| F11 | Fullscreen on / off (desktop) |
| Esc on the main menu | Quit (desktop) |

The game also pauses itself if the window loses focus, so switching windows never costs you a duel.

## Loading screen & main menu

On launch, a **loading screen** prepares every arena before the first duel: it paints all six backdrops and vignettes and synthesizes all six ambience loops, one job per frame, so switching arenas later never stutters. Progress is shown as a revolver cylinder (one chamber loads per arena) and a burning fuse, over a dimmed, banded sunset with a random "frontier wisdom" tip. Once the cylinder spins shut it fades into the menu; any key skips the final beat.

The **main menu** plays out live in the currently selected arena: the player and The Marshal wait at either end of the street while dust and tumbleweeds blow past. Options:

- **Start Duel** — begin the five-duel run.
- **Arena** — Auto Tour or any unlocked arena; the backdrop cross-fades to match.
- **Settings** — fullscreen, sound on/off, effects volume and ambience volume (all saved).
- **How to Play** — the rules and a "Wanted" board of all five opponents.
- **Credits**
- **Quit** (hidden in the browser version)

The **pause menu** has Resume, Settings, How to Play, Main Menu (abandons the run) and Quit.

The bottom strip shows your fastest draw, best bounty, arenas unlocked, and your reputation (earned from your fastest draw).

The window is resizable and keeps its proportions.

## Duel Locations (Arenas)

The game features six distinct duel locations, each with its own vector backdrop, dynamic lighting, procedural ambient soundscape, and atmospheric particles:

1. **Sunset Desert** — The signature arena under a blazing desert sun with retro horizontal sunbands, mesas, saguaro cacti, and drifting tumbleweeds.
2. **Dusty Main Street** — Outside the Silver Spur Saloon with timber porches, balcony railings, batwing doors leaking warm lantern light, hitching rails, and wind-blown dust. *(Unlocked after beating Dusty Pete)*
3. **Moonlit Railway Station** — Dry Creek Depot at midnight under a luminous silver moon, with telegraph wires, station house, platform oil lanterns, and an idling steam locomotive. *(Unlocked after beating Calico Jane)*
4. **Ghost Town Sandstorm** — An abandoned frontier settlement in a ferocious sandstorm with tilting dilapidated ruins, a collapsed belfry, Boot Hill crosses, swirling sand sheets, and racing tumbleweeds. *(Unlocked after beating Dead-Eye Dan)*
5. **Canyon Bridge** — High atop a wooden suspension trestle spanning the dizzying depths of Gallows Gorge at twilight, framed by sheer sandstone cliffs and circling eagles. *(Unlocked after beating Black Bart)*
6. **Rain-Soaked Street** — Midnight downpour with wet muddy roads, glistening puddle reflections of warm street lanterns, driving rain streaks, puddle splashes, and dynamic lightning flashes. *(Unlocked after beating The Marshal)*

By default in Campaign Tour (`AUTO`), each round takes place in its respective arena. You can also manually lock to any unlocked location using `L` or `[` / `]`. Unlocked arenas persist between game sessions.

## Visual Polish & Effects

- **Muzzle Flash**: Multi-layered radiant blast with inner white-hot core, starburst spikes, and dynamic scene illumination.
- **Gun Smoke**: Realistic billowing black-powder smoke puffs that burst from the revolver barrel, expand, rise with thermal buoyancy, and drift with the wind.
- **Camera Shake**: Trauma-based screen shake that kicks with gunshots and settles smoothly.
- **Wind-blown Dust & Particles**: Dynamic gusting wind carrying dust motes and wind wisps across the plains, sand sheets during the sandstorm, and driving rain streaks with puddle splash ripples.
- **Procedural Ambient Audio**: Synthesized looping soundscapes for each arena (desert wind, saloon creaks, night depot steam hum, howling sandstorm, resonant canyon gorge, rain patter & thunder).

## Rules

- After you step up, the gunslinger walks out and you wait for a random time between 1.6 and 4.8 seconds.
- When the bell rings and DRAW! appears, press as fast as you can.
- Press before the bell, or within 100 ms of it, and it counts as a false start.
- If you beat the opponent's draw time you win their bounty. Otherwise you lose a bullet and face them again.
- Win all five duels to become Marshal of Dry Creek.

## How it is built

| File | Purpose |
| --- | --- |
| `main.py` | Game states (title/menu, pace, ready, draw, result), arena progression & unlocks, camera shake, timing, input, HUD, result cards |
| `loading.py` | The loading screen: real asset preloading with revolver-cylinder progress |
| `menu.py` | Main menu, pause menu, Settings, How to Play and Credits |
| `ui.py` | Shared UI: fonts, text cache, ornaments, the `OptionPanel` widget, and the game icon |
| `storage.py` | Save data: a JSON file on the desktop, `localStorage` in the browser |
| `tools/` | Build and asset scripts (see "Releasing on itch.io") |
| `scene.py` | 6 arena vector backdrops, tailored vignettes, dynamic wind & dust system, gunsmoke particle simulation, and gunslingers with muzzle flash |
| `sound.py` | Bell, gunshot, menu tick and cylinder click, and 6 procedural looping ambient soundscapes generated in code |
| `config.py` | Version and author, resolution, palette, rules, opponent table, and arena definitions |
| `tests/` | Test suite covering duel flow, 5-round difficulty targets, arena unlocks, camera shake, smoke, the main menu, and the loading screen |


Design notes:

- Draw times are measured from the scheduled bell time to the moment the input event is handled, in milliseconds.
- The game has one input action, `Game.on_action(now)`. What it does depends on the current phase, so keyboard, mouse, and touch all go through the same path.
- If the window is frozen for more than 300 ms (dragged, minimized), the round's timers shift forward so the player is not punished.
- The window uses Pygame's `SCALED` mode, so the game draws at a fixed 960x640 and scales to any screen.

## Tweak the difficulty

Edit the `ENEMIES` table in `config.py`. Each entry has an average draw time in milliseconds and a bounty. `JITTER_MS` controls how much each opponent's time varies per round.

## Tests

```
python -m unittest discover -s tests
```

## The Rye font

The western display lettering (title, DRAW!, result headings) uses **Rye** by Nicole Fally, bundled in `assets/fonts/Rye-Regular.ttf` under the SIL Open Font License (see `assets/fonts/Rye-OFL.txt`). If the file is removed, the game falls back to Pygame's built-in font.

## Ideas for later

- Two-player mode on one keyboard
- A fake-out round with a false bell
- Touch controls and an Android build (see below)

## Android note

Pygame does not publish to the Play Store directly. Realistic routes are a Kivy port built with Buildozer, or rebuilding the game in Godot, which exports to Android with a one-click preset. The logic in `main.py` (one input action, a timed state machine, drawing separated from game rules) carries over to either.


## Releasing on itch.io

Everything needed is in this folder. The full walkthrough is in [`store_page/UPLOAD_GUIDE.md`](store_page/UPLOAD_GUIDE.md).

| Step | Command (Windows: double-click the .bat) | Output |
| --- | --- | --- |
| Browser build | `build_web.bat` (or `python tools/build_web.py`) | `release/dry-creek-duel-web.zip` |
| Play the browser build locally | `build_web.bat --serve`, then open http://localhost:8000 | |
| Windows build | `build_windows.bat` | `release/DryCreekDuel-windows.zip` |
| Re-render sounds to `.ogg` | `python tools/render_sounds.py` (needs ffmpeg) | `assets/sounds/` |
| Remake the icon | `python tools/make_icons.py` | `assets/icon.png`, `assets/icon.ico` |
| Remake store images | `python tools/make_store_assets.py` | `store_page/` |

Notes:

- The browser build uses [pygbag](https://github.com/pygame-web/pygbag). This is why the main loop is `async` and calls `await asyncio.sleep(0)` every frame. On the desktop that line does nothing.
- In the browser, saves go to the page's `localStorage`, Quit is hidden, and fullscreen uses itch.io's button.
- Sounds are pre-rendered to `assets/sounds/*.ogg` so the browser doesn't spend seconds synthesizing them. If that folder is empty, the game synthesizes them in code exactly as before.
- `AUTHOR` and `VERSION` live in `config.py`. The credit "Made and designed by Soham Pawar" appears on the loading screen, the main menu, the Credits screen and the window title.
- `store_page/` holds the cover (630×500), six screenshots, a gameplay GIF and the page text.

---
Made and designed by Soham Pawar. © 2026 Soham Pawar. All rights reserved.
