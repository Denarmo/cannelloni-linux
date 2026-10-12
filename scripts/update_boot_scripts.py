import os

wildcard_snippet = '''if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi'''

files_to_update = [
    'workspace/gkdpixel/boot/boot.sh',
    'workspace/m17/boot/boot.sh',
    'workspace/magicmini/install/boot.sh',
    'workspace/my282/install/boot.sh',
    'workspace/my355/install/boot.sh',
    'workspace/rg35xx/boot/boot.sh',
    'workspace/rg35xxplus/boot/boot.sh',
    'workspace/tg5040/install/boot.sh',
    'workspace/trimuismart/install/boot.sh',
    'workspace/zero28/install/boot.sh',
]

for path in files_to_update:
    if not os.path.isfile(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'FOUND_ZIP' in content:
        print(f'{path}: already has FOUND_ZIP logic')
        continue
    
    # We look for the last UPDATE_PATH=... definition before "if [ -f $UPDATE_PATH ]" or "if [ -f \"$UPDATE_PATH\" ]"
    if 'UPDATE_PATH=' in content:
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.startswith('UPDATE_PATH=') or ('UPDATE_PATH=' in line and 'FOUND_ZIP' not in line and not line.strip().startswith('#')):
                new_lines.append(wildcard_snippet)
        new_content = '\n'.join(new_lines)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        print(f'{path}: updated with wildcard snippet')
    else:
        print(f'{path}: no UPDATE_PATH found')
