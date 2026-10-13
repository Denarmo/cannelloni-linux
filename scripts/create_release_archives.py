import os
import sys
import io
import zipfile
import shutil
import struct
import urllib.request
import tarfile
import binascii
import subprocess
import glob

from nds_cores import collect_nds_cores
from release_version import release_version

RELEASE_VERSION = release_version()
RELEASE_TAG = "v" + RELEASE_VERSION
RELEASE_NAME = "Cannelloni-" + RELEASE_VERSION

SRC_BASE_ZIP = "build_release/temp/base.zip"
SRC_EXTRAS_ZIP = "build_release/temp/extras.zip"
OUT_DIR = "releases"
OUT_UNIFIED_ZIP = os.path.join(OUT_DIR, f"{RELEASE_NAME}.zip")
OUT_ALIAS_ZIP = os.path.join(OUT_DIR, "Cannelloni.zip")
OUT_INSTALLER_ZIP = os.path.join(OUT_DIR, "Cannelloni-Installer.zip")
PAYLOAD_ZIP = "build_release/temp/Cannelloni.zip"

def add_installer_files(zout, payload_path, installer_exe):
    """Store one OS payload alongside the installer, without loose OS copies."""
    zout.write(payload_path, "Cannelloni.zip", compress_type=zipfile.ZIP_STORED)
    installer_files = [
        ("VERSION", "VERSION", 0o644),
        ("installer/Cannelloni-Installer.bat", "Cannelloni-Installer.bat", 0o644),
        ("installer/Cannelloni-Installer.sh", "Cannelloni-Installer.sh", 0o755),
        ("installer/cannelloni_installer.py", "cannelloni_installer.py", 0o755),
        ("installer/README.txt", "README.txt", 0o644),
    ]
    if installer_exe is not None:
        installer_files.append((installer_exe, "Cannelloni-Installer.exe", 0o755))
    for path, name, mode in installer_files:
        with open(path, "rb") as source:
            data = source.read()
        if name.endswith((".sh", ".py", ".txt")):
            data = data.replace(b"\r\n", b"\n")
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = mode << 16
        zout.writestr(info, data)


