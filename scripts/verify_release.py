import zipfile, io, hashlib

with zipfile.ZipFile('releases/Cannelloni-20261012-0.zip', 'r') as root_z:
    root_names = root_z.namelist()
    print(f'Root zip total entries: {len(root_names)}')
    
    # Check language pak
    lang_paks = [n for n in root_names if 'Language.pak' in n]
    print(f'Language.pak entries found: {len(lang_paks)} (e.g. {lang_paks[:2]})')
    
    # Check wifi pak
    wifi_sh = root_z.read('Settings/miyoomini/Wi-Fi.pak/launch.sh').decode('utf-8')
    has_axp = 'wifion' in wifi_sh
    has_chmod = 'chmod +x' in wifi_sh
    print(f'Wi-Fi launch.sh has wifion: {has_axp}, has early chmod: {has_chmod}')
    
    # Check Cannelloni.zip inside
    cann_data = root_z.read('Cannelloni.zip')
    with zipfile.ZipFile(io.BytesIO(cann_data), 'r') as cz:
        cz_names = cz.namelist()
        print(f'Cannelloni.zip entries: {len(cz_names)}')
        
        # Check assets@1x.png in .system/res/ vs #f1c40f
        a1_cz = cz.read('.system/res/assets@1x.png')
        a1_f1 = cz.read('.system/res/themes/#f1c40f/assets@1x.png')
        print(f'.system/res/assets@1x.png matches #f1c40f theme: {hashlib.md5(a1_cz).hexdigest() == hashlib.md5(a1_f1).hexdigest()}')
        
        # Check lang files in Cannelloni.zip
        langs = [n for n in cz_names if '.system/res/lang/' in n]
        print(f'Translation files in Cannelloni.zip: {langs}')
        
        # Check device_select.sh in Cannelloni.zip
        dev_sh = cz.read('.system/common/device_select.sh').decode('utf-8')
        print(f'device_select.sh has Language selection: {"STEP 1: Language Selection" in dev_sh}')
        print(f'device_select.sh has Accent Color selection: {"STEP 2: Accent Color Selection" in dev_sh}')
        print(f'device_select.sh has Device Model selection: {"STEP 3: Device Model Selection" in dev_sh}')
        
        # Check current accent flag
        print(f'.current_accent in Cannelloni.zip: {".userdata/shared/.cannelloni/.current_accent" in cz_names}')
        print(f'language.txt in Cannelloni.zip: {".userdata/shared/.cannelloni/language.txt" in cz_names}')
