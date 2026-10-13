"""Exercise the shipped CGI and owned network-tool processes on a POSIX shell."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "scripts/templates"


def find_shell():
    shell = shutil.which("sh")
    candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/sh.exe"
    return shell or (str(candidate) if candidate.is_file() else None)


def script(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + content + "\n", encoding="utf-8", newline="\n")
    path.chmod(0o755)


@unittest.skipUnless(find_shell(), "A POSIX shell is required")
class KitchenTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="kitchen tests ")
        self.addCleanup(temp.cleanup)
        self.sd = Path(temp.name)
        for category in ("Roms", "Bios", "Saves"):
            (self.sd / category).mkdir()
        self.env = dict(os.environ, SDCARD=self.sd.as_posix(), SDCARD_PATH=self.sd.as_posix(),
                        PLATFORM="miyoomini", REQUEST_METHOD="GET")
        self.env["PATH"] = str(self.sd / "bin") + os.pathsep + str(Path(find_shell()).parent) + os.pathsep + self.env.get("PATH", "")

    def request(self, params, body=b"", method="GET"):
        env = dict(self.env, QUERY_STRING=urlencode(params), REQUEST_METHOD=method,
                   CONTENT_LENGTH=str(len(body)))
        result = subprocess.run([find_shell(), (TEMPLATES / "kitchen_api.cgi").as_posix()],
                                env=env, input=body, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        headers, data = result.stdout.split(b"\r\n\r\n", 1)
        return headers.decode(), data

    def test_lists_encoded_unicode_and_quoted_names_without_reading_rom_data(self):
        folder = self.sd / "Roms/Game Boy Advance (GBA)"
        folder.mkdir()
        for name in ("Mario & Luigi.gba", 'Quote " and slash.gba', "Pokémon.gba", "%20 percent.gba"):
            # NTFS cannot store literal quote characters; the other cases run everywhere.
            if os.name == "nt" and '"' in name:
                continue
            (folder / name).write_bytes(b"ROM data")
        # A directory listing must never stream every ROM through wc.
        script(self.sd / "bin/wc", 'echo "ROM contents were read" >&2; exit 97')
        headers, data = self.request({"action": "list", "dir": "Roms/Game Boy Advance (GBA)"})
        self.assertNotIn("Status:", headers)
        files = json.loads(data)
        self.assertEqual({f["name"] for f in files}, {p.name for p in folder.iterdir()})
        self.assertTrue(all(f["size"] == "8 B" for f in files))

    def test_upload_download_delete_and_failed_upload_preserves_existing_file(self):
        name = "space + percent%20.bin"
        content = bytes(range(256)) * 4
        headers, body = self.request({"action": "upload", "dir": "Saves", "name": name}, content, "POST")
        self.assertNotIn("Status:", headers)
        self.assertEqual(json.loads(body)["status"], "ok")
        self.assertEqual((self.sd / "Saves" / name).read_bytes(), content)
        headers, downloaded = self.request({"action": "download", "path": "Saves/" + name})
        self.assertEqual(downloaded, content)
        self.assertIn("Content-Length: 1024", headers)
        self.env["CONTENT_LENGTH"] = "0"
        env = dict(self.env, QUERY_STRING=urlencode({"action": "upload", "dir": "Saves", "name": name}),
                   REQUEST_METHOD="POST", CONTENT_LENGTH="99")
        result = subprocess.run([find_shell(), (TEMPLATES / "kitchen_api.cgi").as_posix()], env=env,
                                input=b"truncated", capture_output=True, timeout=15)
        self.assertIn(b"400 Bad Request", result.stdout)
        self.assertEqual((self.sd / "Saves" / name).read_bytes(), content)
        self.assertFalse(list((self.sd / "Saves").glob(".kitchen-upload.*")))
        headers, body = self.request({"action": "delete", "path": "Saves/" + name}, method="POST")
        self.assertEqual(json.loads(body)["status"], "ok")
        self.assertFalse((self.sd / "Saves" / name).exists())

    def test_rejects_escape_root_delete_and_wrong_http_method(self):
        (self.sd / "outside.bin").write_bytes(b"keep")
        for params, method in (
            ({"action": "download", "path": "Roms/../outside.bin"}, "GET"),
            ({"action": "list", "dir": "missing"}, "GET"),
            ({"action": "delete", "path": "Roms"}, "POST"),
            ({"action": "delete", "path": "Roms/../outside.bin"}, "POST"),
            ({"action": "upload", "dir": "Roms", "name": "../outside.bin"}, "POST"),
            ({"action": "delete", "path": "Saves/file.bin"}, "GET"),
        ):
            with self.subTest(params=params):
                headers, body = self.request(params, method=method)
                self.assertIn("Status: 4", headers)
                self.assertIn("error", json.loads(body))
        self.assertEqual((self.sd / "outside.bin").read_bytes(), b"keep")

    def test_storage_status_reports_real_values(self):
        script(self.sd / "bin/df", "printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n/dev/card 2097152 524288 1572864 25%% /card\\n'")
        headers, body = self.request({"action": "status"})
        self.assertNotIn("Status:", headers)
        self.assertEqual(json.loads(body), {"total": "2.0 GB", "used": "0.5 GB", "free": "1.5 GB", "percent": 25})

    def test_launcher_stops_owned_foreground_server_when_screen_closes(self):
        pak = self.sd / "Tools/miyoomini/Nonna's Kitchen.pak"
        (pak / "web/cgi-bin").mkdir(parents=True)
        for source, destination in (("kitchen_launch.sh", "launch.sh"), ("kitchen_api.cgi", "web/cgi-bin/api.cgi"), ("kitchen_index.html", "web/index.html")):
            shutil.copyfile(TEMPLATES / source, pak / destination)
        self.env["TEST_RECORD"] = (self.sd / "server.txt").as_posix()
        script(self.sd / "bin/ip", "printf '    inet 192.168.1.5/24 scope global wlan0\\n'")
        script(self.sd / "bin/busybox", '''
[ "$1" = httpd ] && [ "$2" = -f ] || exit 99
printf 'started %s\\n' "$$" > "$TEST_RECORD"
trap 'echo stopped >> "$TEST_RECORD"; exit 0' TERM INT HUP
while :; do sleep 0.1; done
''')
        for mode in ("close", "signal"):
            with self.subTest(mode=mode):
                message = 'sleep 0.2; exit 0' if mode == "close" else '''
trap 'exit 0' TERM
kill -TERM "$PPID"
while :; do sleep 0.1; done
'''
                script(self.sd / ".system/miyoomini/bin/say.elf", message)
                result = subprocess.run([find_shell(), (pak / "launch.sh").as_posix()], env=self.env,
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                self.assertRegex((self.sd / "server.txt").read_text(), r"started \d+\nstopped\n")


@unittest.skipUnless(find_shell(), "A POSIX shell is required")
class WifiProgressTests(unittest.TestCase):
    def test_reports_authentication_address_assignment_success_and_timeout(self):
        source = (TEMPLATES / "wifi_launch.sh").read_text()
        function = re.search(r"^wait_for_connection\(\) \{.*?^\}", source, re.S | re.M).group()
        for result in ("success", "timeout"):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "progress.sh"
                # wpa_cli and connection_ip run in command substitutions, so progression
                # uses elapsed in the caller rather than mutation in those subprocesses.
                script(path, '''
SSID='Test network'
show_message() { printf '%s\\n' "$1"; }
sleep() { :; }
wpa_cli() {
    case "$elapsed" in 0) echo wpa_state=4WAY_HANDSHAKE;; *) echo wpa_state=COMPLETED;; esac
}
connection_ip() { if [ "$elapsed" -ge 2 ] && [ "$TEST_RESULT" = success ]; then echo 192.168.1.12; fi; }
ifconfig() { :; }
''' + function + '\nwait_for_connection')
                env = dict(os.environ, TEST_RESULT=result)
                env["PATH"] = str(Path(find_shell()).parent) + os.pathsep + env.get("PATH", "")
                process = subprocess.run([find_shell(), path.as_posix()], env=env,
                                         capture_output=True, text=True, timeout=15)
                self.assertIn("Checking Wi-Fi password", process.stdout)
                self.assertIn("Obtaining IP address", process.stdout)
                if result == "success":
                    self.assertEqual(process.returncode, 0, process.stderr)
                    self.assertIn("IP address: 192.168.1.12", process.stdout)
                else:
                    self.assertEqual(process.returncode, 1, process.stderr)
                    self.assertIn("29s / 30s", process.stdout)
                    self.assertIn("No IP address was assigned", process.stdout)

    def test_shipped_copies_match_templates_and_are_valid_shell(self):
        for template, glob in (
            ("kitchen_launch.sh", "skeleton/EXTRAS/Tools/*/Nonna's Kitchen.pak/launch.sh"),
            ("kitchen_api.cgi", "skeleton/EXTRAS/Tools/*/Nonna's Kitchen.pak/web/cgi-bin/api.cgi"),
            ("kitchen_index.html", "skeleton/EXTRAS/Tools/*/Nonna's Kitchen.pak/web/index.html"),
            ("wifi_launch.sh", "skeleton/EXTRAS/Settings/*/Wi-Fi.pak/launch.sh"),
        ):
            canonical = (TEMPLATES / template).read_bytes()
            for path in ROOT.glob(glob):
                if path.parts[-3] == "rgb30" and template == "wifi_launch.sh":
                    continue
                self.assertEqual(path.read_bytes(), canonical, str(path))
            if not template.endswith(".html"):
                result = subprocess.run([find_shell(), "-n", (TEMPLATES / template).as_posix()], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(shutil.which("busybox") and os.name != "nt", "Real BusyBox HTTP server is required")
class BusyboxHttpTests(unittest.TestCase):
    def test_http_cgi_file_round_trip_with_busybox_applets(self):
        with tempfile.TemporaryDirectory(prefix="kitchen http ") as directory:
            root = Path(directory)
            web = root / "web"
            (web / "cgi-bin").mkdir(parents=True)
            cgi = web / "cgi-bin/api.cgi"
            shutil.copyfile(TEMPLATES / "kitchen_api.cgi", cgi)
            cgi.chmod(0o755)
            roms = root / "card/Roms/Game Boy (GB)"
            roms.mkdir(parents=True)
            (roms / "Pokémon + %20.gb").write_bytes(b"test ROM")
            applets = root / "bin"
            applets.mkdir()
            busybox = shutil.which("busybox")
            subprocess.run([busybox, "--install", "-s", str(applets)], check=True, capture_output=True)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            env = dict(os.environ, SDCARD=str(root / "card"), PATH=str(applets) + os.pathsep + os.environ["PATH"])
            server = subprocess.Popen([busybox, "httpd", "-f", "-p", f"127.0.0.1:{port}", "-h", str(web)],
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(50):
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                            break
                    except OSError:
                        time.sleep(0.02)
                base = f"http://127.0.0.1:{port}/cgi-bin/api.cgi?"
                with urlopen(base + urlencode({"action": "list", "dir": "Roms/Game Boy (GB)"}), timeout=5) as response:
                    listing = json.load(response)
                self.assertEqual(listing[0]["name"], "Pokémon + %20.gb")
                body = bytes(range(256)) * 100
                request = Request(base + urlencode({"action": "upload", "dir": "Roms/Game Boy (GB)", "name": "test.gb"}),
                                  data=body, method="POST")
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(json.load(response)["status"], "ok")
                with urlopen(base + urlencode({"action": "download", "path": "Roms/Game Boy (GB)/test.gb"}), timeout=5) as response:
                    self.assertEqual(response.read(), body)
            finally:
                server.terminate()
                server.wait(timeout=5)
            with self.assertRaises(OSError):
                socket.create_connection(("127.0.0.1", port), timeout=0.2)


if __name__ == "__main__":
    unittest.main()
