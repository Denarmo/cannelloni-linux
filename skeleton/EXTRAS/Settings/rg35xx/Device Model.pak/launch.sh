#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
if [ -f "$DEV_SELECT" ]; then
    chmod +x "$DEV_SELECT" 2>/dev/null
    exec "$DEV_SELECT"
fi

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
DEVICE_TXT="$SHARED_DIR/device_model.txt"
rm -f "$DEVICE_TXT"

SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"
$SAY "Device configuration reset.
Restarting to re-select hardware..."
sync
