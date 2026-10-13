#!/bin/sh
mydir="$(dirname "$0")"
ROM="$1"
EMU_TAG="NDS"

mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
mkdir -p "$LOGS_PATH"

LOG_FILE="$LOGS_PATH/$EMU_TAG.txt"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting DraStic: $ROM ===" > "$LOG_FILE"

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

./drastic "$ROM" >> "$LOG_FILE" 2>&1
sync

cp -f "$mydir/backup/"*.dsv "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
cp -f "$mydir/savestates/"*.dss "$SAVES_PATH/$EMU_TAG/" 2>/dev/null
sync

[ -n "$sv" ] && echo "$sv" > /proc/sys/vm/swappiness 2>/dev/null

if [ "$IS_PLUS" = "true" ] || [ -f /customer/app/axp_test ]; then
    /customer/app/audioserver -60 &
else
    if [ -f /customer/lib/libpadsp.so ]; then
        LD_PRELOAD=as_preload.so audioserver.mod &
    fi
fi
