"""Verify all current release archives; use verify_release_archive.py for one."""
from release_version import ROOT, release_version
from verify_release_archive import verify_archive


if __name__ == "__main__":
    version = release_version()
    for name in (f"Cannelloni-{version}.zip", "Cannelloni.zip", "Cannelloni-Installer.zip"):
        archive = ROOT / "releases" / name
        verify_archive(archive, ROOT / "workspace")
        print(f"Verified {archive}")
