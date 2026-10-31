"""Import the games and demos straight from the SuperGAU ARCHIVE-CD ISO image.

Reads the STDEMOS and STGAMES0..9 folders (disks only, no apps/tools/clipart), takes the disk titles
from each folder's FILES.BBS, copies the ZIPs into the floppies folder and writes a catalogue in the
CompDisks.json format. Ported from SuperGAU's build_data.py.
"""

import io
import json
import re
from pathlib import Path


TEAMS = {"game": ("SuperGAU Games", "SuperGAU_Games"), "demo": ("SuperGAU Demos", "SuperGAU_Demos")}

# disks whose file names do not match FILES.BBS
OVERRIDE = {
    ("STGAMES4", "SHAOLIN.ZIP"): "Chambers of Shaolin",
    ("STGAMES4", "SKIDROW1.ZIP"): "Skid Row Demo (A)",
    ("STGAMES4", "SKIDROW2.ZIP"): "Skid Row Demo (B)",
    ("STGAMES4", "SYNTAXTE.ZIP"): "Syntax Terror Demo",
}
NOTES = {"GAU_718.ZIP": "Image inside the ZIP is a JAM-packed .JPK, not an .MSA/.ST; Hatari cannot boot it as is."}

NOTE = re.compile(r"^(FCOPY|ACOPY|DISKCOPY|\(|PROT|MSA |\d\.?\s*DISK|ODER|L.UFT|LAEUFT)", re.I)
SMALL = {"of", "the", "and", "in", "to", "a", "for", "vs", "on"}
ACR = r"\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|St|Tv|Pc|Usa|Uk|Ocs|Ste|Tt|Rpg|Ads|Atf|Ums)\b"


def disk_folders(iso, use_joliet):
    """Return {folder name: {file name: ISO path}} for STDEMOS and STGAMES*."""
    key = "joliet_path" if use_joliet else "iso_path"
    folders = {}
    for root, _dirs, files in iso.walk(**{key: "/"}):
        name = root.strip("/")
        if "/" in name or not re.fullmatch(r"(?i)STDEMOS|STGAMES\d", name):
            continue
        folders[name] = {f.split(";")[0]: f"{root}/{f}" for f in files}
    return folders


def read_bbs(iso, use_joliet, files):
    """Return {ZIPNAME: [description lines]} from the FILES.BBS of a folder."""
    name = next((n for n in files if n.lower() == "files.bbs"), None)
    listed, current = {}, None
    if name:
        buffer = io.BytesIO()
        iso.get_file_from_iso_fp(buffer, **{"joliet_path" if use_joliet else "iso_path": files[name]})
        for line in buffer.getvalue().decode("cp437", errors="replace").splitlines():
            if not line.strip():
                continue
            match = re.match(r"^([A-Za-z0-9_\-]+\.[A-Za-z0-9]{3})\s+(.*)$", line)
            if match and not line.startswith(" "):
                current = match.group(1).upper()
                listed[current] = [match.group(2).strip()]
            elif current:
                listed[current].append(line.strip())
    return listed


def strip_parens(text):
    """Remove parenthesised text, including nested and unclosed groups."""
    previous = None
    while previous != text:
        previous, text = text, re.sub(r"\([^()]*\)", " ", text)
    return re.sub(r"\(.*$", " ", text)


def pretty(text):
    """Convert an upper-case title to title case, keeping roman numerals and acronyms upper case."""
    words = []
    for index, word in enumerate(text.lower().split()):
        words.append(word if (word in SMALL and index) else re.sub(r"^([a-z])", lambda m: m.group(1).upper(), word))
    result = re.sub(ACR, lambda m: m.group(1).upper(), " ".join(words))
    return re.sub(r"(\w)'S\b", lambda m: m.group(1) + "'s", result).replace("`", "'")


