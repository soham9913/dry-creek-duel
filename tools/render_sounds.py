"""Pre-render every synthesized sound to assets/sounds/*.ogg.

The game can make all of its sounds in code, but that takes a few seconds in a
web browser. Run this once before building for the web or Windows:

    python tools/render_sounds.py

Needs ffmpeg on your PATH for the .ogg encoding (WAV files are kept if it is missing).
"""
import os
import shutil
import subprocess
import sys
import wave
from array import array
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
import sound  # noqa: E402

OUT = ROOT / "assets" / "sounds"


def write_wav(path, samples, rate):
    data = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.ogg"):
        old.unlink()          # make sure the game below synthesizes fresh samples
    s = sound.Sounds()
    rate = s._rate
    jobs = {name: list(gen()) for name, gen in s.effect_generators().items()}
    for arena_id, gen in s.ambient_generators().items():
        jobs[f"ambient_{arena_id}"] = s.loop_samples(gen)
    ffmpeg = shutil.which("ffmpeg")
    for name, samples in jobs.items():
        wav = OUT / f"{name}.wav"
        write_wav(wav, samples, rate)
        if ffmpeg:
            ogg = OUT / f"{name}.ogg"
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "5", str(ogg)],
                           check=True)
            wav.unlink()
            print("wrote", ogg.relative_to(ROOT))
        else:
            print("wrote", wav.relative_to(ROOT), "(install ffmpeg to convert to .ogg)")


if __name__ == "__main__":
    main()
