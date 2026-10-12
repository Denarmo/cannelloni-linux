import glob

nds_launch = """#!/bin/sh

EMU_EXE=melonds

###############################

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
HOME="$USERDATA_PATH"
cd "$HOME"

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"

# Check emulator preference configured in Settings -> Emulators
EMU_PREF_FILE="$SHARED_USERDATA_PATH/.cannelloni/emu_nds.txt"
EMU_PREF=""
[ -f "$EMU_PREF_FILE" ] && EMU_PREF=$(cat "$EMU_PREF_FILE" | tr -d '\\r\\n')

DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS-Drastic.pak/drastic"
[ ! -x "$DRASTIC_EXE" ] && DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS.pak/drastic"

if [ "$EMU_PREF" = "drastic" ] && [ -x "$DRASTIC_EXE" ]; then
    DRASTIC_DIR="$(dirname "$DRASTIC_EXE")"
    cd "$DRASTIC_DIR"
    export LD_LIBRARY_PATH="$DRASTIC_DIR/libs:$LD_LIBRARY_PATH"
    ./drastic "$ROM" &> "$LOGS_PATH/$EMU_TAG.txt"
    exit 0
fi

# Default Libretro Core execution (enables in-game Cannelloni menu and save states)
CORE_FILE="$CORES_PATH/${EMU_EXE}_libretro.so"
if [ ! -f "$CORE_FILE" ]; then
    CORE_FILE="$CORES_PATH/desmume2015_libretro.so"
fi

nice -20 minarch.elf "$CORE_FILE" "$ROM" > "$LOGS_PATH/$EMU_TAG.txt" 2>&1
"""

for p in glob.glob("skeleton/SYSTEM/*/paks/Emus/NDS.pak/launch.sh") + glob.glob("skeleton/EXTRAS/Emus/*/NDS.pak/launch.sh"):
    with open(p, "w", newline="\n") as f:
        f.write(nds_launch)
    print("Updated", p)

print("All NDS launch scripts updated successfully!")
