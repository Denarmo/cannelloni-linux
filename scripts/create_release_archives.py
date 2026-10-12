import os
import io
import zipfile
import shutil
import struct
import urllib.request
import tarfile
import binascii

RELEASE_TAG = "v20261012-0"
RELEASE_NAME = "Cannelloni-20261012-0"
COMMIT_HASH = "daeb0044fa9202568778f309a96eec5d36e885d9"

SRC_BASE_ZIP = "build_release/temp/base.zip"
SRC_EXTRAS_ZIP = "build_release/temp/extras.zip"
OUT_DIR = "releases"
OUT_UNIFIED_ZIP = os.path.join(OUT_DIR, f"{RELEASE_NAME}.zip")

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
            TEXT_EXTS = ('.sh', '.txt', '.json', '.cfg', '.ini', '.csv', '.pak_id', '.md')
            if any(f.endswith(ext) for ext in TEXT_EXTS) or f in ('updater', 'MainUI', 'on-boot', 'service-on', 'service-off', 'wifi-enabled'):
                data = data.replace(b'\r\n', b'\n')
            zinfo = zipfile.ZipInfo(dest)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            is_exec = (
                f.endswith((".sh", ".elf", "MainUI", "updater", ".cgi", ".so")) or
                ("." not in f and not f.startswith(".")) or
                f in (
                    "drastic", "cpuclock", "show_hotkeys", "minui-keyboard",
                    "minui-list", "minui-presenter", "cannelloni-keyboard",
                    "cannelloni-list", "cannelloni-presenter", "cannelloni.elf",
                    "iw", "jq", "service-on", "service-off", "wifi-enabled",
                    "on-boot", "png2raw"
                )
            )
            if is_exec:
                zinfo.external_attr = 0o755 << 16
            else:
                zinfo.external_attr = 0o644 << 16
            zout.writestr(zinfo, data)
            written_entries.add(dest)

def patch_binary_accent_color(data, r=0xf1, g=0xc4, b=0x0f):
    """Patches ARM32, AArch64, and MIPS ELF binaries so RGB_WHITE is initialized to (r, g, b).
    This ensures SDL_FillRect in GFX_blitPill and GFX_blitBar renders 100% solid accent color
    in the center rather than white."""
    if not data.startswith(b'\x7fELF') or len(data) < 52:
        return data
    barr = bytearray(data)
    e_machine = struct.unpack('<H', barr[18:20])[0]
    
    # ARM32 (EM_ARM = 40 = 0x28)
    if e_machine == 40:
        pos = 0
        while True:
            idx_gray = barr.find(b'\x7f\x30\xa0\xe3', pos)
            if idx_gray == -1:
                break
            pos = idx_gray + 4
            for off in range(max(0, idx_gray - 140), idx_gray, 4):
                w = struct.unpack('<I', barr[off:off+4])[0]
                if (w & 0xffffff00) == 0xe3a03000:
                    w2_off, w3_off = -1, -1
                    for j in range(off+4, min(off+48, idx_gray), 4):
                        wj = struct.unpack('<I', barr[j:j+4])[0]
                        if wj == 0xe1a02003 or (wj & 0xffffff00) == 0xe3a02000:
                            w2_off = j
                        elif wj == 0xe1a01003 or (wj & 0xffffff00) == 0xe3a01000:
                            w3_off = j
                    if w2_off != -1 and w3_off != -1:
                        barr[off:off+4] = struct.pack('<I', 0xe3a03000 | b)
                        barr[w2_off:w2_off+4] = struct.pack('<I', 0xe3a02000 | g)
                        barr[w3_off:w3_off+4] = struct.pack('<I', 0xe3a01000 | r)
                        break

    # AArch64 (EM_AARCH64 = 183 = 0xb7)
    elif e_machine == 183:
        pos = 0
        while True:
            idx_gray = barr.find(struct.pack('<I', 0x52800fe3), pos)
            if idx_gray == -1:
                break
            pos = idx_gray + 4
            for off in range(max(0, idx_gray - 140), idx_gray, 4):
                w = struct.unpack('<I', barr[off:off+4])[0]
                if w == 0x12800003 or (w & 0xffe0001f) == 0x52800003:
                    w2_off, w3_off = -1, -1
                    for j in range(off+4, min(off+48, idx_gray), 4):
                        wj = struct.unpack('<I', barr[j:j+4])[0]
                        if wj == 0x2a0303e2 or (wj & 0xffe0001f) == 0x52800002:
                            w2_off = j
                        elif wj == 0x2a0303e1 or (wj & 0xffe0001f) == 0x52800001:
                            w3_off = j
                    if w2_off != -1 and w3_off != -1:
                        barr[off:off+4] = struct.pack('<I', 0x52800003 | (b << 5))
                        barr[w2_off:w2_off+4] = struct.pack('<I', 0x52800002 | (g << 5))
                        barr[w3_off:w3_off+4] = struct.pack('<I', 0x52800001 | (r << 5))
                        break

    # MIPS (EM_MIPS = 8)
    elif e_machine == 8:
        pos = 0
        while True:
            idx_gray = barr.find(struct.pack('<I', 0x2405007f), pos)
            if idx_gray == -1:
                break
            pos = idx_gray + 4
            for off in range(max(0, idx_gray - 140), idx_gray, 4):
                w1 = struct.unpack('<I', barr[off:off+4])[0]
                if (w1 & 0xffff0000) == 0x24050000:
                    w2_off, w3_off = -1, -1
                    for j in range(off+4, min(off+32, idx_gray), 4):
                        wj = struct.unpack('<I', barr[j:j+4])[0]
                        if (wj & 0xffff0000) == 0x24060000 and w2_off == -1:
                            w2_off = j
                        elif (wj & 0xffff0000) == 0x24070000 and w3_off == -1:
                            w3_off = j
                    if w2_off != -1 and w3_off != -1:
                        barr[off:off+4] = struct.pack('<I', 0x24050000 | r)
                        barr[w2_off:w2_off+4] = struct.pack('<I', 0x24060000 | g)
                        barr[w3_off:w3_off+4] = struct.pack('<I', 0x24070000 | b)
                        break

    return bytes(barr)

