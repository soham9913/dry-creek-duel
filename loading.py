"""The loading screen shown at launch.

It does real work: it paints every arena backdrop and vignette and prepares every
ambience loop before the first duel, one task per frame, so switching arenas later
never stalls. Progress is a revolver cylinder with one chamber per arena, plus a
burning fuse.
"""
import asyncio
import math
import random

import pygame

from config import CREDIT_LINE, IS_WEB, ARENAS, BONE, BONE_DIM, EMBER, FPS, INK, LINE, SCREEN, SUN, W
from scene import _glow, get_backdrop, get_vignette
from ui import (BRASS, BRASS_LIGHT, FULL_H, PRIMER, STEEL, STEEL_DARK, STEEL_LIGHT, TextCache,
                clamp01, draw_ornament_rule, ease_out, edge_vignette, load_font, wrap)


# ---------------------------------------------------------------- loading screen
LOADING_TIPS = (
    "Wait for the bell. Whoever moves first gets buried first.",
    "A press within 100 ms of the bell counts as a false start.",
    "Each gunslinger draws faster than the last. The Marshal clears leather in 200 ms.",
    "Win a duel to unlock a new arena. Change arenas from the main menu.",
    "Lose a duel and you spend a bullet. Spend all three and it's Boot Hill.",
    "Press M at any time to turn the sound on or off.",
    "Your fastest draw is saved between sessions. Come back and beat it.",
)

AMBIENCE_NAMES = {
    "desert": "the desert wind",
    "saloon": "saloon door creaks",
    "railway": "the midnight depot",
    "ghost_town": "the sandstorm howl",
    "canyon": "echoes in the gorge",
    "rain": "the midnight rain",
}