def title(line):
    """Return the cleaned game title of a FILES.BBS line, or None for notes and comments."""
    raw = re.split(r"\s{2,}", line.strip())[0]
    if not raw or NOTE.search(raw) or re.search(r"[a-zäöüß]", raw):  # notes / German comments
        return None
    text = strip_parens(raw).replace('"', "")
    text = re.sub(r"\s*\+\s*(FULL\s+)?DOCS?\b.*$", "", text, flags=re.I).strip(" ,-")
    text = re.sub(r"\s+", " ", text)
    letter = re.search(r",\s*([A-F])$", text)
    text = text[:letter.start()] if letter else text
    if len(re.sub(r"[^A-Za-z0-9]", "", text)) < 2:
        return None
    return pretty(text) + (f" ({letter.group(1)})" if letter else "")


def disk_titles(zip_name, folder, lines):
    """Return the list of game titles for a ZIP from its FILES.BBS lines."""
    key = (folder.upper(), zip_name.upper())
    if key in OVERRIDE:
        return [OVERRIDE[key]]
    titles = [t for t in (title(line) for line in lines) if t]
    if titles:
        return titles
    raws = [re.split(r"\s{2,}", line.strip())[0] for line in lines]
    return [pretty(strip_parens(r).replace('"', "").strip()) for r in raws[:1] if r.strip()] \
        or ["Unknown (no description in FILES.BBS)"]


def import_iso(iso_path, floppies_directory, catalogue_target, progress=None):
    """Copy the SuperGAU disks from the ISO into the floppies folder and write their catalogue.

    `progress(done, total)` is called after each disk. Files already present with the same size are skipped.
    Returns `(copied, skipped)`; raises ValueError if the file is not a SuperGAU ISO.
    """
    try:
        import pycdlib
    except ImportError as error:
        raise ValueError("Importing from an ISO needs pycdlib: pip install pycdlib") from error

    floppies_directory = Path(floppies_directory)
    iso = pycdlib.PyCdlib()
    try:
        iso.open(str(iso_path))
    except Exception as error:  # pycdlib raises its own exception types for non-ISO files
        raise ValueError(f"Cannot open the ISO: {error}") from error
    try:
        use_joliet = iso.has_joliet()
        key = "joliet_path" if use_joliet else "iso_path"
        folders = disk_folders(iso, use_joliet)
        jobs = [
            (folder, folders[folder], zip_name)
            for folder in sorted(folders, key=str.lower)
            for zip_name in sorted(f for f in folders[folder] if f.lower().endswith(".zip"))
        ]
        if not jobs:
            raise ValueError("No STDEMOS or STGAMES folders with ZIP disks were found. Is this the SuperGAU ISO?")
        catalogue, copied, skipped = {}, 0, 0
        listings = {}
        for done, (folder, files, zip_name) in enumerate(jobs, 1):
            if folder not in listings:
                listings[folder] = read_bbs(iso, use_joliet, files)
            team, team_folder = TEAMS["demo" if folder.upper() == "STDEMOS" else "game"]
            target = floppies_directory / team_folder / zip_name
            size = iso.get_record(**{key: files[zip_name]}).data_length
            if target.is_file() and target.stat().st_size == size:
                skipped += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_name(target.name + ".part")
                with partial.open("wb") as output:
                    iso.get_file_from_iso_fp(output, **{key: files[zip_name]})
                partial.replace(target)
                copied += 1
            titles = disk_titles(zip_name, folder, listings[folder].get(zip_name.upper(), []))
            entry = {
                "Games": ", ".join(dict.fromkeys(titles)), "File": zip_name, "Team": team,
                "Folder": team_folder, "Source": "supergau", "Origin": folder.upper(),
            }
            if zip_name.upper() in NOTES:
                entry["Note"] = NOTES[zip_name.upper()]
            catalogue[f"{team} {Path(zip_name).stem.upper()}"] = entry
            if progress:
                progress(done, len(jobs))
    finally:
        iso.close()
    catalogue_target = Path(catalogue_target)
    catalogue_target.parent.mkdir(parents=True, exist_ok=True)
    with catalogue_target.open("w", encoding="utf-8") as output:
        json.dump(catalogue, output, indent=1, ensure_ascii=False)
    return copied, skipped
