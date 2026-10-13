"""Supply Buildroot archives using the host's current HTTPS implementation.

Legacy SDK containers must retain their old libc/compiler, but their wget TLS
stack cannot negotiate the current buildroot.org endpoint. Upstream copies
support/ into /root, so prefetch the exact archive there before building Docker.
"""
import argparse
import hashlib
from pathlib import Path
import urllib.request

BUILDROOT = {
    "trimuismart": ("2016.05", "BUILDROOT_VERSION", "5906e378b6b918266d10c95ba4bc353691c7b64827cc132961f8845abb3f6a40"),
    "m17": ("2018.02-rc3", "BUILDROOT_NAME", "e8c94bf6441d8f08acc22ae1694e125c9d1e1a8e906bd15700edd92caeb02444"),
}


def prepare(platform, directory):
    if platform not in BUILDROOT:
        return
    version, variable, checksum = BUILDROOT[platform]
    support = Path(directory) / "support"
    script = support / "build-toolchain.sh"
    content = script.read_text()
    download = f"wget https://buildroot.org/downloads/${variable}.tar.gz"
    guarded = f'[ -f "${variable}.tar.gz" ] || {download}'
    if download not in content:
        raise ValueError(f"Unexpected upstream download command in {script}")
    archive = support / f"buildroot-{version}.tar.gz"
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        print(f"Downloading {archive.name} with host HTTPS...")
        with urllib.request.urlopen(f"https://buildroot.org/downloads/{archive.name}") as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != checksum:
            raise ValueError(f"Buildroot archive checksum mismatch: {archive.name}")
        archive.write_bytes(data)
    if guarded not in content:
        script.write_text(content.replace(download, guarded), newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    prepare(args.platform, args.directory)
