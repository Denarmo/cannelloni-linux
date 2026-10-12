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
- **Universal One-Zip Installation & Device Selector**: No longer requires identifying or manually copying device-specific folders! Simply drag the single unified archive or extract it to the root of your SD card. On initial boot, Cannelloni presents an interactive on-screen Device Selector where you pick your console model, automatically configuring the exact hardware drivers and platform files. Reconfigure hardware anytime via **Settings -> Device Model**.
- **Denarmo Shaders & Shader Settings**: Integrated high-performance GLSL shaders directly from [Denarmo/cannelloni](https://github.com/Denarmo/cannelloni) (`crt-cannelloni`, `crt-cannelloni-lite`, `crt-easymode`, `crt-aperture`, `crt-geom`, `crt-lottes-fast`, `dot`, `lcd3x`, `scanline`, `sharp-bilinear-simple`, `zfast-crt`, `zfast-lcd`). Configure active preset and scope (All Consoles, Handhelds Only, Home Consoles, Nintendo DS) under **Settings -> Shaders**.
- **Secure Wi-Fi Storage**: Wi-Fi credentials are now stored encrypted/obfuscated in `.userdata/shared/.cannelloni/network.conf` with restricted `0600` permissions (never in plain text in the SD card root), with automatic background migration and sanitization from legacy `wifi.txt`.
- **Official Boot Logo**: Centered cannelloni drawing with title **"Cannelloni"** and subtitle **"forked from MinUI/Cannoli"** across all handheld platforms, with automatic SPI flash programming on Miyoo Mini / Plus hardware.
- **Attribution on About Page**: Pressing the Home (`MENU`) button displays **"Cannelloni"** and **"forked from MinUI/Cannoli"** cleanly without crashing.
- **Seamless Accent Color Theming**: Pre-generated theme binary suites and spritesheets for 7 vibrant presets (Cannelloni Gold `#f1c40f`, Tomato Red, Basil Green, Sky Blue, and more) with solid matching selection pills across launcher, in-game menus, settings, and tools, completely eliminating re-boot lockups.
- **Permissive Licensing**: Explicit licensing terms establishing that upstream code is copyright Shaun Inman / MinUI contributors, while all Cannelloni additions and modifications are licensed under the permissive MIT License for anyone to freely use.
- **Unified Single-Zip Distribution**: All core systems, emulators, tools, and platform installers delivered in one unified archive (`Cannelloni-20261012-0.zip`).
- **New Top-Level Settings Menu**: Direct access from the main screen to:
  - **Wi-Fi**: Connect to wireless networks, view IP, and toggle auto-start on boot directly on-device.
  - **Shaders**: Select shader preset and apply scope across consoles.
  - **Device Model**: Interactively switch or reconfigure target handheld console hardware.
  - **Accent Color**: Customize interface colors (Cannelloni Gold `#f1c40f`, Tomato Red, Basil Green, Sky Blue, and more).
  - **Button Mapping**: Swap A/B and X/Y button layouts.
  - **Emulators**: Choose preferred emulators per console (e.g. Libretro DeSmuME vs standalone DraStic for Nintendo DS).
- **Nonna's Kitchen (Web Dashboard)**: Wireless HTTP management service on port `1091` matching Android Cannelloni. Connect with any web browser to view storage, browse files, and drag-and-drop upload ROMs, BIOS, and Saves.
- **Curated Tools Section**: Focused strictly on essential utilities: `Clock`, `Files`, `Input`, `IP`, and `Nonna's Kitchen`.
- **Full Cannelloni Gold UI (#f1c40f)**: Uniform gold accent theming across all UI components, button badges `(A)`/`(B)`, battery fill and charging bolt, Wi-Fi icon, volume and brightness indicators, and solid gold selection pills across all screen scales (1x through 4x).
- **Nintendo DS Emulation**: Libretro core implementation with in-game menu (`MENU` button) and save state support, alongside optional standalone DraStic.

## Installation:
1. Format your SD card as FAT32 (MBR).
2. Drag or extract **`Cannelloni-20261012-0.zip`** directly to the root of your SD card.
3. Insert the card into your handheld and power on.
4. Use the on-screen Device Selector to pick your console model and press A (INSTALL).
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

# 2. Upload asset
asset_name = os.path.basename(UNIFIED_ZIP)
print(f"Checking assets for {asset_name}...")

req_assets = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/releases/{release_id}/assets",
    headers={
        "Authorization": f"token {token}",
        "User-Agent": "Cannelloni",
        "Accept": "application/vnd.github.v3+json"
    }
)
with urllib.request.urlopen(req_assets) as resp:
    assets = json.loads(resp.read().decode('utf-8'))
    for a in assets:
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

print(f"Uploading {UNIFIED_ZIP} ({os.path.getsize(UNIFIED_ZIP)} bytes)...")
with open(UNIFIED_ZIP, "rb") as f:
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

print(f"Release published: https://github.com/{REPO}/releases/tag/{TAG}")
