import os

files = [
    'skeleton/BOOT/common/updater',
    'skeleton/BOOT/miyoo/app/MainUI',
    'skeleton/BOOT/miyoo/app/miyoomini.sh',
    'skeleton/SYSTEM/miyoomini/paks/Cannelloni.pak/launch.sh',
    'workspace/miyoomini/install/boot.sh'
]

for p in files:
    if not os.path.exists(p):
        continue
    with open(p, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        if 'cannelloni_install.log' in line or 'LOG_FILE=' in line:
            continue
        line = line.replace(' >> "$LOG_FILE" 2>&1', '')
        line = line.replace(' >> "$LOG_FILE"', '')
        line = line.replace(' 2>&1 | tee -a "$LOG_FILE"', '')
        if 'echo' in line and '$LOG_FILE' in line:
            continue
        new_lines.append(line)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(new_lines)
    print(f'Cleaned {p}')

print('Installation log references successfully removed!')