def patch_minui_settings(data, platform):
    """Patches minui.elf so that /mnt/SDCARD/Settings/<platform> is discovered and
    added to root alongside Tools."""
    if platform != 'miyoomini':
        return data
    b = bytearray(data)
    hook_offset = 0x1bb98
    jump_offset = 0x54ac
    hook_bin_path = 'build_release/temp/hook_resolved.bin'
    if os.path.isfile(hook_bin_path) and len(b) > hook_offset + 300:
        if b[jump_offset:jump_offset+4] == b'\xb4\x00\x0b\xe3':
            with open(hook_bin_path, 'rb') as f:
                hook = f.read()
            b[hook_offset : hook_offset + len(hook)] = hook
            b_inst = 0xea000000 | 0x59b9
            b[jump_offset : jump_offset + 4] = struct.pack('<I', b_inst)
            print("Patched Settings menu hook into miyoomini ELF!")
    return bytes(b)

def patch_about_page(data, name):
    """Patches minui.elf to display About and Fork labels on the About page.
    Leaves the version.txt path completely untouched to prevent any crash."""
    b = bytearray(data)
    idx = b.find(b"Release\x00Commit\x00\x00")
    if idx != -1:
        b[idx : idx+8] = b"About\x00\x00\x00"
        b[idx+8 : idx+16] = b"Fork\x00\x00\x00\x00"
    return bytes(b)


def build_dmenu_rg35xxplus():
    """Builds RG35XX Plus/H/SP/CubeXX/28XX dmenu.bin with official Cannelloni assets."""
    with zipfile.ZipFile(SRC_BASE_ZIP) as z:
        orig_dmenu = z.read("rg35xxplus/dmenu.bin")
    idx = orig_dmenu.find(b"BINARY\n")
    orig_tar = orig_dmenu[idx+7:]
    unzip_data = None
    with tarfile.open(fileobj=io.BytesIO(orig_tar), mode="r:gz") as tar:
        for m in tar.getmembers():
            if m.name == "unzip":
                unzip_data = tar.extractfile(m).read()
                break
    
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
        def add_bytes(name, data, mode=0o644):
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            ti.mode = mode
            ti.mtime = 1700000000
            tar.addfile(ti, io.BytesIO(data))
        
        add_bytes("bootlogo.bmp", open("workspace/rg35xxplus/boot/bootlogo.bmp", "rb").read())
        add_bytes("installing", open("workspace/rg35xxplus/boot/installing.bmp", "rb").read()[54:])
        add_bytes("updating", open("workspace/rg35xxplus/boot/updating.bmp", "rb").read()[54:])
        add_bytes("bootlogo-r.bmp", open("workspace/rg35xxplus/boot/bootlogo-r.bmp", "rb").read())
        add_bytes("installing-r", open("workspace/rg35xxplus/boot/installing-r.bmp", "rb").read()[54:])
        add_bytes("updating-r", open("workspace/rg35xxplus/boot/updating-r.bmp", "rb").read()[54:])
        add_bytes("bootlogo-s.bmp", open("workspace/rg35xxplus/boot/bootlogo-s.bmp", "rb").read())
        add_bytes("installing-s", open("workspace/rg35xxplus/boot/installing-s.bmp", "rb").read()[54:])
        add_bytes("updating-s", open("workspace/rg35xxplus/boot/updating-s.bmp", "rb").read()[54:])
        add_bytes("bootlogo-w.bmp", open("workspace/rg35xxplus/boot/bootlogo-w.bmp", "rb").read())
        add_bytes("installing-w", open("workspace/rg35xxplus/boot/installing-w.bmp", "rb").read()[54:])
        add_bytes("updating-w", open("workspace/rg35xxplus/boot/updating-w.bmp", "rb").read()[54:])
        if unzip_data:
            add_bytes("unzip", unzip_data, mode=0o755)
    new_tar = tar_buf.getvalue()
    boot_sh = open("workspace/rg35xxplus/boot/boot.sh", "rb").read()
    return boot_sh + b"BINARY\n" + new_tar + b"\n"

