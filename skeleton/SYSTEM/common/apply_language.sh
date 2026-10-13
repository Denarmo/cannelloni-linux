#!/bin/sh

# apply_language.sh [LANG_CODE]
# Dynamically renames Settings and Tools paks, updates map.txt, and configures UI localization.

[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"

SHARED_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
mkdir -p "$SHARED_DIR"
LANG_TXT="$SHARED_DIR/language.txt"

CODE="$1"
[ -z "$CODE" ] && [ -f "$LANG_TXT" ] && CODE=$(cat "$LANG_TXT" | head -n1 | tr -d '\r\n')
[ -z "$CODE" ] && CODE="en"

case "$CODE" in
    *"es"*|*"ES"*|*"spanish"*|*"Spanish"*) CODE="es" ;;
    *"fr"*|*"FR"*|*"french"*|*"French"*)   CODE="fr" ;;
    *"pt"*|*"PT"*|*"portuguese"*|*"Portuguese"*) CODE="pt_BR" ;;
    *"de"*|*"DE"*|*"german"*|*"German"*)   CODE="de" ;;
    *"it"*|*"IT"*|*"italian"*|*"Italian"*) CODE="it" ;;
    *)                                     CODE="en" ;;
esac

echo "$CODE" > "$LANG_TXT"
sync

get_setting_name() {
    ID="$1"
    case "$ID" in
        "accent_color")
            case "$CODE" in
                "es") echo "Color de Acento" ;;
                "fr") echo "Couleur d'accent" ;;
                "pt_BR") echo "Cor de Destaque" ;;
                "de") echo "Akzentfarbe" ;;
                "it") echo "Colore d'accento" ;;
                *)    echo "Accent Color" ;;
            esac
            ;;
        "button_mapping")
            case "$CODE" in
                "es") echo "Mapeo de Botones" ;;
                "fr") echo "Disposition des Boutons" ;;
                "pt_BR") echo "Mapeamento de Botões" ;;
                "de") echo "Tastenbelegung" ;;
                "it") echo "Mappatura Pulsanti" ;;
                *)    echo "Button Mapping" ;;
            esac
            ;;
        "device_model")
            case "$CODE" in
                "es") echo "Modelo de Consola" ;;
                "fr") echo "Modèle de Console" ;;
                "pt_BR") echo "Modelo do Dispositivo" ;;
                "de") echo "Gerätemodell" ;;
                "it") echo "Modello Dispositivo" ;;
                *)    echo "Device Model" ;;
            esac
            ;;
        "emulators")
            case "$CODE" in
                "es"|"pt_BR") echo "Emuladores" ;;
                "fr") echo "Émulateurs" ;;
                "de") echo "Emulatoren" ;;
                "it") echo "Emulatori" ;;
                *)    echo "Emulators" ;;
            esac
            ;;
        "language")
            case "$CODE" in
                "es"|"pt_BR") echo "Idioma" ;;
                "fr") echo "Langue" ;;
                "de") echo "Sprache" ;;
                "it") echo "Lingua" ;;
                *)    echo "Language" ;;
            esac
            ;;
        "shaders")
            case "$CODE" in
                "es") echo "Shaders" ;;
                "fr") echo "Shaders" ;;
                "de") echo "Shader" ;;
                "it") echo "Shader" ;;
                *)    echo "Shaders" ;;
            esac
            ;;
        "wifi")
            echo "Wi-Fi"
            ;;
    esac
}

get_tool_name() {
    ID="$1"
    case "$ID" in
        "clock")
            case "$CODE" in
                "es") echo "Reloj" ;;
                "fr") echo "Horloge" ;;
                "pt_BR") echo "Relógio" ;;
                "de") echo "Uhr" ;;
                "it") echo "Orologio" ;;
                *)    echo "Clock" ;;
            esac
            ;;
        "files")
            case "$CODE" in
                "es") echo "Archivos" ;;
                "fr") echo "Fichiers" ;;
                "pt_BR") echo "Arquivos" ;;
                "de") echo "Dateien" ;;
                "it") echo "File" ;;
                *)    echo "Files" ;;
            esac
            ;;
        "input")
            case "$CODE" in
                "es") echo "Controles" ;;
                "fr") echo "Contrôles" ;;
                "pt_BR") echo "Controles" ;;
                "de") echo "Steuerung" ;;
                "it") echo "Controlli" ;;
                *)    echo "Input" ;;
            esac
            ;;
        "bootlogo")
            case "$CODE" in
                "es") echo "Logo de Arranque" ;;
                "fr") echo "Logo de Démarrage" ;;
                "pt_BR") echo "Logo de Inicialização" ;;
                "de") echo "Bootlogo" ;;
                "it") echo "Logo di Avvio" ;;
                *)    echo "Bootlogo" ;;
            esac
            ;;
        "kitchen")
            echo "Nonna's Kitchen"
            ;;
    esac
}

