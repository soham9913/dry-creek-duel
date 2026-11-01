import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Release info, shown on the loading screen, menu and credits.
GAME_TITLE = "Dry Creek Duel"
VERSION = "1.0.0"
AUTHOR = "Soham Pawar"
CREDIT_LINE = f"Made and designed by {AUTHOR}"
COPYRIGHT = f"\u00a9 2026 {AUTHOR}. All rights reserved."

# Where the game is running. In a browser (itch.io, via pygbag) sys.platform is "emscripten".
IS_WEB = sys.platform == "emscripten"
# Bundled files (fonts, sounds, icon). A PyInstaller .exe unpacks them to sys._MEIPASS.
RES_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

# Logical resolution. The window scales to fit, so these never change at runtime.
W, H = 960, 540            # the scene
HUD_H = 100                # stat strip under the scene
SCREEN = (W, H + HUD_H)
FPS = 120                  # a high cap keeps input latency low

# Gunslinger placement and size.
SC = 1.15
FEET = 468
PLAYER_X, ENEMY_X = 232, 728

# Palette.
INK = (14, 6, 5)
LEATHER = (42, 23, 16)
EMBER = (228, 87, 46)
SUN = (255, 217, 138)
BONE = (240, 224, 196)
BONE_DIM = (185, 163, 135)
LINE = (74, 42, 28)
PANEL = (27, 13, 9)
RUST = (140, 52, 22)

# Rules.
LIVES = 3
MIN_REACTION_MS = 100      # a press sooner than this after the bell counts as a false start
PACE_MS = 900              # walk-out time before the wait begins
WAIT_RANGE_MS = (1600, 4800)
JITTER_MS = 25             # legacy jitter, kept for backwards compatibility

# Five-Round Duel Difficulty System
ROUND_TARGET_MS = {
    1: 450,  # Round 1 - Easy
    2: 350,  # Round 2 - Medium
    3: 280,  # Round 3 - Hard
    4: 240,  # Round 4 - Expert
    5: 200,  # Round 5 - Legendary
}
MIN_ENEMY_MS = 200          # minimum reaction-time limit (cannot be higher than Round 5 target: 200 ms)
ENEMY_VARIATION_PCT = 0.03  # small, controlled variation (+/- 3%)


def calculate_enemy_reaction_time(
    base_reaction_time: Optional[int] = None,
    round_number: int = 1,
    min_ms: int = MIN_ENEMY_MS,
    variation_pct: float = ENEMY_VARIATION_PCT,
    apply_variation: bool = True,
    variation_val: Optional[float] = None,
) -> int:
    """Calculate opponent reaction time using fixed five-round targets.

    Fixed round base targets:
        Round 1 — Easy:      450 ms
        Round 2 — Medium:    350 ms
        Round 3 — Hard:      280 ms
        Round 4 — Expert:    240 ms
        Round 5 — Legendary: 200 ms
    """
    if base_reaction_time is not None:
        target = base_reaction_time
    elif 1 <= round_number <= len(ROUND_TARGET_MS):
        target = ROUND_TARGET_MS[round_number]
    else:
        target = ROUND_TARGET_MS.get(round_number, 200)

    if apply_variation:
        if variation_val is not None:
            factor = 1.0 + variation_val
        else:
            factor = 1.0 + random.uniform(-variation_pct, variation_pct)
        varied = target * factor
    else:
        varied = target

    return max(min_ms, round(varied))


@dataclass(frozen=True)
class Enemy:
    name: str
    short: str
    ms: int                # base draw time in milliseconds
    bounty: int
    accent: tuple
    star: bool = False


ENEMIES = (
    Enemy("Dusty Pete", "Pete", 450, 25, (201, 178, 122)),
    Enemy("Calico Jane", "Jane", 350, 60, (111, 179, 165)),
    Enemy("Dead-Eye Dan", "Dan", 280, 120, (214, 210, 196)),
    Enemy("Black Bart", "Bart", 240, 250, (178, 59, 59)),
    Enemy("The Marshal", "The Marshal", 200, 500, (233, 196, 106), star=True),
)


@dataclass(frozen=True)
class Arena:
    id: str
    name: str
    subtitle: str
    unlock_condition: str
    unlock_duel: int  # 0 means signature/default; 1 means unlocked after beating duel 0 (Pete), etc.
    wind_base: float
    dust_density: int
    vignette_tint: tuple
    cowboy_tint: tuple


ARENAS = (
    Arena(
        id="desert",
        name="Sunset Desert",
        subtitle="The Signature Arena",
        unlock_condition="Signature Arena (Unlocked)",
        unlock_duel=0,
        wind_base=0.10,
        dust_density=40,
        vignette_tint=(8, 3, 2),
        cowboy_tint=(255, 217, 138),
    ),
    Arena(
        id="saloon",
        name="Dusty Main Street",
        subtitle="Outside the Silver Spur Saloon",
        unlock_condition="Defeat Dusty Pete to unlock",
        unlock_duel=1,
        wind_base=0.15,
        dust_density=60,
        vignette_tint=(18, 10, 6),
        cowboy_tint=(235, 185, 120),
    ),
    Arena(
        id="railway",
        name="Moonlit Railway Station",
        subtitle="Dry Creek Depot at Midnight",
        unlock_condition="Defeat Calico Jane to unlock",
        unlock_duel=2,
        wind_base=0.08,
        dust_density=35,
        vignette_tint=(6, 10, 22),
        cowboy_tint=(180, 210, 245),
    ),
    Arena(
        id="ghost_town",
        name="Ghost Town Sandstorm",
        subtitle="The Abandoned Settlement",
        unlock_condition="Defeat Dead-Eye Dan to unlock",
        unlock_duel=3,
        wind_base=0.48,
        dust_density=140,
        vignette_tint=(24, 14, 8),
        cowboy_tint=(220, 160, 95),
    ),
    Arena(
        id="canyon",
        name="Canyon Bridge",
        subtitle="Gallows Gorge Trestle",
        unlock_condition="Defeat Black Bart to unlock",
        unlock_duel=4,
        wind_base=0.24,
        dust_density=65,
        vignette_tint=(16, 8, 14),
        cowboy_tint=(240, 150, 120),
    ),
    Arena(
        id="rain",
        name="Rain-Soaked Street",
        subtitle="Midnight Downpour",
        unlock_condition="Defeat The Marshal to unlock",
        unlock_duel=5,
        wind_base=0.32,
        dust_density=80,
        vignette_tint=(6, 8, 14),
        cowboy_tint=(150, 190, 230),
    ),
)

ARENA_MAP = {a.id: a for a in ARENAS}


def get_arena(arena_id: str) -> Arena:
    return ARENA_MAP.get(arena_id, ARENAS[0])


def get_arena_for_duel(duel_index: int) -> Arena:
    idx = max(0, min(duel_index, len(ARENAS) - 1))
    return ARENAS[idx]


if __name__ == "__main__":
    import asyncio
    from main import main
    asyncio.run(main())


