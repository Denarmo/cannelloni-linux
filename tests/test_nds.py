"""Exercise DS launcher selection and release core validation without a device."""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nds_cores import collect_nds_cores


def find_shell():
    shell = shutil.which("sh")
    if shell:
        return shell
    candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/sh.exe"
    return str(candidate) if candidate.is_file() else None


def write_script(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + content + "\n", encoding="utf-8", newline="\n")
    path.chmod(0o755)


@unittest.skipUnless(find_shell(), "A POSIX shell is needed for launcher tests")
class NDSLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cannelloni nds ")
        self.addCleanup(self.temp.cleanup)
        self.sd = Path(self.temp.name)
        self.system = self.sd / ".system/miyoomini"
        self.cores = self.system / "cores"
        self.cores.mkdir(parents=True)
        self.record = self.sd / "launched.txt"
        self.error = self.sd / "error.txt"
        self.pref = self.sd / ".userdata/shared/.cannelloni/emu_nds.txt"
        self.pref.parent.mkdir(parents=True)
        self.rom = self.sd / "Test Game.nds"
        rom = bytearray(256)
        struct.pack_into("<I", rom, 128, len(rom))
        self.rom.write_bytes(rom)
        self.frontend = self.system / "bin/minarch.elf"
        write_script(self.frontend, 'printf "%s\\n" "libretro" "$1" "$2" > "$TEST_RECORD"\nexit "${TEST_EXIT:-0}"')
        write_script(self.system / "bin/say.elf", 'printf "%s\\n" "$1" > "$TEST_ERROR"')
        write_script(self.sd / "bin/nice", 'shift\nexec "$@"')
        write_script(self.sd / "bin/sync", 'exit 0')
        drastic = self.sd / "Emus/miyoomini/NDS-Drastic.pak"
        write_script(drastic / "drastic", 'exit 0')
        write_script(drastic / "launch.sh", 'printf "%s\\n" "drastic" "$1" > "$TEST_RECORD"')
        self.env = dict(os.environ, SDCARD_PATH=self.sd.as_posix(), PLATFORM="miyoomini",
                        TEST_RECORD=self.record.as_posix(), TEST_ERROR=self.error.as_posix())
        # MSYS receives PATH as a Windows path list, then converts it for sh.
        self.env["PATH"] = str(self.sd / "bin") + os.pathsep + str(Path(find_shell()).parent) + os.pathsep + self.env.get("PATH", "")
        for name in ("CORES_PATH", "SYSTEM_PATH", "USERDATA_PATH", "SHARED_USERDATA_PATH", "BIOS_PATH", "SAVES_PATH", "LOGS_PATH"):
            self.env.pop(name, None)
        (self.cores / "melonds_libretro.so").write_bytes(b"mock core")

    def launch(self):
        return subprocess.run([find_shell(), str(ROOT / "scripts/templates/nds_launch.sh"), self.rom.as_posix()],
                              env=self.env, capture_output=True, text=True, timeout=10)

    def assert_libretro(self, core="melonds_libretro.so"):
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.record.read_text().splitlines(), ["libretro", (self.cores / core).as_posix(), self.rom.as_posix()])

    def test_default_prefers_libretro_even_with_drastic_installed(self):
        self.assert_libretro()

    def test_legacy_packaged_drastic_preference_migrates(self):
        self.pref.write_bytes(b"drastic\r\n")
        self.assert_libretro()
        self.assertEqual(self.pref.read_text(), "libretro\n")

    def test_explicit_standalone_opt_in(self):
        self.pref.write_text("drastic-standalone\n")
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.record.read_text().splitlines(), ["drastic", self.rom.as_posix()])

    def test_missing_standalone_uses_libretro(self):
        self.pref.write_text("drastic-standalone\n")
        (self.sd / "Emus/miyoomini/NDS-Drastic.pak/drastic").unlink()
        self.assert_libretro()

    def test_other_libretro_core_fallback(self):
        (self.cores / "melonds_libretro.so").unlink()
        (self.cores / "desmume2015_libretro.so").write_bytes(b"other core")
        self.assert_libretro("desmume2015_libretro.so")

    def test_missing_core_reports_error_without_starting_drastic(self):
        (self.cores / "melonds_libretro.so").unlink()
        result = self.launch()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())
        self.assertIn("core is missing", self.error.read_text())

    def test_truncated_rom_is_rejected(self):
        self.rom.write_bytes(self.rom.read_bytes()[:200])
        self.assertNotEqual(self.launch().returncode, 0)
        self.assertFalse(self.record.exists())
        self.assertIn("incomplete", self.error.read_text())

    def test_frontend_exit_status_is_preserved(self):
        self.env["TEST_EXIT"] = "23"
        self.assertEqual(self.launch().returncode, 23)

    def test_generated_platform_launchers_match_and_parse(self):
        paths = list(ROOT.glob("skeleton/SYSTEM/*/paks/Emus/NDS.pak/launch.sh"))
        paths += list(ROOT.glob("skeleton/EXTRAS/Emus/*/NDS.pak/launch.sh"))
        template = (ROOT / "scripts/templates/nds_launch.sh").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(len(paths), 13)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(path.read_bytes().replace(b"\r\n", b"\n"), template)
                subprocess.run([find_shell(), "-n", str(path)], check=True, capture_output=True)


class NDSCorePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def binary(self, path, machine=40, bits=1, payload=b""):
        content = bytearray(64)
        content[:6] = b"\x7fELF" + bytes([bits, 1])
        struct.pack_into("<H", content, 18, machine)
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content + payload)
        return path

    def test_real_names_and_platform_specific_bytes_are_preserved(self):
        for platform, machine, bits in (("miyoomini", 40, 1), ("my355", 183, 2)):
            self.binary(f"workspace/all/minarch/build/{platform}/minarch.elf", machine, bits)
            self.binary(f"workspace/{platform}/cores/output/melonds_libretro.so", machine, bits, platform.encode())
        output = collect_nds_cores(["miyoomini", "my355"], self.root)
        self.assertEqual(len(output), 2)
        self.assertTrue(output[".system/my355/cores/melonds_libretro.so"].endswith(b"my355"))
        self.assertTrue(output[".system/miyoomini/cores/melonds_libretro.so"].endswith(b"miyoomini"))

    def test_wrong_architecture_is_rejected(self):
        self.binary("workspace/all/minarch/build/my355/minarch.elf", 183, 2)
        self.binary("workspace/my355/cores/output/melonds_libretro.so", 40, 1)
        with self.assertRaisesRegex(ValueError, "architecture"):
            collect_nds_cores(["my355"], self.root)

    def test_legacy_toolchain_core_keeps_its_actual_name(self):
        self.binary("workspace/all/minarch/build/miyoomini/minarch.elf")
        self.binary("workspace/miyoomini/cores/output/desmume2015_libretro.so")
        output = collect_nds_cores(["miyoomini"], self.root)
        self.assertEqual(list(output), [".system/miyoomini/cores/desmume2015_libretro.so"])

    def test_missing_nds_core_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "NDS libretro"):
            collect_nds_cores(["miyoomini"], self.root)

    def test_rgb30_requires_and_preserves_matching_sdk_runtime(self):
        self.binary("workspace/all/minarch/build/rgb30/minarch.elf", 183, 2)
        self.binary("workspace/rgb30/cores/output/melonds_libretro.so", 183, 2)
        with self.assertRaisesRegex(FileNotFoundError, "SDK runtime"):
            collect_nds_cores(["rgb30"], self.root)
        for library in ("libstdc++.so.6", "libgcc_s.so.1"):
            self.binary("workspace/rgb30/cores/output/runtime/" + library, 183, 2, b"exact SDK runtime")
        output = collect_nds_cores(["rgb30"], self.root)
        self.assertEqual(len(output), 3)
        self.assertTrue(output[".system/rgb30/lib/libstdc++.so.6"].endswith(b"exact SDK runtime"))
        self.binary("workspace/rgb30/cores/output/runtime/libgcc_s.so.1", 40, 1)
        with self.assertRaisesRegex(ValueError, "architecture"):
            collect_nds_cores(["rgb30"], self.root)


@unittest.skipUnless(find_shell(), "A POSIX shell is needed for compiler selection tests")
class NDSCompilerSelectionTests(unittest.TestCase):
    def test_cxx17_probe_selects_matching_core(self):
        with tempfile.TemporaryDirectory(prefix="nds compiler ") as directory:
            root = Path(directory)
            compiler = root / "cross-g++"
            write_script(compiler, 'cat > "$TEST_PROBE"\nexit "$TEST_COMPILER_EXIT"')
            env = dict(os.environ, CROSS_COMPILE=(root / "cross-").as_posix(),
                       TEST_PROBE=(root / "probe.cpp").as_posix())
            env["PATH"] = str(Path(find_shell()).parent) + os.pathsep + env.get("PATH", "")
            for code, expected in (("0", "melonds"), ("1", "desmume2015")):
                with self.subTest(compiler_exit=code):
                    env["TEST_COMPILER_EXIT"] = code
                    result = subprocess.run([find_shell(), str(ROOT / "workspace/all/cores/select-nds-core.sh")],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)
                    self.assertIn("fold expressions", (root / "probe.cpp").read_text())

    def test_missing_cross_compiler_does_not_silently_use_host(self):
        env = dict(os.environ, CROSS_COMPILE="/missing/cross-")
        result = subprocess.run([find_shell(), str(ROOT / "workspace/all/cores/select-nds-core.sh")],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


@unittest.skipUnless(shutil.which("gcc"), "gcc is needed for launcher routing tests")
class NDSRoutingTests(unittest.TestCase):
    def test_builtin_nds_takes_priority_over_old_external_pak(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = (ROOT / "workspace/all/common/utils.c").read_text()
            function = re.search(r"void getEmuPath\(.*?\n\}", source, re.S).group(0)
            harness = root / "routing.c"
            harness.write_text('#include <stdio.h>\n#include <string.h>\n#include <sys/stat.h>\n'
                               f'#define SDCARD_PATH "{root.as_posix()}"\n#define PLATFORM "miyoomini"\n'
                               '#define PAKS_PATH SDCARD_PATH "/.system/miyoomini/paks"\n'
                               'int exists(char *p) { struct stat st; return stat(p, &st) == 0; }\n'
                               + function + '\nint main(int argc, char **argv) { char path[4096]; getEmuPath(argv[1], path); puts(path); }\n')
            executable = root / ("routing.exe" if os.name == "nt" else "routing")
            subprocess.run([shutil.which("gcc"), str(harness), "-o", str(executable)], check=True, capture_output=True)
            for name in ("NDS", "GBA"):
                for pak in (root / f".system/miyoomini/paks/Emus/{name}.pak/launch.sh", root / f"Emus/miyoomini/{name}.pak/launch.sh"):
                    pak.parent.mkdir(parents=True)
                    pak.touch()
            result = subprocess.check_output([str(executable), "NDS"], text=True).strip()
            self.assertEqual(result, (root / ".system/miyoomini/paks/Emus/NDS.pak/launch.sh").as_posix())
            result = subprocess.check_output([str(executable), "GBA"], text=True).strip()
            self.assertEqual(result, (root / "Emus/miyoomini/GBA.pak/launch.sh").as_posix())


if __name__ == "__main__":
    unittest.main()
