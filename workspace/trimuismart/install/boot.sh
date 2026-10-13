#!/bin/sh
# NOTE: becomes .tmp_update/trimuismart.sh

PLATFORM="trimuismart"
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
	# TODO: this shouldn't be necessary but might be?
	export LD_LIBRARY_PATH=/usr/trimui/lib:$LD_LIBRARY_PATH
	export PATH=/usr/trimui/bin:$PATH
	
	cd $(dirname "$0")/$PLATFORM
	./leds_off
	if [ -d "$SYSTEM_PATH" ]; then
		ACTION="updating"
	else
		ACTION="installing"
	fi
	./show.elf ./${ACTION}.png 2>/dev/null &

	touch /tmp/cannelloni_anim_active
	(
		while [ -f /tmp/cannelloni_anim_active ]; do
			for f in ./${ACTION}_*.png; do
				[ ! -f "$f" ] && break
				[ ! -f /tmp/cannelloni_anim_active ] && break
				./show.elf "$f" 2>/dev/null
				usleep 100000 2>/dev/null || sleep 1
			done
		done
	) &
	ANIM_PID=$!

	HAS_NESTED_ZIP=false
	if ./unzip -l "$UPDATE_PATH" 2>/dev/null | grep -qi 'Cannelloni\.zip'; then
		HAS_NESTED_ZIP=true
	fi

	./unzip -o "$UPDATE_PATH" -d "$SDCARD_PATH" # &> /mnt/SDCARD/unzip.txt
	if [ "$HAS_NESTED_ZIP" = true ] && [ -f "$SDCARD_PATH/Cannelloni.zip" ]; then
		./unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH"
	fi
	rm -f "$UPDATE_PATH"
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	rm -f "$SDCARD_PATH"/Cannelloni-Installer* "$SDCARD_PATH"/cannelloni_installer* 2>/dev/null
	sync

	rm -f /tmp/cannelloni_anim_active
	kill $ANIM_PID 2>/dev/null
	wait $ANIM_PID 2>/dev/null
	
	# the updated system finishes the install/update
	if [ -f $SYSTEM_PATH/$PLATFORM/bin/install.sh ]; then
		$SYSTEM_PATH/$PLATFORM/bin/install.sh # &> $SDCARD_PATH/log.txt
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

LAUNCH_PATH="$SYSTEM_PATH/$PLATFORM/paks/Cannelloni.pak/launch.sh"
while [ -f "$LAUNCH_PATH" ] ; do
	"$LAUNCH_PATH"
done

poweroff # under no circumstances should stock be allowed to touch this card
