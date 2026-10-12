#!/bin/sh
# NOTE: becomes .tmp_update/miyoomini.sh

echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] .tmp_update/miyoomini.sh triggered ==="

PLATFORM="miyoomini"
SDCARD_PATH="/mnt/SDCARD"
UPDATE_PATH="$SDCARD_PATH/Cannelloni.zip"
SYSTEM_PATH="$SDCARD_PATH/.system"

echo "UPDATE_PATH: $UPDATE_PATH (exists: $([ -f "$UPDATE_PATH" ] && echo YES || echo NO))"
echo "SYSTEM_PATH: $SYSTEM_PATH (exists: $([ -d "$SYSTEM_PATH" ] && echo YES || echo NO))"
sync

CPU_PATH=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > "$CPU_PATH" 2>/dev/null

# install/update
if [ -f "$UPDATE_PATH" ]; then 
	echo "Install package detected at $UPDATE_PATH"
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
		echo "Existing .system found, showing updating.png..."
		./show.elf ./updating.png 2>/dev/null &
	else
		echo "Fresh install, showing installing.png..."
		./show.elf ./installing.png 2>/dev/null &
	fi
	sync
	
	echo "Unpacking update archive to $SDCARD_PATH/..."
	mv $SDCARD_PATH/.tmp_update $SDCARD_PATH/.tmp_update-old 2>/dev/null
	
	# Unzip update
	unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH"
	UNZIP_RESULT=$?
	echo "unzip exited with code: $UNZIP_RESULT"
	sync
	
	if [ $UNZIP_RESULT -eq 0 ]; then
		echo "Unpack succeeded, cleaning up archive..."
		rm -f "$UPDATE_PATH"
		rm -rf $SDCARD_PATH/.tmp_update-old
	else
		echo "WARNING: unzip returned non-zero code $UNZIP_RESULT, keeping archive"
	fi
	
	# Verify extracted binaries
	echo "Binaries in $SYSTEM_PATH/$PLATFORM/bin/:"
	ls -la "$SYSTEM_PATH/$PLATFORM/bin/"
	sync
	
	# the updated system finishes the install/update
	if [ -f "$SYSTEM_PATH/$PLATFORM/bin/install.sh" ]; then
		echo "Running install.sh..."
		chmod +x "$SYSTEM_PATH/$PLATFORM/bin/install.sh" 2>/dev/null
		"$SYSTEM_PATH/$PLATFORM/bin/install.sh"
		echo "install.sh finished with code $?"
	fi
	sync

	# Flash official Cannelloni boot logo to SPI flash if available
	USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
	mkdir -p "$USERDATA_PATH"
	BOOTLOGO_FLAG="$USERDATA_PATH/.bootlogo_flashed"
	if [ ! -f "$BOOTLOGO_FLAG" ] && [ -e "/dev/mtd3" ]; then
		if [ -f "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" ] && [ -x "$SYSTEM_PATH/$PLATFORM/bin/logowrite.elf" ]; then
			echo "Flashing Cannelloni boot logo to SPI flash (/dev/mtd3)..."
			TMP_FLASH="/tmp/bootlogo_flash"
			mkdir -p "$TMP_FLASH"
			cd "$TMP_FLASH"
			"$SYSTEM_PATH/$PLATFORM/bin/logoread.elf" >/dev/null 2>&1
			cp -f "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" ./image1.jpg 2>/dev/null
			if "$SYSTEM_PATH/$PLATFORM/bin/logomake.elf" >/dev/null 2>&1 && "$SYSTEM_PATH/$PLATFORM/bin/logowrite.elf" >/dev/null 2>&1; then
				echo "Cannelloni boot logo flashed successfully!"
				touch "$BOOTLOGO_FLAG"
			fi
			cd "$SDCARD_PATH"
			rm -rf "$TMP_FLASH"
		fi
	fi
	sync
fi

# or launch (and keep launched)
LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
echo "Checking LAUNCH_PATH: $LAUNCH_PATH"
echo "LAUNCH_PATH exists: $([ -f "$LAUNCH_PATH" ] && echo YES || echo NO)"
sync

if [ -f "$LAUNCH_PATH" ]; then
	chmod +x "$LAUNCH_PATH" 2>/dev/null
	chmod +x "$SYSTEM_PATH/$PLATFORM/bin/"* 2>/dev/null
	echo "Launching Cannelloni main loop..."
	sync
	while [ -f "$LAUNCH_PATH" ] ; do
		"$LAUNCH_PATH"
		LAUNCH_EXIT=$?
		echo "LAUNCH_PATH exited with code: $LAUNCH_EXIT"
		sync
		sleep 1
	done
else
	echo "ERROR: LAUNCH_PATH not found! Expected at $LAUNCH_PATH"
	sync
fi

echo "miyoomini.sh loop ended. System will reboot in 3 seconds."
sync
sleep 3
reboot
