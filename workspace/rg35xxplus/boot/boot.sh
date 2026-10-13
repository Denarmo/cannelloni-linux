#!/bin/sh

TF1_PATH=/mnt/mmc # TF1/NO NAME partition
TF2_PATH=/mnt/sdcard # TF2

rm $TF1_PATH/log.txt
touch $TF1_PATH/log.txt

RGXX_MODEL=`strings /mnt/vendor/bin/dmenu.bin | grep ^RG`

FLAG_PATH=$TF1_PATH/.cannelloni_installed
SDCARD_PATH=$TF1_PATH
SYSTEM_DIR=/.system
SYSTEM_FRAG=$SYSTEM_DIR/rg35xxplus
UPDATE_FRAG=/Cannelloni.zip
SYSTEM_PATH=${SDCARD_PATH}${SYSTEM_FRAG}
UPDATE_PATH=${SDCARD_PATH}${UPDATE_FRAG}
if [ ! -f "$UPDATE_PATH" ]; then
	FOUND_ZIP=$(ls "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip 2>/dev/null | head -n1)
	if [ -n "$FOUND_ZIP" ] && [ -f "$FOUND_ZIP" ]; then
		UPDATE_PATH="$FOUND_ZIP"
	fi
fi

# rm /mnt/sdcard
# mkdir -p /mnt/sdcard
# poweroff

if [ -h $TF2_PATH ] && [ "$TF2_PATH" -ef "$TF1_PATH" ]; then
	echo "deleting old TF2 -> TF1 symlink" >> $TF1_PATH/log.txt
	unlink $TF2_PATH
fi

if mountpoint -q $TF2_PATH; then
	echo "TF2 already mounted" >> $TF1_PATH/log.txt
else
	echo "mount TF2" >> $TF1_PATH/log.txt
	mkdir -p $TF2_PATH
	SDCARD_DEVICE=/dev/mmcblk1p1
	mount -t vfat -o rw,utf8,noatime $SDCARD_DEVICE $TF2_PATH
	if [ $? -ne 0 ]; then
		echo "mount failed, symlink to TF1" >> $TF1_PATH/log.txt
		rm -d $TF2_PATH
		ln -s $TF1_PATH $TF2_PATH
	fi
fi

if [ -d ${TF1_PATH}${SYSTEM_FRAG} ] || [ -f ${TF1_PATH}${UPDATE_FRAG} ]; then
	echo "found Cannelloni on TF1" >> $TF1_PATH/log.txt
	if [ ! -h $TF2_PATH ]; then
		echo "no system on TF2, unmount and symlink to TF1" >> $TF1_PATH/log.txt
		umount $TF2_PATH
		rm -rf $TF2_PATH
		ln -s $TF1_PATH $TF2_PATH
	fi
fi

SDCARD_PATH=$TF2_PATH
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
	echo "zip detected" >> $TF1_PATH/log.txt
	
	MODES=`cat /sys/class/graphics/fb0/modes`
	case $MODES in
	*"480x640"*)
		SUFFIX="-r"
		echo "rotated framebuffer" >> $TF1_PATH/log.txt
		;;
	esac
	
	case "$RGXX_MODEL" in
		RGcubexx)
			SUFFIX="-s"
			;;
		RG34xx*)
			SUFFIX="-w"
			;;
	esac
	
	if [ ! -d $SYSTEM_PATH ]; then
		ACTION=installing
		echo "install Cannelloni" >> $TF1_PATH/log.txt
	else
		ACTION=updating
		echo "update Cannelloni" >> $TF1_PATH/log.txt
	fi
	
	# extract tar.gz from this sh file
	LINE=$((`grep -na '^BINARY' $0 | cut -d ':' -f 1 | tail -1` + 1))
	tail -n +$LINE "$0" > /tmp/data
	tar -xf /tmp/data -C /tmp > /dev/null 2>&1
	
	# show action
	dd if=/tmp/$ACTION$SUFFIX of=/dev/fb0
	sync
	echo 0,0 > /sys/class/graphics/fb0/pan

	# install bootlogo.bmp
	if [ $ACTION = "installing" ] || [ ! -f $FLAG_PATH ]; then
		echo "replace bootlogo" >> $TF1_PATH/log.txt
		touch $FLAG_PATH
		BOOT_DEVICE=/dev/mmcblk0p2
		BOOT_PATH=/mnt/boot
		mkdir -p $BOOT_PATH
		mount -t vfat -o rw,utf8,noatime $BOOT_DEVICE $BOOT_PATH
		cp /tmp/bootlogo$SUFFIX.bmp $BOOT_PATH/bootlogo.bmp
		umount $BOOT_PATH
		rm -rf $BOOT_PATH
	fi

	HAS_NESTED_ZIP=false
	if /tmp/unzip -l "$UPDATE_PATH" 2>/dev/null | grep -qi 'Cannelloni\.zip'; then
		HAS_NESTED_ZIP=true
	fi

	/tmp/unzip -o $UPDATE_PATH -d $SDCARD_PATH >> $TF1_PATH/log.txt
	if [ "$HAS_NESTED_ZIP" = true ] && [ -f "$SDCARD_PATH/Cannelloni.zip" ]; then
		/tmp/unzip -o "$SDCARD_PATH/Cannelloni.zip" -d "$SDCARD_PATH" >> $TF1_PATH/log.txt
	fi
	rm -f "$UPDATE_PATH"
	rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
	rm -f "$SDCARD_PATH"/Cannelloni-Installer* "$SDCARD_PATH"/cannelloni_installer* 2>/dev/null
	sync

	# the updated system finishes the install/update
	echo "finishing update..." >> $TF1_PATH/log.txt
	$SYSTEM_PATH/bin/install.sh >> $TF1_PATH/log.txt

	DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
	[ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
	if [ -f "$DEV_SELECT" ]; then
		chmod +x "$DEV_SELECT" 2>/dev/null
		"$DEV_SELECT" >> $TF1_PATH/log.txt
	fi
	sync
fi

if [ -f $SYSTEM_PATH/paks/Cannelloni.pak/launch.sh ]; then
	echo "launch Cannelloni" >> $TF1_PATH/log.txt
	$SYSTEM_PATH/paks/Cannelloni.pak/launch.sh
else
	echo "couldn't find launch.sh" >> $TF1_PATH/log.txt
	if [ -h $TF2_PATH ] && [ "$TF2_PATH" -ef "$TF1_PATH" ]; then
		echo "deleting old TF2 -> TF1 symlink" >> $TF1_PATH/log.txt
		unlink $TF2_PATH
	fi
fi

sync && poweroff
sleep 60

exit 0
