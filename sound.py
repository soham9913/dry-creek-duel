"""Procedural sound effects.

Every sound is synthesized in code. For faster start-up (especially in the
browser) the same sounds can be pre-rendered to assets/sounds/*.ogg with
tools/render_sounds.py; when those files exist they are loaded instead.
"""
import math
import random
from array import array

import pygame

from config import RES_ROOT

SOUND_DIR = RES_ROOT / "assets" / "sounds"
AMBIENT_BASE_VOLUME = 0.65


class Sounds:
    def __init__(self):
        self.enabled = True
        self.ok = False
        self._bell = None
        self._shot = None
        self._click = None
        self._tick = None
        self._ambients = {}
        self._current_arena = None
        self._ambient_channel = None
        self.sfx_volume = 1.0
        self.ambience_volume = 1.0
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(8)
            self._rate, _, self._channels = pygame.mixer.get_init()
            self._bell = self._load_or_make("bell", self._bell_samples)
            self._shot = self._load_or_make("shot", self._shot_samples)
            self._click = self._load_or_make("click", self._click_samples)
            self._tick = self._load_or_make("tick", self._tick_samples)
            self._ambient_channel = pygame.mixer.Channel(1)
            self._ambient_channel.set_volume(AMBIENT_BASE_VOLUME)

            self.ok = True
        except pygame.error:
            self.ok = False          # no audio device: the game still runs silently

    def ambient_generators(self):
        return {
            "desert": self._desert_ambient_samples,
            "saloon": self._saloon_ambient_samples,
            "railway": self._railway_ambient_samples,
            "ghost_town": self._sandstorm_ambient_samples,
            "canyon": self._canyon_ambient_samples,
            "rain": self._rain_ambient_samples,
        }

    def effect_generators(self):
        return {
            "bell": self._bell_samples,
            "shot": self._shot_samples,
            "click": self._click_samples,
            "tick": self._tick_samples,
        }

    def _load_or_make(self, name, generator, loop=False):
        """Use assets/sounds/<name>.ogg if it was pre-rendered, otherwise synthesize."""
        path = SOUND_DIR / f"{name}.ogg"
        if path.is_file():
            try:
                return pygame.mixer.Sound(str(path))
            except pygame.error:
                pass
        return self._make(self.loop_samples(generator)) if loop else self._make(generator())

    def _get_ambient(self, arena_id):
        if not self.ok:
            return None
        if arena_id not in self._ambients:
            gen = self.ambient_generators().get(arena_id)
            if gen:
                self._ambients[arena_id] = self._load_or_make(f"ambient_{arena_id}", gen, loop=True)
        return self._ambients.get(arena_id)

    def _make(self, samples):
        data = array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            for _ in range(self._channels):
                data.append(v)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def loop_samples(self, generator):
        """Samples for a seamless loop: the tail is cross-faded into the head."""
        samples = list(generator())
        n = len(samples)
        fade_len = int(self._rate * 0.15)
        for i in range(fade_len):
            w = i / fade_len
            samples[i] = samples[i] * w + samples[n - fade_len + i] * (1.0 - w)
        return samples[:n - fade_len]

    def _make_loop(self, generator):
        return self._make(self.loop_samples(generator))

    def _bell_samples(self):
        n = int(self._rate * 1.3)
        for i in range(n):
            t = i / self._rate
            env = math.exp(-t * 4.5) * min(1.0, t / 0.005)
            yield env * (0.28 * math.sin(2 * math.pi * 880 * t) + 0.1 * math.sin(2 * math.pi * 1318 * t))

    def _shot_samples(self):
        n = int(self._rate * 0.55)
        state = 0.0
        for i in range(n):
            k = i / n
            alpha = 0.55 - 0.5 * k                   # the filter closes as the shot dies away
            state += alpha * ((random.random() * 2 - 1) - state)
            yield state * (1 - k) ** 3 * 1.6

    def _click_samples(self):
        """Revolver cylinder locking into place: a sharp metal snap with a short ring."""
        n = int(self._rate * 0.09)
        state = 0.0
        for i in range(n):
            t = i / self._rate
            state += 0.6 * ((random.random() * 2 - 1) - state)
            snap = state * math.exp(-t * 140)
            ring = 0.22 * math.sin(2 * math.pi * 2350 * t) * math.exp(-t * 55)
            yield (snap * 0.9 + ring) * 0.55

    def _tick_samples(self):
        """A soft wooden tick for moving between menu options."""
        n = int(self._rate * 0.04)
        lp = 0.0
        for i in range(n):
            t = i / self._rate
            lp += 0.25 * ((random.random() * 2 - 1) - lp)
            body = 0.5 * math.sin(2 * math.pi * 620 * t)
            yield (lp * 0.6 + body) * math.exp(-t * 160) * 0.35

    def _desert_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = lp2 = lp3 = 0.0
        bp = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            # Natural, gentle breathing wind swell
            swell = 0.55 + 0.30 * math.sin(2 * math.pi * 0.22 * t) + 0.15 * math.sin(2 * math.pi * 0.55 * t)
            # Cascaded multi-pole low-pass filter (removes hiss, leaves warm gentle breath)
            alpha = 0.012 + 0.009 * swell
            lp1 += alpha * (white - lp1)
            lp2 += alpha * (lp1 - lp2)
            lp3 += alpha * (lp2 - lp3)
            # Subtle mid-air breath (bandpass filtered noise, NO artificial sine wave whistle)
            bp += 0.045 * (white - bp)
            air = (lp1 - bp) * 0.25 * swell
            yield (lp3 * 1.4 + air * 0.35) * 0.45

    def _saloon_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = lp2 = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            swell = 0.5 + 0.25 * math.sin(2 * math.pi * 0.18 * t) + 0.25 * math.sin(2 * math.pi * 0.42 * t)
            alpha = 0.013 + 0.007 * swell
            lp1 += alpha * (white - lp1)
            lp2 += alpha * (lp1 - lp2)
            yield lp2 * 0.5

    def _railway_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = lp2 = lp3 = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            # Gentle nocturnal night breeze
            lp1 += 0.010 * (white - lp1)
            lp2 += 0.010 * (lp1 - lp2)
            lp3 += 0.010 * (lp2 - lp3)
            # Very faint rhythmic locomotive breath
            chuff_phase = (t * 1.8) % 1.0
            chuff = math.exp(-chuff_phase * 9.0) * lp1 * 0.35
            yield (lp3 * 1.1 + chuff) * 0.4

    def _sandstorm_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = lp2 = bp = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            # Natural blowing gusts
            gust = 0.5 + 0.35 * math.sin(2 * math.pi * 0.28 * t) + 0.15 * math.sin(2 * math.pi * 0.72 * t)
            alpha = 0.022 + 0.018 * gust
            lp1 += alpha * (white - lp1)
            lp2 += alpha * (lp1 - lp2)
            bp += 0.055 * (white - bp)
            sand = (lp1 - bp) * 0.35 * gust
            yield (lp2 * 1.1 + sand * 0.5) * 0.55

    def _canyon_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = lp2 = lp3 = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            swell = 0.5 + 0.35 * math.sin(2 * math.pi * 0.15 * t) + 0.15 * math.sin(2 * math.pi * 0.45 * t)
            alpha = 0.009 + 0.006 * swell
            lp1 += alpha * (white - lp1)
            lp2 += alpha * (lp1 - lp2)
            lp3 += alpha * (lp2 - lp3)
            yield lp3 * 0.55

    def _rain_ambient_samples(self):
        duration = 2.5
        n = int(self._rate * duration)
        lp1 = 0.0
        thunder_state = 0.0
        for i in range(n):
            t = i / self._rate
            white = random.random() * 2.0 - 1.0
            # Gentle soft rain patter
            lp1 += 0.065 * (white - lp1)
            rain_drop = (white - lp1) if random.random() < 0.20 else 0.0
            # Distant soft thunder rumble
            thunder_state += 0.006 * (white - thunder_state)
            thunder_env = max(0.0, math.sin(2 * math.pi * 0.4 * t)) ** 8
            thunder = thunder_state * 1.6 * thunder_env
            yield (rain_drop * 0.22 + lp1 * 0.06 + thunder) * 0.38

    def set_arena(self, arena_id):
        if not self.ok:
            return
        if arena_id != self._current_arena:
            self._current_arena = arena_id
            if self._ambient_channel:
                self._ambient_channel.stop()
                snd = self._get_ambient(arena_id)
                if snd and self.enabled:
                    self._ambient_channel.play(snd, loops=-1)

    def set_volumes(self, sfx=None, ambience=None):
        """Volumes from 0.0 to 1.0, set from the Settings screen."""
        if sfx is not None:
            self.sfx_volume = max(0.0, min(1.0, sfx))
        if ambience is not None:
            self.ambience_volume = max(0.0, min(1.0, ambience))
        if not self.ok:
            return
        for snd in (self._bell, self._shot, self._click, self._tick):
            if snd:
                snd.set_volume(self.sfx_volume)
        if self._ambient_channel:
            self._ambient_channel.set_volume(AMBIENT_BASE_VOLUME * self.ambience_volume)

    def bell(self):
        if self.enabled and self.ok:
            self._bell.play()

    def gunshot(self):
        if self.enabled and self.ok:
            self._shot.play()

    def click(self):
        if self.enabled and self.ok and self._click:
            self._click.play()

    def tick(self):
        if self.enabled and self.ok and self._tick:
            self._tick.play()

    def preload_ambient(self, arena_id):
        """Synthesize an arena's ambience loop ahead of time (used by the loading screen)."""
        self._get_ambient(arena_id)

    def toggle(self):
        self.enabled = not self.enabled
        if self.ok and self._ambient_channel:
            if not self.enabled:
                self._ambient_channel.stop()
            else:
                snd = self._get_ambient(self._current_arena)
                if snd:
                    self._ambient_channel.play(snd, loops=-1)
        return self.enabled


if __name__ == "__main__":
    import asyncio
    from main import main
    asyncio.run(main())

