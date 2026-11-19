"""Require YYYY.MM.DD[.BUILD] releases: no suffix on the first build of a day, then .1, .2, ..."""
import json
import re
from datetime import date
from pathlib import Path


def validate_version(version: str) -> None:
    """Validate the padded date and the optional unpadded build number.

    The first build of a day has no suffix. A `.0` suffix stays valid for releases published before.
    """
    found = re.fullmatch(r"([0-9]{4})\.([0-9]{2})\.([0-9]{2})(?:\.(0|[1-9][0-9]*))?", version)
    if found is None:
        raise ValueError(f"Version {version} must look like YYYY.MM.DD[.BUILD], e.g. 2026.02.03 or 2026.02.03.1")
    date(*map(int, found.groups()[:3]))


if __name__ == "__main__":
    version = json.loads(Path("custom_components/medication_monitoring/manifest.json").read_text())["version"]
    validate_version(version)
    print(f"Version {version} follows YYYY.MM.DD[.BUILD]")
