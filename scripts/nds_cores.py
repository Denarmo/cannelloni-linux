"""Select platform-built NDS cores without renaming or architecture fallbacks."""
from pathlib import Path
import struct

NDS_CORES = ("melonds_libretro.so", "desmume2015_libretro.so", "desmume_libretro.so")


def elf_target(path):
    with Path(path).open("rb") as stream:
        header = stream.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF" or header[4] not in (1, 2) or header[5] not in (1, 2):
        raise ValueError(f"Not a valid ELF binary: {path}")
    endian = "<" if header[5] == 1 else ">"
    return header[4], header[5], struct.unpack_from(endian + "H", header, 18)[0]


def collect_nds_cores(platforms, root=Path(".")):
    """Require a real NDS core for every platform and match it to its frontend."""
    root = Path(root)
    cores = {}
    for platform in platforms:
        output = root / "workspace" / platform / "cores/output"
        if not any((output / name).is_file() for name in NDS_CORES):
            raise FileNotFoundError(f"Build the {platform} NDS libretro core before packaging: {output}")
        frontend = root / "workspace/all/minarch/build" / platform / "minarch.elf"
        target = elf_target(frontend)
        for core_name in NDS_CORES:
            source = output / core_name
            if not source.is_file():
                continue
            if elf_target(source) != target:
                raise ValueError(f"NDS core architecture does not match {platform} minarch: {source}")
            cores[f".system/{platform}/cores/{core_name}"] = source.read_bytes()
    return cores
