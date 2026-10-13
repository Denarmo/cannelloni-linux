"""Prevent tag, OS, archive and installer version drift."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "installer"))
import cannelloni_installer
from release_version import release_version


class ReleaseVersionTests(unittest.TestCase):
    def test_installer_and_release_share_canonical_version(self):
        self.assertEqual(cannelloni_installer.VERSION, release_version())
        self.assertEqual(release_version("v" + cannelloni_installer.VERSION), cannelloni_installer.VERSION)

    def test_wrong_tag_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "differs from VERSION"):
            release_version("v20261012-0")

    def test_invalid_source_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "VERSION"
            for value in ("20261012-0", "1.0", "01.0.0", "1.0.0-01"):
                with self.subTest(value=value):
                    path.write_text(value)
                    with self.assertRaisesRegex(ValueError, "semantic version"):
                        release_version("", path)
            for value in ("1.0.0", "1.1.0-rc.1", "2.0.0+build.5"):
                path.write_text(value)
                self.assertEqual(release_version("", path), value)

    def test_frozen_installer_reads_bundled_version(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "VERSION").write_text("1.0.0\n")
            with mock.patch.object(sys, "_MEIPASS", directory, create=True):
                self.assertEqual(cannelloni_installer.installer_version(), "1.0.0")

    def test_payload_rejects_old_version(self):
        import zipfile
        from io import BytesIO
        from verify_release_archive import verify_payload
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(".system/version.txt", "20261012-0\nold\n")
        with zipfile.ZipFile(buffer) as archive:
            with self.assertRaisesRegex(ValueError, "OS version"):
                verify_payload(archive, ())


if __name__ == "__main__":
    unittest.main()
