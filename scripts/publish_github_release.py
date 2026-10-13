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
ALIAS_ZIP = "releases/Cannelloni.zip"

INSTALLER_ZIP = "releases/Cannelloni-Installer.zip"

BODY = """# Cannelloni v20261012-0

Welcome to Cannelloni for Linux handhelds (Anbernic, Miyoo, TrimUI, Powkiddy, MagicX, and GKD).

## What's New in this Release:
- **Portable Cross-Platform GUI SD Installer**: Delivered release archive includes a standalone, reactive GUI installer running seamlessly on both Windows and Linux with zero external dependencies:
  - **Standalone Windows Executable (`Cannelloni-Installer.exe`)**: Double-clickable executable, no Python installation needed.
  - **Windows Batch Launcher (`Cannelloni-Installer.bat`)** & **Linux Launcher (`Cannelloni-Installer.sh`)**.
  - **Automatic Drive Detection**: Scans and identifies removable SD cards with storage metrics and manual browse fallback.
  - **Live Dynamic Localization**: Switch between 6 languages (English, Spanish, French, Portuguese - Brazil, German, Italian) with instantaneous UI retranslation.
  - **Live Accent Color Previews & Handheld Simulator**: Visual circular swatches with interactive retro handheld mockup reacting in real-time to color selections (Cannelloni Gold `#f1c40f`, Tomato Red, Basil Green, Sky Blue, Royal Purple, Carrot Orange, Clean White).
  - **All 17 Supported Handheld Consoles**: Explicit profiles and hardware optimization for Miyoo Mini, Mini Plus, A30, Flip, TrimUI Smart, Smart Pro, Brick, Anbernic RG35XX, RG35XX Plus, RG35XX H, RG35XX SP, RG28XX, RG CubeXX, Powkiddy RGB30, MagicX XU10, GKD Pixel, and M17.
  - **One-Click Automated Setup**: Extracts the full OS payload, writes hardware configuration flags, copies boot splash dat files, and pre-applies theme assets directly to the SD card.
- **Universal Release Archive**: Archive contains `Cannelloni.zip` plus the portable installer and bootstrap files for instant one-click PC setup or direct on-device automatic unzipping.
- **Interactive 3-Step Setup Wizard**: For direct on-device installs, Cannelloni presents an interactive setup wizard on initial boot (Language -> Accent Color -> Device Model).
- **Full Localization**: Comprehensive translation dictionaries for English (`en`), Spanish (`es`), French (`fr`), Portuguese - Brazil (`pt_BR`), German (`de`), and Italian (`it`).
- **Default Yellow Accent Color on First Boot**: High-contrast `#f1c40f` pre-rendered assets across all scales (1x through 4x).
- **Reliable Wi-Fi & Start-on-Boot**: Hardware radio power management and auto-start services on boot.
- **Denarmo Shaders & Shader Settings**: 12 GLSL CRT, scanline, and LCD shaders integrated under in-game menu and Settings -> Shaders.
- **Secure Wi-Fi Storage**: Network credentials obfuscated in `.userdata/shared/.cannelloni/network.conf` with 0600 permissions.
- **Nonna's Kitchen (Web Dashboard)**: Wireless HTTP management service on port 1091 for drag-and-drop uploading of ROMs, BIOS, and Saves.
- **Nintendo DS Emulation**: Libretro core implementation with in-game menu and save state support, alongside optional standalone DraStic.

## Installation Methods:

### Method 1: One-Click GUI Installer (Recommended)
1. Extract the downloaded release archive (`Cannelloni.zip` or `Cannelloni-Installer.zip`).
2. Run `Cannelloni-Installer.exe` (Windows) or `./Cannelloni-Installer.sh` (Linux).
3. Select your SD card, Language, Accent Color, and Device Model.
4. Click **Install Cannelloni to SD Card**.
5. Safely eject the card, insert into your device, and power on!

### Method 2: Direct On-Device Installation
1. Format your SD card as FAT32 (MBR).
2. Copy `Cannelloni.zip` directly to the root of your SD card.
3. Insert into your handheld and power on. Cannelloni extracts and configures automatically!
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

release_id = None
try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        release_id = res['id']
        print(f"Created new release: ID {release_id}")
except urllib.error.HTTPError as e:
    if e.code == 422: # Already exists, fetch release ID
        print("Release exists, fetching existing release ID...")
        req_get = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
            headers={
                "Authorization": f"token {token}",
                "User-Agent": "Cannelloni",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req_get) as resp_get:
            res_get = json.loads(resp_get.read().decode('utf-8'))
            release_id = res_get['id']
            print(f"Found existing release ID {release_id}")
            
            # Update release body
            req_patch = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/{release_id}",
                data=release_payload,
                headers={
                    "Authorization": f"token {token}",
                    "User-Agent": "Cannelloni",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.github.v3+json"
                },
                method='PATCH'
            )
            urllib.request.urlopen(req_patch)
            print("Updated release notes.")
    else:
        raise

# 2. Upload assets (Cannelloni.zip and Cannelloni-Installer.zip)
assets_to_upload = [ALIAS_ZIP, INSTALLER_ZIP]

# Fetch current assets list
req_assets = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/releases/{release_id}/assets",
    headers={
        "Authorization": f"token {token}",
        "User-Agent": "Cannelloni",
        "Accept": "application/vnd.github.v3+json"
    }
)
with urllib.request.urlopen(req_assets) as resp:
    existing_assets = json.loads(resp.read().decode('utf-8'))

target_names = [os.path.basename(p) for p in assets_to_upload]

# Remove any obsolete assets (such as Cannelloni-20261012-0.zip) so only 1 zip is published
for a in existing_assets:
    if a['name'] not in target_names:
        print(f"Deleting obsolete asset ID {a['id']} ({a['name']})...")
        req_del = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}",
            headers={
                "Authorization": f"token {token}",
                "User-Agent": "Cannelloni",
                "Accept": "application/vnd.github.v3+json"
            },
            method='DELETE'
        )
        urllib.request.urlopen(req_del)

for file_path in assets_to_upload:
    if not os.path.isfile(file_path):
        print(f"Skipping {file_path}, file not found")
        continue

    asset_name = os.path.basename(file_path)
    print(f"\nChecking assets for {asset_name}...")
    for a in existing_assets:
        if a['name'] == asset_name:
            print(f"Deleting existing asset ID {a['id']} ({asset_name})...")
            req_del = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}",
                headers={
                    "Authorization": f"token {token}",
                    "User-Agent": "Cannelloni",
                    "Accept": "application/vnd.github.v3+json"
                },
                method='DELETE'
            )
            urllib.request.urlopen(req_del)

    print(f"Uploading {file_path} ({os.path.getsize(file_path)} bytes)...")
    with open(file_path, "rb") as f:
        zip_bytes = f.read()

    req_up = urllib.request.Request(
        f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name={asset_name}",
        data=zip_bytes,
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "Cannelloni",
            "Content-Type": "application/zip",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    with urllib.request.urlopen(req_up) as resp:
        print(f"Successfully uploaded {asset_name} to GitHub Release {TAG}!")

print(f"\nRelease published successfully: https://github.com/{REPO}/releases/tag/{TAG}")

# Copy to E:\ if mounted
if os.path.isdir("E:\\"):
    import shutil
    print("\nCopying release packages to mounted SD card at E:\\...")
    try:
        shutil.copy2(ALIAS_ZIP, "E:\\Cannelloni.zip")
        shutil.copy2("dist/Cannelloni-Installer.exe", "E:\\Cannelloni-Installer.exe")
        shutil.copy2("installer/Cannelloni-Installer.bat", "E:\\Cannelloni-Installer.bat")
        shutil.copy2("installer/Cannelloni-Installer.sh", "E:\\Cannelloni-Installer.sh")
        shutil.copy2("installer/cannelloni_installer.py", "E:\\cannelloni_installer.py")
        print("Copied files to E:\\ successfully!")
    except Exception as e:
        print(f"Warning: Could not copy to E:\\: {e}")

