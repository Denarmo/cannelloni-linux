"""Distribute the canonical portable web service to every supported platform."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    for pak in (ROOT / "skeleton/EXTRAS/Tools").glob("*/Nonna's Kitchen.pak"):
        for source, destination in (
            ("kitchen_launch.sh", "launch.sh"),
            ("kitchen_api.cgi", "web/cgi-bin/api.cgi"),
            ("kitchen_index.html", "web/index.html"),
        ):
            (pak / destination).write_bytes((ROOT / "scripts/templates" / source).read_bytes())


if __name__ == "__main__":
    main()
