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
mkdir -p "$SHARED_DIR"
LANG_TXT="$SHARED_DIR/language.txt"

CURRENT_LANG="en"
[ -f "$LANG_TXT" ] && CURRENT_LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')

LIST_FILE="/tmp/lang-choice-list.txt"
OUT_FILE="/tmp/lang-choice-out.txt"
rm -f "$OUT_FILE"

cat << 'EOF' > "$LIST_FILE"
English
Español (Spanish)
Français (French)
Português (Brasil)
Deutsch (German)
Italiano (Italian)
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$LIST_FILE" --format text --confirm-text "SELECT" --title "Language / Idioma" --write-location "$OUT_FILE"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$OUT_FILE" ]; then
        exit 0
    fi
    CHOICE=$(cat "$OUT_FILE" | head -n1)
else
    CHOICE="English"
fi

CODE="en"
MSG="Language set to English!
Restarting interface..."

case "$CHOICE" in
    *"Español"*)
        CODE="es"
        MSG="¡Idioma configurado a Español!
Reiniciando interfaz..."
        ;;
    *"Français"*)
        CODE="fr"
        MSG="Langue définie sur Français !
Redémarrage de l'interface..."
        ;;
    *"Português"*)
        CODE="pt_BR"
        MSG="Idioma definido para Português (Brasil)!
Reiniciando interface..."
        ;;
    *"Deutsch"*)
        CODE="de"
        MSG="Sprache auf Deutsch eingestellt!
Benutzeroberfläche wird neu gestartet..."
        ;;
    *"Italiano"*)
        CODE="it"
        MSG="Lingua impostata su Italiano!
Riavvio dell'interfaccia..."
        ;;
    *)
        CODE="en"
        MSG="Language set to English!
Restarting interface..."
        ;;
esac

echo "$CODE" > "$LANG_TXT"
sync

$SAY "$MSG"
sync
