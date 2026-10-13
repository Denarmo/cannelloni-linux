"""Exercise the handheld shader Settings menu with a scripted list picker."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_shader_paks import SHADER_SCRIPT_TEMPLATE


def find_shell():
    shell = shutil.which("sh")
    fallback = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/sh.exe"
    return shell or (str(fallback) if fallback.is_file() else None)


@unittest.skipUnless(find_shell(), "A POSIX shell is required for Settings menu tests")
class ShaderSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cannelloni shader settings ")
        self.addCleanup(self.temp.cleanup)
        self.sd = Path(self.temp.name)
        self.shared = self.sd / ".userdata/shared/.cannelloni"
        self.shared.mkdir(parents=True)
        self.conf = self.shared / "shader.conf"
        self.override = self.sd / ".userdata/miyoomini/NDS/minarch.cfg"
        self.override.parent.mkdir(parents=True)
        self.original_override = "minarch_screen_effect = 7\nminarch_screen_sharpness = 2\n"
        self.override.write_text(self.original_override, newline="\n")
        self.script = self.sd / "launch.sh"
        self.script.write_text(SHADER_SCRIPT_TEMPLATE, encoding="utf-8", newline="\n")
        self.write_script(self.sd / ".system/miyoomini/bin/cannelloni-list", '''
while [ $# -gt 0 ]; do
    case "$1" in
        --file) INPUT="$2"; shift ;;
        --write-location) OUTPUT="$2"; shift ;;
    esac
    shift
done
[ "$TEST_CANCEL" = "1" ] && exit 1
case "$INPUT" in
    *shader-menu-list*) printf '%s\\n' "$TEST_MENU" > "$OUTPUT" ;;
    *) printf '%s\\n' "$TEST_CHOICE" > "$OUTPUT" ;;
esac
''')
        self.write_script(self.sd / ".system/miyoomini/bin/say.elf", "exit 0")
        self.write_script(self.sd / "bin/sync", "exit 0")
        self.env = dict(os.environ, SDCARD_PATH=self.sd.as_posix(), PLATFORM="miyoomini")
        self.env["PATH"] = str(self.sd / "bin") + os.pathsep + str(Path(find_shell()).parent) + os.pathsep + self.env.get("PATH", "")

    def write_script(self, path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
        path.chmod(0o755)

    def choose(self, menu, choice, cancel=False):
        env = dict(self.env, TEST_MENU=menu, TEST_CHOICE=choice, TEST_CANCEL="1" if cancel else "0")
        result = subprocess.run([find_shell(), str(self.script)], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.override.read_text(), self.original_override)

    def read_config(self, path=None):
        return dict(line.split("=", 1) for line in (path or self.conf).read_text().splitlines())

    def test_presets_remain_distinct_and_keep_configured_parameters(self):
        self.conf.write_text("intensity=75\nsharpness=2\n")
        presets = [
            ("None", "none"), ("Simple Scanlines", "line"), ("Simple LCD Grid", "grid"),
            ("CRT-Cannelloni", "crt-cannelloni"), ("CRT-Cannelloni Lite", "crt-cannelloni-lite"),
            ("CRT-EasyMode", "crt-easymode"), ("CRT-Aperture", "crt-aperture"),
            ("CRT-Geom", "crt-geom"), ("CRT-Lottes Fast", "crt-lottes-fast"),
            ("Zfast-CRT", "zfast-crt"), ("LCD3x", "lcd3x"), ("Zfast-LCD", "zfast-lcd"),
            ("Dot Matrix", "dot"), ("Scanlines", "scanline"), ("Sharp Bilinear Simple", "sharp-bilinear-simple"),
        ]
        for effect, (label, preset) in enumerate(presets):
            with self.subTest(preset=preset):
                self.choose("1.", label)
                config = self.read_config()
                self.assertEqual(config["preset"], preset)
                self.assertEqual(config["effect"], str(effect))
                self.assertEqual(config["intensity"], "75")
                self.assertEqual(config["sharpness"], "2")
                if preset == "crt-cannelloni-lite":
                    self.assertTrue(config["glslp"].endswith("/crt-cannelloni/crt-cannelloni-lite.glslp"))
                elif effect > 2:
                    self.assertTrue(config["glslp"].endswith(f"/{preset}/{preset}.glslp"))
                else:
                    self.assertNotIn("glslp", config)

    def test_parameters_write_shared_defaults_without_erasing_preset(self):
        self.conf.write_text("preset=crt-cannelloni\n")
        parameters = [
            ("Scanline Intensity: Authentic (75%)", "intensity", "75"),
            ("Curvature: Arcade CRT Tube (15%)", "curvature", "arcade"),
            ("Sharpness: Soft (Bilinear Blur)", "sharpness", "2"),
            ("Brightness: Bright (125%)", "brightness", "125"),
            ("Mask Strength: Strong (75%)", "mask", "75"),
            ("Glow: Balanced (50%)", "glow", "50"),
        ]
        for label, key, value in parameters:
            with self.subTest(parameter=key):
                self.choose("2.", label)
                self.assertEqual(self.read_config()[key], value)
                self.assertEqual(self.read_config()["preset"], "crt-cannelloni")

    def test_family_presets_only_write_family_defaults(self):
        for choice, family, preset, effect in [
            ("Nintendo DS", "nds", "zfast-lcd", "11"),
            ("Game Boy", "handheld", "lcd3x", "10"),
            ("Retro Home Consoles", "console", "crt-cannelloni", "3"),
        ]:
            with self.subTest(family=family):
                self.choose("3.", choice)
                config = self.read_config(self.shared / f"shader_{family}.conf")
                self.assertEqual(config["preset"], preset)
                self.assertEqual(config["effect"], effect)
        self.assertFalse(self.conf.exists())

    def test_reset_clears_shared_defaults_and_keeps_game_overrides(self):
        self.conf.write_text("preset=crt-cannelloni\nintensity=75\n")
        for family in ("nds", "handheld", "console"):
            (self.shared / f"shader_{family}.conf").write_text("preset=grid\n")
        self.choose("4.", "")
        self.assertEqual(self.read_config(), {"preset": "none", "effect": "0"})
        for family in ("nds", "handheld", "console"):
            self.assertFalse((self.shared / f"shader_{family}.conf").exists())

    def test_cancel_leaves_shared_defaults_unchanged(self):
        self.conf.write_text("preset=crt-cannelloni\n")
        self.choose("1.", "LCD3x", cancel=True)
        self.assertEqual(self.read_config(), {"preset": "crt-cannelloni"})


if __name__ == "__main__":
    unittest.main()
