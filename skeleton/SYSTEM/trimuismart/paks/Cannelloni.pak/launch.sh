#!/bin/sh
# Cannelloni.pak

# recover from readonly SD card -------------------------------
touch /mnt/writetest
sync
if [ -f /mnt/writetest ] ; then
	rm -f /mnt/writetest
else
	e2fsck -p /dev/root > /mnt/SDCARD/RootRecovery.txt
	reboot
fi

#######################################

export PLATFORM="trimuismart"
export SDCARD_PATH="/mnt/SDCARD"
export BIOS_PATH="$SDCARD_PATH/Bios"
export SAVES_PATH="$SDCARD_PATH/Saves"
export SYSTEM_PATH="$SDCARD_PATH/.system/$PLATFORM"
export CORES_PATH="$SYSTEM_PATH/cores"
export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
export SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"
export LOGS_PATH="$USERDATA_PATH/logs"
export DATETIME_PATH="$SHARED_USERDATA_PATH/datetime.txt"

mkdir -p "$USERDATA_PATH"
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


#######################################

echo A,B,X,Y,L,R > /sys/module/gpio_keys_polled/parameters/button_config

echo userspace > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
CPU_PATH=/sys/devices/system/cpu/cpu0/cpufreq/scaling_setspeed
CPU_SPEED_PERF=1536000
echo $CPU_SPEED_PERF > $CPU_PATH

#######################################

export LD_LIBRARY_PATH=$SYSTEM_PATH/lib:/usr/trimui/lib:$LD_LIBRARY_PATH
export PATH=$SYSTEM_PATH/bin:/usr/trimui/bin:$PATH

leds_off

killall -9 MtpDaemon
killall -9 wpa_supplicant
ifconfig wlan0 down

keymon.elf &

#######################################

# init datetime
if [ -f "$DATETIME_PATH" ]; then
	DATETIME=`cat "$DATETIME_PATH"`
	date +'%F %T' -s "$DATETIME"
	DATETIME=`date +'%s'`
	date -u -s "@$DATETIME"
fi

#######################################

AUTO_PATH=$USERDATA_PATH/auto.sh
if [ -f "$AUTO_PATH" ]; then
	/bin/sh "$AUTO_PATH"
fi

cd $(dirname "$0")

#######################################

EXEC_PATH="/tmp/cannelloni_exec"
NEXT_PATH="/tmp/next"
touch "$EXEC_PATH"  && sync
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

while [ -f $EXEC_PATH ]; do
	cannelloni.elf &> $LOGS_PATH/cannelloni.txt
	echo $CPU_SPEED_PERF > $CPU_PATH
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
	
	# physical powerswitch, enter low power mode
	if [ -f "/tmp/poweroff" ]; then
		rm -f "/tmp/poweroff"
		killall keymon.elf
		shutdown
		echo 60000 > $CPU_PATH
		LED_ON=true
		while :; do
			if $LED_ON; then
				LED_ON=false
				leds_off
			else
				LED_ON=true
				leds_on
			fi
			sleep 0.5
		done
	fi
done

poweroff # just in case
