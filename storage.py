"""Save data that works both on the desktop and in a web browser.

Desktop (and the Windows .exe): a small JSON file in the player's home folder.
Browser (itch.io): the page's localStorage, because files written inside a
browser game disappear when the tab closes.
"""
import json
import os
from pathlib import Path

from config import IS_WEB

SAVE_PATH = Path(os.environ.get("DRYCREEK_SAVE", Path.home() / ".dry_creek_duel.json"))
WEB_KEY = "dry_creek_duel_save"


def _web_storage():
    try:
        import platform  # pygbag replaces this module with a bridge to the browser
        return platform.window.localStorage
    except Exception:
        return None


def read_raw() -> str:
    if IS_WEB:
        store = _web_storage()
        if store is not None:
            try:
                value = store.getItem(WEB_KEY)
                return value if isinstance(value, str) else ""
            except Exception:
                return ""
        return ""
    try:
        return SAVE_PATH.read_text()
    except OSError:
        return ""


def write_raw(text: str) -> None:
    if IS_WEB:
        store = _web_storage()
        if store is not None:
            try:
                store.setItem(WEB_KEY, text)
            except Exception:
                pass
        return
    try:
        SAVE_PATH.write_text(text)
    except OSError:
        pass


def load_save_data() -> dict:
    try:
        data = json.loads(read_raw() or "{}")
        if isinstance(data, dict):
            return data
    except (ValueError, TypeError):
        pass
    return {}


def save_save_data(updates: dict) -> None:
    data = load_save_data()
    data.update(updates)
    write_raw(json.dumps(data))
