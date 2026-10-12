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

def add_dir_to_zip(zout, src_dir, zip_prefix):
    """Recursively adds a local directory into a zip archive with proper permissions."""
    if not os.path.isdir(src_dir):
        return
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel = os.path.relpath(full_path, src_dir).replace("\\", "/")
            dest = f"{zip_prefix}/{rel}".strip("/")
            with open(full_path, "rb") as fp:
                data = fp.read()
            zinfo = zipfile.ZipInfo(dest)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            is_exec = (
                f.endswith((".sh", ".elf", "MainUI", "updater")) or
                ("." not in f and not f.startswith(".")) or
                f in (
                    "drastic", "cpuclock", "show_hotkeys", "minui-keyboard",
                    "minui-list", "minui-presenter", "iw", "jq", "service-on",
                    "service-off", "wifi-enabled", "on-boot", "png2raw"
                )
            )
            if is_exec:
                zinfo.external_attr = 0o755 << 16
            else:
                zinfo.external_attr = 0o644 << 16
            zout.writestr(zinfo, data)

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

    # Update .tmp_update/miyoomini.sh with updated boot script
    if name == ".tmp_update/miyoomini.sh":
        with open("workspace/miyoomini/install/boot.sh", "rb") as f:
            data = f.read()

    # Update miyoomini launch.sh
    if name == ".system/miyoomini/paks/Cannelloni.pak/launch.sh":
        with open("skeleton/SYSTEM/miyoomini/paks/Cannelloni.pak/launch.sh", "rb") as f:
            data = f.read()

    # Overwrite assets@*.png with our tinted Cannelloni gold #f1c40f spritesheet
    if name.startswith(".system/res/assets@") and name.endswith(".png"):
        local_res = os.path.join("skeleton/SYSTEM/res", os.path.basename(name))
        if os.path.isfile(local_res):
            with open(local_res, "rb") as f:
                data = f.read()

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

    # Ensure cannelloni.elf exists alongside minui.elf
    if name.endswith("/bin/minui.elf"):
        cannelloni_name = name.replace("/bin/minui.elf", "/bin/cannelloni.elf")
        zinfo_c = zipfile.ZipInfo(cannelloni_name)
        zinfo_c.compress_type = zipfile.ZIP_DEFLATED
        zinfo_c.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_c, data)

    zinfo = zipfile.ZipInfo(name)
    zinfo.compress_type = zipfile.ZIP_DEFLATED
    if name.endswith(".sh") or name.endswith("MainUI") or name.endswith("updater") or name.endswith(".elf") or name.endswith(".bin"):
        zinfo.external_attr = 0o755 << 16
    else:
        zinfo.external_attr = 0o644 << 16
    out_cannelloni_zip.writestr(zinfo, data)

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

# Inject NDS Libretro cores across all platforms in Cannelloni.zip
print("Injecting NDS libretro cores into Cannelloni.zip...")
for p in platforms:
    if p == 'rg35xxplus':
        core_file = "build_release/temp/cores/melonds_libretro_aarch64.so"
    else:
        core_file = "build_release/temp/cores/melonds_libretro.so"

    if os.path.isfile(core_file):
        with open(core_file, "rb") as f:
            core_bytes = f.read()
        zinfo_m = zipfile.ZipInfo(f".system/{p}/cores/melonds_libretro.so")
        zinfo_m.compress_type = zipfile.ZIP_DEFLATED
        zinfo_m.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_m, core_bytes)

        zinfo_d = zipfile.ZipInfo(f".system/{p}/cores/desmume2015_libretro.so")
        zinfo_d.compress_type = zipfile.ZIP_DEFLATED
        zinfo_d.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_d, core_bytes)

# Add NDS.pak across all platforms from skeleton
for p in platforms:
    nds_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
    if os.path.isdir(nds_dir):
        add_dir_to_zip(out_cannelloni_zip, nds_dir, f".system/{p}/paks/Emus/NDS.pak")

