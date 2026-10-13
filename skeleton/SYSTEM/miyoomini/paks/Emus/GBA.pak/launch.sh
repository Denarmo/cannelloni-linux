#!/bin/sh

EMU_EXE=gpsp

###############################

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"

if [ ! -f "$ROM" ] || [ ! -s "$ROM" ]; then
	[ -n "$LOGS_PATH" ] && mkdir -p "$LOGS_PATH"
	echo "ROM file does not exist or is empty: $ROM" > "$LOGS_PATH/$EMU_TAG.txt"
	SAY="$SYSTEM_PATH/bin/say.elf"
	[ ! -x "$SAY" ] && SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
	[ ! -x "$SAY" ] && SAY="say.elf"
	if command -v "$SAY" >/dev/null 2>&1 || [ -x "$SAY" ]; then
		"$SAY" "ROM file is empty (0 bytes).
Please re-transfer game." 2
	fi
	exit 1
fi
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
HOME="$USERDATA_PATH"
cd "$HOME"
nice -20 minarch.elf "$CORES_PATH/${EMU_EXE}_libretro.so" "$ROM" &> "$LOGS_PATH/$EMU_TAG.txt"
