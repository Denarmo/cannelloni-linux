import os
import glob

def update_launch_scripts():
    installer_block = """# Universal Zip Auto-Installer: detect dropped release zip, unpack, and cleanup
FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
    echo "Update archive detected at $FOUND_ZIP"
    [ -x "$SYSTEM_PATH/bin/show.elf" ] && [ -f "$SYSTEM_PATH/res/updating.png" ] && "$SYSTEM_PATH/bin/show.elf" "$SYSTEM_PATH/res/updating.png" 2>/dev/null &
    
    unzip -o "$FOUND_ZIP" -d "$SDCARD_PATH"
    
    if [ -f "$SDCARD_PATH/Cannelloni.zip" ] && [ "$FOUND_ZIP" != "$SDCARD_PATH/Cannelloni.zip" ]; then
        unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
    fi
    
    rm -f "$FOUND_ZIP"
    rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
    sync
    
    DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
    [ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
    if [ -f "$DEV_SELECT" ]; then
        chmod +x "$DEV_SELECT" 2>/dev/null
        "$DEV_SELECT"
    fi
    sync
fi
"""
    marker = '# On first boot / install, prompt user to select their device model if not yet configured'

    for p in sorted(glob.glob('skeleton/SYSTEM/*/paks/Cannelloni.pak/launch.sh')):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'Universal Zip Auto-Installer' not in content:
            if marker in content:
                new_content = content.replace(marker, installer_block + '\n' + marker, 1)
                with open(p, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(new_content)
                print(f"Updated {p}")
            else:
                print(f"WARNING: marker not found in {p}")
        else:
            print(f"Already updated {p}")

if __name__ == "__main__":
    update_launch_scripts()
