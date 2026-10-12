#!/bin/sh

EMU_EXE=melonds

###############################

EMU_TAG=$(basename "$(dirname "$0")" .pak)
ROM="$1"
mkdir -p "$BIOS_PATH/$EMU_TAG"
mkdir -p "$SAVES_PATH/$EMU_TAG"
HOME="$USERDATA_PATH"
cd "$HOME"

export LD_LIBRARY_PATH="$SYSTEM_PATH/lib:$CORES_PATH:$LD_LIBRARY_PATH"

LOG_FILE="$LOGS_PATH/$EMU_TAG.txt"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting NDS: $ROM ===" > "$LOG_FILE"
echo "Core: $CORES_PATH/${EMU_EXE}_libretro.so" >> "$LOG_FILE"

CORE_FILE="$CORES_PATH/${EMU_EXE}_libretro.so"
if [ ! -f "$CORE_FILE" ]; then
    CORE_FILE="$CORES_PATH/desmume2015_libretro.so"
fi

nice -20 minarch.elf "$CORE_FILE" "$ROM" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "minarch exited with code: $EXIT_CODE" >> "$LOG_FILE"
