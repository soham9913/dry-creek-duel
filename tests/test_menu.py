"""Main menu, pause menu, settings and loading screen tests.
Headless:  python -m unittest discover -s tests"""
import asyncio
import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("DRYCREEK_SAVE", os.path.join(tempfile.mkdtemp(), "save.json"))  # shared with other test modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

from config import ARENAS, LIVES, SCREEN  # noqa: E402
import scene  # noqa: E402
import storage  # noqa: E402
from loading import LoadingScreen  # noqa: E402
from main import PAUSE_BUTTON, SAVE_PATH, Game  # noqa: E402
from sound import Sounds  # noqa: E402


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def saved():
    return json.loads(SAVE_PATH.read_text())


class MenuTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode(SCREEN)

    def setUp(self):
        if SAVE_PATH.exists():
            SAVE_PATH.unlink()
        self.g = Game(self.screen)
        self.menu = self.g.menu
        self.menu.panel.place(480, top=self.menu.TOP)

    def select(self, name):
        self.menu.panel.select(name)


class MainMenuTests(MenuTestCase):
    def test_game_opens_on_the_menu_with_start_selected(self):
        self.assertEqual(self.g.phase, "title")
        self.assertEqual(self.menu.item, "start")
        self.g.render(500)

    def test_enter_on_start_begins_the_first_duel(self):
        self.g.handle(key(pygame.K_RETURN))
        self.assertEqual(self.g.phase, "pace")
        self.assertEqual(self.g.duel, 0)

    def test_up_down_navigation_wraps(self):
        self.g.handle(key(pygame.K_UP))
        self.assertEqual(self.menu.item, "quit")
        self.g.handle(key(pygame.K_DOWN))
        self.g.handle(key(pygame.K_DOWN))
        self.assertEqual(self.menu.item, "arena")

    def test_arena_row_cycles_unlocked_arenas(self):
        self.g.unlocked_arenas = {"desert", "saloon"}
        self.select("arena")
        self.g.handle(key(pygame.K_RIGHT))
        self.assertEqual(self.g.selected_arena, "desert")
        self.g.handle(key(pygame.K_RIGHT))
        self.assertEqual(self.g.selected_arena, "saloon")
        self.assertEqual(self.g.current_arena_id, "saloon")
        self.g.handle(key(pygame.K_LEFT))
        self.assertEqual(self.menu.arena_text(), "SUNSET DESERT")

    def test_clicking_arena_arrows_cycles_both_ways(self):
        self.g.unlocked_arenas = {"desert", "saloon"}
        i = self.menu.panel.index_of("arena")
        _, right = self.menu.panel.arrow_rects(i)
        self.menu.click(right.center, 0)
        self.assertEqual(self.g.selected_arena, "desert")
        left, _ = self.menu.panel.arrow_rects(i)
        self.menu.click(left.center, 0)
        self.assertEqual(self.g.selected_arena, "auto")

    def test_mouse_hover_selects_and_click_activates(self):
        p = self.menu.panel
        self.menu.hover(p.row_rect(p.index_of("howto")).center)
        self.assertEqual(self.menu.item, "howto")
        self.menu.click(p.row_rect(p.index_of("start")).center, 0)
        self.assertEqual(self.g.phase, "pace")

    def test_clicking_outside_the_menu_does_nothing(self):
        self.menu.click((20, 20), 0)
        self.assertEqual(self.g.phase, "title")

    def test_info_cards_open_and_any_key_closes_them(self):
        for name in ("howto", "credits"):
            self.select(name)
            self.g.handle(key(pygame.K_RETURN))
            self.assertEqual(self.menu.sub.name, name)
            self.g.render(1000)
            self.g.handle(key(pygame.K_x))
            self.assertIsNone(self.menu.sub.name)

    def test_escape_closes_a_sub_screen_before_quitting(self):
        self.select("credits")
        self.g.handle(key(pygame.K_RETURN))
        self.g.handle(key(pygame.K_ESCAPE))
        self.assertTrue(self.g.running)
        self.g.handle(key(pygame.K_ESCAPE))
        self.assertFalse(self.g.running)

    def test_quit_row_stops_the_game(self):
        self.select("quit")
        self.g.handle(key(pygame.K_RETURN))
        self.assertFalse(self.g.running)

    def test_best_bounty_is_saved(self):
        self.g.handle(key(pygame.K_RETURN))
        r = self.g.round
        r.cue_ts = self.g.last_now + 100
        r.enemy_ms = 400
        self.g.press(200)
        self.assertEqual(self.g.best_bounty, 25)
        self.assertEqual(Game(self.screen).best_bounty, 25)

    def test_menu_renders_in_every_arena(self):
        self.g.unlocked_arenas = {a.id for a in ARENAS}
        for i, _ in enumerate(ARENAS):
            self.g.cycle_arena(1)
            self.g.render(i * 100 + 50)


