import glob, os

device_pak_content = '''#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        PLATFORM="miyoomini"
    fi
fi
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
if [ -f "$DEV_SELECT" ]; then
    chmod +x "$DEV_SELECT" 2>/dev/null
    exec "$DEV_SELECT" --device-only
fi

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
DEVICE_TXT="$SHARED_DIR/device_model.txt"
rm -f "$DEVICE_TXT"

SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"
$SAY "Device configuration reset.
Restarting to re-select hardware..."
sync
'''

for p_dir in glob.glob('skeleton/EXTRAS/Settings/*/Device Model.pak'):
    with open(os.path.join(p_dir, 'launch.sh'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(device_pak_content)
    print(f'Updated {p_dir}')
