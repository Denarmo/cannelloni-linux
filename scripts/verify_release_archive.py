"""Verify rebuilt release payloads without relying on old MinUI ELF offsets."""
import argparse
from contextlib import ExitStack
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile

from create_release_archives import PLATFORMS, load_built_frontends
from nds_cores import NDS_CORES, NDS_RUNTIMES
from release_version import release_version


def elf_target(data):
    if len(data) < 20 or data[:4] != b"\x7fELF" or data[4] not in (1, 2) or data[5] not in (1, 2):
        raise ValueError("Invalid ELF header in release")
    return data[4], data[5], struct.unpack_from("<H" if data[5] == 1 else ">H", data, 18)[0]


def verify_payload(payload, platforms=PLATFORMS, builds=None):
    names = payload.namelist()
    if payload.read(".system/version.txt").decode("utf-8").splitlines()[0] != release_version():
        raise ValueError("OS version does not match VERSION")
    for platform in platforms:
        base = f".system/{platform}/"
        for name in ("cannelloni", "minarch"):
            filename = base + f"bin/{name}.elf"
            if names.count(filename) != 1:
                raise ValueError(f"Missing or duplicate frontend: {filename}")
            data = payload.read(filename)
            elf_target(data)
            if builds is not None and data != builds[(platform, name)]:
                raise ValueError(f"Frontend differs from current build: {filename}")
        frontend = payload.read(base + "bin/minarch.elf")
        if b"cannelloni_shader_mask" not in frontend:
            raise ValueError(f"Shader-enabled minarch missing for {platform}")
        cores = [base + "cores/" + name for name in NDS_CORES if base + "cores/" + name in names]
        if not cores:
            raise ValueError(f"NDS libretro core missing for {platform}")
        for core in cores:
            if names.count(core) != 1 or elf_target(payload.read(core)) != elf_target(frontend):
                raise ValueError(f"Duplicate or incompatible NDS core: {core}")
        for library in NDS_RUNTIMES.get(platform, ()):
            filename = base + "lib/" + library
            if names.count(filename) != 1 or elf_target(payload.read(filename)) != elf_target(frontend):
                raise ValueError(f"Missing, duplicate or incompatible SDK runtime: {filename}")
        launcher = payload.read(base + "paks/Emus/NDS.pak/launch.sh")
        if b'EMU_PREF="libretro"' not in launcher or b"minarch.elf" not in launcher:
            raise ValueError(f"NDS launcher does not default to minarch: {platform}")
        if b"-minarch_screen_effect" in payload.read(base + "system.cfg"):
            raise ValueError(f"Obsolete hardware effect lock: {platform}")
    for filename in (".system/common/shaders/README.txt", ".system/common/shaders/LICENSE.txt"):
        payload.getinfo(filename)
    for filename in names:
        if filename.startswith(".system/res/themes/") and Path(filename).name in ("minarch.elf", "minui.elf", "cannelloni.elf"):
            raise ValueError(f"Theme may overwrite current frontend: {filename}")


def verify_archive(path, workspace=None):
    builds = load_built_frontends(PLATFORMS, workspace) if workspace is not None else None
    with ExitStack() as stack:
        archive = stack.enter_context(zipfile.ZipFile(path))
        if Path(path).name == "Cannelloni-Installer.zip":
            allowed = {"Cannelloni.zip", "Cannoli.zip", "Cannelloni-Installer.exe",
                       "Cannelloni-Installer.bat", "Cannelloni-Installer.sh", "cannelloni_installer.py", "README.txt", "VERSION"}
            if set(archive.namelist()) - allowed:
                raise ValueError("Installer contains loose OS files outside its payload")
            if archive.read("VERSION").decode("utf-8").strip() != release_version():
                raise ValueError("Installer version does not match VERSION")
        for _ in range(3):
            nested = next((name for name in ("Cannelloni.zip", "Cannoli.zip") if name in archive.namelist()), None)
            if nested is None:
                break
            temporary = stack.enter_context(tempfile.TemporaryFile())
            with archive.open(nested) as source:
                shutil.copyfileobj(source, temporary)
            temporary.seek(0)
            archive = stack.enter_context(zipfile.ZipFile(temporary))
        verify_payload(archive, builds=builds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--built-workspace", type=Path, help="Compare frontend bytes against this build workspace")
    args = parser.parse_args()
    verify_archive(args.archive, args.built_workspace)
    print(f"Verified current frontends, NDS cores and shader assets: {args.archive}")
