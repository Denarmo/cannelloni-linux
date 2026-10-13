#!/bin/sh
# becomes /usr/sbin/frontend_start

# Restore the framebuffer to a working state
# Reset the console
# Disactivate the console on framebuffer
/usr/sbin/unlockvt > /dev/null
/usr/bin/reset
echo 0 > /sys/devices/virtual/vtconsole/vtcon1/bind

SDCARD_PATH=/media/roms
SYSTEM_PATH=$SDCARD_PATH/.system/gkdpixel
UPDATE_PATH=$SDCARD_PATH/Cannelloni.zip
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
	dd skip=54 if=/usr/share/cannelloni/$ACTION.bmp of=/dev/fb0 bs=1
	sync
	
	HAS_NESTED_ZIP=false
	if unzip -l "$UPDATE_PATH" 2>/dev/null | grep -qi 'Cannelloni\.zip'; then
		HAS_NESTED_ZIP=true
	fi

	unzip -o $UPDATE_PATH -d $SDCARD_PATH
	if [ "$HAS_NESTED_ZIP" = true ] && [ -f "$SDCARD_PATH/Cannelloni.zip" ]; then
		unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
	fi
	rm -f "$UPDATE_PATH"
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	rm -f "$SDCARD_PATH"/Cannelloni-Installer* "$SDCARD_PATH"/cannelloni_installer* 2>/dev/null
	sync
	
	rm -rf $SDCARD_PATH/gkdpixel
	
	# the updated system finishes the install/update
	$SYSTEM_PATH/bin/install.sh

	DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT"
	fi
	sync
fi

LAUNCH_PATH=/media/roms/.system/gkdpixel/paks/Cannelloni.pak/launch.sh
if [ -f "$LAUNCH_PATH" ]; then
	$LAUNCH_PATH > /media/roms/log.txt 2>&1
else
	/usr/sbin/frontend_start.original
fi