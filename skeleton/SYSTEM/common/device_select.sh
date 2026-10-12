#!/bin/sh
# Cannelloni Universal Installation & Setup Wizard
# Sequence: 1. Language -> 2. Accent Color -> 3. Handheld Device Model

[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        PLATFORM="miyoomini"
    fi
fi
[ -z "$PLATFORM" ] && PLATFORM="miyoomini"

LOG_FILE="$SDCARD_PATH/cannelloni_install.log"
log() {
    echo "$@"
    echo "$@" >> "$LOG_FILE" 2>/dev/null
    sync
}

log "=== [$(date +'%Y-%m-%d %H:%M:%S')] device_select.sh wizard started ==="
log "PLATFORM: $PLATFORM, SDCARD_PATH: $SDCARD_PATH"

export LD_LIBRARY_PATH="$SDCARD_PATH/.system/$PLATFORM/lib:/customer/lib:/config/lib:/lib:$LD_LIBRARY_PATH"
export PATH="$SDCARD_PATH/.system/$PLATFORM/bin:$PATH"
log "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$SHARED_DIR"

DEVICE_TXT="$SHARED_DIR/device_model.txt"
LANG_TXT="$SHARED_DIR/language.txt"
COLOR_TXT="$SHARED_DIR/accent_color.txt"

# Locate cannelloni-list binary
LIST_BIN=""
for loc in \
    "$SDCARD_PATH/.system/$PLATFORM/bin/cannelloni-list" \
    "$SDCARD_PATH/.system/res/themes/#f1c40f/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/Settings/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/Settings/miyoomini/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/Tools/$PLATFORM/Wi-Fi.pak/bin/$PLATFORM/cannelloni-list" \
    "$SDCARD_PATH/.system/$PLATFORM/bin/minui-list" \
    "$SDCARD_PATH/.system/bin/cannelloni-list"; do
    if [ -f "$loc" ]; then
        chmod +x "$loc" 2>/dev/null
        LIST_BIN="$loc"
        break
    fi
done
log "Resolved LIST_BIN: '$LIST_BIN' (executable: $([ -x "$LIST_BIN" ] && echo YES || echo NO))"

MODE="$1"

# ----------------------------------------------------
# STEP 1: Language Selection (Skip if --device-only)
# ----------------------------------------------------
SELECTED_LANG="en"
if [ "$MODE" != "--device-only" ]; then
    CHOICE_LANG_LIST="/tmp/lang-choices.txt"
    CHOICE_LANG_OUT="/tmp/lang-choice-out.txt"
    rm -f "$CHOICE_LANG_OUT"

    cat << 'EOF' > "$CHOICE_LANG_LIST"
English
Español (Spanish)
Français (French)
Português (Brasil)
Deutsch (German)
Italiano (Italian)
EOF

    if [ -x "$LIST_BIN" ]; then
        "$LIST_BIN" --disable-auto-sleep --file "$CHOICE_LANG_LIST" --format text --confirm-text "NEXT" --title "Choose Language" --write-location "$CHOICE_LANG_OUT"
        if [ $? -eq 0 ] && [ -f "$CHOICE_LANG_OUT" ]; then
            CHOSEN_LANG=$(cat "$CHOICE_LANG_OUT" | head -n1)
            case "$CHOSEN_LANG" in
                *"Español"*) SELECTED_LANG="es" ;;
                *"Français"*) SELECTED_LANG="fr" ;;
                *"Português"*) SELECTED_LANG="pt_BR" ;;
                *"Deutsch"*) SELECTED_LANG="de" ;;
                *"Italiano"*) SELECTED_LANG="it" ;;
                *) SELECTED_LANG="en" ;;
            esac
        fi
    fi
    log "Step 1 (Language) resolved to '$SELECTED_LANG'"
    echo "$SELECTED_LANG" > "$LANG_TXT"
else
    [ -f "$LANG_TXT" ] && SELECTED_LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')
fi

