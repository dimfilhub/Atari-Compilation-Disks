import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


class EmulatorLauncher:
    def __init__(self, data_directory):
        self.data_directory = Path(data_directory)
        self.hatari_directory = self.data_directory / "hatari"
        self.steem_directory = self.data_directory / "steem"
        self.tos_path = self.data_directory.resolve() / "tos.img"

    def _steem_ini_with_tos(self, ini_path):
        lines = ini_path.read_text(encoding="utf-8", errors="surrogateescape").splitlines(keepends=True)
        lines = [
            f"ROM_File={self.tos_path}\n" if line.startswith("ROM_File=") else line
            for line in lines
        ]
        generated = Path(tempfile.gettempdir()) / f"atari-comp-disks-{ini_path.name}"
        generated.write_text("".join(lines), encoding="utf-8", errors="surrogateescape")
        return generated

    @staticmethod
    def _find_hatari():
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

    def command(self, emulator, controller, floppy_path):
        if emulator.startswith("steem"):
            if sys.platform != "win32":
                raise RuntimeError("Steem SSE is only available on Windows.")
            ini_name = "steem_keyboard" if controller == "keyboard" else "steem_joystick"
            if emulator == "steemnoscan":
                ini_name += "_noscan"
            return [
                str(self.steem_directory / "Steem32D3D.exe"),
                f"INI={self._steem_ini_with_tos(self.steem_directory / (ini_name + '.ini'))}",
                str(floppy_path),
            ]

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
            "--configfile", str(self.hatari_directory / "atari_keys"),
            "--tos", str(self.tos_path),
            "--machine", "st", "--monitor", "tv", "--fullscreen", "--memsize", "1",
            "--statusbar", "FALSE", "--drive-led", "TRUE",
            "--confirm-quit", "FALSE", "--disk-a", str(floppy_path),
        ]

    def launch(self, emulator, controller, floppy_path):
        floppy_path = Path(floppy_path)
        if floppy_path.suffix.casefold() != ".zip":
            subprocess.run(self.command(emulator, controller, floppy_path), check=False)
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
                    self.command(emulator, controller, extracted_path), check=False,
                )
