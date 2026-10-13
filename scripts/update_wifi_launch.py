"""Distribute the shared Wi-Fi connection UI to supported device paks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("miyoomini", "my282", "my355", "rg35xxplus", "tg5040")


def main():
    source = (ROOT / "scripts/templates/wifi_launch.sh").read_bytes()
    for platform in PLATFORMS:
        (ROOT / "skeleton/EXTRAS/Settings" / platform / "Wi-Fi.pak/launch.sh").write_bytes(source)


if __name__ == "__main__":
    main()
