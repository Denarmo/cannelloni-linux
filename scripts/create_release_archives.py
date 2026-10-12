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

OUT_UNIFIED_ZIP = os.path.join(OUT_DIR, f"{RELEASE_NAME}.zip")

print(f"Building unified release: {OUT_UNIFIED_ZIP}...")

def add_dir_to_zip(zout, src_dir, zip_prefix, written_entries):
    """Recursively adds a local directory into a zip archive with proper permissions."""
    if not os.path.isdir(src_dir):
        return
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel = os.path.relpath(full_path, src_dir).replace("\\", "/")
            dest = f"{zip_prefix}/{rel}".strip("/")
            if dest in written_entries:
                continue
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
            written_entries.add(dest)

def patch_arm32_gold(data):
    """Patches ARM32 ELF binaries so RGB_WHITE is initialized to #f1c40f (Cannelloni Gold).
    This ensures SDL_FillRect in GFX_blitPill and GFX_blitBar renders 100% solid gold
    in the center rather than white."""
    import struct
    b = bytearray(data)
    for i in range(0, len(b) - 48, 4):
        w1 = struct.unpack('<I', b[i:i+4])[0]
        if w1 == 0xe3a030ff:  # MOV r3, #0xff
            w2_off = -1
            w3_off = -1
            for j in range(i+4, min(i+48, len(b)-4), 4):
                w = struct.unpack('<I', b[j:j+4])[0]
                if w == 0xe1a02003:  # MOV r2, r3
                    w2_off = j
                elif w == 0xe1a01003:  # MOV r1, r3
                    w3_off = j
            if w2_off != -1 and w3_off != -1:
                b[i:i+4] = struct.pack('<I', 0xe3a0300f)      # MOV r3, #0x0f (Blue)
                b[w2_off:w2_off+4] = struct.pack('<I', 0xe3a020c4)  # MOV r2, #0xc4 (Green)
                b[w3_off:w3_off+4] = struct.pack('<I', 0xe3a010f1)  # MOV r1, #0xf1 (Red)
    return bytes(b)

def patch_core_glibc(data):
    """Removes GLIBC_2.17 symbol version requirements from ARM cores so they load
    on Miyoo Mini (glibc 2.4/2.15/2.27)."""
    import struct
    b = bytearray(data)
    # 1. Replace hash of GLIBC_2.17 (0x6969197) with hash of GLIBC_2.4 (0xd696914)
    old_hash = struct.pack('<I', 0x6969197)
    new_hash = struct.pack('<I', 0xd696914)
    idx = 0
    while True:
        idx = b.find(old_hash, idx)
        if idx == -1:
            break
        b[idx:idx+4] = new_hash
        idx += 4
    # 2. Replace b'GLIBC_2.17' with b'GLIBC_2.4\x00\x00'
    idx = 0
    while True:
        idx = b.find(b'GLIBC_2.17', idx)
        if idx == -1:
            break
        b[idx:idx+10] = b'GLIBC_2.4\x00\x00'
        idx += 10
    return bytes(b)

# ----------------------------------------------------
# 1. Process and rebuild Cannelloni.zip (from MinUI.zip)
# ----------------------------------------------------
print("Processing Cannelloni.zip...")
with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in:
    minui_zip_bytes = base_in.read("MinUI.zip")

in_minui_zip = zipfile.ZipFile(io.BytesIO(minui_zip_bytes), "r")
out_cannelloni_zip_buf = io.BytesIO()
out_cannelloni_zip = zipfile.ZipFile(out_cannelloni_zip_buf, "w", zipfile.ZIP_DEFLATED)

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

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

    # Update platform Cannelloni.pak launch.sh from skeleton
    for p in platforms:
        if name == f".system/{p}/paks/Cannelloni.pak/launch.sh":
            plat_launch = f"skeleton/SYSTEM/{p}/paks/Cannelloni.pak/launch.sh"
            if os.path.isfile(plat_launch):
                with open(plat_launch, "rb") as f:
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

    # Patch ARM32 binaries to bake in Cannelloni Gold (#f1c40f) for selection pills and slider bars
    if name.endswith("/bin/minui.elf") or name.endswith("/bin/minarch.elf"):
        data = patch_arm32_gold(data)

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
        core_bytes = patch_core_glibc(core_bytes)
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
        add_dir_to_zip(out_cannelloni_zip, nds_dir, f".system/{p}/paks/Emus/NDS.pak", set())

# Default accent color configuration in Cannelloni.zip
out_cannelloni_zip.writestr(".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n")

in_minui_zip.close()
out_cannelloni_zip.close()
cannelloni_zip_bytes = out_cannelloni_zip_buf.getvalue()

# ----------------------------------------------------
# 2. Build single unified release archive
# ----------------------------------------------------
print(f"Writing {OUT_UNIFIED_ZIP}...")
written_entries = set()

