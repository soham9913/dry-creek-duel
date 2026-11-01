"""Build the browser version for itch.io.

    python tools/build_web.py            # build release/dry-creek-duel-web.zip
    python tools/build_web.py --serve    # build, then play it at http://localhost:8000

Only the game's own files are copied into a clean folder first, so the virtual
environment, tests and build output are never packed into the web build.
Upload the resulting zip to itch.io as an HTML game (see store_page/UPLOAD_GUIDE.md).
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "build" / "dry-creek-duel"
RELEASE = ROOT / "release"
GAME_FILES = ["main.py", "config.py", "scene.py", "sound.py", "storage.py", "ui.py", "loading.py", "menu.py"]
ASSET_DIRS = ["assets/fonts", "assets/sounds"]


def stage():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name in GAME_FILES:
        shutil.copy2(ROOT / name, STAGE / name)
    for d in ASSET_DIRS:
        shutil.copytree(ROOT / d, STAGE / d, ignore=shutil.ignore_patterns("*.wav", ".gitkeep"))
    shutil.copy2(ROOT / "assets" / "icon.png", STAGE / "favicon.png")   # pygbag uses this for the tab icon
    if not list((STAGE / "assets" / "sounds").glob("*.ogg")):
        print("note: no pre-rendered sounds; run tools/render_sounds.py first for a faster browser start")


def main():
    try:
        import pygbag  # noqa: F401
    except ImportError:
        sys.exit("pygbag is not installed. Run:  pip install pygbag")
    stage()
    serve = "--serve" in sys.argv
    cmd = [sys.executable, "-m", "pygbag", "--title", "Dry Creek Duel", "--app_name", "dry-creek-duel"]
    if not serve:
        cmd += ["--build", "--archive"]
    cmd.append(str(STAGE))
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    if not serve:
        RELEASE.mkdir(exist_ok=True)
        built = STAGE / "build" / "web.zip"
        out = RELEASE / "dry-creek-duel-web.zip"
        shutil.copy2(built, out)
        print("\nReady for itch.io:", out)


if __name__ == "__main__":
    main()
