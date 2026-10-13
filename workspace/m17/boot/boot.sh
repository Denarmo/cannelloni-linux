#!/bin/sh

# NOTE: becomes em_ui.sh

PLATFORM="m17"
SDCARD_PATH="/sdcard"
UPDATE_PATH="$SDCARD_PATH/Cannelloni.zip"
if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi
SYSTEM_PATH="$SDCARD_PATH/.system"

# install/update
if [ -f "$UPDATE_PATH" ]; then 
	if [ ! -d $SYSTEM_PATH ]; then
		ACTION=installing
	else
		ACTION=updating
	fi

	# initialize fb0
	cat /sys/class/graphics/fb0/modes > /sys/class/graphics/fb0/mode

	# extract the zip file appended to the end of this script to tmp
	CUT=$((`grep -n '^BINARY' $0 | cut -d ':' -f 1 | tail -1` + 1))
	tail -n +$CUT "$0" | uudecode -o /tmp/data
	
	# unzip and display one of the two images it contains 
	unzip -o /tmp/data -d /tmp
	dd if=/tmp/$ACTION of=/dev/fb0
	sync
	
	# finally unzip Cannelloni.zip
	HAS_NESTED_ZIP=false
	if unzip -l "$UPDATE_PATH" 2>/dev/null | grep -qi 'Cannelloni\.zip'; then
		HAS_NESTED_ZIP=true
	fi

	unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH"
	if [ "$HAS_NESTED_ZIP" = true ] && [ -f "$SDCARD_PATH/Cannelloni.zip" ]; then
		unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
	fi
	rm -f "$UPDATE_PATH"
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	rm -f "$SDCARD_PATH"/Cannelloni-Installer* "$SDCARD_PATH"/cannelloni_installer* 2>/dev/null
	sync
	
	# the updated system finishes the install/update
	$SYSTEM_PATH/$PLATFORM/bin/install.sh # &> $SDCARD_PATH/install.txt
	dd if=/dev/zero of=/dev/fb0

	DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT"
	fi
	sync
fi

LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
while [ -f "$LAUNCH_PATH" ] ; do
	taskset 8 "$LAUNCH_PATH"
done

poweroff # under no circumstances should stock be allowed to touch this card

exit 0