with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in, \
     zipfile.ZipFile(SRC_EXTRAS_ZIP, "r") as ext_in, \
     zipfile.ZipFile(OUT_UNIFIED_ZIP, "w", zipfile.ZIP_DEFLATED) as out_zip:

    # 1. Cannelloni.zip into root
    out_zip.writestr("Cannelloni.zip", cannelloni_zip_bytes)
    written_entries.add("Cannelloni.zip")

    # 2. README.txt into root
    with open("skeleton/BASE/README.txt", "rb") as f:
        out_zip.writestr("README.txt", f.read())
    written_entries.add("README.txt")

    # 3. Base zip entries (bootloaders, update scripts, platform dirs)
    for item in base_in.infolist():
        name = item.filename
        if name in ("MinUI.zip", "Cannelloni.zip", "README.txt") or name in written_entries:
            continue

        data = base_in.read(name)
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
        out_zip.writestr(zinfo, data)
        written_entries.add(name)

        # Write .tmp_update directly to root of archive for native Miyoo stock updater compatibility
        if name.startswith("miyoo354/app/.tmp_update/"):
            tmp_name = name.replace("miyoo354/app/.tmp_update/", ".tmp_update/")
            if tmp_name not in written_entries:
                zinfo_tmp = zipfile.ZipInfo(tmp_name)
                zinfo_tmp.compress_type = zipfile.ZIP_DEFLATED
                if tmp_name.endswith(".sh") or tmp_name.endswith("updater") or tmp_name.endswith(".elf"):
                    zinfo_tmp.external_attr = 0o755 << 16
                else:
                    zinfo_tmp.external_attr = 0o644 << 16
                out_zip.writestr(zinfo_tmp, data)
                written_entries.add(tmp_name)

    # 4. Extras zip entries (extra emulators, tools, bios/rom placeholders)
    for item in ext_in.infolist():
        name = item.filename
        if name in ("README.txt", "Cannelloni.zip", "MinUI.zip") or name in written_entries:
            continue
        # Skip tools and emu paks that we are inserting freshly
        if any(name.startswith(f"Tools/{p}/Wi-Fi.pak/") or name.startswith(f"Tools/{p}/Nonna's Kitchen.pak/") or name.startswith(f"Emus/{p}/NDS.pak/") for p in platforms):
            continue

        data = ext_in.read(name)
        try:
            content = data.decode("utf-8")
            content = content.replace("MinUI", "Cannelloni").replace("minui", "cannelloni")
            data = content.encode("utf-8")
        except UnicodeDecodeError:
            pass

        out_zip.writestr(item, data)
        written_entries.add(name)

    # 5. Add Nintendo DS ROM & Bios folders
    if "Roms/Nintendo DS (NDS)/.keep" not in written_entries:
        out_zip.writestr("Roms/Nintendo DS (NDS)/.keep", b"# Nintendo DS ROMs (.nds, .zip)\n")
        written_entries.add("Roms/Nintendo DS (NDS)/.keep")
    if "Bios/NDS/.keep" not in written_entries:
        out_zip.writestr("Bios/NDS/.keep", b"# NDS Bios: bios7.bin, bios9.bin, firmware.bin\n")
        written_entries.add("Bios/NDS/.keep")

    # 6. Default accent color setting
    out_zip.writestr(".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n")
    written_entries.add(".userdata/shared/.cannelloni/accent_color.txt")

    # 7. Add Nonna's Kitchen & Wi-Fi tool paks across all platforms
    for p in platforms:
        k_dir = f"skeleton/EXTRAS/Tools/{p}/Nonna's Kitchen.pak"
        if not os.path.isdir(k_dir):
            k_dir = "skeleton/EXTRAS/Tools/miyoomini/Nonna's Kitchen.pak"
        add_dir_to_zip(out_zip, k_dir, f"Tools/{p}/Nonna's Kitchen.pak", written_entries)

        w_dir = f"skeleton/EXTRAS/Tools/{p}/Wi-Fi.pak"
        if not os.path.isdir(w_dir):
            w_dir = "skeleton/EXTRAS/Tools/miyoomini/Wi-Fi.pak"
        add_dir_to_zip(out_zip, w_dir, f"Tools/{p}/Wi-Fi.pak", written_entries)

        nds_emu_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
        if os.path.isdir(nds_emu_dir):
            add_dir_to_zip(out_zip, nds_emu_dir, f"Emus/{p}/NDS.pak", written_entries)

    # 8. Include NDS-Drastic.pak in Emus/miyoomini for users who also want standalone DraStic
    drastic_dir = "skeleton/EXTRAS/Emus/miyoomini/NDS-Drastic.pak"
    if os.path.isdir(drastic_dir):
        add_dir_to_zip(out_zip, drastic_dir, "Emus/miyoomini/NDS-Drastic.pak", written_entries)

print(f"Unified package completed: {os.path.getsize(OUT_UNIFIED_ZIP)} bytes ({len(written_entries)} entries)")
print("Release archive built successfully!")
