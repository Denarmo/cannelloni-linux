#!/bin/sh

# apply_accent_color.sh [HEX_COLOR]
# Dynamically applies the chosen accent color to spritesheets and UI binaries safely.

[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
COLOR_FILE="$SHARED_DIR/accent_color.txt"
CURRENT_FILE="$SHARED_DIR/.current_accent"

HEX="$1"
if [ -z "$HEX" ]; then
    if [ -f "$COLOR_FILE" ]; then
        HEX=$(cat "$COLOR_FILE" | head -n1 | tr -d '\r\n')
    else
        HEX="#f1c40f"
    fi
fi

# Normalize hex
case "$HEX" in
    *"#e74c3c"*|*"e74c3c"*) HEX="#e74c3c" ;; # Tomato Red
    *"#2ecc71"*|*"2ecc71"*) HEX="#2ecc71" ;; # Basil Green
    *"#3498db"*|*"3498db"*) HEX="#3498db" ;; # Sky Blue
    *"#9b59b6"*|*"9b59b6"*) HEX="#9b59b6" ;; # Amethyst Purple
    *"#e67e22"*|*"e67e22"*) HEX="#e67e22" ;; # Carrot Orange
    *"#ffffff"*|*"ffffff"*) HEX="#ffffff" ;; # Pasta White
    *)                      HEX="#f1c40f" ;; # Cannelloni Gold (Default)
esac

echo "$HEX" > "$COLOR_FILE"

# 1. Update spritesheet assets from pre-rendered theme
THEME_DIR="$SDCARD_PATH/.system/res/themes/$HEX"
RES_DIR="$SDCARD_PATH/.system/res"
if [ -d "$THEME_DIR" ] && [ -d "$RES_DIR" ]; then
    cp -f "$THEME_DIR/assets@"*.png "$RES_DIR/" 2>/dev/null
    echo "Copied assets for theme $HEX"
fi

# 2. Update pre-compiled binaries for the current theme if available
BIN_SRC="$THEME_DIR/bin/$PLATFORM"
BIN_DST="$SDCARD_PATH/.system/$PLATFORM/bin"
if [ -d "$BIN_SRC" ] && [ -d "$BIN_DST" ]; then
    cp -f "$BIN_SRC/"* "$BIN_DST/" 2>/dev/null
    chmod +x "$BIN_DST/"* 2>/dev/null
    echo "Updated binaries for $PLATFORM theme $HEX"
fi

# 3. Update Settings Wi-Fi list tool if present
WIFI_BIN="$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM"
if [ -d "$BIN_SRC" ] && [ -d "$WIFI_BIN" ]; then
    [ -f "$BIN_SRC/cannelloni-list" ] && cp -f "$BIN_SRC/cannelloni-list" "$WIFI_BIN/" 2>/dev/null
    [ -f "$BIN_SRC/minui-list" ] && cp -f "$BIN_SRC/minui-list" "$WIFI_BIN/" 2>/dev/null
    chmod +x "$WIFI_BIN/"* 2>/dev/null
fi

echo "$HEX" > "$CURRENT_FILE"
sync
echo "Applied accent color $HEX successfully!"
