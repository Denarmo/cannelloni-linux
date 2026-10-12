#!/bin/sh
# NOTE: becomes .tmp_update/zero28.sh

PLATFORM="zero28"
SDCARD_PATH="/mnt/SDCARD"
UPDATE_PATH="$SDCARD_PATH/Cannelloni.zip"
if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi
SYSTEM_PATH="$SDCARD_PATH/.system"

CPU_PATH=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > "$CPU_PATH"

# install/update
if [ -f "$UPDATE_PATH" ]; then
	cd $(dirname "$0")/$PLATFORM

	if [ -d "$SYSTEM_PATH" ]; then
		./show.elf ./updating.png
	else
		./show.elf ./installing.png
	fi

	mv $SDCARD_PATH/.tmp_update $SDCARD_PATH/.tmp_update-old 2>/dev/null
	unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH"
	if [ -f "$SDCARD_PATH/Cannelloni.zip" ] && [ "$UPDATE_PATH" != "$SDCARD_PATH/Cannelloni.zip" ]; then
		unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
	fi
	rm -f "$UPDATE_PATH"
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	rm -rf $SDCARD_PATH/.tmp_update-old 2>/dev/null

	# the updated system finishes the install/update
	if [ -f "$SYSTEM_PATH/$PLATFORM/bin/install.sh" ]; then
		chmod +x "$SYSTEM_PATH/$PLATFORM/bin/install.sh" 2>/dev/null
		"$SYSTEM_PATH/$PLATFORM/bin/install.sh"
	fi
	sync

	DEV_SELECT="$SYSTEM_PATH/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SYSTEM_PATH/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT"
	fi
	sync
fi

# or launch (and keep launched)
LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
while [ -f "$LAUNCH_PATH" ] ; do
	"$LAUNCH_PATH"
done

poweroff # under no circumstances should stock be allowed to touch this card
