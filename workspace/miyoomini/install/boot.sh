#!/bin/sh
# NOTE: becomes .tmp_update/miyoomini.sh

LOG_FILE="/mnt/SDCARD/cannelloni_install.log"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] .tmp_update/miyoomini.sh triggered ===" >> "$LOG_FILE" 2>&1

PLATFORM="miyoomini"
SDCARD_PATH="/mnt/SDCARD"
UPDATE_PATH="$SDCARD_PATH/Cannelloni.zip"
if [ ! -f "$UPDATE_PATH" ] && [ -f "$SDCARD_PATH/MinUI.zip" ]; then
	UPDATE_PATH="$SDCARD_PATH/MinUI.zip"
fi
SYSTEM_PATH="$SDCARD_PATH/.system"

echo "UPDATE_PATH: $UPDATE_PATH (exists: $([ -f "$UPDATE_PATH" ] && echo YES || echo NO))" >> "$LOG_FILE" 2>&1
echo "SYSTEM_PATH: $SYSTEM_PATH (exists: $([ -d "$SYSTEM_PATH" ] && echo YES || echo NO))" >> "$LOG_FILE"
sync

CPU_PATH=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > "$CPU_PATH" 2>/dev/null

# install/update
if [ -f "$UPDATE_PATH" ]; then 
	echo "Install package detected at $UPDATE_PATH" >> "$LOG_FILE" 2>&1
	cd $(dirname "$0")/$PLATFORM
	
	# init backlight
	echo 0 > /sys/class/pwm/pwmchip0/export 2>/dev/null
	echo 800 > /sys/class/pwm/pwmchip0/pwm0/period 2>/dev/null
	echo 50 > /sys/class/pwm/pwmchip0/pwm0/duty_cycle 2>/dev/null
	echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable 2>/dev/null

	# init lcd
	cat /proc/ls 2>/dev/null
	sleep 1
	export LCD_INIT=1

	chmod +x ./show.elf 2>/dev/null
	if [ -d "$SYSTEM_PATH" ]; then
		echo "Existing .system found, showing updating.png..." >> "$LOG_FILE" 2>&1
		./show.elf ./updating.png 2>/dev/null &
	else
		echo "Fresh install, showing installing.png..." >> "$LOG_FILE" 2>&1
		./show.elf ./installing.png 2>/dev/null &
	fi
	sync
	
	echo "Unpacking update archive to $SDCARD_PATH/..." >> "$LOG_FILE" 2>&1
	mv $SDCARD_PATH/.tmp_update $SDCARD_PATH/.tmp_update-old 2>/dev/null
	
	# Unzip update
	unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH" >> "$LOG_FILE" 2>&1
	UNZIP_RESULT=$?
	echo "unzip exited with code: $UNZIP_RESULT" >> "$LOG_FILE" 2>&1
	sync
	
	if [ $UNZIP_RESULT -eq 0 ]; then
		echo "Unpack succeeded, cleaning up archive..." >> "$LOG_FILE" 2>&1
		rm -f "$UPDATE_PATH"
		rm -rf $SDCARD_PATH/.tmp_update-old
	else
		echo "WARNING: unzip returned non-zero code $UNZIP_RESULT, keeping archive" >> "$LOG_FILE" 2>&1
	fi
	
	# Verify extracted binaries
	echo "Binaries in $SYSTEM_PATH/$PLATFORM/bin/:" >> "$LOG_FILE" 2>&1
	ls -la "$SYSTEM_PATH/$PLATFORM/bin/" >> "$LOG_FILE" 2>&1
	sync
	
	# the updated system finishes the install/update
	if [ -f "$SYSTEM_PATH/$PLATFORM/bin/install.sh" ]; then
		echo "Running install.sh..." >> "$LOG_FILE" 2>&1
		chmod +x "$SYSTEM_PATH/$PLATFORM/bin/install.sh" 2>/dev/null
		"$SYSTEM_PATH/$PLATFORM/bin/install.sh" >> "$LOG_FILE" 2>&1
		echo "install.sh finished with code $?" >> "$LOG_FILE" 2>&1
	fi
	sync
fi

# or launch (and keep launched)
LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
echo "Checking LAUNCH_PATH: $LAUNCH_PATH" >> "$LOG_FILE" 2>&1
echo "LAUNCH_PATH exists: $([ -f "$LAUNCH_PATH" ] && echo YES || echo NO)" >> "$LOG_FILE" 2>&1
sync

if [ -f "$LAUNCH_PATH" ]; then
	chmod +x "$LAUNCH_PATH" 2>/dev/null
	chmod +x "$SYSTEM_PATH/$PLATFORM/bin/"* 2>/dev/null
	echo "Launching Cannelloni main loop..." >> "$LOG_FILE" 2>&1
	sync
	while [ -f "$LAUNCH_PATH" ] ; do
		"$LAUNCH_PATH" >> "$LOG_FILE" 2>&1
		LAUNCH_EXIT=$?
		echo "LAUNCH_PATH exited with code: $LAUNCH_EXIT" >> "$LOG_FILE" 2>&1
		sync
		sleep 1
	done
else
	echo "ERROR: LAUNCH_PATH not found! Expected at $LAUNCH_PATH" >> "$LOG_FILE" 2>&1
	sync
fi

echo "miyoomini.sh loop ended. System will reboot in 3 seconds." >> "$LOG_FILE" 2>&1
sync
sleep 3
reboot
