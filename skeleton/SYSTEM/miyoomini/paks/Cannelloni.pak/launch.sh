#!/bin/sh
# Cannelloni.pak

if [ -z "$LCD_INIT" ]; then
	# an update may have already initilized the LCD
	/mnt/SDCARD/.system/miyoomini/bin/blank.elf

	# init backlight
	echo 0 > /sys/class/pwm/pwmchip0/export
	echo 800 > /sys/class/pwm/pwmchip0/pwm0/period
	echo 6 > /sys/class/pwm/pwmchip0/pwm0/duty_cycle
	echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable

	# init lcd
	cat /proc/ls
	sleep 0.5
fi

# init charger detection
if [ ! -f /sys/devices/gpiochip0/gpio/gpio59/direction ]; then
	echo 59 > /sys/class/gpio/export
	echo in > /sys/devices/gpiochip0/gpio/gpio59/direction
fi


#######################################

if [ -f /customer/app/axp_test ]; then
	IS_PLUS=true
else
	IS_PLUS=false
fi
export IS_PLUS
export PLATFORM="miyoomini"
export SDCARD_PATH="/mnt/SDCARD"
export BIOS_PATH="$SDCARD_PATH/Bios"
export SAVES_PATH="$SDCARD_PATH/Saves"
export SYSTEM_PATH="$SDCARD_PATH/.system/$PLATFORM"
export CORES_PATH="$SYSTEM_PATH/cores"
export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
export SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"
export LOGS_PATH="$USERDATA_PATH/logs"
export DATETIME_PATH="$SHARED_USERDATA_PATH/datetime.txt" # used by bin/shutdown

mkdir -p "$USERDATA_PATH"
mkdir -p "$LOGS_PATH"
mkdir -p "$SHARED_USERDATA_PATH/.cannelloni"

#######################################

export CPU_SPEED_MENU=504000
export CPU_SPEED_GAME=1296000
export CPU_SPEED_PERF=1488000
echo userspace > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
overclock.elf $CPU_SPEED_PERF

export MY_MODEL=`strings -n 5 /customer/app/MainUI | grep MY` # 0.13s

MIYOO_VERSION=`/etc/fw_printenv miyoo_version`
export MIYOO_VERSION=${MIYOO_VERSION#miyoo_version=}

#######################################

# killall tee # NOTE: killing tee is somehow responsible for audioserver crashes
rm -f "$SDCARD_PATH/update.log"

#######################################

export LD_LIBRARY_PATH=$SYSTEM_PATH/lib:$LD_LIBRARY_PATH
export PATH=$SYSTEM_PATH/bin:$PATH

#######################################

if $IS_PLUS; then
	/customer/app/audioserver -60 & # &> $SDCARD_PATH/audioserver.txt &
	export LD_PRELOAD=/customer/lib/libpadsp.so
else
	if [ -f /customer/lib/libpadsp.so ]; then
	    LD_PRELOAD=as_preload.so audioserver.mod &
	    export LD_PRELOAD=libpadsp.so
	fi
fi

#######################################

lumon.elf & # adjust lcd luma and saturation

if $IS_PLUS; then
	CHARGING=`/customer/app/axp_test | awk -F'[,: {}]+' '{print $7}'`
	if [ "$CHARGING" == "3" ]; then
		batmon.elf # &> /mnt/SDCARD/batmon.txt
	fi
else
	CHARGING=`cat /sys/devices/gpiochip0/gpio/gpio59/value`
	if [ "$CHARGING" == "1" ]; then
		batmon.elf # &> /mnt/SDCARD/batmon.txt
	fi
fi

keymon.elf & # &> /mnt/SDCARD/keymon.txt &

#######################################

# init datetime
if [ -f "$DATETIME_PATH" ] && [ ! -f "$USERDATA_PATH/enable-rtc" ]; then
	DATETIME=`cat "$DATETIME_PATH"`
	date +'%F %T' -s "$DATETIME"
	DATETIME=`date +'%s'`
	date -u -s "@$DATETIME"
fi

#######################################

AUTO_PATH=$USERDATA_PATH/auto.sh
if [ -f "$AUTO_PATH" ]; then
	"$AUTO_PATH"
fi

cd $(dirname "$0")

#######################################

EXEC_PATH=/tmp/cannelloni_exec
NEXT_PATH="/tmp/next"
touch "$EXEC_PATH"  && sync

LOG_FILE="/mnt/SDCARD/cannelloni_install.log"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Cannelloni.pak/launch.sh loop starting ===" >> "$LOG_FILE" 2>&1
echo "EXEC_PATH: $EXEC_PATH" >> "$LOG_FILE" 2>&1
echo "PATH: $PATH" >> "$LOG_FILE" 2>&1
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> "$LOG_FILE" 2>&1
sync

while [ -f "$EXEC_PATH" ]; do
	overclock.elf $CPU_SPEED_PERF
	echo "Attempting to launch UI binary..." >> "$LOG_FILE" 2>&1
	sync
	if command -v cannelloni.elf >/dev/null 2>&1; then
		echo "Executing cannelloni.elf..." >> "$LOG_FILE" 2>&1
		cannelloni.elf 2>&1 | tee -a "$LOG_FILE" > "$LOGS_PATH/cannelloni.txt"
	elif [ -f "$SYSTEM_PATH/bin/cannelloni.elf" ]; then
		echo "Executing $SYSTEM_PATH/bin/cannelloni.elf..." >> "$LOG_FILE" 2>&1
		"$SYSTEM_PATH/bin/cannelloni.elf" 2>&1 | tee -a "$LOG_FILE" > "$LOGS_PATH/cannelloni.txt"
	elif command -v minui.elf >/dev/null 2>&1; then
		echo "Executing minui.elf..." >> "$LOG_FILE" 2>&1
		minui.elf 2>&1 | tee -a "$LOG_FILE" > "$LOGS_PATH/cannelloni.txt"
	elif [ -f "$SYSTEM_PATH/bin/minui.elf" ]; then
		echo "Executing $SYSTEM_PATH/bin/minui.elf..." >> "$LOG_FILE" 2>&1
		"$SYSTEM_PATH/bin/minui.elf" 2>&1 | tee -a "$LOG_FILE" > "$LOGS_PATH/cannelloni.txt"
	else
		echo "CRITICAL: No UI executable found!" >> "$LOG_FILE" 2>&1
		ls -la "$SYSTEM_PATH/bin/" >> "$LOG_FILE" 2>&1
		sync
		break
	fi
	BIN_CODE=$?
	echo "UI binary exited with code: $BIN_CODE" >> "$LOG_FILE" 2>&1
	sync
	
	echo `date +'%F %T'` > "$DATETIME_PATH"
	sync
	
	if [ -f $NEXT_PATH ]; then
		CMD=`cat $NEXT_PATH`
		echo "Processing NEXT_PATH command: $CMD" >> "$LOG_FILE" 2>&1
		eval $CMD
		rm -f $NEXT_PATH
		if [ -f "/tmp/using-swap" ]; then
			swapoff $USERDATA_PATH/swapfile
			rm -f "/tmp/using-swap"
		fi
		
		echo `date +'%F %T'` > "$DATETIME_PATH"
		overclock.elf $CPU_SPEED_PERF
		sync
	fi
done

echo "Cannelloni.pak/launch.sh loop terminated. Shutting down in 3s..." >> "$LOG_FILE" 2>&1
sync
sleep 3
shutdown # just in case
