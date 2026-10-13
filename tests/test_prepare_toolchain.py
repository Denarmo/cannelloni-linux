from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_toolchain


class PrepareToolchainTests(unittest.TestCase):
    def test_legacy_archive_cache_is_checked_and_wget_guard_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            support = Path(directory) / "support"
            support.mkdir()
            script = support / "build-toolchain.sh"
            original = "#!/bin/sh\nBUILDROOT_VERSION=buildroot-test\nwget https://buildroot.org/downloads/$BUILDROOT_VERSION.tar.gz\n"
            script.write_text(original)
            data = b"verified archive fixture"
            import hashlib
            metadata = ("test", "BUILDROOT_VERSION", hashlib.sha256(data).hexdigest())
            with mock.patch.dict(prepare_toolchain.BUILDROOT, {"test": metadata}):
                with mock.patch.object(prepare_toolchain.urllib.request, "urlopen") as download:
                    download.return_value.__enter__.return_value.read.return_value = data
                    prepare_toolchain.prepare("test", directory)
                    prepare_toolchain.prepare("test", directory)
                    self.assertEqual(download.call_count, 1)
                self.assertEqual(script.read_text().count('[ -f "$BUILDROOT_VERSION.tar.gz" ] ||'), 1)
                self.assertEqual((support / "buildroot-test.tar.gz").read_bytes(), data)

    def test_checksum_mismatch_leaves_script_and_archive_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            support = Path(directory) / "support"
            support.mkdir()
            script = support / "build-toolchain.sh"
            original = "wget https://buildroot.org/downloads/$BUILDROOT_VERSION.tar.gz\n"
            script.write_text(original)
            with mock.patch.object(prepare_toolchain.urllib.request, "urlopen") as download:
                download.return_value.__enter__.return_value.read.return_value = b"wrong bytes"
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    prepare_toolchain.prepare("trimuismart", directory)
            self.assertEqual(script.read_text(), original)
            self.assertFalse((support / "buildroot-2016.05.tar.gz").exists())
