"""Render the itch.io store-page images straight from the game:

    store_page/cover.png            630 x 500 cover image
    store_page/screenshot_1..6.png  960 x 640 in-game screenshots
    store_page/gameplay.gif         a full duel, for the page description

    python tools/make_store_assets.py      (needs Pillow for the GIF:  pip install pillow)

Re-run it whenever the game's look changes.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["DRYCREEK_SAVE"] = os.path.join(tempfile.mkdtemp(), "store.json")   # never touch your real save
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402

import pygame  # noqa: E402

pygame.init()
from config import ARENAS, BONE, BONE_DIM, INK, RUST, SCREEN, SUN, W  # noqa: E402

screen = pygame.display.set_mode(SCREEN)
from main import Game  # noqa: E402
from ui import TextCache, draw_ornament_rule, load_font  # noqa: E402

OUT = ROOT / "store_page"
ALL = {a.id for a in ARENAS}


def new_game(arena=None, best=None):
    random.seed(4)
    g = Game(screen)
    g.unlocked_arenas = set(ALL)
    if arena:
        g.selected_arena = arena
        g.apply_arena(arena)
    g.best = best
    return g


def run(g, t0, t1, step=8):
    t = t0
    while t < t1:
        t = min(t1, t + step)
        g.frame(t)
    return t


def duel(g, now, wait=1600, enemy_ms=320, duel_index=0):
    """Step up and fix the bell time so the shots are repeatable."""
    g.duel = duel_index
    g.on_action(now)
    g.round.cue_at = g.round.pace_end + wait
    g.round.enemy_ms = enemy_ms
    return g.round


def save(name):
    path = OUT / name
    pygame.image.save(screen, str(path))
    print("wrote", path.relative_to(ROOT))


def screenshots():
    # 1. main menu
    g = new_game(best=212)
    g.best_bounty = 455
    run(g, 0, 2600)
    save("screenshot_1.png")

    # 2. the bell rings on Main Street
    g = new_game("saloon", best=212)
    r = duel(g, 0, duel_index=1)
    run(g, 0, r.cue_at + 175)              # just after the bell's flash fades
    save("screenshot_2.png")

    # 3. a clean win at the railway depot
    g = new_game("railway", best=212)
    r = duel(g, 0, enemy_ms=280, duel_index=2)
    run(g, 0, r.cue_at + 1)
    g.on_action(r.cue_ts + 214)
    run(g, g.last_now, r.show_at + 200)
    save("screenshot_3.png")

    # 4. the wait, in the ghost town sandstorm
    g = new_game("ghost_town", best=212)
    r = duel(g, 0, wait=4000, duel_index=3)
    run(g, 0, r.pace_end + 3300)
    save("screenshot_4.png")

    # 5. Black Bart fires first on Gallows Gorge
    g = new_game("canyon", best=212)
    r = duel(g, 0, enemy_ms=240, duel_index=3)
    run(g, 0, r.cue_at + 1)
    g.on_action(r.cue_ts + 300)
    run(g, g.last_now, r.e.shot_at + 25)
    save("screenshot_5.png")

    # 6. lightning over the rain-soaked street
    g = new_game("rain", best=212)
    r = duel(g, 0, wait=3000, duel_index=4)
    run(g, 0, r.pace_end + 1500)
    g.ambient._next_lightning = 0
    t = r.pace_end + 1500
    for _ in range(14):                     # let the lightning flash fade to a glow
        t += 8
        g.frame(t)
    save("screenshot_6.png")


def cover():
    """630x500: the moment of the shot under the desert sun, with the logo."""
    g = new_game("desert")
    r = duel(g, 0, enemy_ms=320)
    run(g, 0, r.cue_at + 1)
    g.on_action(r.cue_ts + 205)
    run(g, g.last_now, r.p.shot_at + 40)
    shot = g.scene.copy()                         # the scene without HUD or camera shake

    crop = shot.subsurface(pygame.Rect(140, 0, 680, 540)).copy()
    art = pygame.transform.smoothscale(crop, (630, 500))
    cover = pygame.Surface((630, 500))
    cover.blit(art, (0, 0))
    shade = pygame.Surface((630, 500), pygame.SRCALPHA)
    for y in range(500):
        top = max(0.0, 1 - y / 210) ** 1.3 * 220
        bottom = max(0.0, (y - 400) / 100) ** 1.5 * 200
        pygame.draw.line(shade, (*INK, int(min(255, top + bottom))), (0, y), (630, y))
    cover.blit(shade, (0, 0))

    text = TextCache()
    kicker = text.spaced(load_font(26, display=True), "DRY CREEK", BONE, 9)
    cover.blit(kicker, kicker.get_rect(midtop=(315, 22)))
    big = load_font(96, display=True)
    shadow = text.outlined(big, "DUEL", RUST, RUST, 5)
    logo = text.outlined(big, "DUEL", SUN, INK, 5)
    cover.blit(shadow, shadow.get_rect(midtop=(315, 52 + 6)))
    cover.blit(logo, logo.get_rect(midtop=(315, 52)))
    tag = text.spaced(load_font(19), "WAIT FOR THE BELL. DRAW FIRST.", BONE_DIM, 3)
    cover.blit(tag, tag.get_rect(center=(315, 470)))
    draw_ornament_rule(cover, 315, 470, 270, (110, 62, 40), gap=tag.get_width() // 2 + 16)
    path = OUT / "cover.png"
    pygame.image.save(cover, str(path))
    print("wrote", path.relative_to(ROOT))


def gameplay_gif():
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed: skipped gameplay.gif (pip install pillow)")
        return
    frames = []

    def grab():
        img = Image.frombytes("RGB", SCREEN, pygame.image.tobytes(screen, "RGB"))
        frames.append(img.resize((640, 427), Image.LANCZOS))

    g = new_game("desert", best=None)
    t = run(g, 0, 900)
    for _ in range(12):                           # a beat on the menu
        t += 40
        g.frame(t)
        grab()
    r = duel(g, t, wait=1700, enemy_ms=330)
    end = r.cue_at + 2600
    hit = False
    while t < end:
        t += 40 if not (r.cue_at - 40 <= t <= r.cue_at + 900) else 20     # slower around the draw
        if not hit and r.cue_ts is not None and t >= r.cue_ts + 228:
            g.on_action(r.cue_ts + 228)
            hit = True
        g.frame(t)
        grab()
    for _ in range(30):                           # hold on the result card
        t += 40
        g.frame(t)
        grab()
    q = [f.quantize(colors=200, dither=Image.Dither.NONE) for f in frames]
    path = OUT / "gameplay.gif"
    q[0].save(path, save_all=True, append_images=q[1:], duration=40, loop=0, optimize=True)
    print("wrote", path.relative_to(ROOT), f"({len(frames)} frames, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    screenshots()
    cover()
    gameplay_gif()
