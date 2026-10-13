import os

SHADER_SCRIPT_TEMPLATE = r'''#!/bin/sh

PAK_DIR="$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        PLATFORM="miyoomini"
    fi
fi
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

SAY="$SDCARD_PATH/.system/$PLATFORM/bin/say.elf"
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

# Shared defaults are read by minarch before console/game overrides. Never
# rewrite minarch.cfg here: those files also hold the user's other settings.
set_shader_value() {
    touch "$1"
    sed -i "/^$2=/d" "$1"
    printf '%s=%s\n' "$2" "$3" >> "$1"
}

write_shader_preset() {
    PRESET_ID="$2"
    case "$PRESET_ID" in
        none) EFFECT=0 ;;
        line) EFFECT=1 ;;
        grid) EFFECT=2 ;;
        crt-cannelloni) EFFECT=3 ;;
        crt-cannelloni-lite) EFFECT=4 ;;
        crt-easymode) EFFECT=5 ;;
        crt-aperture) EFFECT=6 ;;
        crt-geom) EFFECT=7 ;;
        crt-lottes-fast) EFFECT=8 ;;
        zfast-crt) EFFECT=9 ;;
        lcd3x) EFFECT=10 ;;
        zfast-lcd) EFFECT=11 ;;
        dot) EFFECT=12 ;;
        scanline) EFFECT=13 ;;
        sharp-bilinear-simple) EFFECT=14 ;;
        *) return 1 ;;
    esac
    set_shader_value "$1" preset "$PRESET_ID"
    set_shader_value "$1" effect "$EFFECT"
    sed -i '/^glslp=/d' "$1"
    case "$PRESET_ID" in
        none|line|grid) ;;
        crt-cannelloni-lite)
            set_shader_value "$1" glslp "$SDCARD_PATH/.system/common/shaders/crt-cannelloni/crt-cannelloni-lite.glslp"
            ;;
        *) set_shader_value "$1" glslp "$SDCARD_PATH/.system/common/shaders/$PRESET_ID/$PRESET_ID.glslp" ;;
    esac
}

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
        MSG_RESET="Shaders globales desactivados. Se conservan los ajustes de cada juego."
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
        MSG_RESET="Shaders globaux désactivés. Les réglages par jeu sont conservés."
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
        MSG_RESET="Shaders globais desativados. Ajustes por jogo preservados."
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
        MSG_RESET="Globale Shader ausgeschaltet. Spieleinstellungen bleiben erhalten."
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
        MSG_RESET="Shader globali disattivati. Impostazioni dei giochi conservate."
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
        MSG_RESET="Shared shader defaults reset (Off). Game overrides are preserved."
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
4. Restablecer Shaders Globales
EOF
        ;;
    "fr")
        cat << 'EOF' > "$MENU_LIST"
1. Sélectionner le Préréglage
2. Configurer les Paramètres
3. Attribuer par Console
4. Réinitialiser les Shaders Globaux
EOF
        ;;
    "pt_BR")
        cat << 'EOF' > "$MENU_LIST"
1. Selecionar Predefinição de Shader
2. Configurar Parâmetros de Shader
3. Atribuir Shaders por Console
4. Restaurar Shaders Globais
EOF
        ;;
    "de")
        cat << 'EOF' > "$MENU_LIST"
1. Aktives Shader-Profil wählen
2. Shader-Parameter konfigurieren
3. Shader nach Konsole zuweisen
4. Globale Shader zurücksetzen
EOF
        ;;
    "it")
        cat << 'EOF' > "$MENU_LIST"
1. Seleziona Profilo Shader
2. Configura Parametri Shader
3. Assegna Shader per Console
4. Ripristina Shader Globali
EOF
        ;;
    *)
        cat << 'EOF' > "$MENU_LIST"
1. Select Active Shader Preset
2. Configure Shader Parameters
3. Assign Shaders by Console System
4. Reset Shared Shader Defaults
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
Simple Scanlines
Simple LCD Grid
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

        case "$CHOICE" in
            *"Simple Scanlines"*) PRESET="line" ;;
            *"Simple LCD Grid"*) PRESET="grid" ;;
            *"CRT-Cannelloni Lite"*) PRESET="crt-cannelloni-lite" ;;
            *"CRT-Cannelloni"*) PRESET="crt-cannelloni" ;;
            *"CRT-EasyMode"*) PRESET="crt-easymode" ;;
            *"CRT-Aperture"*) PRESET="crt-aperture" ;;
            *"CRT-Geom"*) PRESET="crt-geom" ;;
            *"CRT-Lottes"*) PRESET="crt-lottes-fast" ;;
            *"Zfast-CRT"*) PRESET="zfast-crt" ;;
            *"LCD3x"*) PRESET="lcd3x" ;;
            *"Zfast-LCD"*) PRESET="zfast-lcd" ;;
            *"Dot Matrix"*) PRESET="dot" ;;
            *"Scanlines"*) PRESET="scanline" ;;
            *"Sharp Bilinear"*) PRESET="sharp-bilinear-simple" ;;
            *) PRESET="none" ;;
        esac
        write_shader_preset "$SHADER_CONF" "$PRESET"

        sync
        "$SAY" "$MSG_CONF_PRESET
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
Brightness: Dim (50%)
Brightness: Low (75%)
Brightness: Normal (100%)
Brightness: Bright (125%)
Brightness: Maximum (150%)
Mask Strength: Off (0%)
Mask Strength: Light (25%)
Mask Strength: Balanced (50%)
Mask Strength: Strong (75%)
Mask Strength: Maximum (100%)
Glow: Off (0%)
Glow: Light (25%)
Glow: Balanced (50%)
Glow: Strong (75%)
Glow: Maximum (100%)
EOF
        "$LIST_BIN" --disable-auto-sleep --file "$PARAM_LIST" --format text --confirm-text "$CONFIRM_APPLY" --title "$TITLE_PARAM" --write-location "$PARAM_OUT"
        [ $? -ne 0 ] || [ ! -f "$PARAM_OUT" ] && exit 0
        P_CHOICE=$(cat "$PARAM_OUT" | head -n1)

        case "$P_CHOICE" in
            *"Scanline Intensity"*)
                INT=$(echo "$P_CHOICE" | grep -o "[0-9]\+%" | tr -d '%')
                [ -z "$INT" ] && INT="50"
                set_shader_value "$SHADER_CONF" intensity "$INT"
                MSG="$MSG_CONF_PARAM Scanlines: $INT%"
                ;;
            *"Curvature"*)
                CURV="flat"
                echo "$P_CHOICE" | grep -q "Subtle" && CURV="subtle"
                echo "$P_CHOICE" | grep -q "Arcade" && CURV="arcade"
                set_shader_value "$SHADER_CONF" curvature "$CURV"
                MSG="$MSG_CONF_PARAM Curvature: $CURV"
                ;;
            *"Sharpness"*)
                SHP="0"
                echo "$P_CHOICE" | grep -q "Crisp" && SHP="1"
                echo "$P_CHOICE" | grep -q "Soft" && SHP="2"
                set_shader_value "$SHADER_CONF" sharpness "$SHP"
                MSG="$MSG_CONF_PARAM $P_CHOICE"
                ;;
            *"Brightness"*|*"Mask Strength"*|*"Glow"*)
                VALUE=$(echo "$P_CHOICE" | sed -n 's/.*(\([0-9]*\)%).*/\1/p')
                case "$P_CHOICE" in
                    *"Brightness"*) KEY="brightness" ;;
                    *"Mask Strength"*) KEY="mask" ;;
                    *"Glow"*) KEY="glow" ;;
                esac
                set_shader_value "$SHADER_CONF" "$KEY" "$VALUE"
                MSG="$MSG_CONF_PARAM $P_CHOICE"
                ;;
        esac
        sync
        "$SAY" "$MSG"
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
                write_shader_preset "$CFG_DIR/shader_nds.conf" zfast-lcd
                MSG="NDS: LCD Grid"
                ;;
            *"Game Boy"*)
                write_shader_preset "$CFG_DIR/shader_handheld.conf" lcd3x
                MSG="GB/GBA: LCD3x"
                ;;
            *"Retro Home Consoles"*)
                write_shader_preset "$CFG_DIR/shader_console.conf" crt-cannelloni
                MSG="Home Consoles: CRT-Cannelloni"
                ;;
        esac
        sync
        "$SAY" "$MSG_CONF_PARAM
$MSG"
        ;;

    *"4."*|*"Reset"*|*"Restablecer"*|*"Réinitialiser"*|*"Restaurar"*|*"zurücksetzen"*|*"Ripristina"*)
        rm -f "$SHADER_CONF" "$CFG_DIR/shader_nds.conf" "$CFG_DIR/shader_handheld.conf" "$CFG_DIR/shader_console.conf"
        write_shader_preset "$SHADER_CONF" none
        sync
        "$SAY" "$MSG_RESET"
        ;;
esac

sync
'''

def update_shader_paks():
    settings_root = "skeleton/EXTRAS/Settings"
    platforms = [d for d in os.listdir(settings_root) if os.path.isdir(os.path.join(settings_root, d))]
    count = 0
    clean_script = SHADER_SCRIPT_TEMPLATE.strip().replace("\r\n", "\n") + "\n"
    
    for plat in platforms:
        pak_dir = os.path.join(settings_root, plat, "Shaders.pak")
        os.makedirs(pak_dir, exist_ok=True)
        launch_file = os.path.join(pak_dir, "launch.sh")
        with open(launch_file, "wb") as f:
            f.write(clean_script.encode("utf-8"))
        count += 1
    
    print(f"Updated Shaders.pak across {count} platforms.")

if __name__ == "__main__":
    update_shader_paks()