# Set localized strings for wizard steps 2 and 3 based on selected language
case "$SELECTED_LANG" in
    "es")
        TITLE_COLOR="Elegir Color de Acento"
        TITLE_DEVICE="Elige tu Consola"
        CONFIRM_NEXT="SIGUIENTE"
        CONFIRM_INSTALL="INSTALAR"
        MSG_CONF="¡Cannelloni Configurado!"
        MSG_LANG_LABEL="Idioma: Español"
        ;;
    "fr")
        TITLE_COLOR="Choisir la couleur d'accent"
        TITLE_DEVICE="Choisissez votre console"
        CONFIRM_NEXT="SUIVANT"
        CONFIRM_INSTALL="INSTALLER"
        MSG_CONF="Cannelloni configuré !"
        MSG_LANG_LABEL="Langue: Français"
        ;;
    "pt_BR")
        TITLE_COLOR="Escolha a Cor de Destaque"
        TITLE_DEVICE="Escolha seu Console"
        CONFIRM_NEXT="AVANÇAR"
        CONFIRM_INSTALL="INSTALAR"
        MSG_CONF="Cannelloni Configurado!"
        MSG_LANG_LABEL="Idioma: Português (Brasil)"
        ;;
    "de")
        TITLE_COLOR="Akzentfarbe wählen"
        TITLE_DEVICE="Wähle deine Konsole"
        CONFIRM_NEXT="WEITER"
        CONFIRM_INSTALL="INSTALLIEREN"
        MSG_CONF="Cannelloni eingerichtet!"
        MSG_LANG_LABEL="Sprache: Deutsch"
        ;;
    "it")
        TITLE_COLOR="Scegli Colore Accento"
        TITLE_DEVICE="Scegli la tua Console"
        CONFIRM_NEXT="AVANTI"
        CONFIRM_INSTALL="INSTALLA"
        MSG_CONF="Cannelloni Configurato!"
        MSG_LANG_LABEL="Lingua: Italiano"
        ;;
    *)
        TITLE_COLOR="Choose Accent Color"
        TITLE_DEVICE="Choose Your Device"
        CONFIRM_NEXT="NEXT"
        CONFIRM_INSTALL="INSTALL"
        MSG_CONF="Cannelloni Configured!"
        MSG_LANG_LABEL="Language: English"
        ;;
esac

# ----------------------------------------------------
# STEP 2: Accent Color Selection (Skip if --device-only)
# ----------------------------------------------------
SELECTED_HEX="#f1c40f"
if [ "$MODE" != "--device-only" ]; then
    CHOICE_COLOR_LIST="/tmp/color-choices.txt"
    CHOICE_COLOR_OUT="/tmp/color-choice-out.txt"
    rm -f "$CHOICE_COLOR_OUT"

    cat << 'EOF' > "$CHOICE_COLOR_LIST"
Cannelloni Gold (#f1c40f)
Tomato Red (#e74c3c)
Basil Green (#2ecc71)
Sky Blue (#3498db)
Amethyst Purple (#9b59b6)
Carrot Orange (#e67e22)
Pasta White (#ffffff)
EOF

    if [ -x "$LIST_BIN" ]; then
        "$LIST_BIN" --disable-auto-sleep --file "$CHOICE_COLOR_LIST" --format text --confirm-text "$CONFIRM_NEXT" --title "$TITLE_COLOR" --write-location "$CHOICE_COLOR_OUT"
        if [ $? -eq 0 ] && [ -f "$CHOICE_COLOR_OUT" ]; then
            CHOSEN_COLOR=$(cat "$CHOICE_COLOR_OUT" | head -n1)
            case "$CHOSEN_COLOR" in
                *"#e74c3c"*) SELECTED_HEX="#e74c3c" ;;
                *"#2ecc71"*) SELECTED_HEX="#2ecc71" ;;
                *"#3498db"*) SELECTED_HEX="#3498db" ;;
                *"#9b59b6"*) SELECTED_HEX="#9b59b6" ;;
                *"#e67e22"*) SELECTED_HEX="#e67e22" ;;
                *"#ffffff"*) SELECTED_HEX="#ffffff" ;;
                *) SELECTED_HEX="#f1c40f" ;;
            esac
        fi
    fi
    log "Step 2 (Accent Color) resolved to '$SELECTED_HEX'"
    echo "$SELECTED_HEX" > "$COLOR_TXT"

    # Immediately apply accent color assets so step 3 renders with user's selected accent theme
    APPLY_SH="$SDCARD_PATH/.system/bin/apply_accent_color.sh"
    [ ! -f "$APPLY_SH" ] && APPLY_SH="$SDCARD_PATH/.system/common/apply_accent_color.sh"
    if [ -f "$APPLY_SH" ]; then
        chmod +x "$APPLY_SH" 2>/dev/null
        "$APPLY_SH" "$SELECTED_HEX" >/dev/null 2>&1
    fi
