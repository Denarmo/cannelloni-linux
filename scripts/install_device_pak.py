import os

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

device_launch = r"""#!/bin/sh

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
"""

for p in platforms:
    target_dir = f'skeleton/EXTRAS/Settings/{p}/Device Model.pak'
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, 'launch.sh')
    with open(target_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(device_launch)
    print('Created Device Model.pak for', p)
