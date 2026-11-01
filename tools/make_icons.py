"""Write assets/icon.png (browser tab / itch.io) and assets/icon.ico (Windows .exe).

    python tools/make_icons.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))
from ui import build_icon  # noqa: E402

png = ROOT / "assets" / "icon.png"
pygame.image.save(build_icon(256), str(png))
print("wrote", png.relative_to(ROOT))
try:
    from PIL import Image
    ico = ROOT / "assets" / "icon.ico"
    Image.open(png).save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", ico.relative_to(ROOT))
except ImportError:
    print("Pillow not installed: skipped icon.ico (pip install pillow)")
