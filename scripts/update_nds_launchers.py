import glob
import os

nds_script = """#!/bin/sh

EMU_EXE=melonds

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
mkdir -p "$LOGS_PATH"
HOME="$USERDATA_PATH"
cd "$HOME"

LOG_FILE="$SDCARD_PATH/cannelloni_nds.log"
USER_LOG="$LOGS_PATH/$EMU_TAG.txt"

log() {
    echo "$@"
    echo "$@" >> "$LOG_FILE"
    echo "$@" >> "$USER_LOG" 2>/dev/null
    sync
}

echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting NDS Launcher ===" > "$LOG_FILE"
log "ROM Path: $ROM"
if [ ! -f "$ROM" ] || [ ! -s "$ROM" ]; then
    log "ERROR: ROM file does not exist or is empty at '$ROM'!"
    SAY="$SYSTEM_PATH/bin/say.elf"
    [ ! -x "$SAY" ] && SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
    [ ! -x "$SAY" ] && SAY="say.elf"
    if command -v "$SAY" >/dev/null 2>&1 || [ -x "$SAY" ]; then
        "$SAY" "ROM file is empty (0 bytes).
Please re-transfer game." 2
    fi
    exit 1
fi
log "ROM file exists: $(wc -c < "$ROM" 2>/dev/null) bytes"

# Verify NDS ROM integrity (detect truncated/aborted transfers)
case "$ROM" in
    *.nds|*.NDS)
        hdr_sz=""
        if command -v od >/dev/null 2>&1; then
            hdr_sz=$(od -j 128 -N 4 -t u4 "$ROM" 2>/dev/null | awk 'NR==1 {print $2}')
        elif command -v hexdump >/dev/null 2>&1; then
            hdr_sz=$(hexdump -s 128 -n 4 -e '1/4 "%u\\n"' "$ROM" 2>/dev/null)
        fi
        act_sz=$(wc -c < "$ROM" 2>/dev/null | tr -d ' \\t\\r\\n')
        if [ -n "$hdr_sz" ] && [ -n "$act_sz" ] && [ "$act_sz" -lt "$hdr_sz" ]; then
            log "ERROR: NDS ROM is incomplete/truncated! File size is $act_sz bytes, but header specifies $hdr_sz bytes."
            log "Please re-upload the full game via Nonna's Kitchen."
            SAY="$SYSTEM_PATH/bin/say.elf"
            [ ! -x "$SAY" ] && SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
            [ ! -x "$SAY" ] && SAY="say.elf"
            if command -v "$SAY" >/dev/null 2>&1 || [ -x "$SAY" ]; then
                "$SAY" "NDS ROM is incomplete/truncated.
Please re-upload game." 3
            fi
            exit 1
        fi
        ;;
esac

log "Platform: $PLATFORM"
log "System Path: $SYSTEM_PATH"
log "Cores Path: $CORES_PATH"
log "Bios Path: $BIOS_PATH/$EMU_TAG"
log "Saves Path: $SAVES_PATH/$EMU_TAG"
log "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
log "PATH: $PATH"

# Ensure fallback environment variables
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$SHARED_USERDATA_PATH" ] && SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"

# Standalone DraStic check
DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS-Drastic.pak/drastic"
[ ! -f "$DRASTIC_EXE" ] && DRASTIC_EXE="$SDCARD_PATH/Emus/$PLATFORM/NDS.pak/drastic"
[ ! -f "$DRASTIC_EXE" ] && DRASTIC_EXE="$(dirname "$0")/drastic"
[ -f "$DRASTIC_EXE" ] && chmod +x "$DRASTIC_EXE" 2>/dev/null

# Check emulator preference configured in Settings -> Emulators
EMU_PREF_FILE="$SHARED_USERDATA_PATH/.cannelloni/emu_nds.txt"
EMU_PREF=""
[ -f "$EMU_PREF_FILE" ] && EMU_PREF=$(cat "$EMU_PREF_FILE" | tr -d '\\r\\n')
log "Emulator preference: $EMU_PREF"

USE_DRASTIC=0
if [ -f "$DRASTIC_EXE" ]; then
    if [ "$EMU_PREF" = "drastic" ]; then
        USE_DRASTIC=1
    elif [ -z "$EMU_PREF" ]; then
        # Default to DraStic if preference not explicitly chosen
        USE_DRASTIC=1
    fi
fi

if [ "$USE_DRASTIC" -eq 1 ]; then
    if [ -f "$DRASTIC_EXE" ]; then
        log "Launching standalone DraStic at $DRASTIC_EXE..."
        mydir="$(dirname "$DRASTIC_EXE")"
        cd "$mydir" || exit 1

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

        if [ -f /mnt/SDCARD/.tmp_update/script/stop_audioserver.sh ]; then
            /mnt/SDCARD/.tmp_update/script/stop_audioserver.sh
        else
            killall -9 audioserver audioserver.mod 2>/dev/null
        fi

        sv=$(cat /proc/sys/vm/swappiness 2>/dev/null)
        echo 10 > /proc/sys/vm/swappiness 2>/dev/null

        if [ -x "$mydir/cpuclock" ]; then
            "$mydir/cpuclock" 1500 2>/dev/null
        elif command -v overclock.elf >/dev/null 2>&1; then
            overclock.elf 1488000 2>/dev/null
        fi

        mkdir -p "$SAVES_PATH/$EMU_TAG"
        mkdir -p "$mydir/backup"
        mkdir -p "$mydir/savestates"
        cp -f "$SAVES_PATH/$EMU_TAG/"*.dsv "$mydir/backup/" 2>/dev/null
        cp -f "$SAVES_PATH/$EMU_TAG/"*.dss "$mydir/savestates/" 2>/dev/null

        log "Running DraStic binary..."
        ./drastic "$ROM" >> "$LOG_FILE" 2>&1
        DRASTIC_EXIT=$?
        log "DraStic exited with code: $DRASTIC_EXIT"
        sync

        cp -f "$mydir/backup/"*.dsv "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
        cp -f "$mydir/savestates/"*.dss "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
        sync

        [ -n "$sv" ] && echo "$sv" > /proc/sys/vm/swappiness 2>/dev/null
        exit $DRASTIC_EXIT
    else
        log "WARNING: DraStic preference selected but DraStic binary not found at $DRASTIC_EXE. Falling back to Libretro core..."
    fi
fi

# Libretro Core path (Default, provides in-game Cannelloni menu and save states)
log "Preparing Libretro core execution..."
cd "$HOME"

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"
if [ -f "$SYSTEM_PATH/lib/libstdc++.so.6" ]; then
    export LD_PRELOAD="$SYSTEM_PATH/lib/libstdc++.so.6 /lib/librt.so.1:$LD_PRELOAD"
    log "LD_PRELOAD set to: $LD_PRELOAD"
fi

CORE_FILE=""
for c in "$CORES_PATH/melonds_libretro.so" "$CORES_PATH/desmume2015_libretro.so" "$CORES_PATH/desmume_libretro.so"; do
    if [ -f "$c" ]; then
        CORE_FILE="$c"
        break
    fi
done

if [ -z "$CORE_FILE" ]; then
    log "CRITICAL ERROR: No NDS libretro core found in $CORES_PATH!"
    ls -la "$CORES_PATH" >> "$LOG_FILE" 2>&1
    exit 1
fi

CORE_SZ=$(wc -c < "$CORE_FILE" 2>/dev/null)
log "Active Core: $CORE_FILE ($CORE_SZ bytes)"

MINARCH_BIN="$(command -v minarch.elf 2>/dev/null)"
[ -z "$MINARCH_BIN" ] && [ -x "$SYSTEM_PATH/bin/minarch.elf" ] && MINARCH_BIN="$SYSTEM_PATH/bin/minarch.elf"

if [ -z "$MINARCH_BIN" ]; then
    log "CRITICAL ERROR: minarch.elf not found or not executable! PATH=$PATH, SYSTEM_PATH=$SYSTEM_PATH"
    exit 1
fi

log "Active Frontend: $MINARCH_BIN"
log "Executing: nice -20 $MINARCH_BIN $CORE_FILE $ROM"

nice -20 "$MINARCH_BIN" "$CORE_FILE" "$ROM" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
log "=== minarch exited with code: $EXIT_CODE ==="
sync
exit $EXIT_CODE
"""

nds_script_bytes = nds_script.strip().replace("\r\n", "\n").encode("utf-8") + b"\n"

paths = glob.glob("skeleton/SYSTEM/*/paks/Emus/NDS.pak/launch.sh") + glob.glob("skeleton/EXTRAS/Emus/*/NDS.pak/launch.sh")
for p in paths:
    with open(p, "wb") as f:
        f.write(nds_script_bytes)
    print("Updated:", p)
print(f"Total NDS launch scripts updated: {len(paths)}")
