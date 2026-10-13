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

MAP_FILE="$SDCARD_PATH/.userdata/shared/.cannelloni/button_swap.txt"
LANG_TXT="$SDCARD_PATH/.userdata/shared/.cannelloni/language.txt"
mkdir -p "$(dirname "$MAP_FILE")"

CURRENT="default"
[ -f "$MAP_FILE" ] && CURRENT=$(cat "$MAP_FILE" | head -n1 | tr -d '\r\n')

LANG="en"
[ -f "$LANG_TXT" ] && LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')

TITLE="Button Mapping"
BTN="SELECT"
MSG_DEFAULT="Buttons mapped to Nintendo Layout!\n(A: Confirm, B: Cancel)"
MSG_SWAPPED="Buttons mapped to Swapped Layout!\n(B: Confirm, A: Cancel)"

LIST_FILE="/tmp/button-map-list.txt"
OUT_FILE="/tmp/button-map-choice.txt"
rm -f "$OUT_FILE"

case "$LANG" in
    "es")
        TITLE="Mapeo de Botones"
        BTN="SELECCIONAR"
        MSG_DEFAULT="¡Botones configurados a Distribución Nintendo!\n(A: Confirmar, B: Cancelar)"
        MSG_SWAPPED="¡Botones configurados a Distribución Invertida!\n(B: Confirmar, A: Cancelar)"
        cat << 'EOF' > "$LIST_FILE"
Distribución Nintendo (A: Confirmar, B: Cancelar)
Distribución Invertida (B: Confirmar, A: Cancelar)
EOF
        ;;
    "fr")
        TITLE="Disposition des Boutons"
        BTN="SÉLECTIONNER"
        MSG_DEFAULT="Boutons configurés sur Disposition Nintendo !\n(A : Confirmer, B : Annuler)"
        MSG_SWAPPED="Boutons configurés sur Disposition Inversée !\n(B : Confirmer, A : Annuler)"
        cat << 'EOF' > "$LIST_FILE"
Disposition Nintendo (A: Confirmer, B: Annuler)
Disposition Inversée (B: Confirmer, A: Annuler)
EOF
        ;;
    "pt_BR")
        TITLE="Mapeamento de Botões"
        BTN="SELECIONAR"
        MSG_DEFAULT="Botões mapeados para Layout Nintendo!\n(A: Confirmar, B: Cancelar)"
        MSG_SWAPPED="Botões mapeados para Layout Invertido!\n(B: Confirmar, A: Cancelar)"
        cat << 'EOF' > "$LIST_FILE"
Layout Nintendo (A: Confirmar, B: Cancelar)
Layout Invertido (B: Confirmar, A: Cancelar)
EOF
        ;;
    "de")
        TITLE="Tastenbelegung"
        BTN="AUSWÄHLEN"
        MSG_DEFAULT="Tasten auf Nintendo-Layout eingestellt!\n(A: Bestätigen, B: Abbrechen)"
        MSG_SWAPPED="Tasten auf Vertauschtes Layout eingestellt!\n(B: Bestätigen, A: Abbrechen)"
        cat << 'EOF' > "$LIST_FILE"
Nintendo-Layout (A: Bestätigen, B: Abbrechen)
Vertauschtes Layout (B: Bestätigen, A: Abbrechen)
EOF
        ;;
    "it")
        TITLE="Mappatura Pulsanti"
        BTN="SELEZIONA"
        MSG_DEFAULT="Pulsanti mappati su Layout Nintendo!\n(A: Conferma, B: Annulla)"
        MSG_SWAPPED="Pulsanti mappati su Layout Invertito!\n(B: Conferma, A: Annulla)"
        cat << 'EOF' > "$LIST_FILE"
Layout Nintendo (A: Conferma, B: Annulla)
Layout Invertito (B: Conferma, A: Annulla)
EOF
        ;;
    *)
        cat << 'EOF' > "$LIST_FILE"
Nintendo Layout (A: Confirm, B: Cancel)
Swapped Layout (B: Confirm, A: Cancel, Y: North, X: West)
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
    CHOICE="Nintendo Layout"
fi

case "$CHOICE" in
    *"Swapped"*|*"Invertida"*|*"Inversée"*|*"Invertido"*|*"Vertauschtes"*)
        echo "swapped" > "$MAP_FILE"
        MSG="$MSG_SWAPPED"
        ;;
    *)
        echo "default" > "$MAP_FILE"
        MSG="$MSG_DEFAULT"
        ;;
esac
sync

if [ -x "$SAY" ]; then
    $SAY "$MSG"
fi
sync
