"""Game-flow tests. They run without a window or sound card:  python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["DRYCREEK_SAVE"] = os.path.join(tempfile.mkdtemp(), "save.json")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

from config import (ARENAS, ARENA_MAP, ENEMIES, ENEMY_VARIATION_PCT, LIVES,
                    MIN_ENEMY_MS, ROUND_TARGET_MS, SCREEN,
                    calculate_enemy_reaction_time, get_arena, get_arena_for_duel)
from main import Game  # noqa: E402
from scene import (SmokeSystem, get_backdrop, get_muzzle_pos,
                   get_vignette)


def run_to(game, t, step=16):
    """Advance the game clock in frame-sized steps, like the real loop does."""
    now = game.last_now
    while now < t:
        now = min(t, now + step)
        game.update(now)
        game.render(now)


class DuelFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode(SCREEN)

    def setUp(self):
        if os.path.exists(os.environ["DRYCREEK_SAVE"]):
            os.remove(os.environ["DRYCREEK_SAVE"])     # every test starts without a saved best time

    def new_duel(self, enemy_ms=400):
        g = Game(self.screen)
        g.on_action(0)                        # step up
        g.round.cue_at = 2000
        g.round.enemy_ms = enemy_ms
        return g

    def at_cue(self, g):
        run_to(g, 2000)
        self.assertEqual(g.phase, "draw")
        self.assertEqual(g.round.cue_ts, 2000)

    def test_phases_run_in_order(self):
        g = self.new_duel()
        self.assertEqual(g.phase, "pace")
        run_to(g, 1000)
        self.assertEqual(g.phase, "ready")
        self.at_cue(g)

    def test_fast_draw_wins_and_scores(self):
        g = self.new_duel()
        self.at_cue(g)
        g.on_action(2250)
        self.assertEqual(g.round.outcome, "win")
        self.assertEqual(g.round.player_ms, 250)
        self.assertEqual(g.bounty, ENEMIES[0].bounty)
        self.assertEqual(g.best, 250)
        self.assertEqual(g.lives, LIVES)
        run_to(g, 4000)
        self.assertEqual(g.card["head"], "Dusty Pete is down")

    def test_slow_draw_loses_a_bullet(self):
        g = self.new_duel(enemy_ms=300)
        self.at_cue(g)
        g.on_action(2350)
        self.assertEqual(g.round.outcome, "lose")
        self.assertEqual(g.lives, LIVES - 1)
        self.assertEqual(g.after, "retry")

    def test_early_press_is_a_foul(self):
        g = self.new_duel()
        run_to(g, 1500)
        self.assertEqual(g.phase, "ready")
        g.on_action(1500)
        self.assertEqual(g.round.outcome, "foul")
        self.assertEqual(g.lives, LIVES - 1)

    def test_press_just_after_bell_is_a_false_start(self):
        g = self.new_duel()
        self.at_cue(g)
        g.on_action(2060)
        self.assertEqual(g.round.outcome, "foul")

    def test_no_press_means_enemy_draws_first(self):
        g = self.new_duel(enemy_ms=400)
        run_to(g, 2500)
        self.assertEqual(g.round.outcome, "slow")
        self.assertEqual(g.lives, LIVES - 1)

    def test_presses_while_walking_out_are_ignored(self):
        g = self.new_duel()
        g.on_action(300)
        self.assertEqual(g.phase, "pace")

    def test_result_card_blocks_input_until_shown(self):
        g = self.new_duel()
        self.at_cue(g)
        g.on_action(2250)
        g.on_action(2300)                     # card not shown yet, so nothing happens
        self.assertEqual(g.phase, "result")
        run_to(g, 4500)
        g.on_action(4500)
        self.assertEqual(g.phase, "pace")
        self.assertEqual(g.duel, 1)

    def test_three_losses_end_the_run_and_restart_resets_it(self):
        g = self.new_duel(enemy_ms=300)
        t = 0
        for _ in range(LIVES):
            run_to(g, g.round.cue_at)
            self.assertEqual(g.phase, "draw")
            g.on_action(g.round.cue_ts + 350)
            self.assertEqual(g.round.outcome, "lose")
            run_to(g, g.round.show_at + 50)
            t = g.last_now
            if g.after != "over":
                g.on_action(t)
                g.round.cue_at = g.last_now + 1500
                g.round.enemy_ms = 300
                run_to(g, g.round.cue_at)
        self.assertEqual(g.after, "over")
        self.assertEqual(g.card["head"], "Boot Hill")
        g.on_action(g.last_now)
        self.assertEqual((g.duel, g.lives, g.bounty), (0, LIVES, 0))

    def test_beating_the_marshal_wins_the_run(self):
        g = Game(self.screen)
        g.duel = len(ENEMIES) - 1
        g.on_action(0)
        g.round.cue_at, g.round.enemy_ms = 2000, 300
        self.at_cue(g)
        g.on_action(2200)
        self.assertEqual(g.after, "champion")
        run_to(g, g.round.show_at + 50)
        self.assertEqual(g.card["head"], "Marshal of Dry Creek")

    # ------------------------------------------------------------ five-round difficulty tests
    def test_five_round_exact_reaction_time_targets(self):
        """Verify each round uses its exact configured base reaction-time target:
        Round 1: 450 ms, Round 2: 350 ms, Round 3: 280 ms, Round 4: 240 ms, Round 5: 200 ms.
        """
        expected_targets = {1: 450, 2: 350, 3: 280, 4: 240, 5: 200}
        self.assertEqual(ROUND_TARGET_MS, expected_targets)

        for round_num, target in expected_targets.items():
            # Check using round_number lookup
            ms = calculate_enemy_reaction_time(round_number=round_num, apply_variation=False)
            self.assertEqual(ms, target, f"Round {round_num} target mismatch")

            # Check ENEMIES configuration matches
            self.assertEqual(ENEMIES[round_num - 1].ms, target, f"Enemy {round_num} ms mismatch")

    def test_no_previous_multipliers_applied(self):
        """Ensure no 15% or 9% multiplier is applied on top of the fixed targets."""
        for round_num in range(1, 6):
            expected = ROUND_TARGET_MS[round_num]
            calculated = calculate_enemy_reaction_time(
                base_reaction_time=expected,
                round_number=round_num,
                apply_variation=False
            )
            self.assertEqual(calculated, expected)

    def test_minimum_cap_updated_and_allows_later_rounds(self):
        """Verify MIN_ENEMY_MS allows Round 4 (240 ms) and Round 5 (200 ms) targets."""
        self.assertLessEqual(MIN_ENEMY_MS, 200)

        # Round 4 must reach 240 ms
        r4 = calculate_enemy_reaction_time(round_number=4, apply_variation=False)
        self.assertEqual(r4, 240)

        # Round 5 must reach 200 ms
        r5 = calculate_enemy_reaction_time(round_number=5, apply_variation=False)
        self.assertEqual(r5, 200)

    def test_small_controlled_variation_and_consistency(self):
        """Controlled variation is small (+/- 3%) and never inverts difficulty order."""
        for _ in range(50):
            times = [calculate_enemy_reaction_time(round_number=r) for r in range(1, 6)]
            # Verify strictly descending times (faster opponent as rounds progress)
            for i in range(len(times) - 1):
                self.assertGreater(times[i], times[i + 1],
                                   f"Round {i+1} ({times[i]}) not faster than Round {i+2} ({times[i+1]})")

            # Verify all stay within controlled variation of their base targets
            for r, t in enumerate(times, start=1):
                base = ROUND_TARGET_MS[r]
                self.assertGreaterEqual(t, max(MIN_ENEMY_MS, round(base * (1 - ENEMY_VARIATION_PCT))))
                self.assertLessEqual(t, round(base * (1 + ENEMY_VARIATION_PCT)))

    def test_restarting_round_does_not_increase_difficulty(self):
        """Retrying the same round after a loss or foul maintains the same difficulty target."""
        g = Game(self.screen)
        g.on_action(0)  # step up to round 1
        self.assertEqual(g.round_number, 1)
        self.assertEqual(g.enemy.ms, 450)

        # Player fouls
        run_to(g, 1200)
        g.on_action(1200)
        self.assertEqual(g.round.outcome, "foul")
        self.assertEqual(g.after, "retry")

        # Advance past result card and rematch
        run_to(g, g.round.show_at + 50)
        g.on_action(g.last_now)

        # Still round 1 with 450 ms target
        self.assertEqual(g.duel, 0)
        self.assertEqual(g.round_number, 1)
        self.assertEqual(g.enemy.ms, 450)

    def test_starting_new_game_resets_progression(self):
        """Starting a new game resets round_number to 1 and uses Round 1 target."""
        g = Game(self.screen)
        g.round_number = 5
        self.assertEqual(g.duel, 4)
        self.assertEqual(g.enemy.ms, 200)

        g.reset_run()
        self.assertEqual(g.duel, 0)
        self.assertEqual(g.round_number, 1)
        self.assertEqual(g.enemy.ms, 450)

    def test_game_duel_progression_uses_five_round_targets(self):
        """When moving to each duel upon winning, enemy reaction time uses each round's target."""
        g = Game(self.screen)
        g.on_action(0)

        for round_num in range(1, 6):
            self.assertEqual(g.round_number, round_num)
            base_target = ROUND_TARGET_MS[round_num]
            # Verify the round enemy_ms is within controlled variation of the target
            self.assertGreaterEqual(g.round.enemy_ms, max(MIN_ENEMY_MS, round(base_target * (1 - ENEMY_VARIATION_PCT))))
            self.assertLessEqual(g.round.enemy_ms, round(base_target * (1 + ENEMY_VARIATION_PCT)))

            if round_num < 5:
                # Win round
                g.round.cue_ts = g.last_now + 100
                g.round.enemy_ms = 400
                g.press(100)
                self.assertEqual(g.after, "next")
                run_to(g, g.round.show_at + 50)
                g.on_action(g.last_now)

    # ------------------------------------------------------------ multiple arena & visual effects tests
    def test_six_arenas_exist_and_render_correctly(self):
        """Verify all 6 duel locations exist, have unique backdrops and vignettes."""
        expected_ids = ["desert", "saloon", "railway", "ghost_town", "canyon", "rain"]
        self.assertEqual(len(ARENAS), 6)
        self.assertEqual([a.id for a in ARENAS], expected_ids)

        for arena in ARENAS:
            surf = get_backdrop(arena.id)
            self.assertEqual(surf.get_size(), (960, 540))
            vig = get_vignette(arena.vignette_tint)
            self.assertEqual(vig.get_size(), (960, 540))

    def test_arena_unlock_progression(self):
        """Verify arenas unlock sequentially as the player beats duels."""
        g = Game(self.screen)
        # Initially only signature desert is unlocked
        self.assertEqual(g.unlocked_arenas, {"desert"})

        # Beat Pete (Round 1) -> unlocks Saloon
        g.on_action(0)
        g.round.cue_at = 2000
        g.round.enemy_ms = 450
        self.at_cue(g)
        g.on_action(2150)
        self.assertEqual(g.round.outcome, "win")
        self.assertIn("saloon", g.unlocked_arenas)
        self.assertEqual(g.newly_unlocked.id, "saloon")
        run_to(g, g.round.show_at + 50)
        self.assertTrue(any("NEW ARENA UNLOCKED" in line for line, _ in g.card["lines"]))

        # Advance to round 2 (Calico Jane)
        g.on_action(g.last_now)
        self.assertEqual(g.duel, 1)
        # Campaign auto tour should now show Saloon
        self.assertEqual(g.current_arena_id, "saloon")

        # Beat Jane (Round 2) -> unlocks Railway
        g.round.cue_at = g.last_now + 1500
        g.round.enemy_ms = 400
        run_to(g, g.round.cue_at)
        g.on_action(g.last_now + 150)
        self.assertEqual(g.round.outcome, "win")
        self.assertIn("railway", g.unlocked_arenas)

        # Advance to round 3 (Dead-Eye Dan) -> shows Railway
        run_to(g, g.round.show_at + 50)
        g.on_action(g.last_now)
        self.assertEqual(g.current_arena_id, "railway")

        # Beat Dan (Round 3) -> unlocks Ghost Town
        g.round.cue_at = g.last_now + 1500
        g.round.enemy_ms = 280
        run_to(g, g.round.cue_at)
        g.on_action(g.last_now + 150)
        self.assertEqual(g.round.outcome, "win")
        self.assertIn("ghost_town", g.unlocked_arenas)

        # Advance to round 4 (Black Bart) -> shows Ghost Town
        run_to(g, g.round.show_at + 50)
        g.on_action(g.last_now)
        self.assertEqual(g.current_arena_id, "ghost_town")

        # Beat Bart (Round 4) -> unlocks Canyon Bridge
        g.round.cue_at = g.last_now + 1500
        g.round.enemy_ms = 200
        run_to(g, g.round.cue_at)
        g.on_action(g.last_now + 150)
        self.assertEqual(g.round.outcome, "win")
        self.assertIn("canyon", g.unlocked_arenas)

        # Advance to round 5 (The Marshal) -> shows Canyon Bridge
        run_to(g, g.round.show_at + 50)
        g.on_action(g.last_now)
        self.assertEqual(g.current_arena_id, "canyon")

        # Beat The Marshal (Round 5 - Champion) -> unlocks Rain-Soaked Street
        g.round.cue_at = g.last_now + 1500
        g.round.enemy_ms = 180
        run_to(g, g.round.cue_at)
        g.on_action(g.last_now + 150)
        self.assertEqual(g.round.outcome, "win")
        self.assertEqual(g.after, "champion")
        self.assertIn("rain", g.unlocked_arenas)

    def test_arena_manual_selection_and_cycling(self):
        """Player can lock to a specific arena and cycle through unlocked locations."""
        g = Game(self.screen)
        g.unlocked_arenas = {"desert", "saloon", "railway"}
        self.assertEqual(g.selected_arena, "auto")

        # Cycle forward
        g.cycle_arena(1)
        self.assertEqual(g.selected_arena, "desert")
        self.assertEqual(g.current_arena_id, "desert")

        g.cycle_arena(1)
        self.assertEqual(g.selected_arena, "saloon")
        self.assertEqual(g.current_arena_id, "saloon")

        # When locked to saloon, advancing duels keeps saloon arena
        g.on_action(0)
        self.assertEqual(g.current_arena_id, "saloon")

    def test_camera_shake_and_gunsmoke_trigger_on_shot(self):
        """When a shot is fired, camera shake triggers and gunsmoke spawns."""
        g = self.new_duel()
        self.at_cue(g)
        # Player shoots
        g.on_action(2200)
        self.assertEqual(g.round.outcome, "win")

        # Advance to shot time
        shot_time = g.round.p.shot_at
        run_to(g, shot_time + 10)

        # Gunshot fired: camera shake should be active
        self.assertGreater(g.camera_shake.trauma, 0.0)
        ox, oy = g.camera_shake.get_offset()
        # Non-zero or shaken offset
        self.assertTrue(g.round.p.smoked)
        self.assertGreater(len(g.smoke.puffs), 0)

        # Advancing time allows camera shake to decay smoothly
        run_to(g, shot_time + 600)
        self.assertAlmostEqual(g.camera_shake.trauma, 0.0, places=1)

    def test_get_muzzle_pos(self):
        """Verify muzzle calculation accurately places gun barrel for both sides."""
        p_mx, p_my = get_muzzle_pos(232, 1, 1.55)
        e_mx, e_my = get_muzzle_pos(728, -1, 1.55)

        # Player shoots rightward: muzzle is in front (x > 232)
        self.assertGreater(p_mx, 232)
        # Enemy shoots leftward: muzzle is in front (x < 728)
        self.assertLess(e_mx, 728)
        # Gun barrel height is above ground
        self.assertLess(p_my, 468)
        self.assertGreater(p_my, 200)


if __name__ == "__main__":
    unittest.main()

