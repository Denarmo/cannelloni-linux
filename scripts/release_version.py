"""Read the canonical semantic version and validate release inputs."""
import argparse
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def release_version(requested=None, version_file=ROOT / "VERSION"):
    version = Path(version_file).read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"VERSION must contain a semantic version, got {version!r}")
    if requested is None:
        requested = os.environ.get("RELEASE_VERSION", "")
    requested = requested.strip().removeprefix("v")
    if requested and requested != version:
        raise ValueError(f"Requested release {requested!r} differs from VERSION ({version}). Update VERSION before releasing.")
    return version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()
    version = release_version()
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"version={version}\ntag=v{version}\n")
    print(version)
