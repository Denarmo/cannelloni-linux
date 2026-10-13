import os
import sys
import shutil
import tempfile
import unittest
from unittest import mock
import zipfile
import json
from http.server import HTTPServer
import threading
import urllib.request

# Ensure installer module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "installer")))
import cannelloni_installer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import create_release_archives

class TestCannelloniInstaller(unittest.TestCase):
    def setUp(self):
        self.fixture_dir = tempfile.TemporaryDirectory(prefix="cannelloni_payload_")
        self.addCleanup(self.fixture_dir.cleanup)
        self.payload_path = os.path.join(self.fixture_dir.name, "Cannelloni.zip")
        self.payload_files = {
            ".system/miyoomini/cores/desmume2015_libretro.so": b"test libretro core",
            ".system/miyoomini/bin/minarch.elf": b"test frontend",
            ".system/miyoomini/dat/boot.dat": b"test splash",
            ".system/res/themes/#e74c3c/assets@1x.png": b"test red theme",
            ".system/res/themes/#e74c3c/bin/miyoomini/minarch.elf": b"test red frontend",
            ".system/res/themes/#e74c3c/bin/miyoomini/cannelloni-list": b"test red widget",
            "miyoo/app/MainUI": b"test bootstrap",
            "Settings/miyoomini/Shaders.pak/launch.sh": b"test shader settings",
            "Emus/miyoomini/NDS.pak/launch.sh": b"test DS launcher",
            "README.txt": b"test OS instructions",
        }
        with zipfile.ZipFile(self.payload_path, "w") as archive:
            for name, data in self.payload_files.items():
                archive.writestr(name, data)

    def install_fixture(self, zip_path, target_path):
        with mock.patch.object(cannelloni_installer, "find_cannelloni_zip", return_value=zip_path):
            return cannelloni_installer.perform_installation(
                target_path, "es", "#e74c3c", "miyoominiplus", lambda p: None, lambda s: None
            )

    def test_languages_complete(self):
        """Verify all 6 languages exist and contain all required keys."""
        required_langs = ["en", "es", "fr", "pt_BR", "de", "it"]
        base_keys = set(cannelloni_installer.LANGUAGES["en"].keys())
        for lang in required_langs:
            self.assertIn(lang, cannelloni_installer.LANGUAGES, f"Language {lang} missing from LANGUAGES dict")
            lang_keys = set(cannelloni_installer.LANGUAGES[lang].keys())
            missing = base_keys - lang_keys
            self.assertEqual(len(missing), 0, f"Language {lang} is missing keys: {missing}")

    def test_accent_colors(self):
        """Verify all 7 accent colors are defined with valid hex and rgb values."""
        self.assertEqual(len(cannelloni_installer.ACCENT_COLORS), 7)
        expected_hexes = [
            "#f1c40f", "#e74c3c", "#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#ffffff"
        ]
        actual_hexes = [c["hex"] for c in cannelloni_installer.ACCENT_COLORS]
        self.assertEqual(actual_hexes, expected_hexes)
        for c in cannelloni_installer.ACCENT_COLORS:
            self.assertTrue(c["hex"].startswith("#") and len(c["hex"]) == 7)
            self.assertEqual(len(c["rgb"]), 3)

    def test_device_models(self):
        """Verify all 18 supported handhelds are properly configured."""
        self.assertEqual(len(cannelloni_installer.DEVICES), 18)
        expected_ids = [
            "miyoomini", "miyoominiplus", "my282", "my355", "trimuismart",
            "tg5040", "tg5040_brick", "rg35xx", "rg35xxplus", "rg35xxh",
            "rg35xxsp", "rg28xx", "rgcubexx", "rgb30", "magicmini",
            "zero28", "gkdpixel", "m17"
        ]
        actual_ids = [d["id"] for d in cannelloni_installer.DEVICES]
        self.assertEqual(actual_ids, expected_ids)
        for dev in cannelloni_installer.DEVICES:
            self.assertIn("name", dev)
            self.assertIn("platform", dev)
            self.assertIn("brand", dev)
            self.assertIn("desc", dev)

    def test_drive_detection(self):
        """Verify detect_drives() returns a valid list of drive dictionaries."""
        drives = cannelloni_installer.detect_drives()
        self.assertIsInstance(drives, list)
        for d in drives:
            self.assertIn("path", d)
            self.assertIn("display", d)
            self.assertIn("free", d)

    def test_find_cannelloni_zip(self):
        """Both payload names are discovered next to the script."""
        script_path = os.path.join(self.fixture_dir.name, "cannelloni_installer.py")
        with mock.patch.object(cannelloni_installer, "__file__", script_path):
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), self.payload_path)
            renamed = os.path.join(self.fixture_dir.name, "Cannoli.zip")
            os.rename(self.payload_path, renamed)
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), renamed)

    def test_frozen_installer_prefers_adjacent_payload(self):
        """A bundled payload must win over a stale development build."""
        executable = os.path.join(self.fixture_dir.name, "Cannelloni-Installer.exe")
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", executable):
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), self.payload_path)

    def test_nested_payload_is_the_only_installation_source(self):
        """Outer release copies must not overwrite or supplement payload files."""
        for payload_name in cannelloni_installer.PAYLOAD_NAMES:
            with self.subTest(payload_name=payload_name), tempfile.TemporaryDirectory() as target:
                wrapper = os.path.join(self.fixture_dir.name, "release.zip")
                with zipfile.ZipFile(wrapper, "w") as archive:
                    archive.write(self.payload_path, payload_name)
                    archive.writestr("Emus/miyoomini/NDS.pak/launch.sh", b"stale standalone launcher")
                    archive.writestr(".system/outer-only-file", b"must not be copied")
                    archive.writestr("Cannelloni-Installer.exe", b"installer")
                self.assertTrue(self.install_fixture(wrapper, target))
                with open(os.path.join(target, "Emus", "miyoomini", "NDS.pak", "launch.sh"), "rb") as source:
                    self.assertEqual(source.read(), self.payload_files["Emus/miyoomini/NDS.pak/launch.sh"])
                self.assertFalse(os.path.exists(os.path.join(target, ".system", "outer-only-file")))
                self.assertFalse(os.path.exists(os.path.join(target, payload_name)))
                self.assertFalse(os.path.exists(os.path.join(target, "Cannelloni-Installer.exe")))

    def test_installation_preserves_source_on_target_card(self):
        """Retain source data without leaving a first-boot update candidate."""
        launcher = os.path.join(self.fixture_dir.name, "Cannelloni-Installer.sh")
        with open(launcher, "w") as source:
            source.write("launcher")
        with open(self.payload_path, "rb") as source:
            original = source.read()
        self.assertTrue(self.install_fixture(self.payload_path, self.fixture_dir.name))
        completed = self.payload_path + ".installed"
        self.assertFalse(os.path.exists(self.payload_path))
        with open(completed, "rb") as source:
            self.assertEqual(source.read(), original)
        self.assertFalse(any(name.endswith(".zip") for name in os.listdir(self.fixture_dir.name)))
        self.assertTrue(os.path.isfile(launcher))
        script_path = os.path.join(self.fixture_dir.name, "cannelloni_installer.py")
        with mock.patch.object(cannelloni_installer, "__file__", script_path):
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), completed)
        self.assertTrue(self.install_fixture(completed, self.fixture_dir.name))
        self.assertFalse(os.path.exists(completed + ".installed"))

    def test_preserved_source_does_not_overwrite_an_existing_archive(self):
        completed = self.payload_path + ".installed"
        with open(completed, "wb") as source:
            source.write(b"earlier installation")
        self.assertTrue(self.install_fixture(self.payload_path, self.fixture_dir.name))
        with open(completed, "rb") as source:
            self.assertEqual(source.read(), b"earlier installation")
        self.assertTrue(os.path.isfile(completed + ".1"))
        script_path = os.path.join(self.fixture_dir.name, "cannelloni_installer.py")
        with mock.patch.object(cannelloni_installer, "__file__", script_path):
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), completed + ".1")
            shutil.copyfile(completed + ".1", self.payload_path)
            self.assertEqual(cannelloni_installer.find_cannelloni_zip(), self.payload_path)

    def test_source_outside_target_keeps_its_original_name_and_bytes(self):
        with open(self.payload_path, "rb") as source:
            original = source.read()
        with tempfile.TemporaryDirectory() as target:
            self.assertTrue(self.install_fixture(self.payload_path, target))
        with open(self.payload_path, "rb") as source:
            self.assertEqual(source.read(), original)
        self.assertFalse(os.path.exists(self.payload_path + ".installed"))

    def test_failed_configuration_leaves_source_archive_in_place(self):
        real_open = open

        def fail_settings_write(path, mode="r", *args, **kwargs):
            if str(path).endswith("language.txt") and mode == "w":
                raise OSError("SD card write failed")
            return real_open(path, mode, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=fail_settings_write):
            with self.assertRaisesRegex(OSError, "SD card write failed"):
                self.install_fixture(self.payload_path, self.fixture_dir.name)
        self.assertTrue(os.path.isfile(self.payload_path))
        self.assertFalse(os.path.exists(self.payload_path + ".installed"))

    def test_failed_source_rename_removes_only_its_empty_reservation(self):
        with mock.patch.object(os, "replace", side_effect=OSError("source is busy")):
            with self.assertRaisesRegex(OSError, "source is busy"):
                self.install_fixture(self.payload_path, self.fixture_dir.name)
        self.assertTrue(os.path.isfile(self.payload_path))
        self.assertFalse(os.path.exists(self.payload_path + ".installed"))

    def test_invalid_payload_does_not_install_files(self):
        with zipfile.ZipFile(self.payload_path, "w") as archive:
            archive.writestr("unrelated.txt", b"not an OS")
        with tempfile.TemporaryDirectory() as target:
            with self.assertRaisesRegex(ValueError, "OS payload"):
                self.install_fixture(self.payload_path, target)
            self.assertEqual(os.listdir(target), [])
        with self.assertRaisesRegex(ValueError, "OS payload"):
            self.install_fixture(self.payload_path, self.fixture_dir.name)
        self.assertTrue(os.path.isfile(self.payload_path))
        self.assertFalse(os.path.exists(self.payload_path + ".installed"))

    def test_payload_paths_validated_before_extraction(self):
        with zipfile.ZipFile(self.payload_path, "a") as archive:
            archive.writestr("../outside.txt", b"must not escape target")
        with tempfile.TemporaryDirectory() as target:
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                self.install_fixture(self.payload_path, target)
            self.assertEqual(os.listdir(target), [])

    def test_installer_package_contains_no_loose_os_files(self):
        """Packaging must not duplicate the OS outside its bundled archive."""
        output = os.path.join(self.fixture_dir.name, "Cannelloni-Installer.zip")
        executable = os.path.join(self.fixture_dir.name, "Cannelloni-Installer.exe")
        with open(executable, "wb") as source:
            source.write(b"test installer executable")
        repository = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        old_cwd = os.getcwd()
        try:
            os.chdir(repository)
            create_release_archives.build_installer_archive(output, self.payload_path, executable)
        finally:
            os.chdir(old_cwd)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), {
                "Cannelloni.zip", "Cannelloni-Installer.exe", "Cannelloni-Installer.bat",
                "Cannelloni-Installer.sh", "cannelloni_installer.py", "README.txt", "VERSION",
            })
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            with open(self.payload_path, "rb") as source:
                self.assertEqual(archive.read("Cannelloni.zip"), source.read())
        with tempfile.TemporaryDirectory() as target:
            self.assertTrue(self.install_fixture(output, target))
            self.assertTrue(os.path.isfile(os.path.join(target, "miyoo", "app", "MainUI")))

    def test_perform_installation(self):
        """Verify installation process in a temporary mock target SD directory."""
        temp_target = tempfile.mkdtemp(prefix="cannelloni_test_sd_")
        zip_locator = mock.patch.object(cannelloni_installer, "find_cannelloni_zip", return_value=self.payload_path)
        zip_locator.start()
        self.addCleanup(zip_locator.stop)
        try:
            progress_values = []
            status_messages = []

            success = cannelloni_installer.perform_installation(
                target_path=temp_target,
                lang_code="es",
                accent_hex="#e74c3c",
                device_id="miyoominiplus",
                progress_callback=lambda p: progress_values.append(p),
                status_callback=lambda s: status_messages.append(s)
            )

            self.assertTrue(success)
            self.assertTrue(len(progress_values) > 0)
            self.assertEqual(progress_values[-1], 100)

            # Check pre-configured files
            shared_dir = os.path.join(temp_target, ".userdata", "shared", ".cannelloni")
            self.assertTrue(os.path.isdir(shared_dir))

            with open(os.path.join(shared_dir, "language.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "es")

            with open(os.path.join(shared_dir, "accent_color.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "#e74c3c")

            with open(os.path.join(shared_dir, "device_model.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "Miyoo Mini Plus (v4 / Wi-Fi)")

            with open(os.path.join(shared_dir, "platform.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "miyoomini")

            with open(os.path.join(shared_dir, "device.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "plus")

            # Check .is_plus flag for Miyoo Mini Plus
            plus_flag = os.path.join(temp_target, ".userdata", "miyoomini", ".is_plus")
            self.assertTrue(os.path.isfile(plus_flag))

            # Check extracted root directories
            self.assertTrue(os.path.isdir(os.path.join(temp_target, ".system")))
            self.assertTrue(os.path.isfile(os.path.join(temp_target, "README.txt")))

            # Check that NDS cores from nested payload are extracted
            desmume_core = os.path.join(temp_target, ".system", "miyoomini", "cores", "desmume2015_libretro.so")
            self.assertTrue(os.path.isfile(desmume_core), f"NDS core missing: {desmume_core}")

            # Check that themes are extracted and pre-applied
            theme_asset = os.path.join(temp_target, ".system", "res", "assets@1x.png")
            self.assertTrue(os.path.isfile(theme_asset), f"Theme asset missing: {theme_asset}")
            with open(os.path.join(temp_target, ".system", "miyoomini", "bin", "minarch.elf"), "rb") as source:
                self.assertEqual(source.read(), b"test frontend", "Old theme frontends must not replace the current binary")
            with open(os.path.join(temp_target, ".system", "miyoomini", "bin", "cannelloni-list"), "rb") as source:
                self.assertEqual(source.read(), b"test red widget")

            # Check that installer files and zip are cleaned up from target root
            for bad_file in ("Cannelloni.zip", "Cannelloni-Installer.exe", "Cannelloni-Installer.bat", "Cannelloni-Installer.sh", "cannelloni_installer.py"):
                self.assertFalse(os.path.exists(os.path.join(temp_target, bad_file)), f"Misplaced file {bad_file} found in target SD root")
        finally:
            shutil.rmtree(temp_target, ignore_errors=True)

    def test_web_api(self):
        """Verify Web GUI API endpoints."""
        server = HTTPServer(("127.0.0.1", 0), cannelloni_installer.WebHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            # Test /api/init
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/init") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("devices", data)
                self.assertIn("colors", data)
                self.assertIn("drives", data)
                self.assertIn("languages", data)
                self.assertEqual(len(data["devices"]), 18)
                self.assertEqual(len(data["colors"]), 7)
                self.assertEqual(len(data["languages"]), 6)

            # Test /
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("CANNELLONI SD INSTALLER", html)

            # Test /api/install with empty drive (should return HTTP 400)
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/install",
                data=json.dumps({"drive": "", "lang": "en", "color": "#f1c40f", "device": "miyoomini"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req)
                self.fail("Expected HTTP 400 for empty drive")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 400)
                err_body = json.loads(e.read().decode("utf-8"))
                self.assertIn("error", err_body)

            # Test /api/progress
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/progress") as resp:
                self.assertEqual(resp.status, 200)
                prog = json.loads(resp.read().decode("utf-8"))
                self.assertIn("progress", prog)
                self.assertIn("status", prog)
        finally:
            server.shutdown()
            server.server_close()

    def test_linux_simulation_detect_drives(self):
        """Simulate Linux environment and drive detection logic."""
        orig_platform = sys.platform
        orig_isdir = os.path.isdir
        orig_ismount = os.path.ismount
        orig_listdir = os.listdir
        orig_disk_usage = shutil.disk_usage

        orig_user = os.environ.get("USER")
        try:
            sys.platform = "linux"
            os.environ["USER"] = "testuser"
            mock_media = "/media/testuser"
            mock_sd = os.path.join(mock_media, "SDCARD_CANNELLONI")

            def mock_is_dir(path):
                if path in ("/media/testuser", "/media", mock_sd):
                    return True
                return orig_isdir(path)

            def mock_is_mount(path):
                if path == mock_sd:
                    return True
                return False

            def mock_list_dir(path):
                if path == "/media/testuser":
                    return ["SDCARD_CANNELLONI"]
                return []

            def mock_usage(path):
                import collections
                Usage = collections.namedtuple("Usage", ["total", "used", "free"])
                return Usage(32000000000, 2000000000, 30000000000)

            os.path.isdir = mock_is_dir
            os.path.ismount = mock_is_mount
            os.listdir = mock_list_dir
            shutil.disk_usage = mock_usage

            drives = cannelloni_installer.detect_drives()
            self.assertIsInstance(drives, list)
            sd_drive = next((d for d in drives if d["path"] == mock_sd), None)
            self.assertIsNotNone(sd_drive)
            self.assertEqual(sd_drive["label"], "SDCARD_CANNELLONI")
            self.assertTrue(sd_drive["is_removable"])
        finally:
            if orig_user is None:
                os.environ.pop("USER", None)
            else:
                os.environ["USER"] = orig_user
            sys.platform = orig_platform
            os.path.isdir = orig_isdir
            os.path.ismount = orig_ismount
            os.listdir = orig_listdir
            shutil.disk_usage = orig_disk_usage

    def test_linux_shell_launcher(self):
        """Verify Linux shell launcher exists, uses Unix LF endings, and starts with valid shebang."""
        sh_path = os.path.join(os.path.dirname(__file__), "..", "installer", "Cannelloni-Installer.sh")
        self.assertTrue(os.path.isfile(sh_path))
        with open(sh_path, "rb") as f:
            data = f.read()
        self.assertNotIn(b"\r\n", data, "Linux shell launcher must use LF line endings")
        self.assertTrue(data.startswith(b"#!/usr/bin/env bash") or data.startswith(b"#!/bin/sh"))

    def test_tkinter_app_lifecycle(self):
        """Verify Tkinter GUI can be initialized and dynamically update states."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

        try:
            app = cannelloni_installer.CannelloniInstallerApp(root)
            self.assertIsNotNone(app)

            # Test language switching
            app.select_language("de")
            self.assertEqual(app.current_lang, "de")
            app.select_language("fr")
            self.assertEqual(app.current_lang, "fr")

            # Test color switching
            app.select_accent_color("#2ecc71")
            self.assertEqual(app.current_color, "#2ecc71")

            # Test device switching
            rg_idx = next(i for i, d in enumerate(cannelloni_installer.DEVICES) if d["id"] == "rg35xxplus")
            app.device_combo.current(rg_idx)
            app.on_device_selected()
            self.assertEqual(app.current_device_id, "rg35xxplus")
        finally:
            root.destroy()

if __name__ == "__main__":
    unittest.main()

