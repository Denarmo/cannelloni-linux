import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from create_release_archives import PLATFORMS
from verify_release_archive import verify_archive, verify_payload
from release_version import release_version
from nds_cores import NDS_RUNTIMES


def elf(machine=40):
    data = bytearray(52)
    data[:6] = b"\x7fELF\x01\x01"
    struct.pack_into("<H", data, 18, machine)
    return bytes(data)


class ReleaseVerifierTests(unittest.TestCase):
    def payload(self, platforms, change=None):
        files = {
            ".system/version.txt": (release_version() + "\ntest-build\n").encode(),
            ".system/common/shaders/README.txt": b"shader notes",
            ".system/common/shaders/LICENSE.txt": b"shader licenses",
        }
        for platform in platforms:
            base = f".system/{platform}/"
            files.update({
                base + "bin/cannelloni.elf": elf(),
                base + "bin/minarch.elf": elf() + b"cannelloni_shader_mask",
                base + "cores/desmume2015_libretro.so": elf(),
                base + "paks/Emus/NDS.pak/launch.sh": b'EMU_PREF="libretro"\nminarch.elf\n',
                base + "system.cfg": b"minarch_screen_effect = None\n",
            })
            for library in NDS_RUNTIMES.get(platform, ()):
                files[base + "lib/" + library] = elf()
        if change:
            files.update(change)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        data.seek(0)
        return data

    def test_nested_installer_payload_and_older_compiler_core(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Cannelloni-Installer.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Cannelloni.zip", self.payload(PLATFORMS).getvalue())
                archive.writestr("cannelloni_installer.py", b"installer")
                archive.writestr("VERSION", release_version() + "\n")
            verify_archive(path)

    def test_rejects_stale_frontend_core_and_theme(self):
        changes = (
            ({".system/m17/bin/minarch.elf": elf()}, "Shader-enabled"),
            ({".system/m17/cores/desmume2015_libretro.so": elf(183)}, "incompatible"),
            ({".system/res/themes/gold/bin/m17/minarch.elf": elf()}, "Theme may overwrite"),
            ({".system/m17/system.cfg": b"-minarch_screen_effect = None"}, "Obsolete"),
        )
        for change, error in changes:
            with self.subTest(error=error), zipfile.ZipFile(self.payload(("m17",), change)) as archive:
                with self.assertRaisesRegex(ValueError, error):
                    verify_payload(archive, ("m17",))

    def test_rejects_rebuilt_binary_mismatch(self):
        builds = {("m17", "cannelloni"): elf(), ("m17", "minarch"): elf() + b"different build"}
        with zipfile.ZipFile(self.payload(("m17",))) as archive:
            with self.assertRaisesRegex(ValueError, "differs from current build"):
                verify_payload(archive, ("m17",), builds)

    def test_rejects_incompatible_sdk_runtime(self):
        change = {".system/rgb30/lib/libstdc++.so.6": elf(183)}
        with zipfile.ZipFile(self.payload(("rgb30",), change)) as archive:
            with self.assertRaisesRegex(ValueError, "incompatible SDK runtime"):
                verify_payload(archive, ("rgb30",))


if __name__ == "__main__":
    unittest.main()
