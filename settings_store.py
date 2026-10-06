"""Persistent user settings (controller, folders, joystick keys) stored in an INI file."""

import os
import sys
from configparser import ConfigParser
from pathlib import Path


APP_NAME = "Atari ST Compilation Disks Player"
FOLDER_NAMES = ("floppies", "hatari", "tos")
# Hatari key names (SDL) for the keyboard-emulated joystick.
JOYSTICK_ACTIONS = (("kUp", "Up"), ("kDown", "Down"), ("kLeft", "Left"), ("kRight", "Right"), ("kFire", "Fire"))
DEFAULT_JOYSTICK_KEYS = {"kUp": "Up", "kDown": "Down", "kLeft": "Left", "kRight": "Right", "kFire": "Space"}


def settings_file_path():
    """Return the per-user settings.ini path for the current platform."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path.home() / ".config"
    return root / APP_NAME / "settings.ini"


class SettingsStore:
    """Reads and writes the application settings file."""
    def __init__(self, path):
        """Create a store backed by the INI file at `path`; call `load` to read it."""
        self.path = Path(path)
        self.config = ConfigParser()

    def load(self):
        """Read the file and return `(controller, folders)`, using defaults for missing values.

        Folder values are empty strings when the default location should be used.
        """
        self.config.read(self.path, encoding="utf-8")
        controller = self.config.get("controller", "selected_controller", fallback="keyboard")
        folders = {
            name: self.config.get("folders", name, fallback="") for name in FOLDER_NAMES
        }
        return controller, folders

    def load_keys(self):
        """Return the keyboard-joystick key names (Hatari/SDL names) keyed by action, with defaults filled in."""
        return {
            action: self.config.get("keys", action, fallback=default) or default
            for action, default in DEFAULT_JOYSTICK_KEYS.items()
        }

    def save_keys(self, keys):
        """Stage `keys` for saving; only keys that differ from the defaults are stored.

        Call `save` afterwards to write the file.
        """
        self.config["keys"] = {
            action: keys[action] for action in DEFAULT_JOYSTICK_KEYS
            if keys[action] != DEFAULT_JOYSTICK_KEYS[action]
        }

    def save(self, controller, folders):
        """Write the selected controller, custom folders and staged keys to the settings file."""
        self.config["controller"] = {"selected_controller": controller}
        self.config.remove_section("emulator")
        self.config["folders"] = {name: folders.get(name, "") for name in FOLDER_NAMES}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as settings:
            self.config.write(settings)
