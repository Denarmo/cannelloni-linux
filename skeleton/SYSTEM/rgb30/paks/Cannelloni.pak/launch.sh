#!/bin/sh

export PLATFORM="rgb30"
export SDCARD_PATH="/storage/roms"
export BIOS_PATH="$SDCARD_PATH/Bios"
export SAVES_PATH="$SDCARD_PATH/Saves"
export SYSTEM_PATH="$SDCARD_PATH/.system/$PLATFORM"
export CORES_PATH="$SYSTEM_PATH/cores"
export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
export SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"
export LOGS_PATH="$USERDATA_PATH/logs"
export DATETIME_PATH="$SHARED_USERDATA_PATH/datetime.txt"

#######################################

# JELOS aggressively repairs disks and leaves litter on the SD card
rm $SDCARD_PATH/FSCK*.REC

export PATH=$SYSTEM_PATH/bin:$PATH
export LD_LIBRARY_PATH=$SYSTEM_PATH/lib:$LD_LIBRARY_PATH

# required for sdl12-compat
export SDL_VIDEODRIVER=kmsdrm
export SDL_AUDIODRIVER=alsa

# required for sdl1 fbcon
# export SDL_VIDEODRIVER=fbcon
# export SDL_AUDIODRIVER=alsa
# export SDL_NOMOUSE=1

echo userspace > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
CPU_PATH=/sys/devices/system/cpu/cpufreq/policy0/scaling_setspeed
CPU_SPEED_PERF=1992000
echo $CPU_SPEED_PERF > $CPU_PATH

#######################################

keymon.elf & # &> $SDCARD_PATH/keymon.txt &

#######################################

mkdir -p "$LOGS_PATH"
mkdir -p "$SHARED_USERDATA_PATH/.cannelloni"

# Universal Zip Auto-Installer: detect dropped release zip, unpack, and cleanup
FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
    echo "Update archive detected at $FOUND_ZIP"
    [ -x "$SYSTEM_PATH/bin/show.elf" ] && [ -f "$SYSTEM_PATH/res/updating.png" ] && "$SYSTEM_PATH/bin/show.elf" "$SYSTEM_PATH/res/updating.png" 2>/dev/null &
    
    HAS_NESTED_ZIP=false
    if unzip -l "$FOUND_ZIP" 2>/dev/null | grep -qi 'Cannelloni\.zip'; then
        HAS_NESTED_ZIP=true
    fi

    unzip -o "$FOUND_ZIP" -d "$SDCARD_PATH"
    
    if [ "$HAS_NESTED_ZIP" = true ] && [ -f "$SDCARD_PATH/Cannelloni.zip" ]; then
        unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
    fi
    
    rm -f "$FOUND_ZIP"
    rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
    rm -f "$SDCARD_PATH"/Cannelloni-Installer* "$SDCARD_PATH"/cannelloni_installer* 2>/dev/null
    sync
    
    DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
    [ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
    if [ -f "$DEV_SELECT" ]; then
        chmod +x "$DEV_SELECT" 2>/dev/null
        "$DEV_SELECT"
    fi
    sync
fi

# On first boot / install, prompt user to select their device model if not yet configured
DEVICE_MODEL_TXT="$SHARED_USERDATA_PATH/.cannelloni/device_model.txt"
if [ ! -f "$DEVICE_MODEL_TXT" ]; then
    DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
    [ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
    if [ -f "$DEV_SELECT" ]; then
        chmod +x "$DEV_SELECT" 2>/dev/null
        "$DEV_SELECT"
    fi
fi

AUTO_PATH=$USERDATA_PATH/auto.sh
if [ -f "$AUTO_PATH" ]; then
	"$AUTO_PATH" # &> $LOGS_PATH/auto.txt
fi

cd $(dirname "$0")

#######################################

EXEC_PATH=/tmp/cannelloni_exec
NEXT_PATH="/tmp/next"
touch "$EXEC_PATH" && sync
# Apply current accent color theme if needed
COLOR_FILE="$SHARED_USERDATA_PATH/.cannelloni/accent_color.txt"
CURRENT_FILE="$SHARED_USERDATA_PATH/.cannelloni/.current_accent"
if [ -f "$COLOR_FILE" ]; then
	COLOR_VAL=$(cat "$COLOR_FILE" | head -n1 | tr -d '\r\n')
	CURR_VAL=""
	[ -f "$CURRENT_FILE" ] && CURR_VAL=$(cat "$CURRENT_FILE" | head -n1 | tr -d '\r\n')
	if [ "$COLOR_VAL" != "$CURR_VAL" ] && [ -f "$SYSTEM_PATH/bin/apply_accent_color.sh" ]; then
		"$SYSTEM_PATH/bin/apply_accent_color.sh" "$COLOR_VAL"
	fi
fi

# Ensure language map is applied on boot
LANG_FILE="$SHARED_USERDATA_PATH/.cannelloni/language.txt"
if [ -f "$LANG_FILE" ]; then
	LANG_VAL=$(cat "$LANG_FILE" | head -n1 | tr -d '\r\n')
	APPLY_LANG="$SDCARD_PATH/.system/common/apply_language.sh"
	[ ! -f "$APPLY_LANG" ] && APPLY_LANG="$SYSTEM_PATH/bin/apply_language.sh"
	if [ -f "$APPLY_LANG" ] && [ ! -f "$SDCARD_PATH/Settings/$PLATFORM/map.txt" ]; then
		"$APPLY_LANG" "$LANG_VAL" >/dev/null 2>&1
	fi
fi

while [ -f "$EXEC_PATH" ]; do
	echo $CPU_SPEED_PERF > $CPU_PATH
	cannelloni.elf &> $LOGS_PATH/cannelloni.txt
	echo `date +'%F %T'` > "$DATETIME_PATH"
	sync
	
	if [ -f $NEXT_PATH ]; then
		CMD=`cat $NEXT_PATH`
		LAUNCH_LOG="$SDCARD_PATH/cannelloni_launch.log"
		echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Launching: $CMD ===" >> "$LAUNCH_LOG"
		echo "Platform: $PLATFORM, System: $SYSTEM_PATH, Cores: $CORES_PATH" >> "$LAUNCH_LOG"
		echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> "$LAUNCH_LOG"
		echo "PATH: $PATH" >> "$LAUNCH_LOG"
		eval $CMD >> "$LAUNCH_LOG" 2>&1
		CMD_EXIT=$?
		echo "=== Command finished with exit code: $CMD_EXIT ===" >> "$LAUNCH_LOG"
		echo "" >> "$LAUNCH_LOG"
		sync
		rm -f $NEXT_PATH
		echo $CPU_SPEED_PERF > $CPU_PATH
		echo `date +'%F %T'` > "$DATETIME_PATH"
		sync
	fi
done

shutdown # just in case