class SettingsTests(MenuTestCase):
    def open_settings(self):
        self.select("settings")
        self.g.handle(key(pygame.K_RETURN))
        self.assertEqual(self.menu.sub.name, "settings")
        return self.menu.sub.settings

    def test_sound_toggle_is_remembered(self):
        panel = self.open_settings()
        panel.select("sound")
        before = self.g.sounds.enabled
        self.g.handle(key(pygame.K_RETURN))
        self.assertEqual(self.g.sounds.enabled, not before)
        self.assertEqual(saved()["sound"], not before)
        self.assertEqual(Game(self.screen).sounds.enabled, not before)

    def test_volume_sliders_change_and_persist(self):
        panel = self.open_settings()
        panel.select("sfx")
        self.g.handle(key(pygame.K_LEFT))
        self.g.handle(key(pygame.K_LEFT))
        self.assertEqual(self.g.volumes["sfx"], 8)
        self.assertAlmostEqual(self.g.sounds.sfx_volume, 0.8)
        panel.select("ambience")
        for _ in range(15):
            self.g.handle(key(pygame.K_LEFT))
        self.assertEqual(self.g.volumes["ambience"], 0)       # clamps at zero
        self.assertEqual(Game(self.screen).volumes, {"sfx": 8, "ambience": 0})

    def test_clicking_a_slider_notch_sets_the_value(self):
        panel = self.open_settings()
        panel.place(480, center_y=310)
        i = panel.index_of("sfx")
        bar = panel.slider_rect(i)
        self.menu.click((bar.x + 3 * 11 + 2, bar.centery), 0)  # the fourth notch
        self.assertEqual(self.g.volumes["sfx"], 4)

    def test_fullscreen_setting_is_saved(self):
        panel = self.open_settings()
        panel.select("fullscreen")
        self.g.handle(key(pygame.K_RETURN))
        self.assertTrue(self.g.fullscreen)
        self.assertTrue(saved()["fullscreen"])

    def test_back_row_closes_settings(self):
        panel = self.open_settings()
        panel.select("back")
        self.g.render(400)
        self.g.handle(key(pygame.K_RETURN))
        self.assertIsNone(self.menu.sub.name)


