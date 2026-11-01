"""Dry Creek Duel: a quick-draw reaction game.
Made and designed by Soham Pawar. (c) 2026 Soham Pawar. All rights reserved.

Wait for the bell, then draw. Move early and you are dead. Beat five gunslingers
before your three bullets run out.

Launch shows a loading screen (which preloads every arena), then the main menu.
Controls: Space / Enter / click draws. L or [ ] changes arena. M toggles sound.
Esc or P pauses a duel. F11 toggles fullscreen on the desktop.

The main loop is async so the same code runs on the desktop and in a web browser
(itch.io, packaged with pygbag).
"""
import asyncio
import logging
import math
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

import pygame

from config import (
    BONE, BONE_DIM, EMBER, ENEMIES, ENEMY_VARIATION_PCT,
    ENEMY_X, FPS, H, HUD_H, INK, LINE, LIVES, MIN_ENEMY_MS,
    MIN_REACTION_MS, PACE_MS, PANEL, PLAYER_X, SCREEN, SUN, W,
    WAIT_RANGE_MS, calculate_enemy_reaction_time,
    ARENAS, AUTHOR, GAME_TITLE, IS_WEB, RES_ROOT, VERSION, get_arena, get_arena_for_duel
)
from scene import (
    Ambient, draw_cowboy, get_backdrop, get_vignette, get_muzzle_pos, SmokeSystem
)
from loading import LoadingScreen
from menu import MainMenu, PauseMenu
from sound import Sounds
from storage import SAVE_PATH, load_save_data, save_save_data  # noqa: F401  (SAVE_PATH is used by tests)
from ui import build_icon

ROOT = RES_ROOT
PAUSE_BUTTON = pygame.Rect(W - 46, 12, 32, 32)   # clickable pause button during a duel
DEFAULT_VOLUME = 10                            # volumes run 0..10


# ---------------------------------------------------------------- save file

def load_best() -> Optional[int]:
    value = load_save_data().get("best_ms", 0)
    try:
        val_int = int(value)
        return val_int if val_int > 0 else None
    except (ValueError, TypeError):
        return None


def save_best(ms: int) -> None:
    save_save_data({"best_ms": ms})


def load_best_bounty() -> int:
    try:
        return max(0, int(load_save_data().get("best_bounty", 0)))
    except (ValueError, TypeError):
        return 0


def rate(ms: int) -> str:
    if ms <= 190:
        return "Faster than a rattler"
    if ms <= 240:
        return "Quick draw"
    if ms <= 300:
        return "Steady hand"
    if ms <= 400:
        return "Greenhorn"
    return "Slow as molasses"


# ---------------------------------------------------------------- camera shake
class CameraShake:
    """Decaying trauma-based screen shake for punchy gunshots and thunder."""
    def __init__(self):
        self.trauma = 0.0
        self.time = 0.0

    def add(self, amount=0.65):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt_ms):
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - dt_ms * 0.0024)
            self.time += dt_ms * 0.001

    def get_offset(self):
        if self.trauma <= 0.001:
            return 0, 0
        shake = self.trauma * self.trauma
        max_x = 6.0 * shake
        max_y = 4.5 * shake
        ox = max_x * (math.sin(self.time * 70) + 0.5 * math.sin(self.time * 115))
        oy = max_y * (math.cos(self.time * 80) + 0.5 * math.cos(self.time * 130))
        return int(round(ox)), int(round(oy))


# ---------------------------------------------------------------- round data
@dataclass
class Side:
    arm_at: Optional[float] = None      # when the gun arm starts to rise
    shot_at: Optional[float] = None     # when the shot goes off, None if it never fires
    died_at: Optional[float] = None     # when this side starts to fall
    sounded: bool = False
    smoked: bool = False


@dataclass
class Round:
    enemy: object
    enemy_ms: int
    pace_end: float
    cue_at: float
    cue_ts: Optional[float] = None
    p: Side = field(default_factory=Side)
    e: Side = field(default_factory=Side)
    resolved: bool = False
    shown: bool = False
    show_at: float = 0
    outcome: Optional[str] = None       # win | lose | foul | slow
    player_ms: Optional[int] = None


