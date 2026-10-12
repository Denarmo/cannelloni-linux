#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        PLATFORM="miyoomini"
    fi
fi
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
LANG_TXT="$CFG_DIR/language.txt"

CURRENT_LANG="en"
[ -f "$LANG_TXT" ] && CURRENT_LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')

case "$CURRENT_LANG" in
    "es")
        TITLE_MAIN="Ajustes de Shaders"
        CONFIRM_SELECT="SELECCIONAR"
        CONFIRM_APPLY="APLICAR"
        TITLE_PRESET="Elegir Ajuste de Shader"
        TITLE_PARAM="Parámetros de Shader"
        TITLE_SYS="Shaders por Consola"
        MSG_RESET="Todos los shaders restablecidos a desactivado."
        MSG_CONF_PRESET="Shader establecido a:"
        MSG_CONF_PARAM="Parámetro configurado:"
        ;;
    "fr")
        TITLE_MAIN="Paramètres des Shaders"
        CONFIRM_SELECT="SÉLECTIONNER"
        CONFIRM_APPLY="APPLIQUER"
        TITLE_PRESET="Choisir le Préréglage"
        TITLE_PARAM="Paramètres du Shader"
        TITLE_SYS="Shaders par Console"
        MSG_RESET="Tous les shaders réinitialisés par défaut (Désactivé)."
        MSG_CONF_PRESET="Shader défini sur :"
        MSG_CONF_PARAM="Paramètre configuré :"
        ;;
    "pt_BR")
        TITLE_MAIN="Configurações de Shaders"
        CONFIRM_SELECT="SELECIONAR"
        CONFIRM_APPLY="APLICAR"
        TITLE_PRESET="Escolha a Predefinição"
        TITLE_PARAM="Parâmetros do Shader"
        TITLE_SYS="Shaders por Console"
        MSG_RESET="Todos os shaders restaurados para o padrão."
        MSG_CONF_PRESET="Shader definido para:"
        MSG_CONF_PARAM="Parâmetro configurado:"
        ;;
    "de")
        TITLE_MAIN="Shader-Einstellungen"
        CONFIRM_SELECT="AUSWÄHLEN"
        CONFIRM_APPLY="ÜBERNEHMEN"
        TITLE_PRESET="Shader-Profil wählen"
        TITLE_PARAM="Shader-Parameter"
        TITLE_SYS="Konsolen-Shader"
        MSG_RESET="Alle Shader auf Standard (Aus) zurückgesetzt."
        MSG_CONF_PRESET="Shader eingestellt auf:"
        MSG_CONF_PARAM="Parameter konfiguriert:"
        ;;
    "it")
        TITLE_MAIN="Impostazioni Shader"
        CONFIRM_SELECT="SELEZIONA"
        CONFIRM_APPLY="APPLICA"
        TITLE_PRESET="Scegli Profilo Shader"
        TITLE_PARAM="Parametri Shader"
        TITLE_SYS="Shader per Console"
        MSG_RESET="Tutti gli shader ripristinati come predefiniti (Off)."
        MSG_CONF_PRESET="Shader impostato su:"
        MSG_CONF_PARAM="Parametro configurato:"
        ;;
    *)
        TITLE_MAIN="Shader Settings"
        CONFIRM_SELECT="SELECT"
        CONFIRM_APPLY="APPLY"
        TITLE_PRESET="Choose Shader Preset"
        TITLE_PARAM="Shader Parameters"
        TITLE_SYS="System Shaders"
        MSG_RESET="All shaders reset to default (Off)."
        MSG_CONF_PRESET="Shader set to:"
        MSG_CONF_PARAM="Parameter configured:"
        ;;
esac

MENU_LIST="/tmp/shader-menu-list.txt"
MENU_OUT="/tmp/shader-menu-out.txt"
rm -f "$MENU_OUT"

case "$CURRENT_LANG" in
    "es")
        cat << 'EOF' > "$MENU_LIST"
1. Seleccionar Ajuste de Shader
2. Configurar Parámetros de Shader
3. Asignar Shaders por Consola
4. Restablecer Shaders por Defecto
EOF
        ;;
    "fr")
        cat << 'EOF' > "$MENU_LIST"
1. Sélectionner le Préréglage
2. Configurer les Paramètres
3. Attribuer par Console
4. Réinitialiser par Défaut
EOF
        ;;
    "pt_BR")
        cat << 'EOF' > "$MENU_LIST"
1. Selecionar Predefinição de Shader
2. Configurar Parâmetros de Shader
3. Atribuir Shaders por Console
4. Restaurar Shaders para Padrões
EOF
        ;;
    "de")
        cat << 'EOF' > "$MENU_LIST"
1. Aktives Shader-Profil wählen
2. Shader-Parameter konfigurieren
3. Shader nach Konsole zuweisen
4. Alle Shader zurücksetzen
EOF
        ;;
    "it")
        cat << 'EOF' > "$MENU_LIST"
