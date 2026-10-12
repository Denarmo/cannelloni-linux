import os
import io
import zipfile
import shutil

RELEASE_TAG = "v20261012-0"
RELEASE_NAME = "Cannelloni-20261012-0"
COMMIT_HASH = "daeb0044fa9202568778f309a96eec5d36e885d9"

SRC_BASE_ZIP = "build_release/temp/base.zip"
SRC_EXTRAS_ZIP = "build_release/temp/extras.zip"
OUT_DIR = "releases"
os.makedirs("build_release/temp", exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

import urllib.request
if not os.path.isfile(SRC_BASE_ZIP):
    print("Downloading upstream base release template...")
    urllib.request.urlretrieve("https://github.com/shauninman/MinUI/releases/download/v20251127-1/MinUI-20251127-1-base.zip", SRC_BASE_ZIP)
if not os.path.isfile(SRC_EXTRAS_ZIP):
    print("Downloading upstream extras release template...")
    urllib.request.urlretrieve("https://github.com/shauninman/MinUI/releases/download/v20251127-1/MinUI-20251127-1-extras.zip", SRC_EXTRAS_ZIP)

OUT_BASE_ZIP = os.path.join(OUT_DIR, f"{RELEASE_NAME}-base.zip")
OUT_EXTRAS_ZIP = os.path.join(OUT_DIR, f"{RELEASE_NAME}-extras.zip")

print(f"Building {RELEASE_NAME} releases...")

# ----------------------------------------------------
# 1. Process and rebuild Cannelloni.zip (from MinUI.zip)
# ----------------------------------------------------
print("Processing Cannelloni.zip...")
with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in:
    minui_zip_bytes = base_in.read("MinUI.zip")

in_minui_zip = zipfile.ZipFile(io.BytesIO(minui_zip_bytes), "r")
out_cannelloni_zip_buf = io.BytesIO()
out_cannelloni_zip = zipfile.ZipFile(out_cannelloni_zip_buf, "w", zipfile.ZIP_DEFLATED)

# Read all entries from MinUI.zip, adapting and updating
for item in in_minui_zip.infolist():
    name = item.filename
    data = in_minui_zip.read(name)

    # Rename MinUI.pak -> Cannelloni.pak
    if "paks/MinUI.pak" in name:
        name = name.replace("paks/MinUI.pak", "paks/Cannelloni.pak")
        if name.endswith("launch.sh"):
            # Update launch script to cannelloni.elf
            content = data.decode("utf-8", errors="ignore")
            content = content.replace("minui.elf", "cannelloni.elf")
            content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
            content = content.replace(".minui", ".cannelloni")
            data = content.encode("utf-8")

    # Update version.txt
    if name == ".system/version.txt":
        data = f"{RELEASE_NAME}\n{COMMIT_HASH}\n".encode("utf-8")

    # Update any minui references in scripts
    if name.endswith(".sh") or name.endswith(".txt"):
        try:
            content = data.decode("utf-8")
            content = content.replace("MinUI.pak", "Cannelloni.pak")
            content = content.replace("MinUI.zip", "Cannelloni.zip")
            content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
            content = content.replace(".minui", ".cannelloni")
            data = content.encode("utf-8")
        except UnicodeDecodeError:
            pass

    out_cannelloni_zip.writestr(name, data)

# Add NDS.pak across all platforms from our skeleton
platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

for p in platforms:
    nds_launch_path = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak/launch.sh"
    nds_cfg_path = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak/default.cfg"
    if os.path.isfile(nds_launch_path):
        with open(nds_launch_path, "rb") as f:
            out_cannelloni_zip.writestr(f".system/{p}/paks/Emus/NDS.pak/launch.sh", f.read())
    if os.path.isfile(nds_cfg_path):
        with open(nds_cfg_path, "rb") as f:
            out_cannelloni_zip.writestr(f".system/{p}/paks/Emus/NDS.pak/default.cfg", f.read())

in_minui_zip.close()
out_cannelloni_zip.close()
cannelloni_zip_bytes = out_cannelloni_zip_buf.getvalue()

# ----------------------------------------------------
# 2. Rebuild base zip
# ----------------------------------------------------
print(f"Writing {OUT_BASE_ZIP}...")
with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in, \
     zipfile.ZipFile(OUT_BASE_ZIP, "w", zipfile.ZIP_DEFLATED) as base_out:

    for item in base_in.infolist():
        name = item.filename
        if name == "MinUI.zip":
            # Replace with Cannelloni.zip
            base_out.writestr("Cannelloni.zip", cannelloni_zip_bytes)
            continue
        elif name == "README.txt":
            # Replace with updated README.txt
            with open("skeleton/BASE/README.txt", "rb") as f:
                base_out.writestr("README.txt", f.read())
            continue

        data = base_in.read(name)
        # Process and adapt scripts inside installer directories (e.g. rg35xxplus, trimui, etc.)
        if name.endswith(".sh") or name.endswith(".txt"):
            try:
                content = data.decode("utf-8")
                content = content.replace("MinUI.zip", "Cannelloni.zip")
                content = content.replace("MinUI.pak", "Cannelloni.pak")
                content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
                content = content.replace(".minui", ".cannelloni")
                data = content.encode("utf-8")
            except UnicodeDecodeError:
                pass

        base_out.writestr(name, data)

    # Add Nintendo DS ROM folder
    base_out.writestr("Roms/Nintendo DS (NDS)/.keep", b"# Nintendo DS ROMs (.nds, .zip)\n")
    # Add Bios/NDS folder
    base_out.writestr("Bios/NDS/.keep", b"# NDS Bios: bios7.bin, bios9.bin, firmware.bin\n")

print(f"Base package completed: {os.path.getsize(OUT_BASE_ZIP)} bytes")

# ----------------------------------------------------
# 3. Rebuild extras zip
# ----------------------------------------------------
print(f"Writing {OUT_EXTRAS_ZIP}...")
with zipfile.ZipFile(SRC_EXTRAS_ZIP, "r") as ext_in, \
     zipfile.ZipFile(OUT_EXTRAS_ZIP, "w", zipfile.ZIP_DEFLATED) as ext_out:

    for item in ext_in.infolist():
        name = item.filename
        data = ext_in.read(name)
        if name == "README.txt":
            # Update README with Cannelloni branding
            try:
                content = data.decode("utf-8").replace("MinUI", "Cannelloni").replace("minui", "cannelloni")
                data = content.encode("utf-8")
            except UnicodeDecodeError:
                pass
        ext_out.writestr(name, data)

    # Add Nonna's Kitchen tool pak across all platforms
    for p in platforms:
        pak_path = f"skeleton/EXTRAS/Tools/{p}/Nonna's Kitchen.pak/launch.sh"
        if os.path.isfile(pak_path):
            with open(pak_path, "rb") as f:
                ext_out.writestr(f"Tools/{p}/Nonna's Kitchen.pak/launch.sh", f.read())

print(f"Extras package completed: {os.path.getsize(OUT_EXTRAS_ZIP)} bytes")
print("All release archives built successfully!")
