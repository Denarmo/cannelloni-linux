import os

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

script_content = """#!/bin/sh

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
[ -f "$LANG_TXT" ] && CURRENT_LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\\r\\n')

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

CONFIRM_BTN="SELECT"
case "$CURRENT_LANG" in
    "es") CONFIRM_BTN="SELECCIONAR" ;;
    "fr") CONFIRM_BTN="SÉLECTIONNER" ;;
    "de") CONFIRM_BTN="AUSWÄHLEN" ;;
    "it") CONFIRM_BTN="SELEZIONA" ;;
    "pt_BR") CONFIRM_BTN="SELECIONAR" ;;
esac

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$LIST_FILE" --format text --confirm-text "$CONFIRM_BTN" --title "Language / Idioma" --write-location "$OUT_FILE"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$OUT_FILE" ]; then
        exit 0
    fi
    CHOICE=$(cat "$OUT_FILE" | head -n1)
else
    CHOICE="English"
fi

CODE="en"
MSG="Language set to English!"

case "$CHOICE" in
    *"Español"*)
        CODE="es"
        MSG="¡Idioma configurado a Español!"
        ;;
    *"Français"*)
        CODE="fr"
        MSG="Langue configurée sur Français !"
        ;;
    *"Português"*)
        CODE="pt_BR"
        MSG="Idioma definido para Português (Brasil)!"
        ;;
    *"Deutsch"*)
        CODE="de"
        MSG="Sprache auf Deutsch eingestellt!"
        ;;
    *"Italiano"*)
        CODE="it"
        MSG="Lingua impostata su Italiano!"
        ;;
    *)
        CODE="en"
        MSG="Language set to English!"
        ;;
esac

echo "$CODE" > "$LANG_TXT"
sync

# Dynamically apply language and rename paks immediately
APPLY_LANG="$SDCARD_PATH/.system/common/apply_language.sh"
[ ! -f "$APPLY_LANG" ] && APPLY_LANG="$SDCARD_PATH/.system/$PLATFORM/bin/apply_language.sh"
if [ -f "$APPLY_LANG" ]; then
    chmod +x "$APPLY_LANG" 2>/dev/null
    "$APPLY_LANG" "$CODE"
fi
sync

if [ -x "$SAY" ]; then
    $SAY "$MSG"
fi
sync
"""

for p in platforms:
    p_dir = f'skeleton/EXTRAS/Settings/{p}/Language.pak'
    os.makedirs(p_dir, exist_ok=True)
    launch_path = os.path.join(p_dir, 'launch.sh')
    with open(launch_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(script_content)
    # Ensure .pak_id is present
    with open(os.path.join(p_dir, '.pak_id'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('language\n')
    print(f'Updated Language.pak for {p}')
