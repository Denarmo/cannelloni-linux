import os

paks_map = {
    'Accent Color.pak': 'accent_color',
    'Button Mapping.pak': 'button_mapping',
    'Device Model.pak': 'device_model',
    'Emulators.pak': 'emulators',
    'Language.pak': 'language',
    'Shaders.pak': 'shaders',
    'Wi-Fi.pak': 'wifi',
    'Clock.pak': 'clock',
    'Files.pak': 'files',
    'Input.pak': 'input',
    'IP.pak': 'ip',
    "Nonna's Kitchen.pak": 'nonna',
    'Bootlogo.pak': 'bootlogo'
}

count = 0
for base in ['skeleton/EXTRAS/Settings', 'skeleton/EXTRAS/Tools']:
    if not os.path.exists(base):
        continue
    for plat in os.listdir(base):
        plat_dir = os.path.join(base, plat)
        if not os.path.isdir(plat_dir):
            continue
        for pak_name, pak_id in paks_map.items():
            pak_dir = os.path.join(plat_dir, pak_name)
            if os.path.isdir(pak_dir):
                id_file = os.path.join(pak_dir, '.pak_id')
                with open(id_file, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(pak_id + '\n')
                count += 1
print(f'Wrote {count} .pak_id marker files')