def build_dmenu_rg35xx():
    """Builds RG35XX (original) dmenu.bin with official Cannelloni assets."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("installing", open("workspace/rg35xx/boot/installing.bmp", "rb").read()[64:])
        z.writestr("updating", open("workspace/rg35xx/boot/updating.bmp", "rb").read()[64:])
    zip_data = zip_buf.getvalue()
    uu_lines = [b"begin 644 data\n"]
    for i in range(0, len(zip_data), 45):
        uu_lines.append(binascii.b2a_uu(zip_data[i:i+45]))
    uu_lines.append(b"`\nend\n")
    boot_sh = open("workspace/rg35xx/boot/boot.sh", "rb").read()
    return boot_sh + b"BINARY\n" + b"".join(uu_lines)

def build_release():
    os.makedirs("build_release/temp", exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    if not os.path.isfile(SRC_BASE_ZIP):
        print("Downloading upstream base release template...")
        urllib.request.urlretrieve("https://github.com/shauninman/MinUI/releases/download/v20251127-1/MinUI-20251127-1-base.zip", SRC_BASE_ZIP)
    if not os.path.isfile(SRC_EXTRAS_ZIP):
        print("Downloading upstream extras release template...")
        urllib.request.urlretrieve("https://github.com/shauninman/MinUI/releases/download/v20251127-1/MinUI-20251127-1-extras.zip", SRC_EXTRAS_ZIP)

    print(f"Building unified release: {OUT_UNIFIED_ZIP}...")

    # ----------------------------------------------------
    # 1. Process and rebuild Cannelloni.zip (from MinUI.zip)
    # ----------------------------------------------------
    print("Processing Cannelloni.zip...")
    with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in:
        minui_zip_bytes = base_in.read("MinUI.zip")

    in_minui_zip = zipfile.ZipFile(io.BytesIO(minui_zip_bytes), "r")
    out_cannelloni_release = os.path.join(OUT_DIR, "Cannelloni.zip")
    out_cannelloni_zip = zipfile.ZipFile(out_cannelloni_release, "w", zipfile.ZIP_DEFLATED)
    written_entries = set()

    platforms = [
        'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
        'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
    ]

    # Read all entries from MinUI.zip, adapting and updating
    for item in in_minui_zip.infolist():
        name = item.filename
        data = in_minui_zip.read(name)

        # Skip MinUI.pak entries from upstream as they are superseded by skeleton Cannelloni.pak
        if "paks/MinUI.pak" in name:
            continue

        # Inject updated platform bootstrap and updater scripts
        if name.endswith(".tmp_update/updater") or name == ".tmp_update/updater":
            with open("skeleton/BOOT/common/updater", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/miyoomini.sh") or name == ".tmp_update/miyoomini.sh":
            with open("workspace/miyoomini/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/my282.sh") or name == ".tmp_update/my282.sh":
            with open("workspace/my282/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/my355.sh") or name == ".tmp_update/my355.sh":
            with open("workspace/my355/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/tg5040.sh") or name == ".tmp_update/tg5040.sh":
            with open("workspace/tg5040/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/trimuismart.sh") or name == ".tmp_update/trimuismart.sh":
            with open("workspace/trimuismart/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        elif name.endswith(".tmp_update/zero28.sh") or name == ".tmp_update/zero28.sh":
            with open("workspace/zero28/install/boot.sh", "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
        # Update any minui references in scripts
        elif (name.endswith(".sh") or name.endswith(".txt")) and name != ".system/version.txt":
            try:
                content = data.decode("utf-8")
                content = content.replace("MinUI.pak", "Cannelloni.pak")
                content = content.replace("MinUI.zip", "Cannelloni.zip")
                content = content.replace("MinUI", "Cannelloni")
                content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
                content = content.replace(".minui", ".cannelloni")
                data = content.encode("utf-8")
            except UnicodeDecodeError:
                pass

        # Update version.txt
        if name == ".system/version.txt":
            data = b"Cannelloni\nforked from MinUI/Cannoli\n"

        # Update dat boot logo files with official Cannelloni assets
        if name == ".system/miyoomini/dat/image1.jpg":
            img1_path = "skeleton/SYSTEM/miyoomini/dat/image1.jpg"
            if os.path.isfile(img1_path):
                with open(img1_path, "rb") as fp:
                    data = fp.read()
        elif name == ".system/trimuismart/dat/logo.bmp":
            l_path = "skeleton/SYSTEM/trimuismart/dat/logo.bmp"
            if os.path.isfile(l_path):
                with open(l_path, "rb") as fp:
                    data = fp.read()

        # Override stock MinUI spritesheets with official Cannelloni Gold (#f1c40f) assets
        if name.startswith(".system/res/assets@"):
            bn = os.path.basename(name)
            gold_asset = os.path.join("skeleton/SYSTEM/res/themes/#f1c40f", bn)
            if not os.path.isfile(gold_asset):
                gold_asset = os.path.join("skeleton/SYSTEM/res", bn)
            if os.path.isfile(gold_asset):
                with open(gold_asset, "rb") as fp:
                    data = fp.read()

        # Patch ELF binaries to bake in Cannelloni Gold (#f1c40f) for selection pills and slider bars
        if name.endswith("/bin/minui.elf") or name.endswith("/bin/minarch.elf"):
            data = patch_binary_accent_color(data, 241, 196, 15)

        # Patch About page and Settings menu hook into ELF
        if name.endswith("/bin/minui.elf"):
            data = patch_about_page(data, name)
            if name == ".system/miyoomini/bin/minui.elf":
                data = patch_minui_settings(data, "miyoomini")

        # Ensure cannelloni.elf exists alongside minui.elf
        if name.endswith("/bin/minui.elf"):
            cannelloni_name = name.replace("/bin/minui.elf", "/bin/cannelloni.elf")
            if cannelloni_name not in written_entries:
                zinfo_c = zipfile.ZipInfo(cannelloni_name)
                zinfo_c.compress_type = zipfile.ZIP_DEFLATED
                zinfo_c.external_attr = 0o755 << 16
                out_cannelloni_zip.writestr(zinfo_c, data)
                written_entries.add(cannelloni_name)

        if name not in written_entries:
            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            if name.endswith(".sh") or name.endswith("MainUI") or name.endswith("updater") or name.endswith(".elf") or name.endswith(".bin"):
                zinfo.external_attr = 0o755 << 16
            else:
                zinfo.external_attr = 0o644 << 16
            out_cannelloni_zip.writestr(zinfo, data)
            written_entries.add(name)

    # Inject NDS Libretro cores across all platforms in Cannelloni.zip
    print("Injecting clean NDS libretro cores into Cannelloni.zip...")
    core_file = "build_release/temp/cores/desmume2015_libretro.so"
    if os.path.isfile(core_file):
        with open(core_file, "rb") as f:
            core_bytes = f.read()
        for p in platforms:
            if p == 'rg35xxplus':
                c_file = "build_release/temp/cores/melonds_libretro_aarch64.so"
                c_bytes = open(c_file, "rb").read() if os.path.isfile(c_file) else core_bytes
            else:
                c_bytes = core_bytes

            zinfo_m = zipfile.ZipInfo(f".system/{p}/cores/melonds_libretro.so")
            zinfo_m.compress_type = zipfile.ZIP_DEFLATED
            zinfo_m.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zinfo_m, c_bytes)

            zinfo_d = zipfile.ZipInfo(f".system/{p}/cores/desmume2015_libretro.so")
            zinfo_d.compress_type = zipfile.ZIP_DEFLATED
            zinfo_d.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zinfo_d, c_bytes)

    # Bundle clean libstdc++.so.6 (patched to GLIBC_2.4) for miyoomini
    libstdc_path = "build_release/temp/libstdc++.so.6"
    if os.path.isfile(libstdc_path):
        with open(libstdc_path, "rb") as f:
            libstdc_bytes = f.read()
        zinfo_s = zipfile.ZipInfo(".system/miyoomini/lib/libstdc++.so.6")
        zinfo_s.compress_type = zipfile.ZIP_DEFLATED
        zinfo_s.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_s, libstdc_bytes)

    # Add NDS.pak across all platforms from skeleton
    for p in platforms:
        nds_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
        if os.path.isdir(nds_dir):
            add_dir_to_zip(out_cannelloni_zip, nds_dir, f".system/{p}/paks/Emus/NDS.pak", set())

    # Add pre-rendered accent themes into .system/res/themes
    themes_dir = "skeleton/SYSTEM/res/themes"
    if os.path.isdir(themes_dir):
        add_dir_to_zip(out_cannelloni_zip, themes_dir, ".system/res/themes", set())

    # Pre-generate pre-patched theme binaries for each theme in .system/res/themes/{hex}/bin/{p}/
    print("Pre-generating theme binaries for all accent colors...")
    THEME_COLORS = [
        ("#f1c40f", 241, 196, 15),
        ("#e74c3c", 231, 76, 60),
        ("#2ecc71", 46, 204, 113),
        ("#3498db", 52, 152, 219),
        ("#9b59b6", 155, 89, 182),
        ("#e67e22", 230, 126, 34),
        ("#ffffff", 255, 255, 255),
    ]
    for p in platforms:
        minui_path = f".system/{p}/bin/minui.elf"
        minarch_path = f".system/{p}/bin/minarch.elf"
        if minui_path in in_minui_zip.namelist() and minarch_path in in_minui_zip.namelist():
            raw_minui = in_minui_zip.read(minui_path)
            raw_minarch = in_minui_zip.read(minarch_path)
            base_minui = patch_about_page(raw_minui, minui_path)
            if p == "miyoomini":
                base_minui = patch_minui_settings(base_minui, "miyoomini")
            base_minarch = raw_minarch

            raw_list = None
            list_path = f"skeleton/EXTRAS/Settings/{p}/Wi-Fi.pak/bin/{p}/cannelloni-list"
            if not os.path.isfile(list_path):
                list_path = f"skeleton/EXTRAS/Settings/miyoomini/Wi-Fi.pak/bin/{p}/cannelloni-list"
            if os.path.isfile(list_path):
                with open(list_path, "rb") as fp:
                    raw_list = fp.read()

            for hex_code, tr, tg, tb in THEME_COLORS:
                thm_minui = patch_binary_accent_color(base_minui, tr, tg, tb)
                thm_minarch = patch_binary_accent_color(base_minarch, tr, tg, tb)

                zi = zipfile.ZipInfo(f".system/res/themes/{hex_code}/bin/{p}/cannelloni.elf")
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o755 << 16
                out_cannelloni_zip.writestr(zi, thm_minui)

                zi = zipfile.ZipInfo(f".system/res/themes/{hex_code}/bin/{p}/minui.elf")
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o755 << 16
                out_cannelloni_zip.writestr(zi, thm_minui)

                zi = zipfile.ZipInfo(f".system/res/themes/{hex_code}/bin/{p}/minarch.elf")
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o755 << 16
                out_cannelloni_zip.writestr(zi, thm_minarch)

                if raw_list:
                    thm_list = patch_binary_accent_color(raw_list, tr, tg, tb)
                    zi = zipfile.ZipInfo(f".system/res/themes/{hex_code}/bin/{p}/cannelloni-list")
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.external_attr = 0o755 << 16
                    out_cannelloni_zip.writestr(zi, thm_list)

                    zi = zipfile.ZipInfo(f".system/res/themes/{hex_code}/bin/{p}/minui-list")
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.external_attr = 0o755 << 16
                    out_cannelloni_zip.writestr(zi, thm_list)

    # Bundle bootlogo flashing tools and image into .system/miyoomini/
    for lf in ["logoread.elf", "logomake.elf", "logowrite.elf"]:
        lp = f"skeleton/SYSTEM/miyoomini/bin/{lf}"
        if os.path.isfile(lp):
            with open(lp, "rb") as f:
                l_bytes = f.read()
            zi = zipfile.ZipInfo(f".system/miyoomini/bin/{lf}")
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zi, l_bytes)


    # Add apply_accent_color.sh script across all platforms
    accent_sh_path = "skeleton/SYSTEM/common/apply_accent_color.sh"
    if os.path.isfile(accent_sh_path):
        with open(accent_sh_path, "rb") as f:
            accent_sh_bytes = f.read()
        zinfo_a = zipfile.ZipInfo(".system/bin/apply_accent_color.sh")
        zinfo_a.compress_type = zipfile.ZIP_DEFLATED
        zinfo_a.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_a, accent_sh_bytes)
        for p in platforms:
            zinfo_pa = zipfile.ZipInfo(f".system/{p}/bin/apply_accent_color.sh")
            zinfo_pa.compress_type = zipfile.ZIP_DEFLATED
            zinfo_pa.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zinfo_pa, accent_sh_bytes)

    # Add common shaders into .system/common/shaders/
    shaders_dir = "skeleton/SYSTEM/common/shaders"
    if os.path.isdir(shaders_dir):
        add_dir_to_zip(out_cannelloni_zip, shaders_dir, ".system/common/shaders", set())

    # Add network_store.sh across common and platforms
    net_sh_path = "skeleton/SYSTEM/common/network_store.sh"
    if os.path.isfile(net_sh_path):
        with open(net_sh_path, "rb") as f:
            net_sh_bytes = f.read()
        for dest in [".system/common/network_store.sh", ".system/bin/network_store.sh"] + [f".system/{p}/bin/network_store.sh" for p in platforms]:
            zi_net = zipfile.ZipInfo(dest)
            zi_net.compress_type = zipfile.ZIP_DEFLATED
            zi_net.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zi_net, net_sh_bytes)

    # Add device_select.sh across common and platforms
    dev_sh_path = "skeleton/SYSTEM/common/device_select.sh"
    if os.path.isfile(dev_sh_path):
        with open(dev_sh_path, "rb") as f:
            dev_sh_bytes = f.read().replace(b"\r\n", b"\n")
        for dest in [".system/common/device_select.sh", ".system/bin/device_select.sh"] + [f".system/{p}/bin/device_select.sh" for p in platforms]:
            zi_dev = zipfile.ZipInfo(dest)
            zi_dev.compress_type = zipfile.ZIP_DEFLATED
            zi_dev.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zi_dev, dev_sh_bytes)

    # Add apply_language.sh across common and platforms
    lang_sh_path = "skeleton/SYSTEM/common/apply_language.sh"
    if os.path.isfile(lang_sh_path):
        with open(lang_sh_path, "rb") as f:
            lang_sh_bytes = f.read().replace(b"\r\n", b"\n")
        for dest in [".system/common/apply_language.sh", ".system/bin/apply_language.sh"] + [f".system/{p}/bin/apply_language.sh" for p in platforms]:
            zi_lang = zipfile.ZipInfo(dest)
            zi_lang.compress_type = zipfile.ZIP_DEFLATED
            zi_lang.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zi_lang, lang_sh_bytes)
            written_entries.add(dest)

    # Add updated Cannelloni.pak across all platforms from skeleton
    for p in platforms:
        pak_dir = f"skeleton/SYSTEM/{p}/paks/Cannelloni.pak"
        if os.path.isdir(pak_dir):
            add_dir_to_zip(out_cannelloni_zip, pak_dir, f".system/{p}/paks/Cannelloni.pak", set())

    # Add cannelloni-list across all platforms from skeleton if present
    for p in platforms:
        list_file = f"skeleton/SYSTEM/{p}/bin/cannelloni-list"
        if os.path.isfile(list_file):
            with open(list_file, "rb") as f:
                l_bytes = f.read()
            zi_l = zipfile.ZipInfo(f".system/{p}/bin/cannelloni-list")
            zi_l.compress_type = zipfile.ZIP_DEFLATED
            zi_l.external_attr = 0o755 << 16
            out_cannelloni_zip.writestr(zi_l, l_bytes)

    # Add translation files into .system/res/lang/
    lang_dir = "skeleton/SYSTEM/res/lang"
    if os.path.isdir(lang_dir):
        add_dir_to_zip(out_cannelloni_zip, lang_dir, ".system/res/lang", set())

    # 4. Extras zip entries (allowed tools from upstream extras)
    with zipfile.ZipFile(SRC_EXTRAS_ZIP, "r") as ext_in:
        allowed_tools = {"Clock.pak", "Files.pak", "Input.pak", "IP.pak", "Nonna's Kitchen.pak", "Bootlogo.pak"}
        for item in ext_in.infolist():
            name = item.filename
            if name.startswith("Tools/"):
                parts = name.split("/")
                if len(parts) >= 3 and parts[2] in allowed_tools:
                    if not any(name.startswith(f"Tools/{p}/Wi-Fi.pak/") or name.startswith(f"Tools/{p}/Nonna's Kitchen.pak/") for p in platforms):
                        data = ext_in.read(name)
                        try:
                            content = data.decode("utf-8")
                            content = content.replace("MinUI", "Cannelloni").replace("minui", "cannelloni")
                            data = content.encode("utf-8")
                        except UnicodeDecodeError:
                            pass
                        if name.endswith(".elf"):
                            data = patch_binary_accent_color(data, 241, 196, 15)
                        zinfo = zipfile.ZipInfo(name)
                        zinfo.compress_type = zipfile.ZIP_DEFLATED
                        zinfo.external_attr = 0o755 << 16 if name.endswith((".sh", ".elf", ".bin")) else 0o644 << 16
                        out_cannelloni_zip.writestr(zinfo, data)

    # Add Nonna's Kitchen tool pak across all platforms
    for p in platforms:
        k_dir = f"skeleton/EXTRAS/Tools/{p}/Nonna's Kitchen.pak"
        if not os.path.isdir(k_dir):
            k_dir = "skeleton/EXTRAS/Tools/miyoomini/Nonna's Kitchen.pak"
        add_dir_to_zip(out_cannelloni_zip, k_dir, f"Tools/{p}/Nonna's Kitchen.pak", written_entries)

    # Add Bootlogo.pak for miyoomini from skeleton
    blogo_dir = "skeleton/EXTRAS/Tools/miyoomini/Bootlogo.pak"
    if os.path.isdir(blogo_dir):
        add_dir_to_zip(out_cannelloni_zip, blogo_dir, "Tools/miyoomini/Bootlogo.pak", written_entries)

    # Add Settings section across all platforms (Wi-Fi, Accent Color, Button Mapping, Emulators, Shaders, Device Model)
    for p in platforms:
        s_dir = f"skeleton/EXTRAS/Settings/{p}"
        if not os.path.isdir(s_dir):
            s_dir = "skeleton/EXTRAS/Settings/miyoomini"
        add_dir_to_zip(out_cannelloni_zip, s_dir, f"Settings/{p}", written_entries)

    # Add NDS Libretro core emulator pak across all platforms
    for p in platforms:
        nds_emu_dir = f"skeleton/SYSTEM/{p}/paks/Emus/NDS.pak"
        if os.path.isdir(nds_emu_dir):
            add_dir_to_zip(out_cannelloni_zip, nds_emu_dir, f"Emus/{p}/NDS.pak", written_entries)

    # Include NDS-Drastic.pak in Emus/miyoomini for users who also want standalone DraStic
    drastic_dir = "skeleton/EXTRAS/Emus/miyoomini/NDS-Drastic.pak"
    if os.path.isdir(drastic_dir):
        add_dir_to_zip(out_cannelloni_zip, drastic_dir, "Emus/miyoomini/NDS-Drastic.pak", written_entries)

    # Default accent color, language, emulator, and shader configurations in Cannelloni.zip
    for cfg_path, cfg_val in [
        (".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n"),
        (".userdata/shared/.cannelloni/language.txt", b"en\n"),
        (".userdata/shared/.cannelloni/emu_nds.txt", b"libretro\n"),
        (".userdata/shared/.cannelloni/button_swap.txt", b"default\n"),
        (".userdata/shared/.cannelloni/shader_preset.txt", b"crt-cannelloni\n"),
        (".userdata/shared/.cannelloni/shader_scope.txt", b"all\n"),
    ]:
        if cfg_path not in written_entries:
            out_cannelloni_zip.writestr(cfg_path, cfg_val)
            written_entries.add(cfg_path)

    in_minui_zip.close()

    # ----------------------------------------------------
    # 2. Add platform bootstrap files & user folders directly to single Cannelloni.zip
    # ----------------------------------------------------
    print(f"Adding bootstrap files directly to single archive: {out_cannelloni_release}...")

    BOOTSTRAP_DIRS = (
        "miyoo/", "miyoo354/", "miyoo355/", "miyoo285/", "trimui/",
        "rg35xx/", "rg35xxplus/", "gkdpixel/", "magicx/", "em_ui.sh", ".tmp_update/"
    )

    # 1. README.txt into root
    if "README.txt" not in written_entries:
        with open("skeleton/BASE/README.txt", "rb") as f:
            out_cannelloni_zip.writestr("README.txt", f.read())
        written_entries.add("README.txt")

    # 2. Add Nintendo DS ROM, Bios, and Saves placeholder folders
    for folder in [
        "Roms/Nintendo DS (NDS)", "Roms/Game Boy Advance (GBA)", "Roms/Sony PlayStation (PS)",
        "Bios/NDS", "Bios/PS", "Bios/GBA", "Saves/NDS", "Saves/PS", "Saves/GBA"
    ]:
        keep_path = f"{folder}/.keep"
        if keep_path not in written_entries:
            out_cannelloni_zip.writestr(keep_path, b"")
            written_entries.add(keep_path)

    # 3. Add dmenu.bin directly to root for RG35XX Plus/H/SP TF1 cards
    if "dmenu.bin" not in written_entries:
        dmenu_bytes = build_dmenu_rg35xxplus()
        zinfo_dm = zipfile.ZipInfo("dmenu.bin")
        zinfo_dm.compress_type = zipfile.ZIP_DEFLATED
        zinfo_dm.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_dm, dmenu_bytes)
        written_entries.add("dmenu.bin")

    # 4. Add platform bootstrap files from base_in (and skeleton overrides)
    with zipfile.ZipFile(SRC_BASE_ZIP, "r") as base_in:
        for item in base_in.infolist():
            name = item.filename
            if name in ("MinUI.zip", "Cannelloni.zip", "README.txt") or name in written_entries:
                continue

            # Only include bootstrap folders/files
            if not any(name.startswith(b) for b in BOOTSTRAP_DIRS) and name != "em_ui.sh":
                continue

            data = base_in.read(name)
            if name.endswith("/app/MainUI") or name == "miyoo/app/MainUI":
                with open("skeleton/BOOT/miyoo/app/MainUI", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith("/app/miyoomini.sh"):
                with open("skeleton/BOOT/miyoo/app/miyoomini.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/updater"):
                with open("skeleton/BOOT/common/updater", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/miyoomini.sh"):
                with open("workspace/miyoomini/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/my282.sh"):
                with open("workspace/my282/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/my355.sh"):
                with open("workspace/my355/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/tg5040.sh"):
                with open("workspace/tg5040/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/trimuismart.sh"):
                with open("workspace/trimuismart/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name.endswith(".tmp_update/zero28.sh"):
                with open("workspace/zero28/install/boot.sh", "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
            elif name == "rg35xxplus/dmenu.bin":
                data = build_dmenu_rg35xxplus()
            elif name == "rg35xx/dmenu.bin":
                data = build_dmenu_rg35xx()
            elif name.endswith("installing.png"):
                if "brick" in name:
                    data = open("workspace/tg5040/install/brick/installing.png", "rb").read()
                elif "trimuismart" in name:
                    data = open("workspace/trimuismart/install/installing.png", "rb").read()
                else:
                    data = open("workspace/miyoomini/install/installing.png", "rb").read()
            elif name.endswith("updating.png"):
                if "brick" in name:
                    data = open("workspace/tg5040/install/brick/updating.png", "rb").read()
                elif "trimuismart" in name:
                    data = open("workspace/trimuismart/install/updating.png", "rb").read()
                else:
                    data = open("workspace/miyoomini/install/updating.png", "rb").read()
            elif name == "gkdpixel/install.sh":
                data = open("workspace/gkdpixel/boot/install.sh", "rb").read().replace(b"\r\n", b"\n")
            elif name == "gkdpixel/boot.sh":
                data = open("workspace/gkdpixel/boot/boot.sh", "rb").read().replace(b"\r\n", b"\n")
            elif name == "gkdpixel/installing.bmp":
                data = open("workspace/gkdpixel/boot/installing.bmp", "rb").read()
            elif name.endswith(".sh") or name.endswith(".txt"):
                try:
                    content = data.decode("utf-8")
                    content = content.replace("MinUI.zip", "Cannelloni.zip")
                    content = content.replace("MinUI.pak", "Cannelloni.pak")
                    content = content.replace("MinUI", "Cannelloni")
                    content = content.replace("/tmp/minui_exec", "/tmp/cannelloni_exec")
                    content = content.replace(".minui", ".cannelloni")
                    data = content.encode("utf-8").replace(b"\r\n", b"\n")
                except UnicodeDecodeError:
                    pass

            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            if name.endswith((".sh", "MainUI", "updater", ".elf", ".bin")):
                zinfo.external_attr = 0o755 << 16
            else:
                zinfo.external_attr = 0o644 << 16
            out_cannelloni_zip.writestr(zinfo, data)
            written_entries.add(name)

            # Write .tmp_update directly to root of archive for native Miyoo stock updater compatibility
            if name.startswith("miyoo354/app/.tmp_update/"):
                tmp_name = name.replace("miyoo354/app/.tmp_update/", ".tmp_update/")
                if tmp_name not in written_entries:
                    zinfo_tmp = zipfile.ZipInfo(tmp_name)
                    zinfo_tmp.compress_type = zipfile.ZIP_DEFLATED
                    zinfo_tmp.external_attr = 0o755 << 16 if tmp_name.endswith((".sh", "updater", ".elf")) else 0o644 << 16
                    out_cannelloni_zip.writestr(zinfo_tmp, data)
                    written_entries.add(tmp_name)

    # 5. Inject device_select.sh directly into .tmp_update/ for initial setup wizard
    if ".tmp_update/device_select.sh" not in written_entries:
        with open("skeleton/SYSTEM/common/device_select.sh", "rb") as f:
            dev_sh_bytes = f.read().replace(b"\r\n", b"\n")
        zinfo_dev = zipfile.ZipInfo(".tmp_update/device_select.sh")
        zinfo_dev.compress_type = zipfile.ZIP_DEFLATED
        zinfo_dev.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_dev, dev_sh_bytes)
        written_entries.add(".tmp_update/device_select.sh")

    if ".tmp_update/apply_language.sh" not in written_entries:
        with open("skeleton/SYSTEM/common/apply_language.sh", "rb") as f:
            lang_sh_bytes = f.read().replace(b"\r\n", b"\n")
        zinfo_lang = zipfile.ZipInfo(".tmp_update/apply_language.sh")
        zinfo_lang.compress_type = zipfile.ZIP_DEFLATED
        zinfo_lang.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_lang, lang_sh_bytes)
        written_entries.add(".tmp_update/apply_language.sh")

    out_cannelloni_zip.close()

    shutil.copyfile(out_cannelloni_release, OUT_UNIFIED_ZIP)
    print(f"Single unified release archive completed: {out_cannelloni_release} ({os.path.getsize(out_cannelloni_release)} bytes, {len(written_entries)} entries)")
    print("Release archive built successfully!")

if __name__ == "__main__":
    build_release()
