"""Verify the installer release and its bundled manual-install OS payload."""
from release_version import ROOT
from verify_release_archive import verify_archive


if __name__ == "__main__":
    archive = ROOT / "releases/Cannelloni-Installer.zip"
    verify_archive(archive, ROOT / "workspace")
    print(f"Verified {archive}")
