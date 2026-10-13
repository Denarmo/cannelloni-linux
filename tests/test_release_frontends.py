"""Ensure releases/themes cannot silently restore the upstream frontends."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from create_release_archives import load_built_frontends, add_built_frontends, add_dir_to_zip


class ReleaseFrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cannelloni frontends ")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.expected = {}
        for platform in ("miyoomini", "rg35xxplus"):
            for name in ("cannelloni", "minarch"):
                path = self.workspace / "all" / name / "build" / platform / (name + ".elf")
                path.parent.mkdir(parents=True)
                data = b"\x7fELF" + bytes(48) + (platform + name).encode()
                path.write_bytes(data)
                self.expected[(platform, name)] = data

    def test_release_frontends_preserve_exact_build_bytes(self):
        binaries = load_built_frontends(("miyoomini", "rg35xxplus"), str(self.workspace))
        self.assertEqual(binaries, self.expected)
        output = io.BytesIO()
        written = set()
        with zipfile.ZipFile(output, "w") as archive:
            add_built_frontends(archive, binaries, written)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(len(archive.namelist()), 6)
            self.assertEqual(written, set(archive.namelist()))
            for (platform, name), data in self.expected.items():
                filename = f".system/{platform}/bin/{name}.elf"
                self.assertEqual(archive.read(filename), data)
                self.assertEqual(archive.getinfo(filename).external_attr >> 16, 0o755)
                if name == "cannelloni":
                    self.assertEqual(archive.read(f".system/{platform}/bin/minui.elf"), data)

    def test_missing_build_is_rejected_instead_of_using_upstream_binary(self):
        (self.workspace / "all/minarch/build/miyoomini/minarch.elf").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "Missing rebuilt minarch for miyoomini"):
            load_built_frontends(("miyoomini",), str(self.workspace))

    def test_non_elf_build_is_rejected(self):
        (self.workspace / "all/cannelloni/build/miyoomini/cannelloni.elf").write_bytes(b"invalid executable")
        with self.assertRaisesRegex(ValueError, "Not a Linux ELF executable"):
            load_built_frontends(("miyoomini",), str(self.workspace))

    def test_theme_frontends_are_not_packaged(self):
        theme = self.workspace / "themes/#e74c3c/bin/miyoomini"
        theme.mkdir(parents=True)
        for name in ("minarch.elf", "minui.elf", "cannelloni.elf", "cannelloni-list"):
            (theme / name).write_bytes(name.encode())
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            add_dir_to_zip(archive, str(self.workspace / "themes"), ".system/res/themes", set())
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist(), [".system/res/themes/#e74c3c/bin/miyoomini/cannelloni-list"])

    def test_changing_theme_preserves_current_frontends(self):
        shell = shutil.which("sh")
        fallback = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/sh.exe"
        shell = shell or (str(fallback) if fallback.is_file() else None)
        if not shell:
            self.skipTest("A POSIX shell is required to run accent application")
        sd = self.workspace / "sd"
        shared = sd / ".userdata/shared/.cannelloni"
        shared.mkdir(parents=True)
        current = sd / ".system/miyoomini/bin"
        theme = sd / ".system/res/themes/#e74c3c/bin/miyoomini"
        current.mkdir(parents=True)
        theme.mkdir(parents=True)
        for name in ("minarch.elf", "minui.elf", "cannelloni.elf"):
            (current / name).write_bytes(b"current " + name.encode())
            (theme / name).write_bytes(b"stale " + name.encode())
        (theme / "cannelloni-list").write_bytes(b"red widget")
        env = dict(os.environ, SDCARD_PATH=sd.as_posix(), PLATFORM="miyoomini")
        env["PATH"] = str(Path(shell).parent) + os.pathsep + env.get("PATH", "")
        result = subprocess.run([shell, str(ROOT / "skeleton/SYSTEM/common/apply_accent_color.sh"), "#e74c3c"],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ("minarch.elf", "minui.elf", "cannelloni.elf"):
            self.assertEqual((current / name).read_bytes(), b"current " + name.encode())
        self.assertEqual((current / "cannelloni-list").read_bytes(), b"red widget")
        self.assertEqual((shared / "accent_color.txt").read_text(), "#e74c3c\n")


if __name__ == "__main__":
    unittest.main()
