import os
import sys
from configparser import ConfigParser
from pathlib import Path


APP_NAME = "Atari ST Compilation Disks Player"


def settings_file_path():
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path.home() / ".config"
    return root / APP_NAME / "settings.ini"


class SettingsStore:
    def __init__(self, path):
        self.path = Path(path)
        self.config = ConfigParser()

    def load(self):
        self.config.read(self.path, encoding="utf-8")
        controller = self.config.get("controller", "selected_controller", fallback="keyboard")
        emulator = self.config.get("emulator", "selected_emulator", fallback="hatari")
        if sys.platform != "win32" and emulator.startswith("steem"):
            emulator = "hatari"
        return controller, emulator

    def save(self, controller, emulator):
        self.config["controller"] = {"selected_controller": controller}
        self.config["emulator"] = {"selected_emulator": emulator}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as settings:
            self.config.write(settings)
