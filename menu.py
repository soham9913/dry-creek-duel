"""Menus: the main menu (title screen), the pause menu, and their sub-screens
(Settings, How to Play, Credits).

Every list of options is a ui.OptionPanel, so all menus look and behave the same:
arrow keys or mouse to choose, Enter or click to pick, Left / Right to change a value.
"""
import math

import pygame

from config import (
    ARENAS, AUTHOR, BONE, COPYRIGHT, CREDIT_LINE, BONE_DIM, EMBER, ENEMIES, ENEMY_X, GAME_TITLE, H, HUD_H, INK,
    IS_WEB, LEATHER, LINE, PANEL, PLAYER_X, RUST, SCREEN, SUN, VERSION, W, get_arena,
)
from scene import draw_cowboy, get_backdrop, get_vignette
from ui import (FULL_H, OptionPanel, Row, TextCache, clamp01, draw_ornament_rule, draw_sign,
                ease_in_out, ease_out, edge_vignette, load_font, wrap)

ARENA_SHORT = {
    "desert": "Sunset Desert",
    "saloon": "Main Street",
    "railway": "Railway Depot",
    "ghost_town": "Ghost Town",
    "canyon": "Canyon Bridge",
    "rain": "Rain-Soaked Street",
}
RULES = (
    "Step up and wait. The bell rings after a random 1.6 to 4.8 seconds.",
    "When DRAW! appears, press SPACE, ENTER or click as fast as you can.",
    "Move before the bell, or within 100 ms of it, and it's a false start.",
    "Beat their draw time to win the bounty. Lose and you spend a bullet.",
    "Win all five duels on three bullets to become Marshal of Dry Creek.",
)
CREDITS = (
    ("Made & designed by", AUTHOR),
    ("Lettering", "Rye by Nicole Fally, SIL Open Font License"),
    ("Built with", "Python and Pygame"),
    ("Art & sound", "Every picture and every sound is generated in code"),
)


def veil(screen, alpha):
    v = pygame.Surface(SCREEN, pygame.SRCALPHA)
    v.fill((*INK, int(alpha)))
    screen.blit(v, (0, 0))


# ---------------------------------------------------------------- shared pieces
def settings_rows(game, on_back):
    """Settings used by both the main menu and the pause menu."""
    def volume(name):
        return Row(name, "Effects" if name == "sfx" else "Ambience", "slider",
                   get=lambda: game.volumes[name], set=lambda v: game.set_volume(name, v),
                   hint=("The bell, the gunshots and the menu clicks." if name == "sfx"
                         else "Wind, rain, steam trains and saloon creaks."))

    return [
        Row("fullscreen", "Fullscreen", "toggle", get=lambda: game.fullscreen, set=game.set_fullscreen,
            disabled_text=(lambda: "USE PAGE BUTTON") if IS_WEB else None,
            hint=("In the browser, use the fullscreen button on the page." if IS_WEB
                  else "Fill the whole screen. F11 works anywhere.")),
        Row("sound", "Sound", "toggle", get=lambda: game.sounds.enabled, set=game.set_sound,
            hint="Every sound on or off. M works anywhere."),
        volume("sfx"),
        volume("ambience"),
        Row("back", "Back", action=lambda now: on_back(), hint="Back to the previous screen."),
    ]


