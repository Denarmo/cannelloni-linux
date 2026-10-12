#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"

# Locate minui-list binary
LIST_BIN="$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/minui-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$SDCARD_PATH/Tools/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/minui-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$PAK_DIR/../Wi-Fi.pak/bin/$PLATFORM/minui-list"

CFG_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$CFG_DIR"

CONSOLE_LIST="/tmp/emu-console-list.txt"
CONSOLE_OUT="/tmp/emu-console-choice.txt"
rm -f "$CONSOLE_OUT"

cat << 'EOF' > "$CONSOLE_LIST"
Nintendo DS (NDS)
Game Boy Advance (GBA)
Super Nintendo (SFC)
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$CONSOLE_LIST" --format text --confirm-text "SELECT" --title "Configure Console" --write-location "$CONSOLE_OUT"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$CONSOLE_OUT" ]; then
        exit 0
    fi
    CONSOLE=$(cat "$CONSOLE_OUT" | head -n1)
else
    CONSOLE="Nintendo DS (NDS)"
fi

SUB_LIST="/tmp/emu-choice-list.txt"
SUB_OUT="/tmp/emu-choice-out.txt"
rm -f "$SUB_OUT"

case "$CONSOLE" in
    *"Nintendo DS"*)
        cat << 'EOF' > "$SUB_LIST"
DeSmuME / melonDS (Libretro - In-Game Menu & Saves)
DraStic (Standalone - High Performance)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$SUB_LIST" --format text --confirm-text "SET" --title "Nintendo DS Emulator" --write-location "$SUB_OUT"
        [ $? -ne 0 ] || [ ! -f "$SUB_OUT" ] && exit 0
        EMU_CHOICE=$(cat "$SUB_OUT" | head -n1)
        if echo "$EMU_CHOICE" | grep -q "DraStic"; then
            echo "drastic" > "$CFG_DIR/emu_nds.txt"
            MSG="Nintendo DS emulator set to:
DraStic (Standalone)"
        else
            echo "libretro" > "$CFG_DIR/emu_nds.txt"
            MSG="Nintendo DS emulator set to:
DeSmuME / melonDS (Libretro)"
        fi
        ;;

    *"Game Boy Advance"*)
        cat << 'EOF' > "$SUB_LIST"
gpSP (Libretro - Fast)
mGBA (Libretro - Accurate)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$SUB_LIST" --format text --confirm-text "SET" --title "GBA Emulator" --write-location "$SUB_OUT"
        [ $? -ne 0 ] || [ ! -f "$SUB_OUT" ] && exit 0
        EMU_CHOICE=$(cat "$SUB_OUT" | head -n1)
        if echo "$EMU_CHOICE" | grep -q "mGBA"; then
            echo "mgba" > "$CFG_DIR/emu_gba.txt"
            MSG="GBA emulator set to: mGBA"
        else
            echo "gpsp" > "$CFG_DIR/emu_gba.txt"
            MSG="GBA emulator set to: gpSP"
        fi
        ;;

    *"Super Nintendo"*)
        cat << 'EOF' > "$SUB_LIST"
snes9x2005 (Libretro - Fast)
supafaust (Libretro - Accurate)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$SUB_LIST" --format text --confirm-text "SET" --title "SNES Emulator" --write-location "$SUB_OUT"
        [ $? -ne 0 ] || [ ! -f "$SUB_OUT" ] && exit 0
        EMU_CHOICE=$(cat "$SUB_OUT" | head -n1)
        if echo "$EMU_CHOICE" | grep -q "supafaust"; then
            echo "supafaust" > "$CFG_DIR/emu_sfc.txt"
            MSG="SNES emulator set to: supafaust"
        else
            echo "snes9x2005" > "$CFG_DIR/emu_sfc.txt"
            MSG="SNES emulator set to: snes9x2005"
        fi
        ;;
esac

sync
$SAY "$MSG"
sync
