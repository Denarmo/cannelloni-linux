"""Regenerate all NDS launchers from the shared, menu-integrated launcher."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts/templates/nds_launch.sh"


def write_launchers():
    content = TEMPLATE.read_bytes().replace(b"\r\n", b"\n")
    paths = sorted(ROOT.glob("skeleton/SYSTEM/*/paks/Emus/NDS.pak/launch.sh"))
    paths += sorted(ROOT.glob("skeleton/EXTRAS/Emus/*/NDS.pak/launch.sh"))
    for path in paths:
        path.write_bytes(content)
    return paths


if __name__ == "__main__":
    for path in write_launchers():
        print("Updated:", path.relative_to(ROOT))
