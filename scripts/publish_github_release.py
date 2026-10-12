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
BASE_ZIP = "releases/Cannelloni-20261012-0-base.zip"
EXTRAS_ZIP = "releases/Cannelloni-20261012-0-extras.zip"

BODY = """# Cannelloni v20261012-0

Welcome to Cannelloni for Linux handhelds (Anbernic, Miyoo, TrimUI, Powkiddy, MagicX, and GKD).

## What's New in this Release:
- **Cannelloni Rebrand**: Complete rebranding from MinUI across all code, platforms, launch scripts, and tools.
- **melonDS Libretro Core (Nintendo DS)**: Added internal melonDS libretro core and `NDS.pak` across all 12 supported handheld platforms.
- **Nonna's Kitchen (FTP File Transfer)**: RFC 959 compliant wireless file transfer server on port `2121`. Access your SD card directly over local Wi-Fi with FileZilla, Cyberduck, or your computer's file manager.
- **Interactive Settings Menu**: Press `MENU` in the launcher to access Nonna's Kitchen toggle, Wi-Fi status/connection, and accent color selection.
- **Customizable Accent Color**: Default `#f1c40f` (Cannelloni Gold) with dynamic pill/bar tinting and presets (Gold, Cannoli Blue, Coral Red, Emerald, Purple, Amber, White).

## Installation:
1. Extract `Cannelloni-20261012-0-base.zip` directly to the root of your freshly formatted FAT32 SD card.
2. (Optional) Extract `Cannelloni-20261012-0-extras.zip` to add extra emulators and tools (including Nonna's Kitchen tool pak).
3. Insert the card into your handheld and power on!
"""

print(f"Creating release {TAG} on {REPO}...")

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
        upload_url_template = release_data['upload_url']
        html_url = release_data['html_url']
        print(f"Release created successfully! URL: {html_url}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"Failed to create release: {e.code} {err_body}")
    # Check if release already exists
    req_existing = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
        headers={"Authorization": f"token {token}", "User-Agent": "Cannelloni"}
    )
    with urllib.request.urlopen(req_existing) as resp:
        release_data = json.loads(resp.read().decode('utf-8'))
        release_id = release_data['id']
        html_url = release_data['html_url']
        print(f"Using existing release: {html_url}")

# Upload assets
assets = [
    (BASE_ZIP, "Cannelloni-20261012-0-base.zip"),
    (EXTRAS_ZIP, "Cannelloni-20261012-0-extras.zip")
]

for file_path, asset_name in assets:
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        continue

    print(f"Uploading {asset_name} ({os.path.getsize(file_path)} bytes)...")
    upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name={asset_name}"
    
    with open(file_path, "rb") as f:
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
print(f"Download Release at: {html_url}")
