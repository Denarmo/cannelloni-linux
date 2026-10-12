#!/bin/sh

# SYSTEM/usr/bin/autostart.sh

SDCARD_PATH=/storage/TF2
SYSTEM_FRAG=/.system/magicmini
UPDATE_FRAG=/Cannelloni.zip
SYSTEM_PATH=${SDCARD_PATH}${SYSTEM_FRAG}
UPDATE_PATH=${SDCARD_PATH}${UPDATE_FRAG}
if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi

# is there an update available?
if [ -f $UPDATE_PATH ]; then
	echo "zip detected" >> $SDCARD_PATH/log.txt
	
	if [ ! -d $SYSTEM_PATH ]; then
		ACTION=installing
		echo "install Cannelloni" >> $SDCARD_PATH/log.txt
	else
		ACTION=updating
		echo "update Cannelloni" >> $SDCARD_PATH/log.txt
	fi
	
	# show action
	dd if=/usr/config/cannelloni/$ACTION.bmp of=/dev/fb0 bs=71 skip=1
	echo 0,0 > /sys/class/graphics/fb0/pan

	unzip -o $UPDATE_PATH -d $SDCARD_PATH >> $SDCARD_PATH/log.txt
	if [ -f "$SDCARD_PATH/Cannelloni.zip" ] && [ "$UPDATE_PATH" != "$SDCARD_PATH/Cannelloni.zip" ]; then
		unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH" >> $SDCARD_PATH/log.txt
	fi
	rm -f $UPDATE_PATH
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	sync

	# the updated system finishes the install/update
	if [ -f $SYSTEM_PATH/bin/install.sh ]; then
		$SYSTEM_PATH/bin/install.sh >> $SDCARD_PATH/log.txt
	fi
	sync

	DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT"
	fi
	sync
fi

LAUNCH_PATH=$SYSTEM_PATH/paks/Cannelloni.pak/launch.sh
if [ -f $LAUNCH_PATH ]; then
	$LAUNCH_PATH
fi

sync && shutdown now