# Default accent color configuration in Cannelloni.zip
out_cannelloni_zip.writestr(".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n")

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
        if name.endswith("/app/MainUI") or name == "miyoo/app/MainUI":
            with open("skeleton/BOOT/miyoo/app/MainUI", "rb") as f:
                data = f.read()
        elif name.endswith("/app/miyoomini.sh"):
            with open("skeleton/BOOT/miyoo/app/miyoomini.sh", "rb") as f:
                data = f.read()
        elif name.endswith(".tmp_update/updater"):
            with open("skeleton/BOOT/common/updater", "rb") as f:
                data = f.read()
        elif name.endswith(".tmp_update/miyoomini.sh"):
            with open("workspace/miyoomini/install/boot.sh", "rb") as f:
                data = f.read()
        elif name.endswith(".sh") or name.endswith(".txt"):
            try:
                content = data.decode("utf-8")
                content = content.replace("MinUI.zip", "Cannelloni.zip")
                content = content.replace("MinUI.pak", "Cannelloni.pak")
                content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
                content = content.replace(".minui", ".cannelloni")
                data = content.encode("utf-8")
            except UnicodeDecodeError:
                pass

        zinfo = zipfile.ZipInfo(name)
        zinfo.compress_type = zipfile.ZIP_DEFLATED
        if name.endswith(".sh") or name.endswith("MainUI") or name.endswith("updater") or name.endswith(".elf") or name.endswith(".bin"):
            zinfo.external_attr = 0o755 << 16
        else:
            zinfo.external_attr = 0o644 << 16
        base_out.writestr(zinfo, data)

        # Also write .tmp_update directly to root of base archive for native Miyoo stock updater compatibility
        if name.startswith("miyoo354/app/.tmp_update/"):
            tmp_name = name.replace("miyoo354/app/.tmp_update/", ".tmp_update/")
            zinfo_tmp = zipfile.ZipInfo(tmp_name)
            zinfo_tmp.compress_type = zipfile.ZIP_DEFLATED
            if tmp_name.endswith(".sh") or tmp_name.endswith("updater") or tmp_name.endswith(".elf"):
                zinfo_tmp.external_attr = 0o755 << 16
            else:
                zinfo_tmp.external_attr = 0o644 << 16
            base_out.writestr(zinfo_tmp, data)

    # Add Nintendo DS ROM folder
    base_out.writestr("Roms/Nintendo DS (NDS)/.keep", b"# Nintendo DS ROMs (.nds, .zip)\n")
    # Add Bios/NDS folder
    base_out.writestr("Bios/NDS/.keep", b"# NDS Bios: bios7.bin, bios9.bin, firmware.bin\n")

    # Default accent color setting
    base_out.writestr(".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n")

    # Add Essential Tools (Nonna's Kitchen & Wi-Fi) directly to Base package
    for p in platforms:
        k_dir = f"skeleton/EXTRAS/Tools/{p}/Nonna's Kitchen.pak"
        if not os.path.isdir(k_dir):
            k_dir = "skeleton/EXTRAS/Tools/miyoomini/Nonna's Kitchen.pak"
        add_dir_to_zip(base_out, k_dir, f"Tools/{p}/Nonna's Kitchen.pak")

        w_dir = f"skeleton/EXTRAS/Tools/{p}/Wi-Fi.pak"
        if not os.path.isdir(w_dir):
            w_dir = "skeleton/EXTRAS/Tools/miyoomini/Wi-Fi.pak"
        add_dir_to_zip(base_out, w_dir, f"Tools/{p}/Wi-Fi.pak")

        # Also include NDS.pak in Emus/ for Base package
        nds_emu_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
        if os.path.isdir(nds_emu_dir):
            add_dir_to_zip(base_out, nds_emu_dir, f"Emus/{p}/NDS.pak")

print(f"Base package completed: {os.path.getsize(OUT_BASE_ZIP)} bytes")

# ----------------------------------------------------
# 3. Rebuild extras zip
# ----------------------------------------------------
print(f"Writing {OUT_EXTRAS_ZIP}...")
with zipfile.ZipFile(SRC_EXTRAS_ZIP, "r") as ext_in, \
     zipfile.ZipFile(OUT_EXTRAS_ZIP, "w", zipfile.ZIP_DEFLATED) as ext_out:

    for item in ext_in.infolist():
        name = item.filename
        # Avoid duplicating tools and emu paks that we are inserting freshly
        if any(name.startswith(f"Tools/{p}/Wi-Fi.pak/") or name.startswith(f"Tools/{p}/Nonna's Kitchen.pak/") or name.startswith(f"Emus/{p}/NDS.pak/") for p in platforms):
            continue

        data = ext_in.read(name)
        if name == "README.txt":
            # Update README with Cannelloni branding
            try:
                content = data.decode("utf-8").replace("MinUI", "Cannelloni").replace("minui", "cannelloni")
                data = content.encode("utf-8")
            except UnicodeDecodeError:
                pass
        ext_out.writestr(item, data)

    # Add Nonna's Kitchen & Wi-Fi tool paks across all platforms
    for p in platforms:
        k_dir = f"skeleton/EXTRAS/Tools/{p}/Nonna's Kitchen.pak"
        if not os.path.isdir(k_dir):
            k_dir = "skeleton/EXTRAS/Tools/miyoomini/Nonna's Kitchen.pak"
        add_dir_to_zip(ext_out, k_dir, f"Tools/{p}/Nonna's Kitchen.pak")

        w_dir = f"skeleton/EXTRAS/Tools/{p}/Wi-Fi.pak"
        if not os.path.isdir(w_dir):
            w_dir = "skeleton/EXTRAS/Tools/miyoomini/Wi-Fi.pak"
        add_dir_to_zip(ext_out, w_dir, f"Tools/{p}/Wi-Fi.pak")

        nds_emu_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
        if os.path.isdir(nds_emu_dir):
            add_dir_to_zip(ext_out, nds_emu_dir, f"Emus/{p}/NDS.pak")

    # Include NDS-Drastic.pak in extras for users who also want standalone DraStic
    drastic_dir = "skeleton/EXTRAS/Emus/miyoomini/NDS-Drastic.pak"
    if os.path.isdir(drastic_dir):
        add_dir_to_zip(ext_out, drastic_dir, "Emus/miyoomini/NDS-Drastic.pak")

print(f"Extras package completed: {os.path.getsize(OUT_EXTRAS_ZIP)} bytes")
print("All release archives built successfully!")
