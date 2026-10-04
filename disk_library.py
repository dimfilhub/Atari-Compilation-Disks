import json
from pathlib import Path


TEAMS = (
    ("automation", "Automation", "Aut"),
    ("pompey", "Pompey Pirates", "Pom"),
    ("fof", "Flame of Finland", "Fla"),
    ("superior", "Superior", "Sup"),
    ("medway", "Medway Boys", "Med"),
    ("dbug", "D-Bug", "DBu"),
)


class DiskLibrary:
    def __init__(self, data_directory, catalogue_path):
        self.data_directory = Path(data_directory)
        self.floppies_directory = self.data_directory / "floppies"
        self.team_directories = {
            prefix: self.floppies_directory / folder for folder, _, prefix in TEAMS
        }
        for directory in self.team_directories.values():
            directory.mkdir(parents=True, exist_ok=True)

        with Path(catalogue_path).open(encoding="utf-8") as catalogue:
            self.catalogue = json.load(catalogue)

    def disk_path(self, disk_name):
        prefix = disk_name[:3]
        if prefix not in self.team_directories or disk_name not in self.catalogue:
            return None
        team_directory = self.team_directories[prefix]
        filename = self.catalogue[disk_name]["File"]
        expected_path = team_directory / filename
        if expected_path.is_file():
            return expected_path

        for candidate in team_directory.iterdir():
            if candidate.is_file() and candidate.name.casefold() == filename.casefold():
                return candidate

        file_path = Path(filename)
        if file_path.suffix.casefold() in {".msa", ".st"}:
            archive_name = file_path.with_suffix(".zip").name.casefold()
            for candidate in team_directory.iterdir():
                if candidate.is_file() and candidate.name.casefold() == archive_name:
                    return candidate
        return expected_path

    def available_disks(self):
        available = {}
        for disk_name, details in self.catalogue.items():
            disk_path = self.disk_path(disk_name)
            if disk_path is not None and disk_path.is_file():
                available[disk_name] = details["Games"]
        return available

    def search(self, query):
        term = query.casefold()
        all_results = [
            (disk_name, details["Games"])
            for disk_name, details in self.catalogue.items()
            if term in details["Games"].casefold()
        ]
        collection_results = [
            (disk_name, games)
            for disk_name, games in self.available_disks().items()
            if term in games.casefold()
        ]
        return collection_results, all_results
