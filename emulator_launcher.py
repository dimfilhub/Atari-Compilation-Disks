"""Builds the Hatari command line and runs the emulator for a floppy image."""

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


class EmulatorLauncher:
    """Launches Hatari with a floppy image, unpacking zip archives first."""
    def __init__(self, hatari_directory, tos_path):
        """Remember the Hatari data folder (holding its config file) and the TOS image path.

        `joystick_keys` may be set afterwards to override the keyboard-joystick keys.
        """
        self.hatari_directory = Path(hatari_directory)
        self.tos_path = Path(tos_path).resolve()
        self.joystick_keys = {}

    def _hatari_config_with_keys(self, config_path):
        """Return a config file with `joystick_keys` applied to the [Joystick1] section.

        A temporary copy is written so the shipped config stays untouched; the original
        path is returned when there are no overrides or the file is missing.
        """
        if not self.joystick_keys or not config_path.is_file():
            return config_path
        lines = config_path.read_text(encoding="utf-8", errors="surrogateescape").splitlines(keepends=True)
        section = None
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("["):
                section = stripped.casefold()
            elif section == "[joystick1]" and "=" in stripped:
                name = stripped.split("=", 1)[0].strip()
                if name in self.joystick_keys:
                    lines[index] = f"{name} = {self.joystick_keys[name]}\n"
        generated = Path(tempfile.gettempdir()) / "atari-comp-disks-hatari.cfg"
        generated.write_text("".join(lines), encoding="utf-8", errors="surrogateescape")
        return generated

    @staticmethod
    def _find_hatari():
        """Locate the Hatari executable on PATH or in common install locations; None if not found."""
        executable = shutil.which("hatari")
        if executable:
            return executable
        candidates = [
            Path("/opt/homebrew/bin/hatari"),
            Path("/usr/local/bin/hatari"),
        ]
        if sys.platform == "darwin":
            candidates.extend((
                Path("/Applications/hatari.app/Contents/MacOS/hatari"),
                Path.home() / "Applications/hatari.app/Contents/MacOS/hatari",
            ))
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None

    def command(self, controller, floppy_path):
        """Return the Hatari argument list for `floppy_path`.

        `controller` is "keyboard" (joystick emulated by keys) or "joystick" (real device).
        Raises FileNotFoundError if Hatari cannot be found.
        """
        executable = (
            str(self.hatari_directory / "hatari.exe")
            if sys.platform == "win32"
            else self._find_hatari()
        )
        if executable is None:
            raise FileNotFoundError(
                'Hatari was not found. Install it and ensure "hatari" is available in PATH.'
            )
        joystick = "keys" if controller == "keyboard" else "real"
        return [
            executable, "--joy1", joystick,
            "--configfile", str(self._hatari_config_with_keys(self.hatari_directory / "atari_keys")),
            "--tos", str(self.tos_path),
            "--machine", "st", "--monitor", "tv", "--fullscreen", "--memsize", "1",
            "--statusbar", "FALSE", "--drive-led", "TRUE",
            "--confirm-quit", "FALSE", "--disk-a", str(floppy_path),
        ]

    def launch(self, controller, floppy_path):
        """Run Hatari on the disk and block until it exits.

        A .zip must contain exactly one .msa/.st image (preferring one named like the archive);
        it is extracted to a temporary folder for the duration of the run.
        Raises RuntimeError if the archive is ambiguous or empty.
        """
        floppy_path = Path(floppy_path)
        if floppy_path.suffix.casefold() != ".zip":
            subprocess.run(self.command(controller, floppy_path), check=False)
            return

        with zipfile.ZipFile(floppy_path) as archive:
            disk_images = [
                member for member in archive.infolist()
                if not member.is_dir() and Path(member.filename).suffix.casefold() in {".msa", ".st"}
            ]
            archive_stem = floppy_path.stem.casefold()
            matching_images = [
                member for member in disk_images
                if Path(member.filename).stem.casefold() == archive_stem
            ]
            if matching_images:
                disk_images = matching_images
            if len(disk_images) != 1:
                raise RuntimeError(
                    f"Expected one .MSA or .ST disk image in {floppy_path.name}, "
                    f"found {len(disk_images)}."
                )

            image = disk_images[0]
            with tempfile.TemporaryDirectory(prefix="atari-disk-") as temporary_directory:
                extracted_path = Path(temporary_directory) / Path(image.filename).name
                with archive.open(image) as source, extracted_path.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                subprocess.run(
                    self.command(controller, extracted_path), check=False,
                )
