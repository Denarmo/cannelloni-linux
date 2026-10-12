#!/bin/sh
# Cannelloni Universal Device Selector
# Prompts the user on first boot to choose their handheld console model
# and configures the exact hardware-specific files, drivers, and settings.

[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$SHARED_DIR"
DEVICE_TXT="$SHARED_DIR/device_model.txt"

# Locate cannelloni-list binary for current platform
LIST_BIN=""
for loc in \
    "$SDCARD_PATH/.system/$PLATFORM/bin/cannelloni-list" \
    "$SDCARD_PATH/.system/$PLATFORM/bin/minui-list" \
    "$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/minui-list" \
    "$SDCARD_PATH/Settings/miyoomini/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/Tools/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/.system/bin/cannelloni-list"; do
    if [ -x "$loc" ]; then
        LIST_BIN="$loc"
        break
    fi
done

CHOICE_LIST="/tmp/device-choice-list.txt"
CHOICE_OUT="/tmp/device-choice-out.txt"
rm -f "$CHOICE_OUT"

cat << 'EOF' > "$CHOICE_LIST"
Miyoo Mini (v1 / v2 / v3)
Miyoo Mini Plus (v4 / Wi-Fi)
Miyoo A30 (my282)
Miyoo Flip (my355)
TrimUI Smart
TrimUI Smart Pro
TrimUI Brick
Anbernic RG35XX (Original)
Anbernic RG35XX Plus / H / SP
Powkiddy RGB30
MagicX XU Mini M
MagicX Mini Zero 28
GKD Pixel
M17
EOF

SELECTED=""
if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$CHOICE_LIST" --format text --confirm-text "INSTALL" --title "Choose Your Device" --write-location "$CHOICE_OUT"
    RET=$?
    if [ $RET -eq 0 ] && [ -f "$CHOICE_OUT" ]; then
        SELECTED=$(cat "$CHOICE_OUT" | head -n1)
    fi
fi

# Fallback hardware detection if interactive prompt was skipped or not available
if [ -z "$SELECTED" ]; then
    INFO=$(cat /proc/cpuinfo 2> /dev/null)
    case "$INFO" in
        *"0xd05"*) SELECTED="Miyoo Flip (my355)" ;;
        *"sun8i"*)
            if [ -d /usr/miyoo ]; then
                SELECTED="Miyoo A30 (my282)"
            else
                SELECTED="TrimUI Smart"
            fi
            ;;
        *"SStar"*|*"sstar"*|*"Sigmastar"*|*"SigmaStar"*|*"SSD20"*)
            if [ -f /customer/app/axp_test ]; then
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            else
                SELECTED="Miyoo Mini (v1 / v2 / v3)"
            fi
            ;;
        *"TG5040"*|*"TG3040"*)
            TRIMUI_MODEL=$(strings /usr/trimui/bin/MainUI 2>/dev/null | grep ^Trimui)
            if [ "$TRIMUI_MODEL" = "Trimui Brick" ]; then
                SELECTED="TrimUI Brick"
            else
                SELECTED="TrimUI Smart Pro"
            fi
            ;;
        *"0xd03"*) SELECTED="MagicX Mini Zero 28" ;;
        *)
            if [ -f /customer/app/axp_test ]; then
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            elif [ -d /customer/app ]; then
                SELECTED="Miyoo Mini (v1 / v2 / v3)"
            else
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            fi
            ;;
    esac
fi

echo "$SELECTED" > "$DEVICE_TXT"

TARGET_PLATFORM="miyoomini"
TARGET_DEVICE=""

case "$SELECTED" in
    *"Miyoo Mini Plus"*)
        TARGET_PLATFORM="miyoomini"
        TARGET_DEVICE="plus"
        mkdir -p "$SDCARD_PATH/.userdata/$TARGET_PLATFORM"
        touch "$SDCARD_PATH/.userdata/$TARGET_PLATFORM/.is_plus"
        ;;
    *"Miyoo Mini ("*)
        TARGET_PLATFORM="miyoomini"
        TARGET_DEVICE="mini"
        rm -f "$SDCARD_PATH/.userdata/$TARGET_PLATFORM/.is_plus"
        ;;
    *"Miyoo A30"*)
        TARGET_PLATFORM="my282"
        TARGET_DEVICE="my282"
        ;;
    *"Miyoo Flip"*)
        TARGET_PLATFORM="my355"
        TARGET_DEVICE="my355"
        ;;
    *"TrimUI Smart Pro"*)
        TARGET_PLATFORM="tg5040"
        TARGET_DEVICE="tg5040"
        ;;
    *"TrimUI Brick"*)
        TARGET_PLATFORM="tg5040"
        TARGET_DEVICE="brick"
        ;;
    *"TrimUI Smart"*)
        TARGET_PLATFORM="trimuismart"
        TARGET_DEVICE="smart"
        ;;
    *"Anbernic RG35XX Plus"*)
        TARGET_PLATFORM="rg35xxplus"
        TARGET_DEVICE="rg35xxplus"
        ;;
    *"Anbernic RG35XX ("*)
        TARGET_PLATFORM="rg35xx"
        TARGET_DEVICE="rg35xx"
        ;;
    *"Powkiddy RGB30"*)
        TARGET_PLATFORM="rgb30"
        TARGET_DEVICE="rgb30"
        ;;
    *"MagicX XU Mini M"*)
        TARGET_PLATFORM="magicmini"
        TARGET_DEVICE="magicmini"
        ;;
    *"MagicX Mini Zero 28"*)
        TARGET_PLATFORM="zero28"
        TARGET_DEVICE="zero28"
        ;;
    *"GKD Pixel"*)
        TARGET_PLATFORM="gkdpixel"
        TARGET_DEVICE="gkdpixel"
        ;;
    *"M17"*)
        TARGET_PLATFORM="m17"
        TARGET_DEVICE="m17"
        ;;
esac

echo "$TARGET_PLATFORM" > "$SHARED_DIR/platform.txt"
[ -n "$TARGET_DEVICE" ] && echo "$TARGET_DEVICE" > "$SHARED_DIR/device.txt"

# Configure boot splash and dat assets for the selected hardware
BOOT_DIR="$SDCARD_PATH/.system/$TARGET_PLATFORM/dat"
if [ -d "$BOOT_DIR" ]; then
    mkdir -p "$SDCARD_PATH/.system/dat"
    cp -f "$BOOT_DIR/"* "$SDCARD_PATH/.system/dat/" 2>/dev/null
fi

# Run platform install finish script if available
if [ -f "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" ]; then
    chmod +x "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" 2>/dev/null
    "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" 2>/dev/null
fi

sync
SAY="/mnt/SDCARD/.system/$TARGET_PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"
$SAY "Configured for:
$SELECTED
Starting Cannelloni..."
sync