class LoadingScreen:
    MIN_MS = 1900          # never flash by: long enough to read the tip
    HOLD_MS = 600          # "LOADED" beat after the last chamber
    FADE_MS = 350

    CX, CY, CR = W // 2, 268, 110      # revolver cylinder
    CHAMBER_R, CHAMBER_DIST = 24, 64
    FUSE_X0, FUSE_X1, FUSE_Y = 300, 660, 470

    def __init__(self, screen, sounds):
        self.screen = screen
        self.sounds = sounds
        self.text = TextCache()
        self.f_title = load_font(26, display=True)
        self.f_loaded = load_font(34, display=True)
        self.f_status = load_font(26)
        self.f_small = load_font(20)
        self.f_tip = load_font(24)

        self.tasks = []
        for arena in ARENAS:
            self.tasks.append((f"Painting {arena.name}",
                               lambda a=arena: (get_backdrop(a.id), get_vignette(a.vignette_tint))))
            self.tasks.append((f"Recording {AMBIENCE_NAMES.get(arena.id, 'the wind')}",
                               lambda a=arena: self.sounds.preload_ambient(a.id)))
        self.total = len(self.tasks)
        self.done = 0
        self.status = "Saddling up"

        self.started_at = None
        self.last_now = None
        self.shown = 0.0            # progress as displayed, eased toward the real value
        self.loaded = 0             # chambers with a cartridge in them
        self.pop_at = [None] * len(ARENAS)
        self.angle = 0.0            # cylinder rotation in degrees, eased toward angle_target
        self.angle_target = 0.0
        self.finished_at = None
        self.skip = False
        self.tip = random.choice(LOADING_TIPS)

        rng = random.Random(5)
        self.motes = [[rng.random() * W, rng.random() * FULL_H, 0.008 + rng.random() * 0.02,
                       0.6 + rng.random() * 1.6, 25 + int(rng.random() * 60)] for _ in range(60)]
        self.sparks = []
        self._layer = pygame.Surface(SCREEN, pygame.SRCALPHA)
        self.bg = self._build_background()

    # ------------------------------------------------------------ static art
    def _build_background(self):
        """Ink-black field with a dim, banded sunset disc behind the cylinder,
        echoing the signature desert sun."""
        bg = pygame.Surface(SCREEN)
        bg.fill(INK)
        _glow(bg, (self.CX, self.CY), 300, (70, 24, 12))
        sx, sy, sr = self.CX, self.CY, 168
        for y in range(sy - sr, sy + sr + 1):
            dy = y - sy
            half = int(math.sqrt(max(0, sr * sr - dy * dy)))
            t = (y - (sy - sr)) / (2 * sr)
            color = (int(92 - 40 * t), int(34 - 14 * t), int(18 - 8 * t))
            for i in range(7):
                top = sy + 12 + i * 21
                if top <= y < top + 3 + i * 2.2:
                    color = INK
            pygame.draw.line(bg, color, (sx - half, y), (sx + half, y))
        # a far horizon line with the mesas from the title backdrop, in near-black
        horizon = FULL_H - 150
        pygame.draw.polygon(bg, (24, 10, 7), [(0, horizon + 20), (0, horizon - 22), (70, horizon - 22), (92, horizon - 48),
                                              (180, horizon - 48), (204, horizon - 18), (300, horizon + 20)])
        pygame.draw.polygon(bg, (24, 10, 7), [(640, horizon + 20), (690, horizon - 30), (790, horizon - 30), (812, horizon - 52),
                                              (900, horizon - 52), (930, horizon - 22), (960, horizon - 22), (960, horizon + 20)])
        pygame.draw.rect(bg, (18, 8, 6), (0, horizon + 20, W, FULL_H - horizon - 20))
        pygame.draw.line(bg, (52, 24, 14), (0, horizon + 20), (W, horizon + 20), 1)
        bg.blit(edge_vignette(SCREEN, 170), (0, 0))
        return bg

    # ------------------------------------------------------------ state
    @property
    def ready(self):
        return self.done >= self.total

    def complete(self, now):
        if self.finished_at is None:
            return False
        end = self.finished_at + (0 if self.skip else self.HOLD_MS) + self.FADE_MS
        return now >= end

    def request_skip(self):
        """A key or click after loading finishes skips the 'LOADED' beat."""
        if self.finished_at is not None:
            self.skip = True

    def step(self):
        """Run one loading task. Called once per frame so the screen keeps animating."""
        if self.ready:
            return
        label, task = self.tasks[self.done]
        self.status = label
        task()
        self.done += 1
        if self.ready:
            self.status = "Ready to ride"

    def update(self, now):
        if self.started_at is None:
            self.started_at = now
            self.last_now = now
        dt = max(0.0, now - self.last_now)
        self.last_now = now

        self.step()
        real = self.done / self.total
        time_cap = (now - self.started_at) / self.MIN_MS
        target = min(real, time_cap)
        self.shown += (target - self.shown) * min(1.0, dt * 0.01)
        if target >= 1.0 and self.shown > 0.995:
            self.shown = 1.0

        # A chamber is loaded for each arena's worth of progress.
        chambers = len(ARENAS)
        want = min(chambers, int(self.shown * chambers + 1e-6))
        while self.loaded < want:
            self.pop_at[self.loaded] = now
            self.loaded += 1
            self.angle_target -= 360 / chambers        # turn the next empty chamber to the top
            self.sounds.click()
        if self.shown >= 1.0 and self.finished_at is None:
            self.finished_at = now
            self.angle_target -= 360                   # the gunslinger's spin before holstering
        self.angle += (self.angle_target - self.angle) * min(1.0, dt * (0.006 if self.finished_at else 0.016))

        # Spark particles fly off the burning fuse.
        fx = self.FUSE_X0 + (self.FUSE_X1 - self.FUSE_X0) * self.shown
        if self.shown < 1.0:
            for _ in range(2):
                self.sparks.append([fx, self.FUSE_Y, random.uniform(-0.12, 0.05), random.uniform(-0.16, -0.04),
                                    0.0, random.uniform(220, 420)])
        alive = []
        for s in self.sparks:
            s[4] += dt
            if s[4] < s[5]:
                s[0] += s[2] * dt
                s[1] += s[3] * dt
                s[3] += 0.0005 * dt
                alive.append(s)
        self.sparks = alive
        for m in self.motes:
            m[0] = (m[0] + m[2] * dt) % (W + 20) - 10
            m[1] += math.sin(now * 0.001 + m[3] * 7) * 0.05

    # ------------------------------------------------------------ drawing
    def draw(self, now):
        scr = self.screen
        scr.blit(self.bg, (0, 0))

        layer = self._layer
        layer.fill((0, 0, 0, 0))
        for m in self.motes:
            pygame.draw.circle(layer, (*SUN, m[4]), (int(m[0]), int(m[1])), m[3])
        scr.blit(layer, (0, 0))

        # header
        head = self.text.spaced(self.f_title, "DRY CREEK DUEL", BONE_DIM, 6)
        scr.blit(head, head.get_rect(center=(W // 2, 58)))
        draw_ornament_rule(scr, W // 2, 92, 170, LINE)
        by = self.text.plain(self.f_small, CREDIT_LINE.upper(), BONE_DIM)
        scr.blit(by, by.get_rect(center=(W // 2, 112)))

        self._draw_cylinder(scr, now)
        self._draw_fuse(scr, now)

        # status line: names the task the *displayed* progress has reached
        if self.shown < 1.0 and self.total:
            self.status = self.tasks[min(self.total - 1, int(self.shown * self.total))][0]
        if self.finished_at is not None:
            word = self.text.spaced(self.f_loaded, "LOADED", SUN, 8)
            k = ease_out((now - self.finished_at) / 260)
            word.set_alpha(int(255 * k))
            scr.blit(word, word.get_rect(center=(W // 2, 430 + int(8 * (1 - k)))))
        else:
            dots = "." * (1 + (now // 300) % 3)
            status = self.text.plain(self.f_status, self.status.upper(), BONE)
            r = status.get_rect(center=(W // 2, 432))
            scr.blit(status, r)
            scr.blit(self.text.plain(self.f_status, dots, BONE), (r.right + 2, r.top))

        # frontier wisdom
        lab = self.text.spaced(self.f_small, "FRONTIER WISDOM", EMBER, 3)
        scr.blit(lab, lab.get_rect(center=(W // 2, FULL_H - 84)))
        y = FULL_H - 62
        for line in wrap(self.tip, self.f_tip, 640):
            surf = self.text.plain(self.f_tip, line, BONE_DIM)
            scr.blit(surf, surf.get_rect(center=(W // 2, y)))
            y += surf.get_height() + 2

        # fades
        alpha = 0
        if self.started_at is not None and now - self.started_at < 300:
            alpha = int(255 * (1 - (now - self.started_at) / 300))
        if self.finished_at is not None:
            fade_start = self.finished_at + (0 if self.skip else self.HOLD_MS)
            if now >= fade_start:
                alpha = max(alpha, int(255 * clamp01((now - fade_start) / self.FADE_MS)))
        if alpha:
            veil = pygame.Surface(SCREEN)
            veil.fill(INK)
            veil.set_alpha(alpha)
            scr.blit(veil, (0, 0))

    def _draw_cylinder(self, scr, now):
        cx, cy, cr = self.CX, self.CY, self.CR
        n = len(ARENAS)
        rot = math.radians(self.angle) - math.pi / 2   # chamber 0 starts at the top

        # drop shadow
        shadow = pygame.Surface((cr * 2 + 40, cr * 2 + 40), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 130), (cr + 20, cr + 28), cr + 2)
        scr.blit(shadow, (cx - cr - 20, cy - cr - 20))

        # body with flutes (scallops cut into the rim between chambers), clipped to a circle
        size = cr * 2 + 8
        o = size // 2
        cyl = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(cyl, STEEL_LIGHT, (o, o), cr + 3)
        pygame.draw.circle(cyl, STEEL, (o, o), cr)
        for i in range(n):
            a = rot + (i + 0.5) * math.tau / n
            fx, fy = int(o + math.cos(a) * (cr + 8)), int(o + math.sin(a) * (cr + 8))
            pygame.draw.circle(cyl, STEEL_LIGHT, (fx, fy), 24)
            pygame.draw.circle(cyl, (0, 0, 0, 0), (fx, fy), 22)
        if not hasattr(self, "_cyl_mask"):
            self._cyl_mask = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(self._cyl_mask, (255, 255, 255, 255), (o, o), cr + 3)
        cyl.blit(self._cyl_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        scr.blit(cyl, (cx - o, cy - o))

        # chambers
        for i in range(n):
            a = rot + i * math.tau / n
            px, py = int(cx + math.cos(a) * self.CHAMBER_DIST), int(cy + math.sin(a) * self.CHAMBER_DIST)
            pygame.draw.circle(scr, STEEL_DARK, (px, py), self.CHAMBER_R + 3)
            if i < self.loaded:
                pop = 1.0
                if self.pop_at[i] is not None:
                    t = clamp01((now - self.pop_at[i]) / 220)
                    pop = 1.0 + 0.28 * (1 - ease_out(t))
                    if t < 1:
                        _glow(scr, (px, py), int(40 * (1 - t)) + 4, (255, 196, 110))
                r = int(self.CHAMBER_R * 0.92 * pop)
                pygame.draw.circle(scr, BRASS, (px, py), r)
                pygame.draw.circle(scr, BRASS_LIGHT, (px, py), int(r * 0.78))
                pygame.draw.circle(scr, BRASS, (px, py), int(r * 0.78), 2)
                pygame.draw.circle(scr, (150, 98, 40), (px, py), int(r * 0.38) + 1)
                pygame.draw.circle(scr, PRIMER, (px, py), int(r * 0.38))
                pygame.draw.circle(scr, (255, 246, 220), (px - int(r * 0.32), py - int(r * 0.32)), max(1, r // 6))
            else:
                pygame.draw.circle(scr, (8, 3, 2), (px, py), self.CHAMBER_R)
                pygame.draw.circle(scr, (70, 44, 30), (px, py), self.CHAMBER_R, 2)
                pygame.draw.circle(scr, (20, 9, 6), (px, py), self.CHAMBER_R - 6)

        # centre pin and ratchet
        pygame.draw.circle(scr, STEEL_DARK, (cx, cy), 20)
        pygame.draw.circle(scr, STEEL_LIGHT, (cx, cy), 20, 2)
        for i in range(n):
            a = rot + i * math.tau / n
            pygame.draw.line(scr, STEEL_LIGHT, (cx + math.cos(a) * 8, cy + math.sin(a) * 8),
                             (cx + math.cos(a) * 15, cy + math.sin(a) * 15), 2)
        pygame.draw.circle(scr, (120, 82, 56), (cx, cy), 6)

        # the frame's sight notch: the chamber under it is the next to load
        pygame.draw.polygon(scr, EMBER, [(cx - 9, cy - cr - 20), (cx + 9, cy - cr - 20), (cx, cy - cr - 7)])

        # chamber count (replaced by LOADED once full)
        if self.finished_at is not None:
            return
        count = self.text.plain(self.f_small, f"{self.loaded} / {n}", BONE_DIM)
        scr.blit(count, count.get_rect(center=(cx, cy + cr + 26)))

    def _draw_fuse(self, scr, now):
        x0, x1, y = self.FUSE_X0, self.FUSE_X1, self.FUSE_Y
        fx = int(x0 + (x1 - x0) * self.shown)
        # burned ash behind the spark
        if fx > x0:
            pygame.draw.line(scr, (52, 30, 22), (x0, y), (fx, y), 2)
        # unburned twisted cord ahead of it
        if fx < x1:
            pygame.draw.line(scr, (138, 104, 70), (fx, y), (x1, y), 4)
            for x in range(fx + 3, x1, 6):
                pygame.draw.line(scr, (88, 62, 40), (x, y - 2), (x + 3, y + 2), 1)
        pygame.draw.circle(scr, (52, 30, 22), (x0, y), 3)
        pygame.draw.circle(scr, (138, 104, 70) if self.shown < 1 else (52, 30, 22), (x1, y), 3)

        layer = self._layer
        layer.fill((0, 0, 0, 0))
        for s in self.sparks:
            k = 1 - s[4] / s[5]
            pygame.draw.circle(layer, (255, int(170 + 70 * k), 90, int(255 * k)), (int(s[0]), int(s[1])), 1 + int(k * 1.5))
        scr.blit(layer, (0, 0))
        if self.shown < 1.0:
            flicker = 0.8 + 0.2 * math.sin(now * 0.05)
            _glow(scr, (fx, y), int(18 * flicker), EMBER)
            _glow(scr, (fx, y), int(8 * flicker), SUN)
            pygame.draw.circle(scr, (255, 250, 220), (fx, y), 2)

        pct = self.text.plain(self.f_small, f"{int(self.shown * 100):3d}%", BONE_DIM)
        scr.blit(pct, pct.get_rect(midleft=(x1 + 14, y)))

    # ------------------------------------------------------------ loop
    async def run(self, clock):
        """Returns True when loading finished, False if the player closed the window.
        Async so the same loop runs in a web browser (pygbag) and on the desktop."""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and not IS_WEB:
                        return False
                    if event.key == pygame.K_m:
                        self.sounds.toggle()
                    else:
                        self.request_skip()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.request_skip()
            now = pygame.time.get_ticks()
            self.update(now)
            self.draw(now)
            pygame.display.flip()
            clock.tick(FPS)
            await asyncio.sleep(0)
            if self.complete(now):
                return True


