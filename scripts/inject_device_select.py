import glob

snippet = '''
# On first boot / install, prompt user to select their device model if not yet configured
DEVICE_MODEL_TXT="$SHARED_USERDATA_PATH/.cannelloni/device_model.txt"
if [ ! -f "$DEVICE_MODEL_TXT" ]; then
    DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
    [ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
    if [ -f "$DEV_SELECT" ]; then
        chmod +x "$DEV_SELECT" 2>/dev/null
        "$DEV_SELECT"
    fi
fi
'''

for path in sorted(glob.glob('skeleton/SYSTEM/*/paks/Cannelloni.pak/launch.sh')):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    if 'device_select.sh' in content:
        print(f'{path}: already has device_select.sh')
        continue
    
    target = 'mkdir -p "$SHARED_USERDATA_PATH/.cannelloni"'
    if target in content:
        idx = content.find(target) + len(target)
        new_content = content[:idx] + '\n' + snippet + content[idx:]
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'{path}: updated after mkdir target')
    elif 'mkdir -p "$USERDATA_PATH"' in content:
        target2 = 'mkdir -p "$USERDATA_PATH"'
        idx = content.find(target2) + len(target2)
        new_content = content[:idx] + '\nmkdir -p "$SHARED_USERDATA_PATH/.cannelloni"\n' + snippet + content[idx:]
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'{path}: updated after USERDATA_PATH')
    elif 'mkdir -p "$LOGS_PATH"' in content:
        target3 = 'mkdir -p "$LOGS_PATH"'
        idx = content.find(target3) + len(target3)
        new_content = content[:idx] + '\nmkdir -p "$SHARED_USERDATA_PATH/.cannelloni"\n' + snippet + content[idx:]
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'{path}: updated after LOGS_PATH')
    else:
        print(f'{path}: target not found!')