class PauseTests(MenuTestCase):
    def start(self):
        self.g.on_action(0)
        self.g.round.cue_at = 3000
        self.assertEqual(self.g.phase, "pace")

    def test_escape_pauses_and_the_clock_stands_still(self):
        self.start()
        self.g.frame(500)
        self.g.pause(600)
        self.assertTrue(self.g.paused)
        for real in range(600, 20000, 500):       # a long pause...
            self.g.frame(real)
        self.assertEqual(self.g.phase, "pace")    # ...and nothing moved on
        self.assertEqual(self.g.clock(20000), 600)
        self.g.resume(20000)
        for real in range(20000, 20501, 16):      # 500 ms of game time later
            self.g.frame(real)
        self.assertEqual(self.g.clock(20500), 1100)
        self.assertEqual(self.g.phase, "ready")
        for real in range(20500, 22501, 16):      # the bell is at game time 3000
            self.g.frame(real)
        self.assertEqual(self.g.phase, "draw")

    def test_escape_key_opens_and_closes_pause(self):
        self.start()
        self.g.handle(key(pygame.K_ESCAPE))
        self.assertTrue(self.g.paused)
        self.g.render(self.g.clock())
        self.g.pause_menu.draw(self.screen, pygame.time.get_ticks())
        self.g.handle(key(pygame.K_ESCAPE))
        self.assertFalse(self.g.paused)
        self.g.handle(key(pygame.K_p))
        self.assertTrue(self.g.paused)

    def test_space_while_paused_does_not_draw(self):
        self.start()
        self.g.pause(100)
        self.g.pause_menu.panel.select("howto")
        self.g.handle(key(pygame.K_SPACE))
        self.assertEqual(self.g.phase, "pace")
        self.assertEqual(self.g.pause_menu.sub.name, "howto")

    def test_main_menu_from_pause_abandons_the_run(self):
        self.start()
        self.g.duel, self.g.lives, self.g.bounty = 2, 1, 85
        self.g.handle(key(pygame.K_ESCAPE))
        self.g.pause_menu.panel.select("menu")
        self.g.handle(key(pygame.K_RETURN))
        self.assertFalse(self.g.paused)
        self.assertEqual(self.g.phase, "title")
        self.assertIsNone(self.g.round)
        self.assertEqual((self.g.duel, self.g.lives, self.g.bounty), (0, LIVES, 0))
        self.g.render(self.g.clock())

    def test_resume_row_and_pause_button(self):
        self.start()
        self.g.handle(click(PAUSE_BUTTON.center))
        self.assertTrue(self.g.paused)
        self.g.handle(key(pygame.K_RETURN))       # Resume is selected first
        self.assertFalse(self.g.paused)

    def test_losing_focus_pauses_a_duel_but_not_the_menu(self):
        self.g.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(self.g.paused)
        self.start()
        self.g.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(self.g.paused)


class StorageTests(unittest.TestCase):
    def test_web_storage_uses_local_storage(self):
        class FakeLocalStorage(dict):
            def getItem(self, k):
                return self.get(k)

            def setItem(self, k, v):
                self[k] = v

        fake = FakeLocalStorage()
        old_web, old_fn = storage.IS_WEB, storage._web_storage
        storage.IS_WEB, storage._web_storage = True, lambda: fake
        try:
            self.assertEqual(storage.load_save_data(), {})
            storage.save_save_data({"best_ms": 199})
            storage.save_save_data({"sound": False})
            self.assertEqual(json.loads(fake[storage.WEB_KEY]), {"best_ms": 199, "sound": False})
            self.assertEqual(storage.load_save_data()["best_ms"], 199)
        finally:
            storage.IS_WEB, storage._web_storage = old_web, old_fn


class LoadingScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode(SCREEN)

    def test_preloads_every_arena_and_finishes(self):
        scene._BACKDROP_CACHE.clear()
        sounds = Sounds()
        ls = LoadingScreen(self.screen, sounds)
        t = 0
        while not ls.complete(t) and t < 20000:
            ls.update(t)
            ls.draw(t)
            t += 16
        self.assertTrue(ls.complete(t))
        self.assertEqual(ls.loaded, len(ARENAS))
        self.assertEqual(set(scene._BACKDROP_CACHE), {a.id for a in ARENAS})
        if sounds.ok:
            self.assertEqual(set(sounds._ambients), {a.id for a in ARENAS})
        self.assertGreaterEqual(t, LoadingScreen.MIN_MS)

    def test_key_after_loading_skips_the_hold(self):
        ls = LoadingScreen(self.screen, Sounds())
        t = 0
        while ls.finished_at is None:
            ls.update(t)
            t += 16
        ls.request_skip()
        self.assertTrue(ls.complete(ls.finished_at + LoadingScreen.FADE_MS))

    def test_async_run_loop_finishes(self):
        ls = LoadingScreen(self.screen, Sounds())
        ls.MIN_MS = 50
        ls.request_skip()
        self.assertTrue(asyncio.run(ls.run(pygame.time.Clock())))


if __name__ == "__main__":
    unittest.main()