def build_installer_archive(output_path, payload_path, installer_exe):
    """The desktop installer consumes the archive; it needs no bootstraps."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_installer_files(archive, payload_path, installer_exe)


def add_dir_to_zip(zout, src_dir, zip_prefix, written_entries):
    """Recursively adds a local directory into a zip archive with proper permissions."""
    if not os.path.isdir(src_dir):
        return
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel = os.path.relpath(full_path, src_dir).replace("\\", "/")
            dest = f"{zip_prefix}/{rel}".strip("/")
            if dest.startswith(".system/res/themes/") and f in ("cannelloni.elf", "minui.elf", "minarch.elf"):
                continue  # Frontends read the selected accent at runtime.
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

def inject_spinner_frames(zout, written_entries):
    """Injects all spinning cannelloni animation frames into .tmp_update folders across all platforms."""
    platforms_with_frames = [
        ("miyoomini", "workspace/miyoomini/install", "miyoomini"),
        ("my282", "workspace/my282/install", "my282"),
        ("my355", "workspace/my355/install", "my355"),
        ("zero28", "workspace/zero28/install", "zero28"),
        ("tg5040", "workspace/tg5040/install", "tg5040"),
        ("tg5040/brick", "workspace/tg5040/install/brick", "tg5040/brick"),
        ("trimuismart", "workspace/trimuismart/install", "trimuismart"),
    ]
    for plat_key, src_dir, rel_target in platforms_with_frames:
        if not os.path.isdir(src_dir):
            continue
        for frame in range(12):
            for action in ["installing", "updating"]:
                f_name = f"{action}_{frame:02d}.png"
                src_path = os.path.join(src_dir, f_name)
                if not os.path.isfile(src_path):
                    continue
                with open(src_path, "rb") as fp:
                    frame_bytes = fp.read()
                
                dest_list = [
                    f".tmp_update/{rel_target}/{f_name}",
                    f"miyoo/app/.tmp_update/{rel_target}/{f_name}",
                    f"miyoo354/app/.tmp_update/{rel_target}/{f_name}",
                    f"miyoo355/app/.tmp_update/{rel_target}/{f_name}",
                    f"miyoo285/app/.tmp_update/{rel_target}/{f_name}",
                    f"trimui/app/.tmp_update/{rel_target}/{f_name}",
                    f"magicx/.tmp_update/{rel_target}/{f_name}"
                ]
                for dest in dest_list:
                    if dest not in written_entries:
                        zi = zipfile.ZipInfo(dest)
                        zi.compress_type = zipfile.ZIP_DEFLATED
                        zi.external_attr = 0o644 << 16
                        zout.writestr(zi, frame_bytes)
                        written_entries.add(dest)

PLATFORMS = (
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28',
)


def load_built_frontends(platforms, workspace="workspace"):
    """Never ship an old MinUI binary in place of the modified source."""
    binaries = {}
    for platform in platforms:
        for name in ("cannelloni", "minarch"):
            path = os.path.join(workspace, "all", name, "build", platform, name + ".elf")
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    f"Missing rebuilt {name} for {platform}: {path}. "
                    "Run scripts/build_release_frontends.sh in its device toolchain first."
                )
            with open(path, "rb") as source:
                data = source.read()
            if len(data) < 52 or data[:4] != b"\x7fELF":
                raise ValueError(f"Not a Linux ELF executable: {path}")
            binaries[(platform, name)] = data
    return binaries


def add_built_frontends(archive, binaries, written_entries):
    """Install exact current binaries even if a template omits a platform."""
    for (platform, name), data in binaries.items():
        filenames = ("cannelloni.elf", "minui.elf") if name == "cannelloni" else ("minarch.elf",)
        for filename in filenames:
            destination = f".system/{platform}/bin/{filename}"
            info = zipfile.ZipInfo(destination)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o755 << 16
            archive.writestr(info, data)
            written_entries.add(destination)


def build_release():
    platforms = PLATFORMS
    frontends = load_built_frontends(platforms)
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
    out_cannelloni_zip = zipfile.ZipFile(PAYLOAD_ZIP, "w", zipfile.ZIP_DEFLATED)
    written_entries = set()

    nds_cores = collect_nds_cores(platforms)
    add_built_frontends(out_cannelloni_zip, frontends, written_entries)
    commit_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    out_cannelloni_zip.writestr(".system/version.txt", f"{RELEASE_VERSION}\n{commit_hash}\n")
    written_entries.add(".system/version.txt")

    # Current platform options include the portable shader renderer. Do not
    # restore old template locks for platforms without hardware Line/Grid.
    for platform in platforms:
        for config_path in sorted(glob.glob(f"skeleton/SYSTEM/{platform}/system*.cfg")):
            destination = f".system/{platform}/{os.path.basename(config_path)}"
            with open(config_path, "rb") as config_file:
                config_data = config_file.read().replace(b"\r\n", b"\n")
            out_cannelloni_zip.writestr(destination, config_data)
            written_entries.add(destination)

    # Read all entries from MinUI.zip, adapting and updating
    for item in in_minui_zip.infolist():
        name = item.filename
        data = in_minui_zip.read(name)
        if name in nds_cores or name in written_entries:
            continue

        if name.startswith(".system/res/themes/") and name.endswith(("/minarch.elf", "/minui.elf", "/cannelloni.elf")):
            continue

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

        # Override stock MinUI installing/updating screens with official Cannelloni screens
        if name.endswith("installing.png"):
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

        # Override stock MinUI spritesheets with official Cannelloni Gold (#f1c40f) assets
        if name.startswith(".system/res/assets@"):
            bn = os.path.basename(name)
            gold_asset = os.path.join("skeleton/SYSTEM/res/themes/#f1c40f", bn)
            if not os.path.isfile(gold_asset):
                gold_asset = os.path.join("skeleton/SYSTEM/res", bn)
            if os.path.isfile(gold_asset):
                with open(gold_asset, "rb") as fp:
                    data = fp.read()

        # Override stock MinUI charging screen with official Cannelloni charging screen
        if name == ".system/res/charging-640-480.png":
            ch_path = "skeleton/SYSTEM/res/charging-640-480.png"
            if os.path.isfile(ch_path):
                with open(ch_path, "rb") as fp:
                    data = fp.read()

        if name not in written_entries:
            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            if name.endswith(".sh") or name.endswith("MainUI") or name.endswith("updater") or name.endswith(".elf") or name.endswith(".bin"):
                zinfo.external_attr = 0o755 << 16
            else:
                zinfo.external_attr = 0o644 << 16
            out_cannelloni_zip.writestr(zinfo, data)
            written_entries.add(name)

    # Bundle charging animation frames into .system/res/
    for ch_f in sorted(glob.glob("skeleton/SYSTEM/res/charging_*.png")):
        bn = os.path.basename(ch_f)
        with open(ch_f, "rb") as fp:
            ch_data = fp.read()
        dest = f".system/res/{bn}"
        if dest not in written_entries:
            zi = zipfile.ZipInfo(dest)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            out_cannelloni_zip.writestr(zi, ch_data)
            written_entries.add(dest)

    # Package each real platform build under its own core name. Renaming one
    # DeSmuME binary to melonDS (or copying it across architectures) is invalid.
    print("Injecting platform-built NDS libretro cores into Cannelloni.zip...")
    for core_path, core_bytes in nds_cores.items():
        zinfo_core = zipfile.ZipInfo(core_path)
        zinfo_core.compress_type = zipfile.ZIP_DEFLATED
        zinfo_core.external_attr = 0o755 << 16
        out_cannelloni_zip.writestr(zinfo_core, core_bytes)
        written_entries.add(core_path)

    # Most NDS builds link C++ statically. SDKs without static libraries supply
    # their exact matching runtime through collect_nds_cores above.

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
        # Native frontends load the selected accent color at runtime. Only
        # the external list widget still needs pre-tinted theme binaries.
        raw_list = None
        list_path = f"skeleton/EXTRAS/Settings/{p}/Wi-Fi.pak/bin/{p}/cannelloni-list"
        if not os.path.isfile(list_path):
            list_path = f"skeleton/EXTRAS/Settings/miyoomini/Wi-Fi.pak/bin/{p}/cannelloni-list"
        if os.path.isfile(list_path):
            with open(list_path, "rb") as fp:
                raw_list = fp.read()

        for hex_code, tr, tg, tb in THEME_COLORS:
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
        add_dir_to_zip(out_cannelloni_zip, shaders_dir, ".system/common/shaders", written_entries)

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

    # Default accent color, language, and emulator configurations in Cannelloni.zip
    for cfg_path, cfg_val in [
        (".userdata/shared/.cannelloni/accent_color.txt", b"#f1c40f\n"),
        (".userdata/shared/.cannelloni/language.txt", b"en\n"),
        (".userdata/shared/.cannelloni/emu_nds.txt", b"libretro\n"),
        (".userdata/shared/.cannelloni/button_swap.txt", b"default\n"),
        (".userdata/shared/.cannelloni/shader_preset.txt", b"none\n"),
        (".userdata/shared/.cannelloni/shader_intensity.txt", b"50\n"),
        (".userdata/shared/.cannelloni/shader_curvature.txt", b"flat\n"),
    ]:
        if cfg_path not in written_entries:
            out_cannelloni_zip.writestr(cfg_path, cfg_val)
            written_entries.add(cfg_path)

    in_minui_zip.close()

    # ----------------------------------------------------
    # 2. Add platform bootstrap files & user folders directly to single Cannelloni.zip
    # ----------------------------------------------------
    print(f"Adding bootstrap files directly to single archive: {PAYLOAD_ZIP}...")

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

    # 6. Inject spinning cannelloni animation frames into all .tmp_update folders
    inject_spinner_frames(out_cannelloni_zip, written_entries)

    out_cannelloni_zip.close()
    payload_size = os.path.getsize(PAYLOAD_ZIP)
    print(f"Inner OS payload Cannelloni.zip built: {PAYLOAD_ZIP} ({payload_size} bytes, {len(written_entries)} entries)")

    # ----------------------------------------------------
    # 7. Build/ensure standalone Cannelloni-Installer.exe
    # ----------------------------------------------------
    installer_exe = "dist/Cannelloni-Installer.exe"
    installer_script = "installer/cannelloni_installer.py"
    if not os.path.isfile(installer_exe):
        if sys.platform != "win32":
            raise FileNotFoundError("Build dist/Cannelloni-Installer.exe on Windows first (or download the windows-installer CI artifact).")
    if sys.platform == "win32" and (not os.path.isfile(installer_exe) or max(os.path.getmtime(installer_script), os.path.getmtime("VERSION")) > os.path.getmtime(installer_exe)):
        print("Compiling standalone Cannelloni-Installer.exe with PyInstaller...")
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--noconsole",
            "--name", "Cannelloni-Installer",
            "--add-data", "VERSION;.",
            installer_script
        ], check=True)

    # ----------------------------------------------------
    # 8. Package final delivered release archives
    # ----------------------------------------------------
    print(f"Packaging final delivered release archives containing Cannelloni.zip + GUI installer...")
    delivered_written = set()

    with zipfile.ZipFile(OUT_UNIFIED_ZIP, "w", zipfile.ZIP_DEFLATED) as zout:
        add_installer_files(zout, PAYLOAD_ZIP, installer_exe)
        delivered_written.update(zout.namelist())

        # G. Platform bootstrap files & directories (for on-device direct boot)
        with zipfile.ZipFile(PAYLOAD_ZIP, "r") as pz:
            for item in pz.infolist():
                name = item.filename
                if name.startswith(BOOTSTRAP_DIRS) or name in (
                    "dmenu.bin", "em_ui.sh",
                    ".system/common/device_select.sh",
                    ".system/miyoomini/paks/Cannelloni.pak/launch.sh"
                ) or name.startswith("Emus/miyoomini/NDS-Drastic.pak/") or name.startswith("Emus/miyoomini/NDS.pak/") or name.startswith("Settings/") or name.startswith("Tools/"):
                    if name not in delivered_written:
                        zout.writestr(item, pz.read(name))
                        delivered_written.add(name)

    # Keep the legacy direct-boot release alias, but omit duplicated OS files
    # from the desktop installer package. Its only OS source is the payload.
    shutil.copyfile(OUT_UNIFIED_ZIP, OUT_ALIAS_ZIP)
    build_installer_archive(OUT_INSTALLER_ZIP, PAYLOAD_ZIP, installer_exe)

    print(f"Delivered release archives completed:")
    print(f" - {OUT_ALIAS_ZIP} ({os.path.getsize(OUT_ALIAS_ZIP)} bytes)")
    print(f" - {OUT_UNIFIED_ZIP} ({os.path.getsize(OUT_UNIFIED_ZIP)} bytes)")
    print(f" - {OUT_INSTALLER_ZIP} ({os.path.getsize(OUT_INSTALLER_ZIP)} bytes)")

    print("Release archive built successfully!")

if __name__ == "__main__":
    build_release()
