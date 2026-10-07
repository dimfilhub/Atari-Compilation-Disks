"""Build a standalone executable for the current OS with PyInstaller (run: python build.py)."""
import shutil
import sys

import PyInstaller.__main__

separator = ";" if sys.platform == "win32" else ":"
args = [
    "comp_disks_player.pyw",
    "--name", "AtariCompDisksPlayer",
    "--windowed",
    "--noconfirm",
    "--add-data", f"CompDisks.json{separator}.",
    "--add-data", f"atari.ico{separator}.",
    "--icon", "atari.ico",
]
if sys.platform == "win32":
    args.append("--onefile")
PyInstaller.__main__.run(args)

# Ship the TOS ROM next to the app, where the player looks for `data`.
shutil.copytree("data/roms", "dist/data/roms", dirs_exist_ok=True)
