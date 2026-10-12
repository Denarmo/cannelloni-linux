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

BODY = """# Cannelloni v20261012-0

Welcome to Cannelloni for Linux handhelds (Anbernic, Miyoo, TrimUI, Powkiddy, MagicX, and GKD).

## What's New in this Release:
- **Universal One-Zip Drop-in Installation**: Drop either `Cannelloni.zip` or `Cannelloni-20261012-0.zip` directly to the root of your SD card without extracting it on PC. On boot, Cannelloni automatically unpacks all platform bootstrap and system files, runs the setup wizard, and completely erases the zip archive from the SD card!
- **Interactive 3-Step Setup Wizard**: On initial boot, Cannelloni presents an interactive setup wizard in clear sequential steps:
  1. **Language Selection**: Choose from 6 languages (English, Spanish, French, Portuguese - Brazil, German, Italian).
  2. **Accent Color Theming**: Pick from 7 vibrant accent colors (Cannelloni Gold `#f1c40f`, Tomato Red, Basil Green, Sky Blue, and more), immediately applied to the interface.
  3. **Handheld Console Selection**: Pick your exact device model from all 14 supported handhelds, automatically configuring the exact hardware drivers, bootloader dat assets, and optimized platform binaries.
- **Language Setting & Full Localization**: Change language anytime directly from **Settings -> Language**. Comprehensive translation dictionaries included for English (`en`), Spanish (`es`), French (`fr`), Portuguese - Brazil (`pt_BR`), German (`de`), and Italian (`it`).
- **Default Yellow Accent Color on First Boot**: Fixed first-boot theming by bundling pre-rendered `#f1c40f` spritesheets directly in the system assets and ensuring clean startup theme initialization without requiring manual color changing.
- **Reliable Wi-Fi & Start-on-Boot**: Fixed Wi-Fi settings exiting immediately on launch, added hardware radio power management (`wifion`), and fixed automatic startup on boot paths in `auto.sh`.
- **Denarmo Shaders & Shader Settings**: Integrated high-performance GLSL shaders directly from [Denarmo/cannelloni](https://github.com/Denarmo/cannelloni) (`crt-cannelloni`, `crt-cannelloni-lite`, `crt-easymode`, `crt-aperture`, `crt-geom`, `crt-lottes-fast`, `dot`, `lcd3x`, `scanline`, `sharp-bilinear-simple`, `zfast-crt`, `zfast-lcd`). Configure active preset and scope under **Settings -> Shaders**.
- **Secure Wi-Fi Storage**: Wi-Fi credentials are stored encrypted/obfuscated in `.userdata/shared/.cannelloni/network.conf` with restricted `0600` permissions (never in plain text in the SD card root), with automatic background migration and sanitization from legacy `wifi.txt`.
- **Official Boot Logo**: Centered cannelloni drawing with title **"Cannelloni"** and subtitle **"forked from MinUI/Cannoli"** across all handheld platforms, with automatic SPI flash programming on Miyoo Mini / Plus hardware.
- **Attribution on About Page**: Pressing the Home (`MENU`) button displays **"Cannelloni"** and **"forked from MinUI/Cannoli"** cleanly without crashing.
- **Permissive Licensing**: Explicit licensing terms establishing that upstream code is copyright Shaun Inman / MinUI contributors, while all Cannelloni additions and modifications are licensed under the permissive MIT License for anyone to freely use.
- **Unified Single-Zip Distribution**: All core systems, emulators, tools, and platform installers delivered in one unified archive (`Cannelloni.zip` / `Cannelloni-20261012-0.zip`).
- **New Top-Level Settings Menu**: Direct access from the main screen to:
  - **Language**: Switch system language anytime on-device.
  - **Wi-Fi**: Connect to wireless networks, view IP, and toggle auto-start on boot.
  - **Accent Color**: Customize interface colors (Cannelloni Gold `#f1c40f`, Tomato Red, Basil Green, Sky Blue, and more).
  - **Button Mapping**: Swap A/B and X/Y button layouts.
  - **Emulators**: Choose preferred emulators per console (e.g. Libretro DeSmuME vs standalone DraStic for Nintendo DS).
  - **Shaders**: Select shader preset and apply scope across consoles.
  - **Device Model**: Interactively switch or reconfigure target handheld console hardware.
- **Nonna's Kitchen (Web Dashboard)**: Wireless HTTP management service on port `1091` matching Android Cannelloni. Connect with any web browser to view storage, browse files, and drag-and-drop upload ROMs, BIOS, and Saves.
- **Curated Tools Section**: Focused strictly on essential utilities: `Clock`, `Files`, `Input`, `IP`, and `Nonna's Kitchen`.
- **Full Cannelloni Gold UI (#f1c40f)**: Uniform gold accent theming across all UI components, button badges `(A)`/`(B)`, battery fill and charging bolt, Wi-Fi icon, volume and brightness indicators, and solid gold selection pills across all screen scales (1x through 4x).
- **Nintendo DS Emulation**: Libretro core implementation with in-game menu (`MENU` button) and save state support, alongside optional standalone DraStic.

## Installation:
1. Format your SD card as FAT32 (MBR).
2. Simply drop **`Cannelloni.zip`** (or **`Cannelloni-20261012-0.zip`**) directly to the root of your SD card.
3. Insert the card into your handheld and power on.
4. Cannelloni automatically unpacks all system files and launches the 3-step setup wizard on screen: select Language, select Accent Color, and select your Device Model!
5. After installation finishes, the zip archive is automatically erased from the SD card.
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

# 2. Upload assets (Cannelloni-20261012-0.zip and Cannelloni.zip)
assets_to_upload = [UNIFIED_ZIP, ALIAS_ZIP]

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
