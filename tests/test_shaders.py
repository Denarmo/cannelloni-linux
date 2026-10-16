"""Compile and exercise the portable renderer without SDL or device hardware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShaderTests(unittest.TestCase):
    def test_portable_renderer(self):
        compiler = shutil.which(os.environ.get("CC", "cc")) or shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            self.skipTest("A C99 compiler is required for the shader renderer test")
        with tempfile.TemporaryDirectory(prefix="cannelloni-shaders-") as build:
            executable = Path(build) / ("shader-test.exe" if os.name == "nt" else "shader-test")
            subprocess.run([
                compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
                "-I", str(ROOT / "workspace/all/minarch"),
                str(ROOT / "tests/shader_harness.c"),
                str(ROOT / "workspace/all/minarch/shader.c"),
                "-lm", "-pthread", "-o", str(executable),
            ], check=True, capture_output=True, text=True)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