fi

# ----------------------------------------------------
# STEP 3: Device Model Selection
# ----------------------------------------------------
CHOICE_LIST="/tmp/device-choice-list.txt"
CHOICE_OUT="/tmp/device-choice-out.txt"
rm -f "$CHOICE_OUT"

cat << 'EOF' > "$CHOICE_LIST"
Miyoo Mini (v1 / v2 / v3)
Miyoo Mini Plus (v4 / Wi-Fi)
Miyoo A30 (my282)
Miyoo Flip (my355)
TrimUI Smart
TrimUI Smart Pro
TrimUI Brick
Anbernic RG35XX (Original)
Anbernic RG35XX Plus / H / SP
Powkiddy RGB30
MagicX XU Mini M
MagicX Mini Zero 28
GKD Pixel
M17
EOF

SELECTED=""
if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$CHOICE_LIST" --format text --confirm-text "$CONFIRM_INSTALL" --title "$TITLE_DEVICE" --write-location "$CHOICE_OUT"
    RET=$?
    if [ $RET -eq 0 ] && [ -f "$CHOICE_OUT" ]; then
        SELECTED=$(cat "$CHOICE_OUT" | head -n1)
    fi
fi

# Fallback hardware detection if interactive prompt was skipped or not available
if [ -z "$SELECTED" ]; then
    INFO=$(cat /proc/cpuinfo 2> /dev/null)
    case "$INFO" in
        *"0xd05"*) SELECTED="Miyoo Flip (my355)" ;;
        *"sun8i"*)
            if [ -d /usr/miyoo ]; then
                SELECTED="Miyoo A30 (my282)"
            else
                SELECTED="TrimUI Smart"
            fi
            ;;
        *"SStar"*|*"sstar"*|*"Sigmastar"*|*"SigmaStar"*|*"SSD20"*)
            if [ -f /customer/app/axp_test ]; then
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            else
                SELECTED="Miyoo Mini (v1 / v2 / v3)"
            fi
            ;;
        *"TG5040"*|*"TG3040"*)
            TRIMUI_MODEL=$(strings /usr/trimui/bin/MainUI 2>/dev/null | grep ^Trimui)
            if [ "$TRIMUI_MODEL" = "Trimui Brick" ]; then
                SELECTED="TrimUI Brick"
            else
                SELECTED="TrimUI Smart Pro"
            fi
            ;;
        *"0xd03"*) SELECTED="MagicX Mini Zero 28" ;;
        *)
            if [ -f /customer/app/axp_test ]; then
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            elif [ -d /customer/app ]; then
                SELECTED="Miyoo Mini (v1 / v2 / v3)"
            else
                SELECTED="Miyoo Mini Plus (v4 / Wi-Fi)"
            fi
            ;;
    esac
fi

log "Step 3 (Device Model) resolved to '$SELECTED'"
echo "$SELECTED" > "$DEVICE_TXT"

TARGET_PLATFORM="miyoomini"
TARGET_DEVICE=""

