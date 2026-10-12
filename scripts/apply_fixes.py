import os
import glob
import re
import struct

print("Applying Cannelloni fixes across the repository...")

# ----------------------------------------------------
# 1. Update on-boot script across all Wi-Fi paks
# ----------------------------------------------------
on_boot_content = """#!/bin/sh
set -x
BIN_DIR="$(dirname "$0")"
PAK_DIR="$(dirname "$BIN_DIR")"
PAK_NAME="$(basename "$PAK_DIR")"
PAK_NAME="${PAK_NAME%.*}"

[ -z "$SDCARD_PATH" ] && export SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        export PLATFORM="miyoomini"
    fi
fi
[ -z "$USERDATA_PATH" ] && export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
[ -z "$LOGS_PATH" ] && export LOGS_PATH="$USERDATA_PATH/logs"
mkdir -p "$LOGS_PATH"

rm -f "$LOGS_PATH/$PAK_NAME.on-boot.txt"
exec >>"$LOGS_PATH/$PAK_NAME.on-boot.txt" 2>&1

echo "$0" "$@"
cd "$PAK_DIR" || exit 1

main() {
    /bin/sh "$BIN_DIR/service-on" &
}

main "$@"
"""

for p in glob.glob("skeleton/EXTRAS/Tools/*/Wi-Fi.pak/bin/on-boot"):
    with open(p, "w", newline="\n") as f:
        f.write(on_boot_content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 2. Update launch.sh in Wi-Fi paks (enable_start_on_boot with /bin/sh)
# ----------------------------------------------------
for p in glob.glob("skeleton/EXTRAS/Tools/*/Wi-Fi.pak/launch.sh"):
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Ensure /bin/sh is used in enable_start_on_boot
    content = content.replace(
        'echo "test -f \\"$SDCARD_PATH/Tools/\\$PLATFORM/$PAK_NAME.pak/bin/on-boot\\" && \\"$SDCARD_PATH/Tools/\\$PLATFORM/$PAK_NAME.pak/bin/on-boot\\" # ${PAK_NAME}.pak-on-boot" >>"$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"',
        'echo "test -f \\"$SDCARD_PATH/Tools/\\$PLATFORM/$PAK_NAME.pak/bin/on-boot\\" && /bin/sh \\"$SDCARD_PATH/Tools/\\$PLATFORM/$PAK_NAME.pak/bin/on-boot\\" # ${PAK_NAME}.pak-on-boot" >>"$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"'
    )
    with open(p, "w", newline="\n", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 3. Update service-on in Wi-Fi paks (miyoomini block)
# ----------------------------------------------------
for p in glob.glob("skeleton/EXTRAS/Tools/*/Wi-Fi.pak/bin/service-on"):
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace grep -c with grep -q
    content = content.replace(
        "if ! grep -c 8188fu /proc/modules; then",
        "if ! grep -q 8188fu /proc/modules; then"
    )

    # Ensure wpa_supplicant.conf exists from wifi.txt if missing on boot
    old_block = """    if [ "$PLATFORM" = "miyoomini" ]; then
        killall wpa_supplicant || true
        killall udhcpc || true"""
    
    new_block = """    if [ "$PLATFORM" = "miyoomini" ]; then
        if [ ! -s "/appconfigs/wpa_supplicant.conf" ] || ! grep -q "network=" "/appconfigs/wpa_supplicant.conf" 2>/dev/null; then
            if [ -f "$SDCARD_PATH/wifi.txt" ]; then
                cp "$PAK_DIR/res/wpa_supplicant.conf.miyoomini.tmpl" "$PAK_DIR/res/wpa_supplicant.conf" 2>/dev/null
                while IFS= read -r line || [ -n "$line" ]; do
                    line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    case "$line" in
                        \\#*|"") continue ;;
                    esac
                    ssid=$(echo "$line" | cut -d: -f1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    psk=$(echo "$line" | cut -d: -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    if [ -n "$ssid" ]; then
                        echo "network={" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        echo "    ssid=\\"$ssid\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        if [ -z "$psk" ]; then
                            echo "    key_mgmt=NONE" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        else
                            echo "    psk=\\"$psk\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        fi
                        echo "}" >> "$PAK_DIR/res/wpa_supplicant.conf"
                    fi
                done < "$SDCARD_PATH/wifi.txt"
                cp "$PAK_DIR/res/wpa_supplicant.conf" /appconfigs/wpa_supplicant.conf 2>/dev/null
                cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
            fi
        fi
        killall wpa_supplicant || true
        killall udhcpc || true"""
    
    if old_block in content and new_block not in content:
        content = content.replace(old_block, new_block)

    with open(p, "w", newline="\n", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 4. Update Nonna's Kitchen launch.sh across all tools
# ----------------------------------------------------
kitchen_launch_content = """#!/bin/sh

# Check if Wi-Fi is already connected with a valid IP
get_ip() {
	ip -4 addr show dev wlan0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1
}

IP=$(get_ip)
if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2 | head -n1)
fi

SAY="/mnt/SDCARD/.system/miyoomini/bin/say.elf"
if ! [ -x "$SAY" ]; then
	SAY="say.elf"
fi

# If not connected yet, try bringing Wi-Fi up cleanly WITHOUT killing existing connections
if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	WIFI_ON="/mnt/SDCARD/Tools/miyoomini/Wi-Fi.pak/bin/service-on"
	if [ -f "$WIFI_ON" ]; then
		/bin/sh "$WIFI_ON" >/dev/null 2>&1
	elif [ -f "/customer/app/axp_test" ]; then
		/customer/app/axp_test wifion 2>/dev/null
		ifconfig wlan0 up 2>/dev/null
		if ! pgrep wpa_supplicant >/dev/null 2>&1 && [ -f "/appconfigs/wpa_supplicant.conf" ]; then
			wpa_supplicant -B -D nl80211 -iwlan0 -c /appconfigs/wpa_supplicant.conf 2>/dev/null
			udhcpc -i wlan0 -s /etc/init.d/udhcpc.script -q 2>/dev/null &
		fi
	fi

	# Wait up to 10 seconds for IP address assignment
	for i in 1 2 3 4 5 6 7 8 9 10; do
		IP=$(get_ip)
		[ -z "$IP" ] && IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2 | head -n1)
		if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
			break
		fi
		sleep 1
	done
fi

if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	$SAY "Wi-Fi is not connected.
Configure Wi-Fi in Tools > Wi-Fi first."
	exit 0
fi

# Start FTP server on port 2121
killall tcpsvd ftpd 2>/dev/null
tcpsvd -vE 0.0.0.0 2121 ftpd -w /mnt/SDCARD &
FTP_PID=$!

$SAY "Nonna's Kitchen FTP Active!
Address: ftp://$IP:2121
User: cannelloni | Pass: cannelloni

Press A to stop FTP."

# Stop FTP when user closes (leaving Wi-Fi active!)
kill $FTP_PID 2>/dev/null
killall tcpsvd ftpd 2>/dev/null
"""

for p in glob.glob("skeleton/EXTRAS/Tools/*/Nonna's Kitchen.pak/launch.sh"):
    with open(p, "w", newline="\n") as f:
        f.write(kitchen_launch_content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 5. Update Cannelloni.pak/launch.sh across all platforms
# ----------------------------------------------------
for p in glob.glob("skeleton/SYSTEM/*/paks/Cannelloni.pak/launch.sh"):
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure AUTO_PATH runs with /bin/sh
    content = content.replace(
        'AUTO_PATH=$USERDATA_PATH/auto.sh\nif [ -f "$AUTO_PATH" ]; then\n\t"$AUTO_PATH"\nfi',
        'AUTO_PATH=$USERDATA_PATH/auto.sh\nif [ -f "$AUTO_PATH" ]; then\n\t/bin/sh "$AUTO_PATH"\nfi'
    )
    with open(p, "w", newline="\n", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 6. Update NDS.pak/launch.sh across all platforms
# ----------------------------------------------------
nds_launch_content = """#!/bin/sh

EMU_EXE=melonds

###############################

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
HOME="$USERDATA_PATH"
cd "$HOME"

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"

LOG_FILE="$LOGS_PATH/$EMU_TAG.txt"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting NDS: $ROM ===" > "$LOG_FILE"
echo "Core: $CORES_PATH/${EMU_EXE}_libretro.so" >> "$LOG_FILE"

CORE_FILE="$CORES_PATH/${EMU_EXE}_libretro.so"
if [ ! -f "$CORE_FILE" ]; then
    CORE_FILE="$CORES_PATH/desmume2015_libretro.so"
fi

nice -20 minarch.elf "$CORE_FILE" "$ROM" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "minarch exited with code: $EXIT_CODE" >> "$LOG_FILE"
"""

for p in glob.glob("skeleton/SYSTEM/*/paks/Emus/NDS.pak/launch.sh") + glob.glob("skeleton/EXTRAS/Emus/*/NDS.pak/launch.sh"):
    with open(p, "w", newline="\n") as f:
        f.write(nds_launch_content)
    print(f"Updated {p}")

# ----------------------------------------------------
# 7. Patch GLIBC_2.17 in NDS Libretro Cores
# ----------------------------------------------------
for filename in ['build_release/temp/cores/melonds_libretro.so', 'build_release/temp/cores/desmume2015_libretro.so']:
    if not os.path.isfile(filename):
        continue
    with open(filename, 'rb') as f:
        data = bytearray(f.read())
    
    # 1. Replace hash 0x6969197 with 0xd696914
    old_hash = struct.pack('<I', 0x6969197)
    new_hash = struct.pack('<I', 0xd696914)
    idx = 0
    while True:
        idx = data.find(old_hash, idx)
        if idx == -1:
            break
        data[idx:idx+4] = new_hash
        idx += 4
    
    # 2. Replace b'GLIBC_2.17' with b'GLIBC_2.4\x00\x00'
    idx = 0
    while True:
        idx = data.find(b'GLIBC_2.17', idx)
        if idx == -1:
            break
        data[idx:idx+10] = b'GLIBC_2.4\x00\x00'
        idx += 10
    
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Patched GLIBC_2.17 in {filename}")

print("All fixes applied successfully!")
