#!/bin/sh

# NDS uses minarch/libretro so games share Cannelloni's in-game menu.
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$SHARED_USERDATA_PATH" ] && SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"
[ -z "$USERDATA_PATH" ] && USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
[ -z "$SYSTEM_PATH" ] && SYSTEM_PATH="$SDCARD_PATH/.system/$PLATFORM"
[ -z "$CORES_PATH" ] && CORES_PATH="$SYSTEM_PATH/cores"
[ -z "$BIOS_PATH" ] && BIOS_PATH="$SDCARD_PATH/Bios"
[ -z "$SAVES_PATH" ] && SAVES_PATH="$SDCARD_PATH/Saves"
[ -z "$LOGS_PATH" ] && LOGS_PATH="$USERDATA_PATH/logs"
export SDCARD_PATH SHARED_USERDATA_PATH USERDATA_PATH SYSTEM_PATH CORES_PATH BIOS_PATH SAVES_PATH LOGS_PATH

EMU_TAG="NDS"
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG" "$SAVES_PATH/$EMU_TAG" "$LOGS_PATH" "$USERDATA_PATH"
export HOME="$USERDATA_PATH"
cd "$HOME" || exit 1

LOG_FILE="$SDCARD_PATH/cannelloni_nds.log"
USER_LOG="$LOGS_PATH/$EMU_TAG.txt"
log() {
    echo "$@"
    echo "$@" >> "$LOG_FILE"
    echo "$@" >> "$USER_LOG"
}
show_error() {
    log "ERROR: $1"
    SAY="$SYSTEM_PATH/bin/say.elf"
    [ ! -x "$SAY" ] && SAY="$(command -v say.elf 2>/dev/null)"
    [ -n "$SAY" ] && "$SAY" "$1" 3
}

echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting NDS: $ROM ===" > "$LOG_FILE"
cp "$LOG_FILE" "$USER_LOG"
if [ ! -s "$ROM" ]; then
    show_error "NDS ROM is missing or empty. Please re-transfer the game."
    exit 1
fi

# Detect incomplete .nds transfers while allowing intentionally trimmed ROMs.
case "$ROM" in
    *.nds|*.NDS)
        hdr_sz=""
        if command -v od >/dev/null 2>&1; then
            hdr_sz=$(od -j 128 -N 4 -t u4 "$ROM" 2>/dev/null | awk 'NR==1 {print $2}')
        elif command -v hexdump >/dev/null 2>&1; then
            hdr_sz=$(hexdump -s 128 -n 4 -e '1/4 "%u\n"' "$ROM" 2>/dev/null)
        fi
        act_sz=$(wc -c < "$ROM" | tr -d ' \t\r\n')
        case "$hdr_sz" in
            ''|*[!0-9]*) ;;
            *)
                if [ "$act_sz" -lt "$hdr_sz" ]; then
                    show_error "NDS ROM is incomplete. Please re-transfer the game."
                    exit 1
                fi
                ;;
        esac
        ;;
esac

EMU_PREF_FILE="$SHARED_USERDATA_PATH/.cannelloni/emu_nds.txt"
EMU_PREF="libretro"
[ -f "$EMU_PREF_FILE" ] && EMU_PREF=$(tr -d '\r\n' < "$EMU_PREF_FILE")
if [ "$EMU_PREF" = "drastic" ]; then
    # Older releases shipped this value by default. A fresh Settings choice uses
    # drastic-standalone, so an upgrade cannot silently keep bypassing minarch.
    EMU_PREF="libretro"
    printf '%s\n' "$EMU_PREF" > "$EMU_PREF_FILE"
    log "Migrated legacy NDS default to libretro."
fi

if [ "$EMU_PREF" = "drastic-standalone" ]; then
    DRASTIC_PAK="$SDCARD_PATH/Emus/$PLATFORM/NDS-Drastic.pak"
    if [ "$PLATFORM" = "miyoomini" ] && [ -f "$DRASTIC_PAK/launch.sh" ] && [ -s "$DRASTIC_PAK/drastic" ]; then
        log "Launching explicitly selected standalone DraStic."
        exec /bin/sh "$DRASTIC_PAK/launch.sh" "$ROM"
    fi
    log "Standalone DraStic is unavailable; using libretro."
fi

CORE_FILE=""
for c in "$CORES_PATH/melonds_libretro.so" "$CORES_PATH/desmume2015_libretro.so" "$CORES_PATH/desmume_libretro.so"; do
    if [ -s "$c" ]; then
        CORE_FILE="$c"
        break
    fi
done
if [ -z "$CORE_FILE" ]; then
    show_error "NDS libretro core is missing. Please reinstall Cannelloni for this device."
    exit 1
fi

MINARCH_BIN="$SYSTEM_PATH/bin/minarch.elf"
[ ! -x "$MINARCH_BIN" ] && MINARCH_BIN="$(command -v minarch.elf 2>/dev/null)"
if [ -z "$MINARCH_BIN" ]; then
    show_error "Cannelloni's in-game frontend is missing. Please reinstall Cannelloni."
    exit 1
fi

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"
log "Launching libretro core: $CORE_FILE"
nice -20 "$MINARCH_BIN" "$CORE_FILE" "$ROM" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
log "minarch exited with code: $EXIT_CODE"
sync
exit "$EXIT_CODE"