case "$SELECTED" in
    *"Miyoo Mini Plus"*)
        TARGET_PLATFORM="miyoomini"
        TARGET_DEVICE="plus"
        mkdir -p "$SDCARD_PATH/.userdata/$TARGET_PLATFORM"
        touch "$SDCARD_PATH/.userdata/$TARGET_PLATFORM/.is_plus"
        ;;
    *"Miyoo Mini ("*)
        TARGET_PLATFORM="miyoomini"
        TARGET_DEVICE="mini"
        rm -f "$SDCARD_PATH/.userdata/$TARGET_PLATFORM/.is_plus"
        ;;
    *"Miyoo A30"*)
        TARGET_PLATFORM="my282"
        TARGET_DEVICE="my282"
        ;;
    *"Miyoo Flip"*)
        TARGET_PLATFORM="my355"
        TARGET_DEVICE="my355"
        ;;
    *"TrimUI Smart Pro"*)
        TARGET_PLATFORM="tg5040"
        TARGET_DEVICE="tg5040"
        ;;
    *"TrimUI Brick"*)
        TARGET_PLATFORM="tg5040"
        TARGET_DEVICE="brick"
        ;;
    *"TrimUI Smart"*)
        TARGET_PLATFORM="trimuismart"
        TARGET_DEVICE="smart"
        ;;
    *"Anbernic RG35XX Plus"*)
        TARGET_PLATFORM="rg35xxplus"
        TARGET_DEVICE="rg35xxplus"
        ;;
    *"Anbernic RG35XX ("*)
        TARGET_PLATFORM="rg35xx"
        TARGET_DEVICE="rg35xx"
        ;;
    *"Powkiddy RGB30"*)
        TARGET_PLATFORM="rgb30"
        TARGET_DEVICE="rgb30"
        ;;
    *"MagicX XU Mini M"*)
        TARGET_PLATFORM="magicmini"
        TARGET_DEVICE="magicmini"
        ;;
    *"MagicX Mini Zero 28"*)
        TARGET_PLATFORM="zero28"
        TARGET_DEVICE="zero28"
        ;;
    *"GKD Pixel"*)
        TARGET_PLATFORM="gkdpixel"
        TARGET_DEVICE="gkdpixel"
        ;;
    *"M17"*)
        TARGET_PLATFORM="m17"
        TARGET_DEVICE="m17"
        ;;
esac

echo "$TARGET_PLATFORM" > "$SHARED_DIR/platform.txt"
[ -n "$TARGET_DEVICE" ] && echo "$TARGET_DEVICE" > "$SHARED_DIR/device.txt"
log "Configured platform='$TARGET_PLATFORM', device='$TARGET_DEVICE'"

# Configure boot splash and dat assets for the selected hardware
BOOT_DIR="$SDCARD_PATH/.system/$TARGET_PLATFORM/dat"
if [ -d "$BOOT_DIR" ]; then
    mkdir -p "$SDCARD_PATH/.system/dat"
    cp -f "$BOOT_DIR/"* "$SDCARD_PATH/.system/dat/" 2>/dev/null
    log "Copied boot splash assets from $BOOT_DIR"
fi

# Run platform install finish script if available
if [ -f "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" ]; then
    chmod +x "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" 2>/dev/null
    log "Executing $SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh..."
    "$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/install.sh" >> "$LOG_FILE" 2>&1
    log "install.sh finished with code $?"
fi

# Apply accent color binaries to newly selected target platform
CURR_COLOR="$SELECTED_HEX"
[ -f "$COLOR_TXT" ] && CURR_COLOR=$(cat "$COLOR_TXT" | head -n1 | tr -d '\r\n')
APPLY_SH="$SDCARD_PATH/.system/bin/apply_accent_color.sh"
[ ! -f "$APPLY_SH" ] && APPLY_SH="$SDCARD_PATH/.system/common/apply_accent_color.sh"
if [ -f "$APPLY_SH" ]; then
    chmod +x "$APPLY_SH" 2>/dev/null
    log "Applying accent color '$CURR_COLOR'..."
    "$APPLY_SH" "$CURR_COLOR" >> "$LOG_FILE" 2>&1
fi

log "Wizard configuration complete: Device='$SELECTED', Language='$SELECTED_LANG', Accent='$CURR_COLOR'"

