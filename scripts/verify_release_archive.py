import zipfile, io, struct

print("=== VERIFYING RELEASES/Cannelloni-20261012-0.zip ===")
with zipfile.ZipFile('releases/Cannelloni-20261012-0.zip') as root_z:
    root_names = root_z.namelist()
    print(f"Total entries in root zip: {len(root_names)}")
    
    # 1. Check Cannelloni.zip
    assert "Cannelloni.zip" in root_names, "Cannelloni.zip missing!"
    cz_bytes = root_z.read("Cannelloni.zip")
    
    with zipfile.ZipFile(io.BytesIO(cz_bytes)) as cz:
        cz_names = cz.namelist()
        print(f"Total entries in Cannelloni.zip: {len(cz_names)}")
        
        # Check cannelloni.elf
        elf_data = cz.read(".system/miyoomini/bin/cannelloni.elf")
        w1 = struct.unpack_from('<I', elf_data, 0x18648)[0]
        w2 = struct.unpack_from('<I', elf_data, 0x18650)[0]
        w3 = struct.unpack_from('<I', elf_data, 0x18654)[0]
        print(f"cannelloni.elf ARM gold patch: 0x18648={hex(w1)}, 0x18650={hex(w2)}, 0x18654={hex(w3)}")
        assert w1 == 0xe3a0300f, f"Expected 0xe3a0300f, got {hex(w1)}"
        assert w2 == 0xe3a020c4, f"Expected 0xe3a020c4, got {hex(w2)}"
        assert w3 == 0xe3a010f1, f"Expected 0xe3a010f1, got {hex(w3)}"
        print("  -> cannelloni.elf is 100% CANNELLONI GOLD (no white pill center)!")
        
        # Check themes
        themes = [n for n in cz_names if n.startswith(".system/res/themes/")]
        print(f"Found {len(themes)} theme files in .system/res/themes/")
        assert len(themes) >= 28, f"Expected at least 28 theme files (7 themes * 4 sizes), got {len(themes)}"
        
        # Check apply_accent_color.sh
        assert ".system/bin/apply_accent_color.sh" in cz_names, "apply_accent_color.sh missing in .system/bin/"
        
        # Check cores
        assert ".system/miyoomini/cores/desmume2015_libretro.so" in cz_names, "desmume2015_libretro.so missing!"
        assert ".system/miyoomini/cores/melonds_libretro.so" in cz_names, "melonds_libretro.so missing!"
        assert ".system/miyoomini/lib/libstdc++.so.6" in cz_names, "libstdc++.so.6 missing!"
        print("  -> NDS libretro cores and libstdc++ are present!")
        
    # Check DraStic standalone in root zip
    drastic_files = [n for n in root_names if n.startswith("Emus/miyoomini/NDS-Drastic.pak/")]
    print(f"NDS-Drastic.pak files count: {len(drastic_files)}")
    assert "Emus/miyoomini/NDS-Drastic.pak/drastic" in root_names, "drastic executable missing!"
    assert "Emus/miyoomini/NDS-Drastic.pak/game_database.xml" in root_names, "game_database.xml missing!"
    assert "Emus/miyoomini/NDS-Drastic.pak/libs/libSDL2-2.0.so.0" in root_names, "libSDL2 missing!"
    assert "Emus/miyoomini/NDS-Drastic.pak/libs/libasound.so.2" in root_names, "libasound missing!"
    
    # Check executable bit on drastic
    zinfo = root_z.getinfo("Emus/miyoomini/NDS-Drastic.pak/drastic")
    perm = zinfo.external_attr >> 16
    print(f"DraStic binary permissions: {oct(perm)}")
    assert perm & 0o111, "drastic binary is not executable!"
    
    # Check NDS.pak launch.sh
    assert "Emus/miyoomini/NDS.pak/launch.sh" in root_names, "NDS.pak launch.sh missing!"
    nds_sh = root_z.read("Emus/miyoomini/NDS.pak/launch.sh").decode('utf-8')
    assert "SDL_VIDEODRIVER=mmiyoo" in nds_sh, "mmiyoo video driver missing in NDS.pak/launch.sh!"
    assert "audioserver" in nds_sh, "audioserver handling missing in NDS.pak/launch.sh!"
    assert "minarch.elf" in nds_sh, "minarch.elf missing in NDS.pak/launch.sh!"
    print("  -> NDS.pak launch.sh verified with both Libretro and DraStic support!")

print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
