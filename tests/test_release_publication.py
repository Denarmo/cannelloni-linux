"""The installer is the only downloadable binary release asset."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publish_github_release as release


class ReleasePublicationTests(unittest.TestCase):
    def test_new_release_uploads_only_verified_installer(self):
        self.check_publication(existing=False)

    def test_existing_release_removes_obsolete_archives_after_successful_upload(self):
        self.check_publication(existing=True)

    def check_publication(self, existing):
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.md"
            notes.write_text("Release notes")
            version = release.release_version()
            outputs = ["commit123\n"]
            if existing:
                outputs.append(json.dumps({"assets": [{"name": name} for name in (
                    "Cannelloni-Installer.zip", f"Cannelloni-{version}.zip", "Cannelloni.zip", "unrelated.txt")]}))
            calls = []

            def run(args, **kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, int(not existing) if args[1:3] == ["release", "view"] else 0)

            with mock.patch.object(release, "verify_archive") as verify, \
                 mock.patch.object(release.subprocess, "run", side_effect=run), \
                 mock.patch.object(release.subprocess, "check_output", side_effect=outputs):
                release.publish(notes, "built-workspace")
            installer = str(ROOT / "releases/Cannelloni-Installer.zip")
            verify.assert_called_once_with(Path(installer), "built-workspace")
            upload = next(args for args in calls if args[1:3] == ["release", "upload" if existing else "create"])
            self.assertEqual([arg for arg in upload if arg.endswith(".zip")], [installer])
            deleted = [args for args in calls if args[1:3] == ["release", "delete-asset"]]
            self.assertEqual([args[4] for args in deleted], [f"Cannelloni-{version}.zip", "Cannelloni.zip"] if existing else [])
            for args in deleted:
                self.assertGreater(calls.index(args), calls.index(upload))
            self.assertTrue(all("--repo" in args and release.REPO in args for args in calls))


if __name__ == "__main__":
    unittest.main()