cleanup_bootstrap() {
    PLAT="$1"
    log "Performing post-installation cleanup for platform '$PLAT'..."
    
    # Always remove update zip files
    rm -f "$SDCARD_PATH"/Cannelloni*.zip "$SDCARD_PATH"/cannelloni*.zip "$SDCARD_PATH"/MinUI*.zip 2>/dev/null
    rm -rf "$SDCARD_PATH/.tmp_update-old" 2>/dev/null
    
    # Remove bootstrap files and folders not belonging to the chosen platform
    case "$PLAT" in
        "miyoomini")
            # Keep miyoo and miyoo354
            rm -rf "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" "$SDCARD_PATH/rg35xxplus" \
                   "$SDCARD_PATH/gkdpixel" "$SDCARD_PATH/magicx" "$SDCARD_PATH/miyoo285" \
                   "$SDCARD_PATH/miyoo355" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "my282")
            # Miyoo A30
            rm -rf "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" "$SDCARD_PATH/rg35xxplus" \
                   "$SDCARD_PATH/gkdpixel" "$SDCARD_PATH/magicx" "$SDCARD_PATH/miyoo285" \
                   "$SDCARD_PATH/miyoo355" "$SDCARD_PATH/miyoo354" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "my355")
            # Miyoo Flip
            rm -rf "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" "$SDCARD_PATH/rg35xxplus" \
                   "$SDCARD_PATH/gkdpixel" "$SDCARD_PATH/magicx" "$SDCARD_PATH/miyoo285" \
                   "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "tg5040"|"trimuismart")
            # TrimUI
            rm -rf "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" "$SDCARD_PATH/miyoo355" \
                   "$SDCARD_PATH/miyoo285" "$SDCARD_PATH/rg35xx" "$SDCARD_PATH/rg35xxplus" \
                   "$SDCARD_PATH/gkdpixel" "$SDCARD_PATH/magicx" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "rg35xx"|"rg35xxplus")
            # Anbernic
            rm -rf "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" "$SDCARD_PATH/miyoo355" \
                   "$SDCARD_PATH/miyoo285" "$SDCARD_PATH/trimui" "$SDCARD_PATH/gkdpixel" \
                   "$SDCARD_PATH/magicx" 2>/dev/null
            rm -f "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "gkdpixel")
            rm -rf "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" "$SDCARD_PATH/miyoo355" \
                   "$SDCARD_PATH/miyoo285" "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" \
                   "$SDCARD_PATH/rg35xxplus" "$SDCARD_PATH/magicx" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
        "m17")
            rm -rf "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" "$SDCARD_PATH/miyoo355" \
                   "$SDCARD_PATH/miyoo285" "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" \
                   "$SDCARD_PATH/rg35xxplus" "$SDCARD_PATH/gkdpixel" "$SDCARD_PATH/magicx" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" 2>/dev/null
            ;;
        "magicmini"|"zero28")
            rm -rf "$SDCARD_PATH/miyoo" "$SDCARD_PATH/miyoo354" "$SDCARD_PATH/miyoo355" \
                   "$SDCARD_PATH/miyoo285" "$SDCARD_PATH/trimui" "$SDCARD_PATH/rg35xx" \
                   "$SDCARD_PATH/rg35xxplus" "$SDCARD_PATH/gkdpixel" 2>/dev/null
            rm -f "$SDCARD_PATH/dmenu.bin" "$SDCARD_PATH/em_ui.sh" 2>/dev/null
            ;;
    esac
    log "Cleanup of unnecessary bootstrap folders complete."
    sync
}

if [ "$MODE" != "--device-only" ]; then
    cleanup_bootstrap "$TARGET_PLATFORM"
fi

SAY="$SDCARD_PATH/.system/$TARGET_PLATFORM/bin/say.elf"
[ ! -x "$SAY" ] && SAY="say.elf"
if [ -x "$SAY" ] || command -v say.elf >/dev/null 2>&1; then
    log "Displaying completion confirmation screen..."
    $SAY "$MSG_CONF
Device: $SELECTED
$MSG_LANG_LABEL
Accent: $CURR_COLOR
Starting Cannelloni..." &
    SAY_PID=$!
    sleep 3
    kill -9 $SAY_PID 2>/dev/null
fi

log "=== device_select.sh finished successfully ==="