1. Seleziona Profilo Shader
2. Configura Parametri Shader
3. Assegna Shader per Console
4. Ripristina Shader Predefiniti
EOF
        ;;
    *)
        cat << 'EOF' > "$MENU_LIST"
1. Select Active Shader Preset
2. Configure Shader Parameters
3. Assign Shaders by Console System
4. Reset All Shaders to Default
EOF
        ;;
esac

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$MENU_LIST" --format text --confirm-text "$CONFIRM_SELECT" --title "$TITLE_MAIN" --write-location "$MENU_OUT"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$MENU_OUT" ]; then
        exit 0
    fi
    MENU_CHOICE=$(cat "$MENU_OUT" | head -n1)
else
    MENU_CHOICE="1."
fi

case "$MENU_CHOICE" in
    *"1."*|*"Select"*|*"Seleccionar"*|*"Sélectionner"*|*"Selecionar"*|*"Profil wählen"*|*"Seleziona"*)
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
        "$LIST_BIN" --disable-auto-sleep --file "$PRESET_LIST" --format text --confirm-text "$CONFIRM_APPLY" --title "$TITLE_PRESET" --write-location "$PRESET_OUT"
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

        for cfg in "$SDCARD_PATH/.userdata/$PLATFORM/"*/minarch.cfg "$SDCARD_PATH/.userdata/$PLATFORM/minarch.cfg"; do
            if [ -f "$cfg" ]; then
                sed -i "/minarch_screen_effect/d" "$cfg" 2>/dev/null
                sed -i "/minarch_screen_sharpness/d" "$cfg" 2>/dev/null
                echo "minarch_screen_effect = \"$EFFECT\"" >> "$cfg"
                echo "minarch_screen_sharpness = \"$SHARPNESS\"" >> "$cfg"
            fi
        done

        sync
        $SAY "$MSG_CONF_PRESET
$CHOICE"
        ;;

    *"2."*|*"Configure"*|*"Configurar"*|*"Parameter"*)
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
        "$LIST_BIN" --disable-auto-sleep --file "$PARAM_LIST" --format text --confirm-text "$CONFIRM_APPLY" --title "$TITLE_PARAM" --write-location "$PARAM_OUT"
        [ $? -ne 0 ] || [ ! -f "$PARAM_OUT" ] && exit 0
        P_CHOICE=$(cat "$PARAM_OUT" | head -n1)

        case "$P_CHOICE" in
            *"Scanline Intensity"*)
                INT=$(echo "$P_CHOICE" | grep -o "[0-9]\+%" | tr -d '%')
                [ -z "$INT" ] && INT="50"
                sed -i "/intensity=/d" "$SHADER_CONF" 2>/dev/null
                echo "intensity=$INT" >> "$SHADER_CONF"
                MSG="$MSG_CONF_PARAM Scanlines: $INT%"
                ;;
            *"Curvature"*)
                CURV="flat"
                echo "$P_CHOICE" | grep -q "Subtle" && CURV="subtle"
                echo "$P_CHOICE" | grep -q "Arcade" && CURV="arcade"
                sed -i "/curvature=/d" "$SHADER_CONF" 2>/dev/null
                echo "curvature=$CURV" >> "$SHADER_CONF"
                MSG="$MSG_CONF_PARAM Curvature: $CURV"
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
                MSG="$MSG_CONF_PARAM $P_CHOICE"
                ;;
        esac
        sync
        $SAY "$MSG"
        ;;

    *"3."*|*"Assign"*|*"Asignar"*|*"Attribuer"*|*"Atribuir"*|*"zuweisen"*|*"Assegna"*)
        SYS_LIST="/tmp/shader-sys-list.txt"
        SYS_OUT="/tmp/shader-sys-out.txt"
        rm -f "$SYS_OUT"
        cat << 'EOF' > "$SYS_LIST"
Nintendo DS (melonDS / DeSmuME) -> LCD Grid
Game Boy & GBA (Handhelds) -> LCD3x / Dot Matrix
Retro Home Consoles (NES/SNES/Genesis/PS1) -> CRT-Cannelloni
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$SYS_LIST" --format text --confirm-text "$CONFIRM_APPLY" --title "$TITLE_SYS" --write-location "$SYS_OUT"
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
                MSG="NDS: LCD Grid"
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
                MSG="GB/GBA: LCD3x"
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
                MSG="Home Consoles: CRT-Cannelloni"
                ;;
        esac
        sync
        $SAY "$MSG_CONF_PARAM
$MSG"
        ;;

    *"4."*|*"Reset"*|*"Restablecer"*|*"Réinitialiser"*|*"Restaurar"*|*"zurücksetzen"*|*"Ripristina"*)
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
        $SAY "$MSG_RESET"
        ;;
esac

sync
