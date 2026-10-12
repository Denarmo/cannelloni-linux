import os

code_to_insert = '''
# Ensure language map is applied on boot
LANG_FILE="$SHARED_USERDATA_PATH/.cannelloni/language.txt"
if [ -f "$LANG_FILE" ]; then
\tLANG_VAL=$(cat "$LANG_FILE" | head -n1 | tr -d '\\r\\n')
\tAPPLY_LANG="$SDCARD_PATH/.system/common/apply_language.sh"
\t[ ! -f "$APPLY_LANG" ] && APPLY_LANG="$SYSTEM_PATH/bin/apply_language.sh"
\tif [ -f "$APPLY_LANG" ] && [ ! -f "$SDCARD_PATH/Settings/$PLATFORM/map.txt" ]; then
\t\t"$APPLY_LANG" "$LANG_VAL" >/dev/null 2>&1
\tfi
fi
'''

base = 'skeleton/SYSTEM'
count = 0
for plat in os.listdir(base):
    sh_path = os.path.join(base, plat, 'paks', 'Cannelloni.pak', 'launch.sh')
    if os.path.isfile(sh_path):
        with open(sh_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'LANG_FILE=' not in content:
            target = 'while [ -f "$EXEC_PATH" ]; do'
            if target in content:
                content = content.replace(target, code_to_insert.strip() + '\n\n' + target)
                with open(sh_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content)
                count += 1
                print(f'Updated {plat}')

print(f'Added language boot check to {count} platforms.')
