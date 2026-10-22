"""Catalogue of compilation disks and lookup of the images present on disk."""

import json
from pathlib import Path


DISK_EXTENSIONS = {".msa", ".st", ".zip"}


class DiskLibrary:
    """Maps catalogue disk names to image files in the per-team floppies folders."""
    def __init__(self, floppies_directory, catalogue_path):
        """Load the JSON catalogue and map each disk to its team folder."""
        self.floppies_directory = Path(floppies_directory)
        self.index_cache = {}
        with Path(catalogue_path).open(encoding="utf-8") as catalogue:
            self.catalogue = json.load(catalogue)

        self.team_names = {}
        self.disk_teams = {}
        for disk_name, details in self.catalogue.items():
            self.disk_teams[disk_name] = details["Folder"]
            self.team_names[details["Folder"]] = details["Team"]

    def team_index(self, team):
        """Casefolded name and stem lookups for a team directory.

        Rebuilt only when the directory's modification time changes, so
        repeated lookups cost one stat instead of a full directory listing.
        """
        directory = self.floppies_directory / team
        try:
            mtime = directory.stat().st_mtime_ns
        except OSError:
            self.index_cache.pop(team, None)
            return None
        cached = self.index_cache.get(team)
        if cached is not None and cached[0] == mtime:
            return cached[1], cached[2]

        by_name = {}
        by_stem = {}
        for candidate in directory.iterdir():
            if not candidate.is_file():
                continue
            by_name.setdefault(candidate.name.casefold(), candidate)
            if candidate.suffix.casefold() in DISK_EXTENSIONS:
                by_stem.setdefault(candidate.stem.casefold(), candidate)
        self.index_cache[team] = (mtime, by_name, by_stem)
        return by_name, by_stem

    def disk_path(self, disk_name):
        """Return the expected image path for a catalogue disk, or None if the name is unknown.

        Matching is case-insensitive and tolerates a different disk-image extension
        (.msa/.st/.zip); the path may not exist.
        """
        team = self.disk_teams.get(disk_name)
        if team is None:
            return None
        team_directory = self.floppies_directory / team
        filename = self.catalogue[disk_name]["File"]
        expected_path = team_directory / filename
        index = self.team_index(team)
        if index is None:
            return expected_path
        by_name, by_stem = index
        if filename.casefold() in by_name:
            return by_name[filename.casefold()]

        file_path = Path(filename)
        if file_path.suffix.casefold() in DISK_EXTENSIONS:
            return by_stem.get(file_path.stem.casefold(), expected_path)
        return expected_path

    def teams(self):
        """Return `(folder, display name)` for every catalogue team, sorted by name."""
        return sorted(self.team_names.items(), key=lambda team: team[1].casefold())

    def is_available(self, disk_name):
        """Return True if the disk's image file exists in the floppies folder."""
        disk_path = self.disk_path(disk_name)
        return disk_path is not None and disk_path.is_file()

    def available_disks(self):
        """Return `{disk name: games}` for catalogue disks whose images are present.

        Only teams that have a sub-folder in the floppies folder are examined.
        """
        present_teams = self.present_teams()
        return {
            disk_name: details["Games"]
            for disk_name, details in self.catalogue.items()
            if details["Folder"] in present_teams and self.is_available(disk_name)
        }

    def present_teams(self):
        """Return the catalogue team folders that exist in the floppies folder."""
        try:
            return {
                entry.name for entry in self.floppies_directory.iterdir()
                if entry.is_dir() and entry.name in self.team_names
            }
        except OSError:
            return set()

    def search(self, query):
        """Search game lists case-insensitively for `query`.

        Returns `(collection, all_results)` as lists of `(disk name, games)`; the first holds only disks you own.
        """
        term = query.casefold()
        all_results = [
            (disk_name, details["Games"])
            for disk_name, details in self.catalogue.items()
            if term in details["Games"].casefold()
        ]
        collection_results = [
            (disk_name, games)
            for disk_name, games in all_results
            if self.is_available(disk_name)
        ]
        return collection_results, all_results
