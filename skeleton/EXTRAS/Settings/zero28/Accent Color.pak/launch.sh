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

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
COLOR_FILE="$SHARED_DIR/accent_color.txt"
CURRENT_FILE="$SHARED_DIR/.current_accent"
LANG_TXT="$SHARED_DIR/language.txt"
mkdir -p "$SHARED_DIR"

CURRENT="#f1c40f"
[ -f "$COLOR_FILE" ] && CURRENT=$(cat "$COLOR_FILE" | head -n1 | tr -d '\r\n')

LANG="en"
[ -f "$LANG_TXT" ] && LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')

LIST_FILE="/tmp/accent-color-list.txt"
OUT_FILE="/tmp/accent-color-choice.txt"
rm -f "$OUT_FILE"

TITLE="Accent Color"
BTN="SELECT"
MSG_SUCCESS="Applied accent color successfully!"

case "$LANG" in
    "es")
        TITLE="Color de Acento"
        BTN="SELECCIONAR"
        MSG_SUCCESS="¡Color de acento aplicado con éxito!"
        cat << 'EOF' > "$LIST_FILE"
Oro Cannelloni (#f1c40f)
Rojo Tomate (#e74c3c)
Verde Albahaca (#2ecc71)
Azul Cielo (#3498db)
Púrpura Amatista (#9b59b6)
Naranja Zanahoria (#e67e22)
Blanco Pasta (#ffffff)
EOF
        ;;
    "fr")
        TITLE="Couleur d'accent"
        BTN="SÉLECTIONNER"
        MSG_SUCCESS="Couleur d'accent appliquée avec succès !"
        cat << 'EOF' > "$LIST_FILE"
Or Cannelloni (#f1c40f)
Rouge Tomate (#e74c3c)
Vert Basilic (#2ecc71)
Bleu Ciel (#3498db)
Violet Améthyste (#9b59b6)
Orange Carotte (#e67e22)
Blanc Pâte (#ffffff)
EOF
        ;;
    "pt_BR")
        TITLE="Cor de Destaque"
        BTN="SELECIONAR"
        MSG_SUCCESS="Cor de destaque aplicada com sucesso!"
        cat << 'EOF' > "$LIST_FILE"
Ouro Cannelloni (#f1c40f)
Vermelho Tomate (#e74c3c)
Verde Manjericão (#2ecc71)
Azul Céu (#3498db)
Roxo Ametista (#9b59b6)
Laranja Cenoura (#e67e22)
Branco Massa (#ffffff)
EOF
        ;;
    "de")
        TITLE="Akzentfarbe"
        BTN="AUSWÄHLEN"
        MSG_SUCCESS="Akzentfarbe erfolgreich angewendet!"
        cat << 'EOF' > "$LIST_FILE"
Cannelloni-Gold (#f1c40f)
Tomatenrot (#e74c3c)
Basilikumgrün (#2ecc71)
Himmelblau (#3498db)
Amethystviolett (#9b59b6)
Karottenorange (#e67e22)
Nudelweiß (#ffffff)
EOF
        ;;
    "it")
        TITLE="Colore d'accento"
        BTN="SELEZIONA"
        MSG_SUCCESS="Colore d'accento applicato con successo!"
        cat << 'EOF' > "$LIST_FILE"
Oro Cannelloni (#f1c40f)
Rosso Pomodoro (#e74c3c)
Verde Basilico (#2ecc71)
Blu Cielo (#3498db)
Viola Ametista (#9b59b6)
Arancione Carota (#e67e22)
Bianco Pasta (#ffffff)
EOF
        ;;
    *)
        cat << 'EOF' > "$LIST_FILE"
Cannelloni Gold (#f1c40f)
Tomato Red (#e74c3c)
Basil Green (#2ecc71)
Sky Blue (#3498db)
Amethyst Purple (#9b59b6)
Carrot Orange (#e67e22)
Pasta White (#ffffff)
EOF
        ;;
esac

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$LIST_FILE" --format text --confirm-text "$BTN" --title "$TITLE" --write-location "$OUT_FILE"
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
    *)           HEX="#f1c40f" ;;
esac

echo "$HEX" > "$COLOR_FILE"

APPLY_SH="$SDCARD_PATH/.system/common/apply_accent_color.sh"
[ ! -f "$APPLY_SH" ] && APPLY_SH="$SDCARD_PATH/.system/$PLATFORM/bin/apply_accent_color.sh"
if [ -f "$APPLY_SH" ]; then
    chmod +x "$APPLY_SH" 2>/dev/null
    "$APPLY_SH" "$HEX"
fi
sync

if [ -x "$SAY" ]; then
    $SAY "$MSG_SUCCESS
$HEX"
fi
sync