# ---------------------------------------------------------------- game
class Game:
    def __init__(self, screen: pygame.Surface, sounds: Optional[Sounds] = None, fullscreen: bool = False):
        self.screen = screen
        self.scene = pygame.Surface((W, H))

        # Save data: unlocked arenas & selection
        save_data = load_save_data()
        saved_unlocked = save_data.get("unlocked_arenas", ["desert"])
        self.unlocked_arenas = set(saved_unlocked)
        self.unlocked_arenas.add("desert")  # signature desert always unlocked
        self.selected_arena = save_data.get("selected_arena", "auto")

        self.duel = 0
        self.current_arena_id = self._resolve_arena_id()

        self.backdrop = get_backdrop(self.current_arena_id)
        current_arena = get_arena(self.current_arena_id)
        self.vignette = get_vignette(current_arena.vignette_tint)
        self.vignette_pulse = self.vignette.copy()
        self.ambient = Ambient(self.current_arena_id)
        self.sounds = sounds or Sounds()
        if save_data.get("sound") is False and self.sounds.enabled:
            self.sounds.toggle()
        self.volumes = {name: self._saved_volume(save_data, name) for name in ("sfx", "ambience")}
        self._apply_volumes()
        self.fullscreen = fullscreen
        self.sounds.set_arena(self.current_arena_id)

        self.smoke = SmokeSystem()
        self.camera_shake = CameraShake()
        self.newly_unlocked = None

        self.display_font = self._load_font("Rye-Regular.ttf")
        self.f_title = self._font(34, display=True)
        self.f_head = self._font(30, display=True)
        self.f_big = self._font(112, display=True)
        self.f_mid = self._font(84, display=True)
        self.f_ui = pygame.font.Font(None, 28)
        self.f_small = pygame.font.Font(None, 22)
        self.f_num = pygame.font.Font(None, 44)
        self._text_cache = {}

        self.best = load_best()
        self.best_bounty = load_best_bounty()
        self.phase = "title"            # title (main menu) | pace | ready | draw | result
        self.round: Optional[Round] = None
        self.reset_run()
        self.after = "next"
        self.card = None
        self.last_now = 0.0
        self.running = True
        self.fade_in_at: Optional[float] = None   # brief fade from black after leaving the menu

        # Pausing freezes the game clock: game time = real time - pause_offset.
        self.paused = False
        self.pause_offset = 0.0
        self.paused_real = 0.0

        self.menu = MainMenu(self)
        self.menu.enter(0)
        self.pause_menu = PauseMenu(self)

    # fonts: Rye is used when assets/fonts/Rye-Regular.ttf exists, otherwise the built-in face
    def _load_font(self, name):
        path = ROOT / "assets" / "fonts" / name
        return path if path.is_file() else None

    def _font(self, size, display=False):
        if display and self.display_font:
            try:
                return pygame.font.Font(str(self.display_font), size)
            except (OSError, pygame.error):
                pass
        return pygame.font.Font(None, int(size * (1.25 if display else 1)))

    def _resolve_arena_id(self) -> str:
        """Return the active arena ID based on player choice or campaign round."""
        if self.selected_arena != "auto" and self.selected_arena in self.unlocked_arenas:
            return self.selected_arena
        return get_arena_for_duel(self.duel).id

    def apply_arena(self, arena_id: str):
        """Update backdrop, atmosphere, vignette, and ambient sound to match arena."""
        self.current_arena_id = arena_id
        self.backdrop = get_backdrop(arena_id)
        arena = get_arena(arena_id)
        self.vignette = get_vignette(arena.vignette_tint)
        self.vignette_pulse = self.vignette.copy()
        self.ambient.set_arena(arena_id)
        self.sounds.set_arena(arena_id)

    def cycle_arena(self, delta: int = 1):
        """Cycle between AUTO (tour) and all currently unlocked arenas."""
        options = ["auto"] + [a.id for a in ARENAS if a.id in self.unlocked_arenas]
        cur_idx = options.index(self.selected_arena) if self.selected_arena in options else 0
        new_idx = (cur_idx + delta) % len(options)
        self.selected_arena = options[new_idx]
        save_save_data({"selected_arena": self.selected_arena})
        self.apply_arena(self._resolve_arena_id())

    def toggle_sound(self):
        enabled = self.sounds.toggle()
        save_save_data({"sound": enabled})
        return enabled

    def set_sound(self, on: bool):
        if bool(on) != self.sounds.enabled:
            self.toggle_sound()

    # ------------------------------------------------------------ settings
    @staticmethod
    def _saved_volume(save_data, name):
        try:
            return max(0, min(10, int(save_data.get(f"{name}_volume", DEFAULT_VOLUME))))
        except (ValueError, TypeError):
            return DEFAULT_VOLUME

    def _apply_volumes(self):
        self.sounds.set_volumes(sfx=self.volumes["sfx"] / 10, ambience=self.volumes["ambience"] / 10)

    def set_volume(self, name: str, value: int):
        self.volumes[name] = max(0, min(10, int(value)))
        self._apply_volumes()
        save_save_data({f"{name}_volume": self.volumes[name]})

    def set_fullscreen(self, on: bool):
        if IS_WEB:
            return                       # the browser page has its own fullscreen button
        on = bool(on)
        if on != self.fullscreen:
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error as e:
                logging.warning(f"toggle_fullscreen failed: {e}")
        self.fullscreen = on
        save_save_data({"fullscreen": on})

    def quit(self):
        logging.info("Quit chosen from a menu")
        self.running = False

    # ------------------------------------------------------------ pause & clock
    def clock(self, real: Optional[float] = None) -> float:
        """Game time in ms. It stands still while the game is paused."""
        real = pygame.time.get_ticks() if real is None else real
        return (self.paused_real if self.paused else real) - self.pause_offset

    def pause(self, real: Optional[float] = None):
        if self.paused or self.phase == "title":
            return
        real = pygame.time.get_ticks() if real is None else real
        self.paused = True
        self.paused_real = real
        self.pause_menu.open(real)

    def resume(self, real: Optional[float] = None):
        if not self.paused:
            return
        real = pygame.time.get_ticks() if real is None else real
        self.pause_offset += real - self.paused_real
        self.paused = False
        self.last_now = self.clock(real)

    def leave_to_menu(self):
        """Main Menu, from the pause menu."""
        self.resume()
        self.to_menu(self.clock())

    def reputation(self) -> str:
        return rate(self.best) if self.best else "Unknown drifter"

    def start_from_menu(self, now):
        """START DUEL on the main menu: begin the run with a short fade in.
        (The run is already fresh: the game starts reset, and to_menu resets it.)"""
        self.fade_in_at = now
        self.start_duel(now)

    def to_menu(self, now):
        """Leave the current duel (the run is abandoned) and return to the main menu."""
        self.reset_run()
        self.round = None
        self.card = None
        self.smoke.clear()
        self.phase = "title"
        self.apply_arena(self._resolve_arena_id())
        self.menu.enter(now)

    def reset_run(self):
        self.duel = 0
        self.lives = LIVES
        self.bounty = 0
        self.won = 0
        self.newly_unlocked = None

    @property
    def round_number(self) -> int:
        return self.duel + 1

    @round_number.setter
    def round_number(self, val: int):
        self.duel = max(0, val - 1)

    @property
    def enemy(self):
        return ENEMIES[self.duel]

    # ------------------------------------------------------------ flow
    def start_duel(self, now):
        self.last_now = now
        self.apply_arena(self._resolve_arena_id())
        self.smoke.clear()
        self.newly_unlocked = None

        en = self.enemy
        pace_end = now + PACE_MS
        enemy_ms = calculate_enemy_reaction_time(
            base_reaction_time=en.ms,
            round_number=self.round_number,
            min_ms=MIN_ENEMY_MS,
            variation_pct=ENEMY_VARIATION_PCT,
        )
        self.round = Round(
            enemy=en,
            enemy_ms=enemy_ms,
            pace_end=pace_end,
            cue_at=pace_end + random.uniform(*WAIT_RANGE_MS),
        )
        self.phase = "pace"
        self.card = None

    def finish(self, outcome):
        r = self.round
        self.phase = "result"
        r.resolved = True
        r.outcome = outcome
        if outcome == "win":
            self.bounty += r.enemy.bounty
            self.won += 1
            if self.bounty > self.best_bounty:
                self.best_bounty = self.bounty
                save_save_data({"best_bounty": self.best_bounty})
            if self.best is None or r.player_ms < self.best:
                self.best = r.player_ms
                save_best(self.best)
            self.after = "champion" if self.duel == len(ENEMIES) - 1 else "next"

            # Check if this win unlocks a new arena
            # Beating Pete (duel 0) -> unlocks Saloon (arena 1)
            # Beating Jane (duel 1) -> unlocks Railway (arena 2)
            # Beating Dan (duel 2) -> unlocks Ghost Town (arena 3)
            # Beating Bart (duel 3) -> unlocks Canyon Bridge (arena 4)
            # Beating Marshal (duel 4) -> unlocks Rain-soaked Street (arena 5)
            unlock_idx = self.duel + 1
            if unlock_idx < len(ARENAS):
                candidate = ARENAS[unlock_idx]
                if candidate.id not in self.unlocked_arenas:
                    self.unlocked_arenas.add(candidate.id)
                    self.newly_unlocked = candidate
                    save_save_data({"unlocked_arenas": list(self.unlocked_arenas)})
        else:
            self.lives -= 1
            self.after = "over" if self.lives <= 0 else "retry"
        r.show_at = max(r.p.shot_at or 0, r.e.shot_at or 0) + 1150

    def press(self, reaction):
        r = self.round
        t0, e = r.cue_ts, r.enemy_ms
        r.player_ms = round(reaction)
        r.p.arm_at, r.e.arm_at = t0 + reaction, t0 + e
        if reaction < e:
            r.p.shot_at = t0 + reaction + 80
            r.e.died_at = r.p.shot_at + 70
            if r.e.arm_at >= r.e.died_at:
                r.e.arm_at = None
            self.finish("win")
        else:
            r.e.shot_at = t0 + e + 80
            r.p.died_at = r.e.shot_at + 70
            if r.p.arm_at >= r.p.died_at:
                r.p.arm_at = None
            self.finish("lose")

    def foul(self, ts):
        r = self.round
        r.p.arm_at, r.e.arm_at, r.e.shot_at, r.p.died_at = ts, ts + 220, ts + 300, ts + 370
        self.finish("foul")

    def slow(self):
        r = self.round
        r.e.arm_at = r.cue_ts + r.enemy_ms
        r.e.shot_at = r.e.arm_at + 80
        r.p.died_at = r.e.shot_at + 70
        self.finish("slow")

    def next_step(self, now):
        if self.after == "next":
            self.duel += 1
        elif self.after in ("champion", "over"):
            self.reset_run()
        self.start_duel(now)

    def on_action(self, now):
        """The single input of the game. `now` is the time of the press in ms."""
        if self.phase == "title":
            self.menu.activate(now)
        elif self.phase == "result":
            if self.round and self.round.shown:
                self.next_step(now)
        elif self.phase == "ready":
            self.foul(now)
        elif self.phase == "draw":
            reaction = now - self.round.cue_ts
            if reaction < MIN_REACTION_MS:
                self.foul(now)
            else:
                self.press(reaction)

    # ------------------------------------------------------------ clock
    def update(self, now):
        dt = 0.0 if self.last_now == 0.0 else max(0.0, now - self.last_now)
        self.last_now = now
        r = self.round
        if dt > 300 and r and self.phase in ("pace", "ready", "draw"):
            frozen = min(dt, 2000.0)    # the window was frozen: protect player without infinite stall
            r.pace_end += frozen
            r.cue_at += frozen
            if r.cue_ts is not None:
                r.cue_ts += frozen

        # Camera shake and smoke particle simulation
        self.camera_shake.update(dt)
        current_wind = self.ambient.arena.wind_base
        self.smoke.update(dt, current_wind)

        if self.phase == "pace" and now >= r.pace_end:
            self.phase = "ready"
        if self.phase == "ready" and now >= r.cue_at:
            self.phase = "draw"
            r.cue_ts = r.cue_at
            self.sounds.bell()
        if self.phase == "draw" and now >= r.cue_ts + r.enemy_ms:
            self.slow()
        if r and r.resolved:
            # Gunshots, sound effects, muzzle flash, gunsmoke, and camera shake
            for side, key, x, d in ((r.p, "p", PLAYER_X, 1), (r.e, "e", ENEMY_X, -1)):
                if side.shot_at is not None and now >= side.shot_at:
                    if not side.sounded:
                        side.sounded = True
                        self.sounds.gunshot()
                        # Camera shake kick on gunshot
                        self.camera_shake.add(0.70)
                    if not side.smoked:
                        side.smoked = True
                        arm, fall, _, sway = self.pose(key, side.shot_at)
                        mx, my = get_muzzle_pos(x, d, arm, fall, sway)
                        self.smoke.spawn(mx, my, d, current_wind)

            if not r.shown and now >= r.show_at:
                r.shown = True
                self.card = self.build_card()

    # ------------------------------------------------------------ result card
    def build_card(self):
        r, en = self.round, self.round.enemy
        left = f"{self.lives} bullet{'s' if self.lives != 1 else ''} left."
        unlock_line = [(f"★ NEW ARENA UNLOCKED: {self.newly_unlocked.name.upper()}!", False)] if self.newly_unlocked else []

        if self.after == "champion":
            return dict(head="Marshal of Dry Creek",
                        times=[("Your draw", f"{r.player_ms} ms", True), ("Bounty", f"${self.bounty}", False)],
                        lines=[(f"All five gunslingers are down. {rate(self.best)}.", False)] + unlock_line)
        if self.after == "over":
            why = ("You drew before the bell." if r.outcome == "foul" else
                   f"{en.short} drew before you moved." if r.outcome == "slow" else
                   f"{en.short} drew in {r.enemy_ms} ms.")
            return dict(head="Boot Hill",
                        lines=[(f"{self.won} of {len(ENEMIES)} gunslingers beaten. Bounty ${self.bounty}.", False), (why, True)])
        if r.outcome == "win":
            return dict(head=f"{en.name} is down",
                        times=[("You", f"{r.player_ms} ms", True), (en.short, f"{r.enemy_ms} ms", False)],
                        lines=[(f"{rate(r.player_ms)}. +${en.bounty} bounty.", False)] + unlock_line)
        if r.outcome == "foul":
            return dict(head="Too early", lines=[("You drew before the bell. Wait for it.", False), (left, True)])
        if r.outcome == "slow":
            return dict(head="Too slow", lines=[(f"{en.short} drew in {r.enemy_ms} ms and you never pulled.", False), (left, True)])
        return dict(head=f"{en.short} was faster",
                    times=[("You", f"{r.player_ms} ms", True), (en.short, f"{r.enemy_ms} ms", False)],
                    lines=[(left, True)])

    # ------------------------------------------------------------ drawing
    def pose(self, key, now):
        r = self.round
        ten = 0.0
        if self.phase == "ready" and r:
            ten = max(0.0, min(1.0, (now - r.pace_end) / max(1, r.cue_at - r.pace_end)))
        arm = 0.2 + ten * 0.12
        if self.phase == "ready":
            arm += math.sin(now / 70 + (2 if key == "e" else 0)) * 0.018 * ten
        sway = math.sin(now / 1100 + (1.7 if key == "e" else 0)) * 0.01
        fall = flash = 0.0
        if r and r.resolved:
            s = r.p if key == "p" else r.e
            if s.arm_at is not None and now >= s.arm_at:
                t = max(0.0, min(1.0, (now - s.arm_at) / 90))
                arm += (1.55 - arm) * (t * t * (3 - 2 * t))
            if s.shot_at is not None and now >= s.shot_at:
                t = now - s.shot_at
                flash = 1 - t / 130 if t < 130 else 0.0
                if t < 120:
                    arm += 0.18 * (1 - t / 120)
            if s.died_at is not None and now >= s.died_at:
                t = max(0.0, min(1.0, (now - s.died_at) / 650))
                fall = t * t * (3 - 2 * t)
                arm += (0.4 - arm) * fall
                sway = 0.0
        return arm, fall, flash, sway

    def outlined(self, font, text, fill, outline, width, key=None):
        key = key or (id(font), text, fill, outline, width)
        surf = self._text_cache.get(key)
        if surf is None:
            body = font.render(text, True, fill)
            edge = font.render(text, True, outline)
            surf = pygame.Surface((body.get_width() + width * 2, body.get_height() + width * 2), pygame.SRCALPHA)
            for dx in range(-width, width + 1):
                for dy in range(-width, width + 1):
                    if dx * dx + dy * dy <= width * width:
                        surf.blit(edge, (width + dx, width + dy))
            surf.blit(body, (width, width))
            self._text_cache[key] = surf
        return surf

    def render(self, now):
        if self.phase == "title":
            self.menu.draw(self.screen, now)
            return
        sc = self.scene
        r = self.round
        # Draw backdrop and atmospheric windblown dust/rain/tumbleweeds
        sc.blit(self.backdrop, (0, 0))
        self.ambient.draw(sc, now)

        # Draw gunslingers
        en = self.enemy
        arena = get_arena(self.current_arena_id)
        for key, x, d, accent, star in (("e", ENEMY_X, -1, en.accent, en.star), ("p", PLAYER_X, 1, EMBER, False)):
            arm, fall, flash, sway = self.pose(key, now)
            draw_cowboy(sc, x, d, arm, fall, flash, sway, accent, star, rim_tint=arena.cowboy_tint)

        # Draw gunsmoke billowing from revolvers
        self.smoke.draw(sc)

        if self.phase == "draw" and r:
            t = now - r.cue_ts
            text = self.outlined(self.f_big, "DRAW!", SUN, INK, 6)
            scale = 1 + 0.25 * max(0.0, 1 - t / 160)
            if scale > 1.001:
                text = pygame.transform.smoothscale(text, (int(text.get_width() * scale), int(text.get_height() * scale)))
            sc.blit(text, text.get_rect(center=(W // 2, 150)))
            if t < 220:
                flash = pygame.Surface((W, H), pygame.SRCALPHA)
                flash.fill((255, 214, 150, int(255 * 0.5 * (1 - t / 220))))
                sc.blit(flash, (0, 0))
        if self.phase == "result" and r and r.outcome == "foul" and not r.shown:
            text = self.outlined(self.f_mid, "TOO EARLY", EMBER, INK, 5)
            sc.blit(text, text.get_rect(center=(W // 2, 150)))

        sc.blit(self.vignette, (0, 0))
        if self.phase == "ready" and r:
            pulse = 0.14 * (0.5 + 0.5 * math.sin(now / 260)) * max(0.0, min(1.0, (now - r.pace_end) / 2500))
            self.vignette_pulse.set_alpha(int(255 * pulse * 2))
            sc.blit(self.vignette_pulse, (0, 0))

        # Dynamic screen shake offset
        dx, dy = self.camera_shake.get_offset()
        self.screen.fill(INK)
        self.screen.blit(sc, (dx, dy))
        self.draw_card()
        self.draw_hud()
        if not self.paused:
            self.draw_pause_button()

        if self.fade_in_at is not None:
            k = (now - self.fade_in_at) / 450
            if k >= 1:
                self.fade_in_at = None
            else:
                veil = pygame.Surface(SCREEN)
                veil.fill(INK)
                veil.set_alpha(int(255 * (1 - max(0.0, k)) ** 2))
                self.screen.blit(veil, (0, 0))

    def draw_pause_button(self):
        b = PAUSE_BUTTON
        hover = b.collidepoint(pygame.mouse.get_pos()) if pygame.mouse.get_focused() else False
        surf = pygame.Surface(b.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*PANEL, 230 if hover else 170), surf.get_rect(), border_radius=5)
        pygame.draw.rect(surf, LINE, surf.get_rect(), 1, border_radius=5)
        color = SUN if hover else BONE_DIM
        pygame.draw.rect(surf, color, (10, 9, 4, 14), border_radius=1)
        pygame.draw.rect(surf, color, (18, 9, 4, 14), border_radius=1)
        self.screen.blit(surf, b.topleft)

    def draw_card(self):
        card = self.card
        if not card:
            return
        width = 460
        pad = 18
        y = pad + 6
        rows = []   # (surface, gap_after)
        rows.append((self.f_head.render(card["head"], True, SUN), 8))
        if "times" in card:
            rows.append((None, 0))      # placeholder for the times row
        for text, dim in card.get("lines", []):
            for line in self._wrap(text, self.f_ui, width - pad * 2):
                color = SUN if "★ NEW ARENA" in line else (BONE_DIM if dim else BONE)
                rows.append((self.f_ui.render(line, True, color), 4))

        height = pad * 2 + sum((s.get_height() if s else 56) + gap for s, gap in rows) - 4
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, 232), panel.get_rect(), border_radius=4)
        pygame.draw.rect(panel, LINE, panel.get_rect(), 1, border_radius=4)
        cy = pad
        for surf, gap in rows:
            if surf is None:
                x = pad
                times: list[tuple[str, str, bool]] = card["times"]
                for label, value, you in times:
                    lab = self.f_small.render(label.upper(), True, BONE_DIM)
                    val = self.f_num.render(value, True, SUN if you else BONE)
                    panel.blit(lab, (x, cy))
                    panel.blit(val, (x, cy + 18))
                    x += max(lab.get_width(), val.get_width()) + 30
                cy += 56
            else:
                panel.blit(surf, (pad, cy))
                cy += surf.get_height() + gap
        self.screen.blit(panel, ((W - width) // 2, y))

    @staticmethod
    def _wrap(text, font, max_width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if font.size(trial)[0] <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def prompt(self):
        if self.phase == "title":
            return "Press SPACE or click to step up", "go"
        if self.phase in ("pace", "ready"):
            return "Wait for the bell...", "wait"
        if self.phase == "draw":
            return "DRAW!", "draw"
        if self.round and self.round.shown:
            return {"next": "SPACE: next duel", "retry": "SPACE: rematch",
                    "over": "SPACE: try again", "champion": "SPACE: ride again"}[self.after], "go"
        return "", "wait"

    def draw_hud(self):
        top = H
        pygame.draw.rect(self.screen, PANEL, (0, top, W, HUD_H))
        pygame.draw.line(self.screen, LINE, (0, top), (W, top), 2)

        cur_arena = get_arena(self.current_arena_id)
        mode_note = " (Auto)" if self.selected_arena == "auto" else ""
        stats = [
            ("Duel", f"{self.duel + 1} / {len(ENEMIES)}"),
            ("Opponent", self.enemy.name),
            ("Arena", f"{cur_arena.name}{mode_note}"),
            ("Bounty", f"${self.bounty}"),
            ("Fastest draw", f"{self.best} ms" if self.best else "none yet")
        ]
        x = 20
        for label, value in stats:
            lab = self.f_small.render(label.upper(), True, BONE_DIM)
            val = self.f_ui.render(value, True, BONE)
            self.screen.blit(lab, (x, top + 12))
            self.screen.blit(val, (x, top + 32))
            x += max(lab.get_width(), val.get_width(), 95) + 20

        lab = self.f_small.render("BULLETS", True, BONE_DIM)
        bx = W - 20 - 3 * 22
        self.screen.blit(lab, (bx, top + 12))
        for i in range(3):
            rect = pygame.Rect(bx + i * 22, top + 34, 14, 22)
            if i < self.lives:
                pygame.draw.rect(self.screen, SUN, rect, border_radius=6)
            else:
                pygame.draw.rect(self.screen, LINE, rect, 2, border_radius=6)

        text, mode = self.prompt()
        if text:
            color = {"go": EMBER, "wait": BONE_DIM, "draw": SUN}[mode]
            surf = self.f_ui.render(text.upper(), True, color)
            self.screen.blit(surf, surf.get_rect(center=(W // 2, top + HUD_H - 18)))

        # Bottom control hints
        controls = "M: sound " + ("on" if self.sounds.enabled else "off") + "  |  L: arena  |  P: pause"
        mute = self.f_small.render(controls, True, BONE_DIM)
        self.screen.blit(mute, (20, top + HUD_H - 22))

    # ------------------------------------------------------------ main loop
    def handle(self, event):
        real = pygame.time.get_ticks()
        now = self.clock(real)
        if event.type == pygame.QUIT:
            logging.info(f"Exiting due to QUIT event: {event}")
            self.running = False
            return
        if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
            self.pause(real)            # never lose a duel because you switched windows
            return
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key == pygame.K_m:
                self.toggle_sound()
            elif key == pygame.K_F11:
                self.set_fullscreen(not self.fullscreen)
            elif self.paused:
                if key in (pygame.K_ESCAPE, pygame.K_p):
                    if not self.pause_menu.back():
                        self.resume(real)
                else:
                    self.pause_menu.handle_key(key, real)
            elif self.phase == "title":
                if key == pygame.K_ESCAPE:
                    if not self.menu.back() and not IS_WEB:
                        logging.info("Exiting due to ESC key on the main menu")
                        self.running = False
                elif self.menu.handle_key(key, now):
                    pass
                elif key in (pygame.K_l, pygame.K_RIGHTBRACKET):
                    self.cycle_arena(1)
                elif key == pygame.K_LEFTBRACKET:
                    self.cycle_arena(-1)
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.pause(real)
            elif key in (pygame.K_l, pygame.K_RIGHTBRACKET):
                self.cycle_arena(1)
            elif key == pygame.K_LEFTBRACKET:
                self.cycle_arena(-1)
            elif key == pygame.K_LEFT and self.phase == "result":
                self.cycle_arena(-1)
            elif key == pygame.K_RIGHT and self.phase == "result":
                self.cycle_arena(1)
            elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and not event.mod & pygame.KMOD_ALT:
                self.on_action(now)
        elif event.type == pygame.MOUSEMOTION:
            if self.paused:
                self.pause_menu.hover(event.pos)
            elif self.phase == "title":
                self.menu.hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.paused:
                self.pause_menu.click(event.pos, real)
            elif self.phase == "title":
                self.menu.click(event.pos, now)
            elif PAUSE_BUTTON.collidepoint(event.pos):
                self.pause(real)
            else:
                self.on_action(now)

    def frame(self, real: float):
        """One frame: advance the duel (unless paused) and draw everything."""
        now = self.clock(real)
        if not self.paused:
            self.update(now)
        self.render(now)
        if self.paused:
            self.pause_menu.draw(self.screen, real)

    async def run(self):
        clock = pygame.time.Clock()
        frame = 0
        while self.running:
            for event in pygame.event.get():
                self.handle(event)
            self.frame(pygame.time.get_ticks())
            pygame.display.flip()
            clock.tick(FPS)
            await asyncio.sleep(0)       # lets the browser breathe; a no-op on the desktop
            frame += 1
            if frame == 1:
                logging.info(f"First frame rendered successfully at ticks={pygame.time.get_ticks()}")


def setup_logging():
    if IS_WEB:
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
        return
    try:
        logging.basicConfig(filename="game.log", filemode="w", level=logging.INFO,
                            format="%(asctime)s [%(levelname)s] %(message)s")
    except OSError:                       # e.g. the .exe sits in a read-only folder
        logging.basicConfig(level=logging.WARNING)


def open_window(fullscreen: bool) -> pygame.Surface:
    if IS_WEB:
        return pygame.display.set_mode(SCREEN)
    flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if fullscreen else 0)
    try:
        return pygame.display.set_mode(SCREEN, flags, vsync=1)
    except pygame.error as e:
        logging.warning(f"Failed with vsync: {e}, falling back")
        return pygame.display.set_mode(SCREEN, flags)


async def main():
    setup_logging()
    logging.info(f"{GAME_TITLE} v{VERSION} by {AUTHOR} starting (platform: {sys.platform})")
    font_ok = (RES_ROOT / "assets" / "fonts" / "Rye-Regular.ttf").is_file()
    sounds_found = len(list((RES_ROOT / "assets" / "sounds").glob("*.ogg")))
    logging.info(f"assets at {RES_ROOT}: display font {'found' if font_ok else 'MISSING'}, {sounds_found} sound files")
    pygame.init()
    pygame.display.set_caption(f"{GAME_TITLE} - made and designed by {AUTHOR}")
    try:
        pygame.display.set_icon(build_icon(64))
    except pygame.error:
        pass
    save = load_save_data()
    fullscreen = bool(save.get("fullscreen")) and not IS_WEB
    screen = open_window(fullscreen)
    logging.info("display mode set successfully")
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = pygame.display.get_wm_info().get("window")
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            logging.warning(f"SetForegroundWindow failed: {e}")

    sounds = Sounds()
    if save.get("sound") is False:
        sounds.toggle()
    logging.info("Loading assets")
    if not await LoadingScreen(screen, sounds).run(pygame.time.Clock()):
        logging.info("Closed during loading")
        pygame.quit()
        return
    logging.info("Entering Game.run()")
    await Game(screen, sounds, fullscreen=fullscreen).run()
    logging.info("Game.run() ended")
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

