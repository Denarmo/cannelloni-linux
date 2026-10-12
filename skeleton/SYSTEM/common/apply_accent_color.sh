#!/bin/sh

# apply_accent_color.sh [HEX_COLOR]
# Dynamically applies the chosen accent color to spritesheets and UI binaries.

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
    *"#e74c3c"*|*"e74c3c"*) HEX="#e74c3c" ; R=231; G=76;  B=60  ;; # Tomato Red
    *"#2ecc71"*|*"2ecc71"*) HEX="#2ecc71" ; R=46;  G=204; B=113 ;; # Basil Green
    *"#3498db"*|*"3498db"*) HEX="#3498db" ; R=52;  G=152; B=219 ;; # Sky Blue
    *"#9b59b6"*|*"9b59b6"*) HEX="#9b59b6" ; R=155; G=89;  B=182 ;; # Amethyst Purple
    *"#e67e22"*|*"e67e22"*) HEX="#e67e22" ; R=230; G=126; B=34  ;; # Carrot Orange
    *"#ffffff"*|*"ffffff"*) HEX="#ffffff" ; R=255; G=255; B=255 ;; # Pasta White
    *)                      HEX="#f1c40f" ; R=241; G=196; B=15  ;; # Cannelloni Gold (Default)
esac

echo "$HEX" > "$COLOR_FILE"

# 1. Update spritesheet assets from pre-rendered theme
THEME_DIR="$SDCARD_PATH/.system/res/themes/$HEX"
RES_DIR="$SDCARD_PATH/.system/res"
if [ -d "$THEME_DIR" ] && [ -d "$RES_DIR" ]; then
    cp -f "$THEME_DIR/assets@"*.png "$RES_DIR/" 2>/dev/null
    echo "Copied assets for theme $HEX"
fi

# 2. Patch ARM32/ARM64 ELF binaries for the current platform so SDL_FillRect uses the exact color
BIN_DIR="$SDCARD_PATH/.system/$PLATFORM/bin"

patch_elf_color() {
    ELF_FILE="$1"
    [ ! -f "$ELF_FILE" ] && return
    
    # Calculate hex byte sequences for ARM instructions
    # For miyoomini (ARM32 little-endian):
    # offset 100424 (0x18648): MOV r3, #B -> [B, 0x30, 0xa0, 0xe3]
    # offset 100432 (0x18650): MOV r2, #G -> [G, 0x20, 0xa0, 0xe3]
    # offset 100436 (0x18654): MOV r1, #R -> [R, 0x10, 0xa0, 0xe3]
    if [ "$PLATFORM" = "miyoomini" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=100424 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=100432 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=100436 count=4 conv=notrunc 2>/dev/null
    elif [ "$PLATFORM" = "rg35xx" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=106536 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=106544 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=106548 count=4 conv=notrunc 2>/dev/null
    elif [ "$PLATFORM" = "trimuismart" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=100500 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=100524 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=100532 count=4 conv=notrunc 2>/dev/null
    elif [ "$PLATFORM" = "rg35xxplus" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=44608 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=44616 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=44620 count=4 conv=notrunc 2>/dev/null
    elif [ "$PLATFORM" = "my282" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=7692 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=7700 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=7704 count=4 conv=notrunc 2>/dev/null
    elif [ "$PLATFORM" = "m17" ]; then
        printf "$(printf '\\x%02x\\x30\\xa0\\xe3' $B)" | dd of="$ELF_FILE" bs=1 seek=7096 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x20\\xa0\\xe3' $G)" | dd of="$ELF_FILE" bs=1 seek=7124 count=4 conv=notrunc 2>/dev/null
        printf "$(printf '\\x%02x\\x10\\xa0\\xe3' $R)" | dd of="$ELF_FILE" bs=1 seek=7132 count=4 conv=notrunc 2>/dev/null
    fi
}

patch_elf_color "$BIN_DIR/cannelloni.elf"
patch_elf_color "$BIN_DIR/minui.elf"

echo "$HEX" > "$CURRENT_FILE"
sync
echo "Applied accent color $HEX successfully!"
