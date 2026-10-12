import os
import subprocess
import urllib.request
import json

# 1. Get GitHub token from git credentials
p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, err = p.communicate(input='protocol=https\nhost=github.com\n\n')
token = None
for line in out.splitlines():
    if line.startswith('password='):
        token = line.split('=', 1)[1]

if not token:
    print("Error: Could not retrieve GitHub token from credentials manager")
    exit(1)

REPO = "Denarmo/cannelloni-linux"
TAG = "v20261012-0"
RELEASE_TITLE = "Cannelloni v20261012-0"
UNIFIED_ZIP = "releases/Cannelloni-20261012-0.zip"

BODY = """# Cannelloni v20261012-0

Welcome to Cannelloni for Linux handhelds (Anbernic, Miyoo, TrimUI, Powkiddy, MagicX, and GKD).

## What's New in this Release:
- **Unified Single-Zip Distribution**: All core systems, extra emulators, tools, and installers delivered in one unified archive. No more separate base and extras packages!
- **melonDS Libretro Core (Nintendo DS)**: Fully integrated NDS libretro core and `NDS.pak` across all 12 supported handheld platforms. Press `MENU` in-game to access native Cannelloni save states, settings, and quicksaves.
- **Cannelloni Gold UI (#f1c40f)**: Native gold selection pills and slider bars baked into the core interface spritesheets for all screen resolutions.
- **Interactive On-Device Wi-Fi Tool**: Scan wireless networks, type passwords directly via on-screen virtual keyboard (`minui-keyboard`), and connect directly without needing the stock OS.
- **Nonna's Kitchen (FTP File Transfer)**: RFC 959 wireless file transfer server on port `2121`. Access your SD card wirelessly over local Wi-Fi with FileZilla, Cyberduck, or your computer's file manager.

## Installation:
1. Download **`Cannelloni-20261012-0.zip`**.
2. Extract the contents directly to the root of your freshly formatted FAT32 SD card.
3. Insert the card into your handheld and power on!
"""

print(f"Creating or updating release {TAG} on {REPO}...")

release_payload = json.dumps({
    "tag_name": TAG,
    "target_commitish": "main",
    "name": RELEASE_TITLE,
    "body": BODY,
    "draft": False,
    "prerelease": False
}).encode('utf-8')

req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/releases",
    data=release_payload,
    headers={
        "Authorization": f"token {token}",
        "User-Agent": "Cannelloni",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v3+json"
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        release_data = json.loads(resp.read().decode('utf-8'))
        release_id = release_data['id']
        html_url = release_data['html_url']
        print(f"Release created successfully! URL: {html_url}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"Release exists, updating release {TAG} metadata...")
    req_existing = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
        headers={"Authorization": f"token {token}", "User-Agent": "Cannelloni"}
    )
    with urllib.request.urlopen(req_existing) as resp:
        release_data = json.loads(resp.read().decode('utf-8'))
        release_id = release_data['id']
        html_url = release_data['html_url']
        print(f"Using existing release: {html_url}")

    # Update release body
    req_update = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/{release_id}",
        data=json.dumps({"body": BODY, "name": RELEASE_TITLE}).encode('utf-8'),
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "Cannelloni",
            "Content-Type": "application/json"
        }
    )
    req_update.get_method = lambda: "PATCH"
    with urllib.request.urlopen(req_update) as resp:
        pass

# Delete old base and extras assets to maintain clean single-zip delivery
print("Cleaning up older split assets if present...")
req_assets = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/releases/{release_id}/assets",
    headers={"Authorization": f"token {token}", "User-Agent": "Cannelloni"}
)
try:
    with urllib.request.urlopen(req_assets) as resp:
        existing_assets = json.loads(resp.read().decode('utf-8'))
        for ea in existing_assets:
            if ea['name'] in ("Cannelloni-20261012-0-base.zip", "Cannelloni-20261012-0-extras.zip", "Cannelloni-20261012-0.zip"):
                print(f"Deleting older asset {ea['name']} (id {ea['id']})...")
                del_req = urllib.request.Request(
                    f"https://api.github.com/repos/{REPO}/releases/assets/{ea['id']}",
                    headers={"Authorization": f"token {token}", "User-Agent": "Cannelloni"}
                )
                del_req.get_method = lambda: "DELETE"
                urllib.request.urlopen(del_req)
except Exception as e:
    print(f"Warning during asset cleanup: {e}")

# Upload unified asset
if not os.path.isfile(UNIFIED_ZIP):
    print(f"Error: Unified zip not found at {UNIFIED_ZIP}")
    exit(1)

asset_name = "Cannelloni-20261012-0.zip"
print(f"Uploading unified release asset {asset_name} ({os.path.getsize(UNIFIED_ZIP)} bytes)...")
upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name={asset_name}"

with open(UNIFIED_ZIP, "rb") as f:
    file_bytes = f.read()

req_upload = urllib.request.Request(
    upload_url,
    data=file_bytes,
    headers={
        "Authorization": f"token {token}",
        "User-Agent": "Cannelloni",
        "Content-Type": "application/zip",
        "Content-Length": str(len(file_bytes))
    }
)

try:
    with urllib.request.urlopen(req_upload) as resp:
        asset_data = json.loads(resp.read().decode('utf-8'))
        print(f"Uploaded {asset_name}: {asset_data.get('browser_download_url')}")
except urllib.error.HTTPError as e:
    print(f"Upload error for {asset_name}: {e.code} {e.read().decode('utf-8')}")

print("\nRelease publish process finished successfully!")
print(f"Download Unified Release at: {html_url}")
