"""Import the games and demos of the SuperGAU collection (output of SuperGAU's build_data.py)."""

import json
import shutil
from pathlib import Path

from disk_library import valid_entries


CATALOGUE_NAME = "SuperGAU.json"


def find_source(selected):
    """Return the folder holding SuperGAU.json: the selected folder or its `data` sub-folder, else None."""
    selected = Path(selected)
    for candidate in (selected, selected / "data"):
        if (candidate / CATALOGUE_NAME).is_file():
            return candidate
    return None


def read_catalogue(source):
    """Return the valid entries of `source/SuperGAU.json`; raises ValueError if there are none."""
    try:
        with (Path(source) / CATALOGUE_NAME).open(encoding="utf-8") as catalogue:
            entries = valid_entries(json.load(catalogue))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read {CATALOGUE_NAME}: {error}") from error
    if not entries:
        raise ValueError(f"{CATALOGUE_NAME} contains no usable disks.")
    return entries


def import_collection(source, floppies_directory, catalogue_target, progress=None):
    """Copy the catalogued ZIPs into the floppies folder and save the catalogue to `catalogue_target`.

    Files already present with the same size are skipped. `progress(done, total)` is called after each
    disk. Returns `(copied, skipped, missing)`, where `missing` lists catalogue files absent from `source`.
    The catalogue is written last, and only for the disks that are now in the floppies folder.
    """
    source, floppies_directory = Path(source), Path(floppies_directory)
    entries = read_catalogue(source)
    copied = skipped = 0
    missing = []
    imported = {}
    for done, (name, details) in enumerate(entries.items(), 1):
        origin = source / details["Folder"] / details["File"]
        target = floppies_directory / details["Folder"] / details["File"]
        if not origin.is_file():
            if target.is_file():
                imported[name] = details
            else:
                missing.append(f"{details['Folder']}/{details['File']}")
        else:
            if target.is_file() and target.stat().st_size == origin.stat().st_size:
                skipped += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_name(target.name + ".part")
                shutil.copyfile(origin, partial)
                partial.replace(target)
                copied += 1
            imported[name] = details
        if progress:
            progress(done, len(entries))
    catalogue_target = Path(catalogue_target)
    catalogue_target.parent.mkdir(parents=True, exist_ok=True)
    with catalogue_target.open("w", encoding="utf-8") as catalogue:
        json.dump(imported, catalogue, indent=1, ensure_ascii=False)
    return copied, skipped, missing
