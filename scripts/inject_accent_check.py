import glob, os

snippet = '''# Apply current accent color theme if needed
COLOR_FILE="$SHARED_USERDATA_PATH/.cannelloni/accent_color.txt"
CURRENT_FILE="$SHARED_USERDATA_PATH/.cannelloni/.current_accent"
if [ -f "$COLOR_FILE" ]; then
	COLOR_VAL=$(cat "$COLOR_FILE" | head -n1 | tr -d '\\r\\n')
	CURR_VAL=""
	[ -f "$CURRENT_FILE" ] && CURR_VAL=$(cat "$CURRENT_FILE" | head -n1 | tr -d '\\r\\n')
	if [ "$COLOR_VAL" != "$CURR_VAL" ] && [ -f "$SYSTEM_PATH/bin/apply_accent_color.sh" ]; then
		"$SYSTEM_PATH/bin/apply_accent_color.sh" "$COLOR_VAL"
	fi
fi

'''

for p in sorted(glob.glob('skeleton/SYSTEM/*/paks/Cannelloni.pak/launch.sh')):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    if 'apply_accent_color.sh' in content:
        print(f'{p}: already has apply_accent_color')
        continue
    
    # Locate while [ -f ...EXEC_PATH
    target = None
    for pattern in ['while [ -f "$EXEC_PATH" ]; do', 'while [ -f $EXEC_PATH ]; do']:
        if pattern in content:
            target = pattern
            break
    
    if target:
        idx = content.find(target)
        new_content = content[:idx] + snippet + content[idx:]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'{p}: injected apply_accent_color')
    else:
        print(f'{p}: target while loop not found!')