class InfoCard:
    """How to Play and Credits: a sign of text that any key or click closes."""

    def __init__(self, kind):
        self.kind = kind
        self.text = TextCache()
        self.f_head = load_font(30, display=True)
        self.f_body = load_font(22)
        self.f_small = load_font(21)
        self.f_big = load_font(26)

    def draw(self, screen, now, opened_at):
        k = ease_out((now - opened_at) / 260)
        veil(screen, 205 * k)
        panel = self._howto() if self.kind == "howto" else self._credits()
        panel.set_alpha(int(255 * k))
        screen.blit(panel, panel.get_rect(center=(W // 2, FULL_H // 2 - 10 + int(16 * (1 - k)))))

    def _frame(self, width, height, title):
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        draw_sign(panel, panel.get_rect(), 252)
        head = self.text.plain(self.f_head, title, SUN)
        panel.blit(head, head.get_rect(midtop=(width // 2, 28)))
        y = 28 + head.get_height() + 8
        draw_ornament_rule(panel, width // 2, y, 160, LINE)
        return panel, y + 16

    def _footer(self, panel, y):
        foot = self.text.plain(self.f_small, "Press any key or click to return", EMBER)
        panel.blit(foot, foot.get_rect(midtop=(panel.get_width() // 2, y)))

    def _howto(self):
        width, pad = 680, 28
        body_w = width - pad * 2 - 34
        rows = [(str(n), wrap(rule, self.f_body, body_w)) for n, rule in enumerate(RULES, 1)]
        height = 28 + 46 + 16 + sum(len(r[1]) * 22 + 10 for r in rows) + 92 + pad
        panel, y = self._frame(width, height, "Rules of the Draw")
        for num, lines in rows:
            badge = pygame.Rect(pad, y + 1, 22, 20)
            pygame.draw.rect(panel, EMBER, badge, border_radius=3)
            ns = self.text.plain(self.f_small, num, INK)
            panel.blit(ns, ns.get_rect(center=badge.center))
            for ln in lines:
                panel.blit(self.text.plain(self.f_body, ln, BONE), (pad + 34, y + 2))
                y += 22
            y += 10
        y += 4
        lab = self.text.spaced(self.f_small, "WANTED", EMBER, 4)
        panel.blit(lab, lab.get_rect(midtop=(width // 2, y)))
        y += 24
        col_w = (width - pad * 2) // len(ENEMIES)
        for i, en in enumerate(ENEMIES):
            cx = pad + col_w * i + col_w // 2
            name = self.text.plain(self.f_small, en.name, BONE)
            info = self.text.plain(self.f_small, f"{en.ms} ms  ${en.bounty}", BONE_DIM)
            pygame.draw.rect(panel, en.accent, (cx - 12, y, 24, 3))
            panel.blit(name, name.get_rect(midtop=(cx, y + 8)))
            panel.blit(info, info.get_rect(midtop=(cx, y + 26)))
        self._footer(panel, y + 56)
        return panel

    def _credits(self):
        width = 560
        height = 28 + 46 + 16 + len(CREDITS) * 52 + 40 + 44
        panel, y = self._frame(width, height, "Credits")
        for label, value in CREDITS:
            lab = self.text.spaced(self.f_small, label.upper(), BONE_DIM, 2)
            val = self.text.plain(self.f_big if label == "Made & designed by" else self.f_body, value,
                                  SUN if label == "Made & designed by" else BONE)
            panel.blit(lab, lab.get_rect(midtop=(width // 2, y)))
            panel.blit(val, val.get_rect(midtop=(width // 2, y + 20)))
            y += 52
        thanks = self.text.plain(self.f_body, f"Thanks for playing, partner.  {GAME_TITLE} v{VERSION}", BONE_DIM)
        panel.blit(thanks, thanks.get_rect(midtop=(width // 2, y + 6)))
        self._footer(panel, y + 40)
        return panel


class SubScreens:
    """The Settings / How to Play / Credits screens that open on top of a menu."""

    def __init__(self, game):
        self.g = game
        self.name = None                # None | "settings" | "howto" | "credits"
        self.opened_at = 0
        self.settings = OptionPanel(settings_rows(game, self.close), width=440, title="Settings", sign_alpha=250,
                                    on_tick=game.sounds.tick, on_click=game.sounds.click)
        self.cards = {"howto": InfoCard("howto"), "credits": InfoCard("credits")}

    def open(self, name, now):
        self.name, self.opened_at = name, now
        if name == "settings":
            self.settings.index = 0
            self.settings.hl_y = None

    def close(self):
        self.name = None

    def handle_key(self, key, now):
        if self.name == "settings":
            return self.settings.handle_key(key, now)
        if key == pygame.K_m:
            return False
        self.close()                    # info cards: any other key closes
        return True

    def hover(self, pos):
        if self.name == "settings":
            self.settings.hover(pos)

    def click(self, pos, now):
        if self.name == "settings":
            self.settings.click(pos, now)
        else:
            self.close()

    def draw(self, screen, now):
        if self.name == "settings":
            k = ease_out((now - self.opened_at) / 260)
            veil(screen, 215 * k)
            self.settings.place(W // 2, center_y=FULL_H // 2 - 10)
            self.settings.draw(screen, now, int(255 * k), int(16 * (1 - k)))
        elif self.name in self.cards:
            self.cards[self.name].draw(screen, now, self.opened_at)


# ---------------------------------------------------------------- main menu
class MainMenu:
    """The title screen. Owned by Game; drawn and driven while game.phase == 'title'."""

    TOP = 234

    def __init__(self, game):
        self.g = game
        self.text = TextCache()
        self.f_kicker = load_font(30, display=True)
        self.f_logo = load_font(104, display=True)
        self.f_small = load_font(21)
        self.f_stat = load_font(27)

        self.panel = OptionPanel([
            Row("start", "Start Duel", action=game.start_from_menu,
                hint="Five gunslingers. Three bullets. One bell."),
            Row("arena", "Arena", "choice", get=self.arena_text, action=lambda d, now: game.cycle_arena(d),
                hint=self.arena_hint),
            Row("settings", "Settings", action=lambda now: self.sub.open("settings", now),
                hint="Screen, sound and volume."),
            Row("howto", "How to Play", action=lambda now: self.sub.open("howto", now),
                hint="The rules of the draw and the wanted list."),
            Row("credits", "Credits", action=lambda now: self.sub.open("credits", now),
                hint="Who made this, and with what."),
            Row("quit", "Quit", action=lambda now: game.quit(), hint="Ride off into the sunset.",
                visible=lambda: not IS_WEB),
        ], width=360, row_h=36, on_tick=game.sounds.tick, on_click=game.sounds.click)
        self.sub = SubScreens(game)

        self.entered_at = 0
        self.arena_shown = None
        self.prev_backdrop = None
        self.fade_at = 0

        self.top_shade = self._build_top_shade()
        self.full_vignette = edge_vignette(SCREEN, 110)
        self.title = self._build_title()
        self.title_mask = self.f_logo.render("DUEL", True, (255, 255, 255))

    # ------------------------------------------------------------ text for rows
    def arena_text(self):
        g = self.g
        if g.selected_arena == "auto":
            return "AUTO TOUR"
        return ARENA_SHORT.get(g.selected_arena, get_arena(g.selected_arena).name).upper()

    def arena_hint(self):
        unlocked = len(self.g.unlocked_arenas)
        if self.g.selected_arena == "auto":
            lead = "Auto Tour: every duel rides to its own arena."
        else:
            a = get_arena(self.g.selected_arena)
            lead = f"{a.name}: {a.subtitle}."
        return f"{lead} {unlocked} of {len(ARENAS)} unlocked."

    @property
    def item(self):
        return self.panel.item.key

    # ------------------------------------------------------------ static art
    def _build_top_shade(self):
        shade = pygame.Surface((W, 300), pygame.SRCALPHA)
        for y in range(300):
            a = int(215 * (1 - y / 300) ** 1.4)
            pygame.draw.line(shade, (*INK, a), (0, y), (W, y))
        return shade

    def _build_title(self):
        kicker = self.text.spaced(self.f_kicker, "DRY CREEK", BONE, 10)
        logo = self.text.outlined(self.f_logo, "DUEL", SUN, INK, 5)
        shadow = self.text.outlined(self.f_logo, "DUEL", RUST, RUST, 5)
        width = max(kicker.get_width(), logo.get_width()) + 40
        height = kicker.get_height() + logo.get_height() + 6
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        surf.blit(kicker, kicker.get_rect(midtop=(width // 2, 0)))
        ly = kicker.get_height() - 8
        surf.blit(shadow, shadow.get_rect(midtop=(width // 2, ly + 6)))
        surf.blit(logo, logo.get_rect(midtop=(width // 2, ly)))
        self.logo_offset = (width // 2 - logo.get_width() // 2 + 5, ly + 5)
        return surf

    # ------------------------------------------------------------ input
    def enter(self, now):
        self.entered_at = now
        self.sub.close()
        self.panel.hl_y = None

    def handle_key(self, key, now):
        if self.sub.name:
            return self.sub.handle_key(key, now)
        return self.panel.handle_key(key, now)

    def activate(self, now):
        if self.sub.name == "settings":
            self.sub.settings.activate(now)
        elif self.sub.name:
            self.sub.close()
        else:
            self.panel.activate(now)

    def back(self):
        """Esc on the menu. Returns True if it closed something, False if the game should quit."""
        if self.sub.name:
            self.sub.close()
            return True
        return False

    def hover(self, pos):
        if self.sub.name:
            self.sub.hover(pos)
        else:
            self.panel.hover(pos)

    def click(self, pos, now):
        if self.sub.name:
            self.sub.click(pos, now)
        else:
            self.panel.click(pos, now)

    # ------------------------------------------------------------ drawing
    def draw(self, screen, now):
        g = self.g
        sc = g.scene
        t_in = now - self.entered_at

        # backdrop, cross-fading when the arena changes
        if self.arena_shown != g.current_arena_id:
            if self.arena_shown is not None:
                self.prev_backdrop = get_backdrop(self.arena_shown).copy()
                self.fade_at = now
            self.arena_shown = g.current_arena_id
        sc.blit(get_backdrop(g.current_arena_id), (0, 0))
        if self.prev_backdrop is not None:
            k = clamp01((now - self.fade_at) / 450)
            if k >= 1:
                self.prev_backdrop = None
            else:
                self.prev_backdrop.set_alpha(int(255 * (1 - ease_in_out(k))))
                sc.blit(self.prev_backdrop, (0, 0))
        g.ambient.draw(sc, now)

        # the player and The Marshal, waiting at either end of the street
        arena = get_arena(g.current_arena_id)
        boss = ENEMIES[-1]
        for x, d, accent, star, phase in ((PLAYER_X, 1, EMBER, False, 0.0), (ENEMY_X, -1, boss.accent, boss.star, 1.7)):
            sway = math.sin(now / 1100 + phase) * 0.012
            arm = 0.2 + math.sin(now / 900 + phase) * 0.015
            draw_cowboy(sc, x, d, arm, 0.0, 0.0, sway, accent, star, rim_tint=arena.cowboy_tint)
        sc.blit(get_vignette(arena.vignette_tint), (0, 0))
        sc.blit(self.top_shade, (0, 0))

        screen.fill(INK)
        screen.blit(sc, (0, 0))
        self._draw_strip(screen)
        screen.blit(self.full_vignette, (0, 0))
        ver = self.text.plain(self.f_small, f"v{VERSION}", BONE_DIM)
        screen.blit(ver, ver.get_rect(topright=(W - 14, 10)))
        by = self.text.plain(self.f_small, CREDIT_LINE, BONE_DIM)
        screen.blit(by, by.get_rect(bottomleft=(14, H - 8)))

        self._draw_title(screen, now, t_in)
        k = ease_out((t_in - 220) / 600)
        if k > 0:
            self.panel.place(W // 2, top=self.TOP)
            self.panel.draw(screen, now, int(255 * k), int(24 * (1 - k)))
        if self.sub.name:
            self.sub.draw(screen, now)

    def _draw_title(self, screen, now, t_in):
        k = ease_out((t_in - 80) / 700)
        title = self.title
        title.set_alpha(int(255 * k))
        rect = title.get_rect(midtop=(W // 2, 22 - int(18 * (1 - k))))
        screen.blit(title, rect)

        # a glint of sunlight sweeps across the lettering every few seconds
        phase = ((now - self.entered_at - 900) % 5200) / 700
        if k >= 1 and 0 <= phase <= 1:
            mask = self.title_mask
            mw, mh = mask.get_size()
            band = pygame.Surface((mw, mh), pygame.SRCALPHA)
            bx = int(-80 + (mw + 160) * ease_in_out(phase))
            pygame.draw.polygon(band, (255, 246, 214, 170), [(bx, 0), (bx + 34, 0), (bx + 4, mh), (bx - 30, mh)])
            pygame.draw.polygon(band, (255, 246, 214, 90), [(bx + 44, 0), (bx + 56, 0), (bx + 26, mh), (bx + 14, mh)])
            band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(band, (rect.x + self.logo_offset[0], rect.y + self.logo_offset[1]))

        tag_y = rect.bottom + 10
        tag = self.text.spaced(self.f_small, "A QUICK-DRAW SHOWDOWN", BONE_DIM, 3)
        tag.set_alpha(int(255 * k))
        screen.blit(tag, tag.get_rect(center=(W // 2, tag_y)))
        draw_ornament_rule(screen, W // 2, tag_y, 200, LINE, gap=tag.get_width() // 2 + 18)

    def _draw_strip(self, screen):
        g = self.g
        top = H
        pygame.draw.rect(screen, PANEL, (0, top, W, HUD_H))
        pygame.draw.line(screen, LINE, (0, top), (W, top), 2)
        stats = [
            ("Fastest draw", f"{g.best} ms" if g.best else "none yet"),
            ("Best bounty", f"${g.best_bounty}"),
            ("Arenas", f"{len(g.unlocked_arenas)} / {len(ARENAS)} unlocked"),
            ("Reputation", g.reputation()),
        ]
        x = 24
        for label, value in stats:
            lab = self.text.plain(self.f_small, label.upper(), BONE_DIM)
            val = self.text.plain(self.f_stat, value, BONE)
            screen.blit(lab, (x, top + 14))
            screen.blit(val, (x, top + 34))
            x += max(lab.get_width(), val.get_width()) + 40
        hints = [("UP/DOWN", "choose"), ("ENTER", "select"), ("LEFT/RIGHT", "change"), ("M", "sound"),
                 ("ESC", "back" if IS_WEB else "quit")]
        draw_keycaps(screen, self.text, self.f_small, hints, W // 2, top + HUD_H - 22)


def draw_keycaps(screen, text, font, hints, center_x, y):
    """Key hints drawn as little keycaps:  [ENTER] select  [M] sound ..."""
    pieces = [(text.plain(font, cap, BONE), text.plain(font, action, BONE_DIM)) for cap, action in hints]
    total = sum(c.get_width() + 12 + 6 + a.get_width() for c, a in pieces) + 22 * (len(pieces) - 1)
    x = center_x - total // 2
    for cap, action in pieces:
        box = pygame.Rect(x, y - 10, cap.get_width() + 12, 20)
        pygame.draw.rect(screen, LEATHER, box, border_radius=3)
        pygame.draw.rect(screen, LINE, box, 1, border_radius=3)
        screen.blit(cap, cap.get_rect(center=box.center))
        x = box.right + 6
        screen.blit(action, action.get_rect(midleft=(x, y)))
        x += action.get_width() + 22


# ---------------------------------------------------------------- pause menu
class PauseMenu:
    """Opens over a duel. The duel's clock is frozen by Game while this is open."""

    def __init__(self, game):
        self.g = game
        self.opened_at = 0
        self.panel = OptionPanel([
            Row("resume", "Resume", action=lambda now: game.resume(), hint="Back to the duel. The bell waits for you."),
            Row("settings", "Settings", action=lambda now: self.sub.open("settings", now),
                hint="Screen, sound and volume."),
            Row("howto", "How to Play", action=lambda now: self.sub.open("howto", now),
                hint="The rules of the draw and the wanted list."),
            Row("menu", "Main Menu", action=lambda now: game.leave_to_menu(),
                hint="Abandon this run and return to the main menu."),
            Row("quit", "Quit Game", action=lambda now: game.quit(), hint="Close the game.",
                visible=lambda: not IS_WEB),
        ], width=380, row_h=36, title="Paused", sign_alpha=248, on_tick=game.sounds.tick, on_click=game.sounds.click)
        self.sub = SubScreens(game)
        self.text = TextCache()
        self.f_small = load_font(21)

    def open(self, now):
        self.opened_at = now
        self.panel.index = 0
        self.panel.hl_y = None
        self.sub.close()

    def back(self):
        """Esc while paused. Returns True if it closed a sub-screen, False to resume."""
        if self.sub.name:
            self.sub.close()
            return True
        return False

    def handle_key(self, key, now):
        if self.sub.name:
            return self.sub.handle_key(key, now)
        return self.panel.handle_key(key, now)

    def hover(self, pos):
        (self.sub if self.sub.name else self.panel).hover(pos)

    def click(self, pos, now):
        (self.sub if self.sub.name else self.panel).click(pos, now)

    def draw(self, screen, now):
        k = ease_out((now - self.opened_at) / 220)
        veil(screen, 170 * k)
        if self.sub.name:
            self.sub.draw(screen, now)
            return
        self.panel.place(W // 2, center_y=FULL_H // 2 - 20)
        self.panel.draw(screen, now, int(255 * k), int(12 * (1 - k)))
        draw_keycaps(screen, self.text, self.f_small, [("ESC / P", "resume"), ("ENTER", "select"), ("M", "sound")],
                     W // 2, self.panel.rect.bottom + 26)
