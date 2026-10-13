import os
import sys
import shutil
import tempfile
import unittest
import zipfile
import json
from http.server import HTTPServer
import threading
import urllib.request

# Ensure installer module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "installer")))
import cannelloni_installer

class TestCannelloniInstaller(unittest.TestCase):
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
        """Verify all 17 supported handhelds are properly configured."""
        self.assertEqual(len(cannelloni_installer.DEVICES), 17)
        expected_ids = [
            "miyoomini", "miyoominiplus", "my282", "my355", "trimuismart",
            "tg5040", "tg5040_brick", "rg35xx", "rg35xxplus", "rg35xxh",
            "rg35xxsp", "rg28xx", "rgcubexx", "rgb30", "magicmini",
            "gkdpixel", "m17"
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
        """Verify find_cannelloni_zip finds the existing release archive."""
        zip_path = cannelloni_installer.find_cannelloni_zip()
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.isfile(zip_path))
        self.assertTrue(zip_path.endswith(".zip"))

    def test_perform_installation(self):
        """Verify installation process in a temporary mock target SD directory."""
        temp_target = tempfile.mkdtemp(prefix="cannelloni_test_sd_")
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
                self.assertEqual(len(data["devices"]), 17)
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