# 1. Update Settings map.txt and pak directories across all platforms
TXT_ACCENT=$(get_setting_name "accent_color")
TXT_BUTTON=$(get_setting_name "button_mapping")
TXT_DEVICE=$(get_setting_name "device_model")
TXT_EMU=$(get_setting_name "emulators")
TXT_LANG=$(get_setting_name "language")
TXT_SHADER=$(get_setting_name "shaders")
TXT_WIFI=$(get_setting_name "wifi")

for s_dir in "$SDCARD_PATH/Settings"/*; do
    [ ! -d "$s_dir" ] && continue
    MAP_FILE="$s_dir/map.txt"
    
    # Write full bidirectional mapping into map.txt
    cat << EOF > "$MAP_FILE"
Accent Color.pak	$TXT_ACCENT
Color de Acento.pak	$TXT_ACCENT
Couleur d'accent.pak	$TXT_ACCENT
Cor de Destaque.pak	$TXT_ACCENT
Akzentfarbe.pak	$TXT_ACCENT
Colore d'accento.pak	$TXT_ACCENT
Button Mapping.pak	$TXT_BUTTON
Mapeo de Botones.pak	$TXT_BUTTON
Disposition des Boutons.pak	$TXT_BUTTON
Mapeamento de Botões.pak	$TXT_BUTTON
Tastenbelegung.pak	$TXT_BUTTON
Mappatura Pulsanti.pak	$TXT_BUTTON
Device Model.pak	$TXT_DEVICE
Modelo de Consola.pak	$TXT_DEVICE
Modèle de Console.pak	$TXT_DEVICE
Modelo do Dispositivo.pak	$TXT_DEVICE
Gerätemodell.pak	$TXT_DEVICE
Modello Dispositivo.pak	$TXT_DEVICE
Emulators.pak	$TXT_EMU
Emuladores.pak	$TXT_EMU
Émulateurs.pak	$TXT_EMU
Emulatoren.pak	$TXT_EMU
Emulatori.pak	$TXT_EMU
Language.pak	$TXT_LANG
Idioma.pak	$TXT_LANG
Langue.pak	$TXT_LANG
Sprache.pak	$TXT_LANG
Lingua.pak	$TXT_LANG
Shaders.pak	$TXT_SHADER
Shader.pak	$TXT_SHADER
Wi-Fi.pak	$TXT_WIFI
Wifi.pak	$TXT_WIFI
EOF

    # If directories were previously renamed to another language, normalize them back to English
    for pak in "$s_dir"/*.pak; do
        [ ! -d "$pak" ] && continue
        PAK_NAME=$(basename "$pak")
        TARGET_CANONICAL=""
        case "$PAK_NAME" in
            *"Accent"*|*"Acento"*|*"Akzent"*|*"accent"*) TARGET_CANONICAL="Accent Color.pak" ;;
            *"Button"*|*"Botones"*|*"Boutons"*|*"Tasten"*|*"Pulsanti"*|*"Botões"*) TARGET_CANONICAL="Button Mapping.pak" ;;
            *"Device"*|*"Consola"*|*"Console"*|*"Gerät"*|*"Dispositivo"*) TARGET_CANONICAL="Device Model.pak" ;;
            *"Emulator"*|*"Émulateur"*|*"Emulador"*) TARGET_CANONICAL="Emulators.pak" ;;
            *"Language"*|*"Idioma"*|*"Langue"*|*"Sprache"*|*"Lingua"*) TARGET_CANONICAL="Language.pak" ;;
            *"Shader"*) TARGET_CANONICAL="Shaders.pak" ;;
            *"Wi-Fi"*|*"Wifi"*|*"WiFi"*) TARGET_CANONICAL="Wi-Fi.pak" ;;
        esac
        if [ -n "$TARGET_CANONICAL" ] && [ "$PAK_NAME" != "$TARGET_CANONICAL" ]; then
            TARGET_PATH="$s_dir/$TARGET_CANONICAL"
            [ ! -d "$TARGET_PATH" ] && mv "$pak" "$TARGET_PATH" 2>/dev/null
        fi
    done
done

# 2. Update Tools map.txt across all platforms
TXT_CLOCK=$(get_tool_name "clock")
TXT_FILES=$(get_tool_name "files")
TXT_INPUT=$(get_tool_name "input")
TXT_LOGO=$(get_tool_name "bootlogo")
TXT_KITCHEN=$(get_tool_name "kitchen")

for t_dir in "$SDCARD_PATH/Tools"/*; do
    [ ! -d "$t_dir" ] && continue
    MAP_FILE="$t_dir/map.txt"
    
    cat << EOF > "$MAP_FILE"
Clock.pak	$TXT_CLOCK
Reloj.pak	$TXT_CLOCK
Horloge.pak	$TXT_CLOCK
Relógio.pak	$TXT_CLOCK
Uhr.pak	$TXT_CLOCK
Orologio.pak	$TXT_CLOCK
Files.pak	$TXT_FILES
Archivos.pak	$TXT_FILES
Fichiers.pak	$TXT_FILES
Arquivos.pak	$TXT_FILES
Dateien.pak	$TXT_FILES
File.pak	$TXT_FILES
Input.pak	$TXT_INPUT
Controles.pak	$TXT_INPUT
Contrôles.pak	$TXT_INPUT
Steuerung.pak	$TXT_INPUT
Controlli.pak	$TXT_INPUT
Bootlogo.pak	$TXT_LOGO
Logo de Arranque.pak	$TXT_LOGO
Logo de Démarrage.pak	$TXT_LOGO
Logo de Inicialização.pak	$TXT_LOGO
Logo di Avvio.pak	$TXT_LOGO
Nonna's Kitchen.pak	$TXT_KITCHEN
EOF

    for pak in "$t_dir"/*.pak; do
        [ ! -d "$pak" ] && continue
        PAK_NAME=$(basename "$pak")
        TARGET_CANONICAL=""
        case "$PAK_NAME" in
            *"Clock"*|*"Reloj"*|*"Horloge"*|*"Uhr"*|*"Orologio"*|*"Relógio"*) TARGET_CANONICAL="Clock.pak" ;;
            *"File"*|*"Archivo"*|*"Fichier"*|*"Datei"*|*"Arquivo"*) TARGET_CANONICAL="Files.pak" ;;
            *"Input"*|*"Control"*|*"Steuerung"*|*"Contrôle"*) TARGET_CANONICAL="Input.pak" ;;
            *"Bootlogo"*|*"Logo"*) TARGET_CANONICAL="Bootlogo.pak" ;;
        esac
        if [ -n "$TARGET_CANONICAL" ] && [ "$PAK_NAME" != "$TARGET_CANONICAL" ]; then
            TARGET_PATH="$t_dir/$TARGET_CANONICAL"
            [ ! -d "$TARGET_PATH" ] && mv "$pak" "$TARGET_PATH" 2>/dev/null
        fi
    done
done

# 3. Update Roms map.txt for clean console naming
ROMS_DIR="$SDCARD_PATH/Roms"
if [ -d "$ROMS_DIR" ]; then
    cat << 'EOF' > "$ROMS_DIR/map.txt"
Nintendo DS (NDS)	Nintendo DS
Game Boy Advance (GBA)	Game Boy Advance
Game Boy Color (GBC)	Game Boy Color
Game Boy (GB)	Game Boy
Sony PlayStation (PS)	PlayStation
Sega Genesis (MD)	Mega Drive / Genesis
Super Nintendo (SFC)	Super Nintendo
Nintendo Entertainment System (FC)	NES
Pico-8 (P8)	Pico-8
Arcade (ARCADE)	Arcade
EOF
fi

sync
echo "Applied language '$CODE' across all Settings, Tools, and Roms successfully!"
