#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"

# Locate cannelloni-list binary
LIST_BIN="$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$SDCARD_PATH/Tools/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$PAK_DIR/../Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"

COLOR_FILE="$SDCARD_PATH/.userdata/shared/.cannelloni/accent_color.txt"
mkdir -p "$(dirname "$COLOR_FILE")"

CURRENT="#f1c40f"
[ -f "$COLOR_FILE" ] && CURRENT=$(cat "$COLOR_FILE" | head -n1 | tr -d '\r\n')

LIST_FILE="/tmp/accent-color-list.txt"
OUT_FILE="/tmp/accent-color-choice.txt"
rm -f "$OUT_FILE"

cat << 'EOF' > "$LIST_FILE"
Cannelloni Gold (#f1c40f)
Tomato Red (#e74c3c)
Basil Green (#2ecc71)
Sky Blue (#3498db)
Amethyst Purple (#9b59b6)
Carrot Orange (#e67e22)
Pasta White (#ffffff)
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$LIST_FILE" --format text --confirm-text "SELECT" --title "Accent Color" --write-location "$OUT_FILE"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$OUT_FILE" ]; then
        exit 0
    fi
    CHOICE=$(cat "$OUT_FILE" | head -n1)
else
    CHOICE="Cannelloni Gold (#f1c40f)"
fi

HEX="#f1c40f"
case "$CHOICE" in
    *"#e74c3c"*) HEX="#e74c3c" ;;
    *"#2ecc71"*) HEX="#2ecc71" ;;
    *"#3498db"*) HEX="#3498db" ;;
    *"#9b59b6"*) HEX="#9b59b6" ;;
    *"#e67e22"*) HEX="#e67e22" ;;
    *"#ffffff"*) HEX="#ffffff" ;;
    *) HEX="#f1c40f" ;;
esac

echo "$HEX" > "$COLOR_FILE"
sync

$SAY "Accent Color set to $HEX!
Restarting interface..."
sync
