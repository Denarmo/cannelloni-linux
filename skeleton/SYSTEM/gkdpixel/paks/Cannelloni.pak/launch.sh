#!/bin/sh
# Cannelloni.pak

#######################################

export PLATFORM="gkdpixel"
export SDCARD_PATH="/media/roms"
export BIOS_PATH="$SDCARD_PATH/Bios"
export SAVES_PATH="$SDCARD_PATH/Saves"
export SYSTEM_PATH="$SDCARD_PATH/.system/$PLATFORM"
export CORES_PATH="$SYSTEM_PATH/cores"
export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
export SHARED_USERDATA_PATH="$SDCARD_PATH/.userdata/shared"
export LOGS_PATH="$USERDATA_PATH/logs"
export DATETIME_PATH="$SHARED_USERDATA_PATH/datetime.txt"

mkdir -p "$USERDATA_PATH"
mkdir -p "$LOGS_PATH"
mkdir -p "$SHARED_USERDATA_PATH/.cannelloni"

# On first boot / install, prompt user to select their device model if not yet configured
DEVICE_MODEL_TXT="$SHARED_USERDATA_PATH/.cannelloni/device_model.txt"
if [ ! -f "$DEVICE_MODEL_TXT" ]; then
    DEV_SELECT="$SDCARD_PATH/.system/common/device_select.sh"
    [ ! -f "$DEV_SELECT" ] && DEV_SELECT="$SDCARD_PATH/.system/bin/device_select.sh"
    if [ -f "$DEV_SELECT" ]; then
        chmod +x "$DEV_SELECT" 2>/dev/null
        "$DEV_SELECT"
    fi
fi


#######################################

killall -9 power_daemon
killall -9 key_daemon

#######################################

export LD_LIBRARY_PATH=$SYSTEM_PATH/lib:$LD_LIBRARY_PATH
export PATH=$SYSTEM_PATH/bin:$PATH

keymon.elf &

#######################################

# init datetime
if [ -f "$DATETIME_PATH" ]; then
	DATETIME=`cat "$DATETIME_PATH"`
	date +'%F %T' -s "$DATETIME"
	DATETIME=`date +'%s'`
	date -u -s "@$DATETIME"
fi

#######################################

AUTO_PATH=$USERDATA_PATH/auto.sh
if [ -f "$AUTO_PATH" ]; then
	/bin/sh "$AUTO_PATH"
fi

cd $(dirname "$0")

#######################################

EXEC_PATH="/tmp/cannelloni_exec"
NEXT_PATH="/tmp/next"
touch "$EXEC_PATH"  && sync
# Apply current accent color theme if needed
COLOR_FILE="$SHARED_USERDATA_PATH/.cannelloni/accent_color.txt"
CURRENT_FILE="$SHARED_USERDATA_PATH/.cannelloni/.current_accent"
if [ -f "$COLOR_FILE" ]; then
	COLOR_VAL=$(cat "$COLOR_FILE" | head -n1 | tr -d '\r\n')
	CURR_VAL=""
	[ -f "$CURRENT_FILE" ] && CURR_VAL=$(cat "$CURRENT_FILE" | head -n1 | tr -d '\r\n')
	if [ "$COLOR_VAL" != "$CURR_VAL" ] && [ -f "$SYSTEM_PATH/bin/apply_accent_color.sh" ]; then
		"$SYSTEM_PATH/bin/apply_accent_color.sh" "$COLOR_VAL"
	fi
fi

while [ -f $EXEC_PATH ]; do
	cannelloni.elf &> $LOGS_PATH/cannelloni.txt
	echo `date +'%F %T'` > "$DATETIME_PATH"
	sync
	
	if [ -f $NEXT_PATH ]; then
		CMD=`cat $NEXT_PATH`
		eval $CMD
		rm -f $NEXT_PATH
		echo `date +'%F %T'` > "$DATETIME_PATH"
		sync
	fi
	
	if [ -f "/tmp/poweroff" ]; then
		break
	fi
done

poweroff # TODO: not sure this does anything
