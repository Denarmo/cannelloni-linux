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

CFG_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$CFG_DIR"
LANG_TXT="$CFG_DIR/language.txt"

LANG="en"
[ -f "$LANG_TXT" ] && LANG=$(cat "$LANG_TXT" | head -n1 | tr -d '\\r\\n')

TITLE_MAIN="Configure Console"
BTN="SELECT"

case "$LANG" in
    "es") TITLE_MAIN="Configurar Consola"; BTN="SELECCIONAR" ;;
    "fr") TITLE_MAIN="Configurer la Console"; BTN="SÉLECTIONNER" ;;
    "pt_BR") TITLE_MAIN="Configurar Console"; BTN="SELECIONAR" ;;
    "de") TITLE_MAIN="Konsole Konfigurieren"; BTN="AUSWÄHLEN" ;;
    "it") TITLE_MAIN="Configura Console"; BTN="SELEZIONA" ;;
esac

CONSOLE_LIST="/tmp/emu-console-list.txt"
CONSOLE_OUT="/tmp/emu-console-choice.txt"
rm -f "$CONSOLE_OUT"

cat << 'EOF' > "$CONSOLE_LIST"
Nintendo DS (NDS)
EOF

if [ -x "$LIST_BIN" ]; then
    "$LIST_BIN" --disable-auto-sleep --file "$CONSOLE_LIST" --format text --confirm-text "$BTN" --title "$TITLE_MAIN" --write-location "$CONSOLE_OUT"
    RET=$?
    if [ $RET -ne 0 ] || [ ! -f "$CONSOLE_OUT" ]; then
        exit 0
    fi
    CONSOLE_CHOICE=$(cat "$CONSOLE_OUT" | head -n1)
else
    CONSOLE_CHOICE="Nintendo DS (NDS)"
fi

case "$CONSOLE_CHOICE" in
    *"Nintendo DS"*)
        NDS_CFG="$CFG_DIR/emu_nds.txt"
        NDS_LIST="/tmp/nds-choice-list.txt"
        NDS_OUT="/tmp/nds-choice-out.txt"
        rm -f "$NDS_OUT"

        TITLE_NDS="Nintendo DS Emulator"
        MSG_LIB="Nintendo DS emulator set to Libretro core!"
        MSG_DRA="Nintendo DS emulator set to Standalone DraStic!"

        case "$LANG" in
            "es")
                TITLE_NDS="Emulador Nintendo DS"
                MSG_LIB="¡Emulador Nintendo DS configurado a Núcleo Libretro!"
                MSG_DRA="¡Emulador Nintendo DS configurado a DraStic Independiente!"
                cat << 'EOF' > "$NDS_LIST"
Núcleo Libretro (Menú y Guardado)
DraStic Independiente (Máxima Velocidad)
EOF
                ;;
            "fr")
                TITLE_NDS="Émulateur Nintendo DS"
                MSG_LIB="Émulateur Nintendo DS configuré sur Cœur Libretro !"
                MSG_DRA="Émulateur Nintendo DS configuré sur DraStic Autonome !"
                cat << 'EOF' > "$NDS_LIST"
Cœur Libretro (Menu et Sauvegardes)
DraStic Autonome (Vitesse Maximale)
EOF
                ;;
            "pt_BR")
                TITLE_NDS="Emulador Nintendo DS"
                MSG_LIB="Emulador Nintendo DS definido para Núcleo Libretro!"
                MSG_DRA="Emulador Nintendo DS definido para DraStic Autônomo!"
                cat << 'EOF' > "$NDS_LIST"
Núcleo Libretro (Menu e Salvamento)
DraStic Autônomo (Velocidade Máxima)
EOF
                ;;
            "de")
                TITLE_NDS="Nintendo DS Emulator"
                MSG_LIB="Nintendo DS Emulator auf Libretro-Core eingestellt!"
                MSG_DRA="Nintendo DS Emulator auf Eigenständiges DraStic eingestellt!"
                cat << 'EOF' > "$NDS_LIST"
Libretro-Core (Menü und Speichern)
Eigenständiges DraStic (Maximale Leistung)
EOF
                ;;
            "it")
                TITLE_NDS="Emulatore Nintendo DS"
                MSG_LIB="Emulatore Nintendo DS impostato su Core Libretro!"
                MSG_DRA="Emulatore Nintendo DS impostato su DraStic Autonomo!"
                cat << 'EOF' > "$NDS_LIST"
Core Libretro (Menu e Salvataggi)
DraStic Autonomo (Massima Velocità)
EOF
                ;;
            *)
                cat << 'EOF' > "$NDS_LIST"
Libretro Core (Menu & Save States)
Standalone DraStic (Full Speed)
EOF
                ;;
        esac

        if [ -x "$LIST_BIN" ]; then
            "$LIST_BIN" --disable-auto-sleep --file "$NDS_LIST" --format text --confirm-text "$BTN" --title "$TITLE_NDS" --write-location "$NDS_OUT"
            RET=$?
            if [ $RET -ne 0 ] || [ ! -f "$NDS_OUT" ]; then
                exit 0
            fi
            CHOICE=$(cat "$NDS_OUT" | head -n1)
        else
            CHOICE="Libretro"
        fi

        case "$CHOICE" in
            *"DraStic"*|*"Drastic"*)
                echo "drastic-standalone" > "$NDS_CFG"
                MSG="$MSG_DRA"
                ;;
            *)
                echo "libretro" > "$NDS_CFG"
                MSG="$MSG_LIB"
                ;;
        esac
        sync

        if [ -x "$SAY" ]; then
            $SAY "$MSG"
        fi
        sync
        ;;
esac
"""

for p in platforms:
    p_dir = f'skeleton/EXTRAS/Settings/{p}/Emulators.pak'
    os.makedirs(p_dir, exist_ok=True)
    launch_path = os.path.join(p_dir, 'launch.sh')
    with open(launch_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(script_content)
    with open(os.path.join(p_dir, '.pak_id'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('emulators\n')
    print(f'Updated Emulators.pak for {p}')
