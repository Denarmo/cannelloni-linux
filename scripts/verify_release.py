import zipfile

for zname in ['releases/Cannelloni-20261012-0.zip', 'releases/Cannelloni.zip']:
    with zipfile.ZipFile(zname, 'r') as z:
        names = set(z.namelist())
        print(f"=== {zname} ===")
        print("Total entries:", len(names))
        print("Has .system/common/device_select.sh:", '.system/common/device_select.sh' in names)
        print("Has .system/miyoomini/paks/Cannelloni.pak/launch.sh:", '.system/miyoomini/paks/Cannelloni.pak/launch.sh' in names)
        print("Has .tmp_update/miyoomini.sh:", '.tmp_update/miyoomini.sh' in names)
        print("Has .tmp_update/my282.sh:", '.tmp_update/my282.sh' in names)
        print("Has .tmp_update/tg5040.sh:", '.tmp_update/tg5040.sh' in names)
        print("Has Settings/miyoomini/Wi-Fi.pak:", any('Settings/miyoomini/Wi-Fi.pak' in x for x in names))
        print("Has Tools/miyoomini/Nonna's Kitchen.pak:", any("Nonna's Kitchen.pak" in x for x in names))
        print("Has Emus/miyoomini/NDS.pak:", any('Emus/miyoomini/NDS.pak' in x for x in names))
        print("Has Cannelloni.zip:", 'Cannelloni.zip' in names)
        print("Has dmenu.bin:", 'dmenu.bin' in names)

        # Check launch.sh in .system
        launch_data = z.read('.system/miyoomini/paks/Cannelloni.pak/launch.sh').decode('utf-8')
        print("launch.sh has Universal Zip Auto-Installer:", 'Universal Zip Auto-Installer' in launch_data)
        print("launch.sh erases zip:", 'rm -f "$SDCARD_PATH"/Cannelloni*.zip' in launch_data)

        # Check miyoomini.sh in .tmp_update
        boot_data = z.read('.tmp_update/miyoomini.sh').decode('utf-8')
        print(".tmp_update/miyoomini.sh extracts nested Cannelloni.zip:", 'Found nested Cannelloni.zip' in boot_data)
        print(".tmp_update/miyoomini.sh erases all zips:", 'rm -f "$SDCARD_PATH"/Cannelloni*.zip' in boot_data)
        print(".tmp_update/miyoomini.sh runs device_select.sh:", 'device_select.sh' in boot_data)

        # Check my282.sh in .tmp_update
        my282_data = z.read('.tmp_update/my282.sh').decode('utf-8')
        print(".tmp_update/my282.sh extracts nested Cannelloni.zip:", 'Cannelloni.zip' in my282_data)
        print(".tmp_update/my282.sh erases all zips:", 'rm -f "$SDCARD_PATH"/Cannelloni*.zip' in my282_data)
        print(".tmp_update/my282.sh runs device_select.sh:", 'device_select.sh' in my282_data)
