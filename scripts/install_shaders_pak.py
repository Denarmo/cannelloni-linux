import os

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

shader_script = r"""#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SAY="/mnt/SDCARD/.system/$PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"

# Locate cannelloni-list binary
LIST_BIN="$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$SDCARD_PATH/.system/$PLATFORM/bin/cannelloni-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$SDCARD_PATH/Tools/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"
[ ! -x "$LIST_BIN" ] && LIST_BIN="$PAK_DIR/../Wi-Fi.pak/bin/$PLATFORM/cannelloni-list"

CFG_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$CFG_DIR"
SHADER_CONF="$CFG_DIR/shader.conf"

MENU_LIST="/tmp/shader-menu-list.txt"
MENU_OUT="/tmp/shader-menu-out.txt"
rm -f "$MENU_OUT"

cat << 'EOF' > "$MENU_LIST"
Select Active Shader Preset
Configure Shader Parameters
Assign Shaders by Console System
Reset All Shaders to Default
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$MENU_LIST" --format text --confirm-text "SELECT" --title "Shader Settings" --write-location "$MENU_OUT"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$MENU_OUT" ]; then
        exit 0
    fi
    MENU_CHOICE=$(cat "$MENU_OUT" | head -n1)
else
    MENU_CHOICE="Select Active Shader Preset"
fi

case "$MENU_CHOICE" in
    *"Select Active Shader Preset"*)
        PRESET_LIST="/tmp/shader-preset-list.txt"
        PRESET_OUT="/tmp/shader-preset-out.txt"
        rm -f "$PRESET_OUT"
        cat << 'EOF' > "$PRESET_LIST"
None (Off / Crisp Native Pixels)
CRT-Cannelloni (Denarmo Signature Composite CRT)
CRT-Cannelloni Lite (Fast Composite CRT)
CRT-EasyMode (Clean Scanlines)
CRT-Aperture (Trinitron Phosphor Aperture)
CRT-Geom (Curved Arcade Shadowmask)
CRT-Lottes Fast (Phosphor Glow & Bloom)
Zfast-CRT (Ultra-Fast Performance CRT)
LCD3x (Handheld LCD Subpixel Grid)
Zfast-LCD (Fast Handheld Matrix Grid)
Dot Matrix (Monochrome Retro Grid)
Scanlines (Horizontal Raster Scanlines)
Sharp Bilinear Simple (Pixel-Perfect Scaling)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$PRESET_LIST" --format text --confirm-text "SET" --title "Choose Shader Preset" --write-location "$PRESET_OUT"
        [ $? -ne 0 ] || [ ! -f "$PRESET_OUT" ] && exit 0
        CHOICE=$(cat "$PRESET_OUT" | head -n1)

        PRESET="none"
        EFFECT="0"
        SHARPNESS="0"
        case "$CHOICE" in
            *"CRT-Cannelloni Lite"*)
                PRESET="crt-cannelloni-lite"
                EFFECT="1"
                SHARPNESS="1"
                ;;
            *"CRT-Cannelloni"*)
                PRESET="crt-cannelloni"
                EFFECT="1"
                SHARPNESS="1"
                ;;
            *"CRT-EasyMode"*)
                PRESET="crt-easymode"
                EFFECT="1"
                SHARPNESS="0"
                ;;
            *"CRT-Aperture"*)
                PRESET="crt-aperture"
                EFFECT="1"
                SHARPNESS="1"
                ;;
            *"CRT-Geom"*)
                PRESET="crt-geom"
                EFFECT="1"
                SHARPNESS="1"
                ;;
            *"CRT-Lottes"*)
                PRESET="crt-lottes-fast"
                EFFECT="1"
                SHARPNESS="2"
                ;;
            *"Zfast-CRT"*)
                PRESET="zfast-crt"
                EFFECT="1"
                SHARPNESS="0"
                ;;
            *"LCD3x"*)
                PRESET="lcd3x"
                EFFECT="2"
                SHARPNESS="1"
                ;;
            *"Zfast-LCD"*)
                PRESET="zfast-lcd"
                EFFECT="2"
                SHARPNESS="0"
                ;;
            *"Dot Matrix"*)
                PRESET="dot"
                EFFECT="2"
                SHARPNESS="0"
                ;;
            *"Scanlines"*)
                PRESET="scanline"
                EFFECT="1"
                SHARPNESS="0"
                ;;
            *"Sharp Bilinear"*)
                PRESET="sharp-bilinear-simple"
                EFFECT="0"
                SHARPNESS="1"
                ;;
            *)
                PRESET="none"
                EFFECT="0"
                SHARPNESS="0"
                ;;
        esac

        echo "preset=$PRESET" > "$SHADER_CONF"
        echo "effect=$EFFECT" >> "$SHADER_CONF"
        echo "sharpness=$SHARPNESS" >> "$SHADER_CONF"
        echo "glslp=$SDCARD_PATH/.system/common/shaders/$PRESET/$PRESET.glslp" >> "$SHADER_CONF"

        # Apply to minarch configs
        for cfg in "$SDCARD_PATH/.userdata/$PLATFORM/"*/minarch.cfg "$SDCARD_PATH/.userdata/$PLATFORM/minarch.cfg"; do
            if [ -f "$cfg" ]; then
                sed -i "/minarch_screen_effect/d" "$cfg" 2>/dev/null
                sed -i "/minarch_screen_sharpness/d" "$cfg" 2>/dev/null
                echo "minarch_screen_effect = \"$EFFECT\"" >> "$cfg"
                echo "minarch_screen_sharpness = \"$SHARPNESS\"" >> "$cfg"
            fi
        done

        sync
        $SAY "Shader set to:
$CHOICE"
        ;;

    *"Configure Shader Parameters"*)
        PARAM_LIST="/tmp/shader-param-list.txt"
        PARAM_OUT="/tmp/shader-param-out.txt"
        rm -f "$PARAM_OUT"
        cat << 'EOF' > "$PARAM_LIST"
Scanline Intensity: Light (25%)
Scanline Intensity: Balanced (50%)
Scanline Intensity: Authentic (75%)
Scanline Intensity: Heavy (100%)
Curvature: Flat Screen (0%)
Curvature: Subtle Curve (5%)
Curvature: Arcade CRT Tube (15%)
Sharpness: Sharp (Nearest Neighbor)
Sharpness: Crisp (Integer Bilinear)
Sharpness: Soft (Bilinear Blur)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$PARAM_LIST" --format text --confirm-text "APPLY" --title "Shader Parameters" --write-location "$PARAM_OUT"
        [ $? -ne 0 ] || [ ! -f "$PARAM_OUT" ] && exit 0
        P_CHOICE=$(cat "$PARAM_OUT" | head -n1)

        case "$P_CHOICE" in
            *"Scanline Intensity"*)
                INT=$(echo "$P_CHOICE" | grep -o "[0-9]\+%" | tr -d '%')
                [ -z "$INT" ] && INT="50"
                sed -i "/intensity=/d" "$SHADER_CONF" 2>/dev/null
                echo "intensity=$INT" >> "$SHADER_CONF"
                MSG="Scanline intensity set to $INT%"
                ;;
            *"Curvature"*)
                CURV="flat"
                echo "$P_CHOICE" | grep -q "Subtle" && CURV="subtle"
                echo "$P_CHOICE" | grep -q "Arcade" && CURV="arcade"
                sed -i "/curvature=/d" "$SHADER_CONF" 2>/dev/null
                echo "curvature=$CURV" >> "$SHADER_CONF"
                MSG="Screen curvature set to $CURV"
                ;;
            *"Sharpness"*)
                SHP="0"
                echo "$P_CHOICE" | grep -q "Crisp" && SHP="1"
                echo "$P_CHOICE" | grep -q "Soft" && SHP="2"
                sed -i "/sharpness=/d" "$SHADER_CONF" 2>/dev/null
                echo "sharpness=$SHP" >> "$SHADER_CONF"
                for cfg in "$SDCARD_PATH/.userdata/$PLATFORM/"*/minarch.cfg "$SDCARD_PATH/.userdata/$PLATFORM/minarch.cfg"; do
                    if [ -f "$cfg" ]; then
                        sed -i "/minarch_screen_sharpness/d" "$cfg" 2>/dev/null
                        echo "minarch_screen_sharpness = \"$SHP\"" >> "$cfg"
                    fi
                done
                MSG="Screen sharpness set to $P_CHOICE"
                ;;
        esac
        sync
        $SAY "$MSG"
        ;;

    *"Assign Shaders by Console System"*)
        SYS_LIST="/tmp/shader-sys-list.txt"
        SYS_OUT="/tmp/shader-sys-out.txt"
        rm -f "$SYS_OUT"
        cat << 'EOF' > "$SYS_LIST"
Nintendo DS (melonDS / DeSmuME) -> LCD Grid
Game Boy & GBA (Handhelds) -> LCD3x / Dot Matrix
Retro Home Consoles (NES/SNES/Genesis/PS1) -> CRT-Cannelloni
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$SYS_LIST" --format text --confirm-text "ENABLE" --title "System Shaders" --write-location "$SYS_OUT"
        [ $? -ne 0 ] || [ ! -f "$SYS_OUT" ] && exit 0
        S_CHOICE=$(cat "$SYS_OUT" | head -n1)

        case "$S_CHOICE" in
            *"Nintendo DS"*)
                echo "preset=zfast-lcd" > "$CFG_DIR/shader_nds.conf"
                echo "effect=2" >> "$CFG_DIR/shader_nds.conf"
                NDS_CFG="$SDCARD_PATH/.userdata/$PLATFORM/NDS/minarch.cfg"
                mkdir -p "$(dirname "$NDS_CFG")"
                sed -i "/minarch_screen_effect/d" "$NDS_CFG" 2>/dev/null
                echo 'minarch_screen_effect = "2"' >> "$NDS_CFG"
                MSG="Nintendo DS shader configured: LCD Grid"
                ;;
            *"Game Boy"*)
                echo "preset=lcd3x" > "$CFG_DIR/shader_handheld.conf"
                echo "effect=2" >> "$CFG_DIR/shader_handheld.conf"
                for tag in GB GBC GBA GG; do
                    H_CFG="$SDCARD_PATH/.userdata/$PLATFORM/$tag/minarch.cfg"
                    mkdir -p "$(dirname "$H_CFG")"
                    sed -i "/minarch_screen_effect/d" "$H_CFG" 2>/dev/null
                    echo 'minarch_screen_effect = "2"' >> "$H_CFG"
                done
                MSG="Handheld shaders configured: LCD3x"
                ;;
            *"Retro Home Consoles"*)
                echo "preset=crt-cannelloni" > "$CFG_DIR/shader_console.conf"
                echo "effect=1" >> "$CFG_DIR/shader_console.conf"
                for tag in FC SFC MD PS; do
                    C_CFG="$SDCARD_PATH/.userdata/$PLATFORM/$tag/minarch.cfg"
                    mkdir -p "$(dirname "$C_CFG")"
                    sed -i "/minarch_screen_effect/d" "$C_CFG" 2>/dev/null
                    echo 'minarch_screen_effect = "1"' >> "$C_CFG"
                done
                MSG="Home console shaders configured: CRT-Cannelloni"
                ;;
        esac
        sync
        $SAY "$MSG"
        ;;

    *"Reset All Shaders to Default"*)
        rm -f "$SHADER_CONF" "$CFG_DIR/shader_"*.conf
        for cfg in "$SDCARD_PATH/.userdata/$PLATFORM/"*/minarch.cfg "$SDCARD_PATH/.userdata/$PLATFORM/minarch.cfg"; do
            if [ -f "$cfg" ]; then
                sed -i "/minarch_screen_effect/d" "$cfg" 2>/dev/null
                sed -i "/minarch_screen_sharpness/d" "$cfg" 2>/dev/null
                echo 'minarch_screen_effect = "0"' >> "$cfg"
                echo 'minarch_screen_sharpness = "0"' >> "$cfg"
            fi
        done
        sync
        $SAY "All shaders reset to default (Off)."
        ;;
esac

sync
"""

for p in platforms:
    target_dir = f'skeleton/EXTRAS/Settings/{p}/Shaders.pak'
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, 'launch.sh')
    with open(target_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(shader_script)
    print('Created Shaders.pak for', p)
