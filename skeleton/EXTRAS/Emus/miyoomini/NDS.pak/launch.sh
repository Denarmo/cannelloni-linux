#!/bin/sh

EMU_EXE=melonds

###############################

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
mkdir -p "$LOGS_PATH"
HOME="$USERDATA_PATH"
cd "$HOME"

LOG_FILE="$LOGS_PATH/$EMU_TAG.txt"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting NDS: $ROM ===" > "$LOG_FILE"

# Check emulator preference configured in Settings -> Emulators
EMU_PREF_FILE="$SHARED_USERDATA_PATH/.cannelloni/emu_nds.txt"
EMU_PREF="libretro"
[ -f "$EMU_PREF_FILE" ] && EMU_PREF=$(cat "$EMU_PREF_FILE" | tr -d '\r\n')
echo "Emulator preference: $EMU_PREF" >> "$LOG_FILE"

# Standalone DraStic check (supported on Miyoo Mini)
DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS-Drastic.pak/drastic"
[ ! -x "$DRASTIC_EXE" ] && DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS.pak/drastic"
[ ! -x "$DRASTIC_EXE" ] && DRASTIC_EXE="$(dirname "$0")/drastic"

if [ "$EMU_PREF" = "drastic" ] && [ -x "$DRASTIC_EXE" ]; then
    echo "Launching standalone DraStic..." >> "$LOG_FILE"
    mydir="$(dirname "$DRASTIC_EXE")"
    cd "$mydir" || exit 1

    # Show hotkeys on first launch
    if [ ! -f "/tmp/.show_hotkeys" ] && [ -x "$mydir/show_hotkeys" ]; then
        touch /tmp/.show_hotkeys
        LD_LIBRARY_PATH="$mydir/libs:/customer/lib:/config/lib" "$mydir/show_hotkeys"
    fi

    export HOME="$mydir"
    export PATH="$mydir:$PATH"
    export LD_LIBRARY_PATH="$mydir/libs:$SYSTEM_PATH/lib:$LD_LIBRARY_PATH"
    export SDL_VIDEODRIVER=mmiyoo
    export SDL_AUDIODRIVER=mmiyoo
    export EGL_VIDEODRIVER=mmiyoo

    # Stop audioserver to avoid audio conflicts with DraStic
    if [ -f /mnt/SDCARD/.tmp_update/script/stop_audioserver.sh ]; then
        /mnt/SDCARD/.tmp_update/script/stop_audioserver.sh
    else
        killall -9 audioserver audioserver.mod 2>/dev/null
    fi

    sv=$(cat /proc/sys/vm/swappiness 2>/dev/null)
    echo 10 > /proc/sys/vm/swappiness 2>/dev/null

    # Overclock for smooth DS emulation
    if [ -x "$mydir/cpuclock" ]; then
        "$mydir/cpuclock" 1500 2>/dev/null
    elif command -v overclock.elf >/dev/null 2>&1; then
        overclock.elf 1488000 2>/dev/null
    fi

    # Sync saves from SDCARD/Saves/NDS to DraStic
    mkdir -p "$SAVES_PATH/$EMU_TAG"
    mkdir -p "$mydir/backup"
    mkdir -p "$mydir/savestates"
    cp -f "$SAVES_PATH/$EMU_TAG/"*.dsv "$mydir/backup/" 2>/dev/null
    cp -f "$SAVES_PATH/$EMU_TAG/"*.dss "$mydir/savestates/" 2>/dev/null

    # Set native sound volume
    set_snd_level() {
        local start_time=$(date +%s)
        while [ ! -e /proc/mi_modules/mi_ao/mi_ao0 ]; do
            sleep 0.2
            if [ $(( $(date +%s) - start_time )) -ge 3 ]; then
                return 1
            fi
        done
        echo "set_ao_mute 0" > /proc/mi_modules/mi_ao/mi_ao0 2>/dev/null
        echo "set_ao_volume 0 -30dB" > /proc/mi_modules/mi_ao/mi_ao0 2>/dev/null
        echo "set_ao_volume 1 -30dB" > /proc/mi_modules/mi_ao/mi_ao0 2>/dev/null
    }
    set_snd_level &

    # Launch DraStic
    ./drastic "$ROM" >> "$LOG_FILE" 2>&1
    sync

    # Copy updated saves back to SDCARD/Saves/NDS
    cp -f "$mydir/backup/"*.dsv "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
    cp -f "$mydir/savestates/"*.dss "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
    sync

    [ -n "$sv" ] && echo "$sv" > /proc/sys/vm/swappiness 2>/dev/null

    # Restore audioserver
    if [ "$IS_PLUS" = "true" ] || [ -f /customer/app/axp_test ]; then
        /customer/app/audioserver -60 &
    else
        if [ -f /customer/lib/libpadsp.so ]; then
            LD_PRELOAD=as_preload.so audioserver.mod &
        fi
    fi

    exit 0
fi

# Libretro Core path (Default, provides in-game Cannelloni menu and save states)
echo "Launching Libretro core..." >> "$LOG_FILE"
cd "$HOME"

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"
if [ -f "$SYSTEM_PATH/lib/libstdc++.so.6" ]; then
    export LD_PRELOAD="$SYSTEM_PATH/lib/libstdc++.so.6 /lib/librt.so.1:$LD_PRELOAD"
fi

CORE_FILE="$CORES_PATH/${EMU_EXE}_libretro.so"
if [ ! -f "$CORE_FILE" ]; then
    CORE_FILE="$CORES_PATH/desmume2015_libretro.so"
fi

echo "Core: $CORE_FILE" >> "$LOG_FILE"
nice -20 minarch.elf "$CORE_FILE" "$ROM" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "minarch exited with code: $EXIT_CODE" >> "$LOG_FILE"
