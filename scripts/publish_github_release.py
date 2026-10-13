"""Publish locally built and verified release archives with GitHub CLI."""
import argparse
import json
from pathlib import Path
import subprocess

from release_version import ROOT, release_version
from verify_release_archive import verify_archive

REPO = "Denarmo/cannelloni-linux"


def publish(notes_file, workspace):
    version = release_version()
    tag = "v" + version
    notes_file = Path(notes_file).resolve()
    if not notes_file.is_file():
        raise FileNotFoundError(notes_file)
    assets = [ROOT / "releases" / "Cannelloni-Installer.zip"]
    for asset in assets:
        verify_archive(asset, workspace)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    exists = subprocess.run(["gh", "release", "view", tag, "--repo", REPO],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if exists:
        subprocess.run(["gh", "release", "edit", tag, "--repo", REPO,
                        "--title", f"Cannelloni {version}", "--notes-file", str(notes_file), "--latest"], check=True)
        subprocess.run(["gh", "release", "upload", tag, "--repo", REPO,
                        *map(str, assets), "--clobber"], check=True)
        # Older releases offered duplicate manual-install downloads. The OS ZIP
        # is now available inside the installer; remove these only after upload.
        published = json.loads(subprocess.check_output(
            ["gh", "release", "view", tag, "--repo", REPO, "--json", "assets"], text=True))
        obsolete = {f"Cannelloni-{version}.zip", "Cannelloni.zip"}
        for asset in published["assets"]:
            if asset["name"] in obsolete:
                subprocess.run(["gh", "release", "delete-asset", tag, asset["name"],
                                "--repo", REPO, "--yes"], check=True)
    else:
        subprocess.run(["gh", "release", "create", tag, "--repo", REPO,
                        "--target", commit, "--title", f"Cannelloni {version}",
                        "--notes-file", str(notes_file), "--latest", *map(str, assets)], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes-file", type=Path, default=ROOT / "RELEASE_NOTES.md")
    parser.add_argument("--built-workspace", type=Path, default=ROOT / "workspace")
    args = parser.parse_args()
    publish(args.notes_file, args.built_workspace)
