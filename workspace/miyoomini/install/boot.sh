#!/bin/sh
# NOTE: becomes .tmp_update/miyoomini.sh

LOG_FILE="/mnt/SDCARD/cannelloni_install.log"
log() {
	echo "$@"
	echo "$@" >> "$LOG_FILE" 2>/dev/null
	sync
}

log "=== [$(date +'%Y-%m-%d %H:%M:%S')] .tmp_update/miyoomini.sh triggered ==="

PLATFORM="miyoomini"
SDCARD_PATH="/mnt/SDCARD"
UPDATE_PATH="$SDCARD_PATH/Cannelloni.zip"
if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		log "Found update package: $FOUND_ZIP"
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi
SYSTEM_PATH="$SDCARD_PATH/.system"

log "UPDATE_PATH: $UPDATE_PATH (exists: $([ -f "$UPDATE_PATH" ] && echo YES || echo NO))"
log "SYSTEM_PATH: $SYSTEM_PATH (exists: $([ -d "$SYSTEM_PATH" ] && echo YES || echo NO))"
log "SD card contents before install: $(ls -la "$SDCARD_PATH" 2>/dev/null | tr '\n' ' ')"

CPU_PATH=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > "$CPU_PATH" 2>/dev/null

# install/update or first boot configuration
FIRST_BOOT=false
if [ ! -f "$SDCARD_PATH/.userdata/shared/.cannelloni/device_model.txt" ]; then
	FIRST_BOOT=true
fi

if [ -f "$UPDATE_PATH" ] || [ "$FIRST_BOOT" = true ]; then 
	log "Install/Setup triggered (UPDATE_PATH exists: $([ -f "$UPDATE_PATH" ] && echo YES || echo NO), FIRST_BOOT: $FIRST_BOOT)"
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
	if [ -d "$SYSTEM_PATH" ] && [ "$FIRST_BOOT" = false ]; then
		log "Existing .system found and not first boot, showing updating.png..."
		./show.elf ./updating.png 2>/dev/null &
	else
		log "Showing installing.png..."
		./show.elf ./installing.png 2>/dev/null &
	fi
	sync
	
	if [ -f "$UPDATE_PATH" ]; then
		log "Unpacking update archive $UPDATE_PATH to $SDCARD_PATH/..."
		mv $SDCARD_PATH/.tmp_update $SDCARD_PATH/.tmp_update-old 2>/dev/null
		
		# Unzip update
		unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH" 2>&1 | tee -a "$LOG_FILE"
		UNZIP_RESULT=$?
		log "unzip exited with code: $UNZIP_RESULT"
		
		log "Cleaning up archive..."
		rm -f "$UPDATE_PATH"
		rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
		rm -rf $SDCARD_PATH/.tmp_update-old 2>/dev/null
	fi
	
	# Verify extracted binaries
	log "Binaries in $SYSTEM_PATH/$PLATFORM/bin/:"
	ls -la "$SYSTEM_PATH/$PLATFORM/bin/" >> "$LOG_FILE" 2>&1
	
	# Set library and binary search paths for installer tools
	export LD_LIBRARY_PATH="$SYSTEM_PATH/$PLATFORM/lib:/customer/lib:/config/lib:/lib:$LD_LIBRARY_PATH"
	export PATH="$SYSTEM_PATH/$PLATFORM/bin:$PATH"
	log "Exported LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
	log "Exported PATH: $PATH"
	
	# the updated system finishes the install/update
	if [ -f "$SYSTEM_PATH/$PLATFORM/bin/install.sh" ]; then
		log "Running install.sh..."
		chmod +x "$SYSTEM_PATH/$PLATFORM/bin/install.sh" 2>/dev/null
		"$SYSTEM_PATH/$PLATFORM/bin/install.sh" >> "$LOG_FILE" 2>&1
		log "install.sh finished with code $?"
	fi

	# Prompt user to choose hardware model on installation if needed
	DEV_SELECT="$SYSTEM_PATH/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SYSTEM_PATH/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		log "Running device_select.sh..."
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT" >> "$LOG_FILE" 2>&1
		log "device_select.sh finished with code $?"
	fi

	# Flash official Cannelloni boot logo to SPI flash if available
	USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
	mkdir -p "$USERDATA_PATH"
	BOOTLOGO_FLAG="$USERDATA_PATH/.bootlogo_flashed"
	IMG_MD5=""
	[ -f "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" ] && IMG_MD5=$(md5sum "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" 2>/dev/null | awk '{print $1}')
	SAVED_MD5=""
	[ -f "$BOOTLOGO_FLAG" ] && SAVED_MD5=$(cat "$BOOTLOGO_FLAG" 2>/dev/null)

	if [ -e "/dev/mtd3" ] && [ -n "$IMG_MD5" ] && [ "$IMG_MD5" != "$SAVED_MD5" ]; then
		if [ -f "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" ] && [ -x "$SYSTEM_PATH/$PLATFORM/bin/logowrite.elf" ]; then
			log "Flashing Cannelloni boot logo to SPI flash (/dev/mtd3)..."
			TMP_FLASH="/tmp/bootlogo_flash"
			mkdir -p "$TMP_FLASH"
			cd "$TMP_FLASH"
			"$SYSTEM_PATH/$PLATFORM/bin/logoread.elf" >> "$LOG_FILE" 2>&1
			cp -f "$SYSTEM_PATH/$PLATFORM/dat/image1.jpg" ./image1.jpg 2>/dev/null
			if "$SYSTEM_PATH/$PLATFORM/bin/logomake.elf" >> "$LOG_FILE" 2>&1 && "$SYSTEM_PATH/$PLATFORM/bin/logowrite.elf" >> "$LOG_FILE" 2>&1; then
				log "Cannelloni boot logo flashed successfully!"
				echo "$IMG_MD5" > "$BOOTLOGO_FLAG"
			fi
			cd "$SDCARD_PATH"
			rm -rf "$TMP_FLASH"
		fi
	fi
fi

export LD_LIBRARY_PATH="$SYSTEM_PATH/$PLATFORM/lib:/customer/lib:/config/lib:/lib:$LD_LIBRARY_PATH"
export PATH="$SYSTEM_PATH/$PLATFORM/bin:$PATH"

# or launch (and keep launched)
LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
log "Checking LAUNCH_PATH: $LAUNCH_PATH"
log "LAUNCH_PATH exists: $([ -f "$LAUNCH_PATH" ] && echo YES || echo NO)"

if [ -f "$LAUNCH_PATH" ]; then
	chmod +x "$LAUNCH_PATH" 2>/dev/null
	chmod +x "$SYSTEM_PATH/$PLATFORM/bin/"* 2>/dev/null
	log "Launching Cannelloni main loop..."
	while [ -f "$LAUNCH_PATH" ] ; do
		"$LAUNCH_PATH" >> "$LOG_FILE" 2>&1
		LAUNCH_EXIT=$?
		log "LAUNCH_PATH exited with code: $LAUNCH_EXIT"
		sleep 1
	done
else
	log "ERROR: LAUNCH_PATH not found! Expected at $LAUNCH_PATH"
fi

log "miyoomini.sh loop ended. System will reboot in 3 seconds."
sleep 3
reboot
