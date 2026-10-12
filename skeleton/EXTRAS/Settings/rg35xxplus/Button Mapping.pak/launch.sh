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

MAP_FILE="$SDCARD_PATH/.userdata/shared/.cannelloni/button_swap.txt"
mkdir -p "$(dirname "$MAP_FILE")"

CURRENT="default"
[ -f "$MAP_FILE" ] && CURRENT=$(cat "$MAP_FILE" | head -n1 | tr -d '\r\n')

LIST_FILE="/tmp/button-map-list.txt"
OUT_FILE="/tmp/button-map-choice.txt"
rm -f "$OUT_FILE"

cat << 'EOF' > "$LIST_FILE"
Nintendo Layout (A: Confirm, B: Cancel)
Swapped Layout (B: Confirm, A: Cancel, Y: North, X: West)
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$LIST_FILE" --format text --confirm-text "SELECT" --title "Button Mapping" --write-location "$OUT_FILE"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$OUT_FILE" ]; then
        exit 0
    fi
    CHOICE=$(cat "$OUT_FILE" | head -n1)
else
    CHOICE="Nintendo Layout (A: Confirm, B: Cancel)"
fi

case "$CHOICE" in
    *"Swapped"*)
        echo "swapped" > "$MAP_FILE"
        MSG="Buttons mapped to Swapped Layout!
(B: Confirm, A: Cancel)"
        ;;
    *)
        echo "default" > "$MAP_FILE"
        MSG="Buttons mapped to Nintendo Layout!
(A: Confirm, B: Cancel)"
        ;;
esac
sync

$SAY "$MSG"
sync
