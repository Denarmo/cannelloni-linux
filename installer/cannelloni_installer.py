import os
import sys
import tempfile
from contextlib import contextmanager, ExitStack
import time
import json
import re
import zipfile
import shutil
import threading
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from pathlib import Path

# -----------------------------------------------------------------------------
# Cannelloni Universal SD Installer
# Cross-platform GUI tool (Windows & Linux)
# Supports native Tkinter desktop GUI and lightweight local Web GUI fallback.
# -----------------------------------------------------------------------------

def installer_version():
    """Read the same VERSION file in source checkouts, ZIPs and frozen builds."""
    directory = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for path in (directory / "VERSION", directory.parent / "VERSION"):
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError("VERSION is missing. Extract the complete Cannelloni installer archive.")


VERSION = installer_version()

# Supported handheld profiles
DEVICES = [
    {
        "id": "miyoomini",
        "name": "Miyoo Mini (v1 / v2 / v3)",
        "platform": "miyoomini",
        "device": "mini",
        "brand": "Miyoo",
        "desc": "2.8\" 640x480 • SigmaStar SSD202D • Compact Vertical",
    },
    {
        "id": "miyoominiplus",
        "name": "Miyoo Mini Plus (v4 / Wi-Fi)",
        "platform": "miyoomini",
        "device": "plus",
        "brand": "Miyoo",
        "desc": "3.5\" 640x480 • Wi-Fi • SigmaStar SSD202D • Classic Vertical",
    },
    {
        "id": "my282",
        "name": "Miyoo A30",
        "platform": "my282",
        "device": "my282",
        "brand": "Miyoo",
        "desc": "2.8\" 640x480 • Allwinner A33 Quad-Core • Pocket Horizontal",
    },
    {
        "id": "my355",
        "name": "Miyoo Flip",
        "platform": "my355",
        "device": "my355",
        "brand": "Miyoo",
        "desc": "3.5\" 640x480 • Rockchip RK3566 • Clamshell Dual Analog",
    },
    {
        "id": "trimuismart",
        "name": "TrimUI Smart",
        "platform": "trimuismart",
        "device": "smart",
        "brand": "TrimUI",
        "desc": "2.4\" 320x240 • Wi-Fi / Bluetooth • Allwinner S3 • Micro Pocket",
    },
    {
        "id": "tg5040",
        "name": "TrimUI Smart Pro",
        "platform": "tg5040",
        "device": "tg5040",
        "brand": "TrimUI",
        "desc": "4.96\" 1280x720 16:9 • Allwinner A133 Plus • Stereo Speakers",
    },
    {
        "id": "tg5040_brick",
        "name": "TrimUI Brick",
        "platform": "tg5040",
        "device": "brick",
        "brand": "TrimUI",
        "desc": "3.2\" 1024x768 4:3 Hi-Res • Allwinner A133 Plus • Modern Vertical",
    },
    {
        "id": "rg35xx",
        "name": "Anbernic RG35XX (Original)",
        "platform": "rg35xx",
        "device": "rg35xx",
        "brand": "Anbernic",
        "desc": "3.5\" 640x480 • Actions ATM7039S • Dual TF Slots",
    },
    {
        "id": "rg35xxplus",
        "name": "Anbernic RG35XX Plus",
        "platform": "rg35xxplus",
        "device": "rg35xxplus",
        "brand": "Anbernic",
        "desc": "3.5\" 640x480 • Allwinner H700 64-bit • Wi-Fi • Vertical",
    },
    {
        "id": "rg35xxh",
        "name": "Anbernic RG35XX H",
        "platform": "rg35xxplus",
        "device": "rg35xxh",
        "brand": "Anbernic",
        "desc": "3.5\" 640x480 • Allwinner H700 • Dual Analog Sticks • Horizontal",
    },
    {
        "id": "rg35xxsp",
        "name": "Anbernic RG35XX SP",
        "platform": "rg35xxplus",
        "device": "rg35xxsp",
        "brand": "Anbernic",
        "desc": "3.5\" 640x480 • Allwinner H700 • Clamshell GBA SP Form Factor",
    },
    {
        "id": "rg28xx",
        "name": "Anbernic RG28XX",
        "platform": "rg35xxplus",
        "device": "rg28xx",
        "brand": "Anbernic",
        "desc": "2.8\" 640x480 • Allwinner H700 • Pocket Horizontal",
    },
    {
        "id": "rgcubexx",
        "name": "Anbernic RG CubeXX",
        "platform": "rg35xxplus",
        "device": "rgcubexx",
        "brand": "Anbernic",
        "desc": "3.95\" 720x720 1:1 Square IPS • Allwinner H700 • Dual Analogs",
    },
    {
        "id": "rgb30",
        "name": "Powkiddy RGB30",
        "platform": "rgb30",
        "device": "rgb30",
        "brand": "Powkiddy",
        "desc": "4.0\" 720x720 1:1 Square IPS • Rockchip RK3566 • Dual Analogs",
    },
    {
        "id": "magicmini",
        "name": "MagicX XU Mini M",
        "platform": "magicmini",
        "device": "magicmini",
        "brand": "MagicX",
        "desc": "MagicX XU Mini M • Compact Horizontal • magicmini platform",
    },
    {
        "id": "zero28",
        "name": "MagicX Mini Zero 28",
        "platform": "zero28",
        "device": "zero28",
        "brand": "MagicX",
        "desc": "MagicX Mini Zero 28 • Compact Horizontal • zero28 platform",
    },
    {
        "id": "gkdpixel",
        "name": "GKD Pixel",
        "platform": "gkdpixel",
        "device": "gkdpixel",
        "brand": "GKD",
        "desc": "2.4\" 320x240 • CNC Aluminum Housing • Ingenic JZ4770 Micro",
    },
    {
        "id": "m17",
        "name": "M17",
        "platform": "m17",
        "device": "m17",
        "brand": "M17",
        "desc": "4.3\" 480x272 16:9 • Rockchip RK3128 • Wide Ergonomic Handheld",
    },
]

# Accent Colors with previews
ACCENT_COLORS = [
    {"name": "Cannelloni Gold", "hex": "#f1c40f", "rgb": (241, 196, 15), "text": "#111111"},
    {"name": "Tomato Red",      "hex": "#e74c3c", "rgb": (231, 76, 60),  "text": "#ffffff"},
    {"name": "Basil Green",     "hex": "#2ecc71", "rgb": (46, 204, 113), "text": "#111111"},
    {"name": "Sky Blue",        "hex": "#3498db", "rgb": (52, 152, 219), "text": "#ffffff"},
    {"name": "Royal Purple",    "hex": "#9b59b6", "rgb": (155, 89, 182), "text": "#ffffff"},
    {"name": "Carrot Orange",   "hex": "#e67e22", "rgb": (230, 126, 34), "text": "#ffffff"},
    {"name": "Clean White",     "hex": "#ffffff", "rgb": (255, 255, 255),"text": "#111111"},
]

# Localization Dictionaries
LANGUAGES = {
    "en": {
        "name": "English",
        "title": "Cannelloni SD Installer",
        "subtitle": "Universal Retro Handheld Setup Tool",
        "drive_section": "1. Target SD Card",
        "drive_desc": "Select the removable drive for your handheld's SD card.",
        "refresh": "🔄 Refresh",
        "browse": "📁 Browse...",
        "no_drives": "No removable drives detected. Click Browse or plug in an SD card.",
        "lang_section": "2. System Language",
        "lang_desc": "Choose the interface language for Cannelloni on your handheld.",
        "color_section": "3. Accent Color Theme",
        "color_desc": "Pick your favorite accent color for menu highlights and UI elements.",
        "device_section": "4. Handheld Console Model",
        "device_desc": "Select your exact handheld hardware to optimize drivers and controls.",
        "preview_title": "Live Theme Preview",
        "install_btn": "⚡ Install Cannelloni to SD Card",
        "installing": "Installing Cannelloni...",
        "status_ready": "Ready to install",
        "status_unzipping": "Extracting Cannelloni OS payload ({percent}%)...",
        "status_configuring": "Pre-configuring device, language, and theme...",
        "status_done": "Installation Completed Successfully!",
        "success_title": "Installation Complete! 🍝",
        "success_msg": (
            "Cannelloni has been successfully installed on {drive}!\n\n"
            "Pre-configured settings:\n"
            "• Device: {device}\n"
            "• Language: {lang}\n"
            "• Accent: {color}\n\n"
            "You can now safely eject your SD card, insert it into your {device}, and turn it on.\n"
            "Buon appetito!"
        ),
        "error_no_drive": "Please select a valid SD card drive or folder.",
        "error_drive_not_found": "The selected target directory does not exist.",
        "error_no_zip": "Cannelloni.zip payload not found! Please place Cannelloni.zip next to the installer.",
        "warning_fixed": "The selected drive '{drive}' appears to be a fixed/system disk.\nAre you SURE you want to install Cannelloni here?",
        "eject_hint": "Safely eject before removing the SD card.",
    },
    "es": {
        "name": "Español",
        "title": "Instalador SD de Cannelloni",
        "subtitle": "Herramienta Universal de Configuración para Consolas Retro",
        "drive_section": "1. Tarjeta SD de Destino",
        "drive_desc": "Selecciona la unidad extraíble de tu tarjeta SD.",
        "refresh": "🔄 Actualizar",
        "browse": "📁 Explorar...",
        "no_drives": "No se detectaron unidades extraíbles. Haz clic en Explorar o conecta una SD.",
        "lang_section": "2. Idioma del Sistema",
        "lang_desc": "Elige el idioma de la interfaz de Cannelloni.",
        "color_section": "3. Color de Acento",
        "color_desc": "Elige tu color favorito para los menús y elementos de la interfaz.",
        "device_section": "4. Modelo de Consola",
        "device_desc": "Selecciona tu consola exacta para optimizar controladores y botones.",
        "preview_title": "Vista Previa en Vivo",
        "install_btn": "⚡ Instalar Cannelloni en la Tarjeta SD",
        "installing": "Instalando Cannelloni...",
        "status_ready": "Listo para instalar",
        "status_unzipping": "Extrayendo archivos del sistema Cannelloni ({percent}%)...",
        "status_configuring": "Pre-configurando dispositivo, idioma y tema...",
        "status_done": "¡Instalación completada con éxito!",
        "success_title": "¡Instalación Completada! 🍝",
        "success_msg": (
            "¡Cannelloni se ha instalado correctamente en {drive}!\n\n"
            "Ajustes pre-configurados:\n"
            "• Consola: {device}\n"
            "• Idioma: {lang}\n"
            "• Color: {color}\n\n"
            "Ya puedes expulsar de forma segura tu tarjeta SD, insertarla en tu {device} y encenderla.\n"
            "¡Buon appetito!"
        ),
        "error_no_drive": "Por favor, selecciona una unidad o carpeta SD válida.",
        "error_drive_not_found": "El directorio seleccionado no existe.",
        "error_no_zip": "¡No se encontró Cannelloni.zip! Colócalo junto al instalador.",
        "warning_fixed": "La unidad seleccionada '{drive}' parece ser un disco fijo del sistema.\n¿Estás SEGURO de que deseas instalar Cannelloni aquí?",
        "eject_hint": "Expulsa la tarjeta de forma segura antes de retirarla.",
    },
    "fr": {
        "name": "Français",
        "title": "Installateur SD Cannelloni",
        "subtitle": "Outil Universel de Configuration pour Consoles Rétro",
        "drive_section": "1. Carte SD Cible",
        "drive_desc": "Sélectionnez le lecteur amovible de votre carte SD.",
        "refresh": "🔄 Actualiser",
        "browse": "📁 Parcourir...",
        "no_drives": "Aucun lecteur amovible détecté. Cliquez sur Parcourir ou insérez une carte SD.",
        "lang_section": "2. Langue du Système",
        "lang_desc": "Choisissez la langue de l'interface de Cannelloni.",
        "color_section": "3. Couleur d'Accentuation",
        "color_desc": "Choisissez votre couleur d'accent pour les menus et surbrillances.",
        "device_section": "4. Modèle de Console",
        "device_desc": "Sélectionnez votre console pour optimiser les pilotes et boutons.",
        "preview_title": "Aperçu en Direct",
        "install_btn": "⚡ Installer Cannelloni sur la Carte SD",
        "installing": "Installation de Cannelloni...",
        "status_ready": "Prêt pour l'installation",
        "status_unzipping": "Extraction des fichiers du système Cannelloni ({percent}%)...",
        "status_configuring": "Configuration du modèle, de la langue et du thème...",
        "status_done": "Installation terminée avec succès !",
        "success_title": "Installation Réussie ! 🍝",
        "success_msg": (
            "Cannelloni a été installé avec succès sur {drive} !\n\n"
            "Paramètres préconfigurés :\n"
            "• Console : {device}\n"
            "• Langue : {lang}\n"
            "• Couleur : {color}\n\n"
            "Vous pouvez éjecter votre carte SD en toute sécurité, l'insérer dans votre {device} et l'allumer.\n"
            "Buon appetito !"
        ),
        "error_no_drive": "Veuillez sélectionner un lecteur ou dossier SD valide.",
        "error_drive_not_found": "Le répertoire cible sélectionné n'existe pas.",
        "error_no_zip": "Cannelloni.zip introuvable ! Placez-le à côté de l'installateur.",
        "warning_fixed": "Le lecteur '{drive}' semble être un disque système fixe.\nÊtes-vous SÛR de vouloir installer Cannelloni ici ?",
        "eject_hint": "Éjectez la carte en toute sécurité avant de la retirer.",
    },
    "pt_BR": {
        "name": "Português (Brasil)",
        "title": "Instalador SD Cannelloni",
        "subtitle": "Ferramenta Universal de Configuração para Portáteis Retrô",
        "drive_section": "1. Cartão SD de Destino",
        "drive_desc": "Selecione a unidade removível do seu cartão SD.",
        "refresh": "🔄 Atualizar",
        "browse": "📁 Procurar...",
        "no_drives": "Nenhuma unidade removível detectada. Clique em Procurar ou conecte um SD.",
        "lang_section": "2. Idioma do Sistema",
        "lang_desc": "Escolha o idioma da interface do Cannelloni.",
        "color_section": "3. Cor de Destaque",
        "color_desc": "Escolha sua cor favorita para os menus e realces da interface.",
        "device_section": "4. Modelo do Portátil",
        "device_desc": "Selecione seu console exato para otimizar drivers e botões.",
        "preview_title": "Prévia em Tempo Real",
        "install_btn": "⚡ Instalar Cannelloni no Cartão SD",
        "installing": "Instalando Cannelloni...",
        "status_ready": "Pronto para instalar",
        "status_unzipping": "Extraindo arquivos do sistema Cannelloni ({percent}%)...",
        "status_configuring": "Pré-configurando dispositivo, idioma e tema...",
        "status_done": "Instalação concluída com sucesso!",
        "success_title": "Instalação Concluída! 🍝",
        "success_msg": (
            "Cannelloni foi instalado com sucesso em {drive}!\n\n"
            "Configurações aplicadas:\n"
            "• Dispositivo: {device}\n"
            "• Idioma: {lang}\n"
            "• Destaque: {color}\n\n"
            "Você já pode ejetar seu cartão SD com segurança, colocá-lo no {device} e ligá-lo.\n"
            "Buon appetito!"
        ),
        "error_no_drive": "Por favor, selecione uma unidade ou pasta SD válida.",
        "error_drive_not_found": "O diretório selecionado não existe.",
        "error_no_zip": "Cannelloni.zip não encontrado! Coloque-o junto ao instalador.",
        "warning_fixed": "A unidade '{drive}' parece ser um disco fixo do sistema.\nTem CERTEZA de que deseja instalar Cannelloni aqui?",
        "eject_hint": "Ejete o cartão com segurança antes de desconectar.",
    },
    "de": {
        "name": "Deutsch",
        "title": "Cannelloni SD-Installationsprogramm",
        "subtitle": "Universelles Konfigurationswerkzeug für Retro-Handhelds",
        "drive_section": "1. Ziel-SD-Karte",
        "drive_desc": "Wählen Sie das Wechsellaufwerk Ihrer SD-Karte aus.",
        "refresh": "🔄 Aktualisieren",
        "browse": "📁 Durchsuchen...",
        "no_drives": "Kein Wechsellaufwerk erkannt. Klicken Sie auf Durchsuchen oder stecken Sie eine SD-Karte ein.",
        "lang_section": "2. Systemsprache",
        "lang_desc": "Wählen Sie die Benutzeroberflächensprache für Cannelloni.",
        "color_section": "3. Akzentfarbe",
        "color_desc": "Wählen Sie Ihre bevorzugte Akzentfarbe für Menü-Hervorhebungen.",
        "device_section": "4. Handheld-Konsolenmodell",
        "device_desc": "Wählen Sie Ihre Konsole aus, um Treiber und Tastenbelegung zu optimieren.",
        "preview_title": "Live-Vorschau",
        "install_btn": "⚡ Cannelloni auf SD-Karte installieren",
        "installing": "Cannelloni wird installiert...",
        "status_ready": "Bereit zur Installation",
        "status_unzipping": "Cannelloni-Dateien werden entpackt ({percent}%)...",
        "status_configuring": "Gerät, Sprache und Theme werden vorkonfiguriert...",
        "status_done": "Installation erfolgreich abgeschlossen!",
        "success_title": "Installation Abgeschlossen! 🍝",
        "success_msg": (
            "Cannelloni wurde erfolgreich auf {drive} installiert!\n\n"
            "Vorkonfigurierte Einstellungen:\n"
            "• Konsole: {device}\n"
            "• Sprache: {lang}\n"
            "• Akzent: {color}\n\n"
            "Sie können die SD-Karte jetzt sicher auswerfen, in Ihr {device} einlegen und einschalten.\n"
            "Buon appetito!"
        ),
        "error_no_drive": "Bitte wählen Sie ein gültiges SD-Laufwerk oder einen Ordner.",
        "error_drive_not_found": "Das ausgewählte Zielverzeichnis existiert nicht.",
        "error_no_zip": "Cannelloni.zip nicht gefunden! Bitte neben dem Installationsprogramm platzieren.",
        "warning_fixed": "Das Laufwerk '{drive}' scheint eine feste Festplatte zu sein.\nSind Sie SICHER, dass Sie Cannelloni hier installieren möchten?",
        "eject_hint": "Werfen Sie die SD-Karte vor dem Entfernen sicher aus.",
    },
    "it": {
        "name": "Italiano",
        "title": "Installatore SD Cannelloni",
        "subtitle": "Strumento Universale di Configurazione per Console Retrò",
        "drive_section": "1. Scheda SD di Destinazione",
        "drive_desc": "Seleziona l'unità rimovibile della tua scheda SD.",
        "refresh": "🔄 Aggiorna",
        "browse": "📁 Sfoglia...",
        "no_drives": "Nessuna unità rimovibile rilevata. Clicca su Sfoglia o inserisci una scheda SD.",
        "lang_section": "2. Lingua di Sistema",
        "lang_desc": "Scegli la lingua dell'interfaccia di Cannelloni.",
        "color_section": "3. Colore d'Accento",
        "color_desc": "Scegli il tuo colore preferito per i menu e le selezioni.",
        "device_section": "4. Modello di Console",
        "device_desc": "Seleziona la tua console esatta per ottimizzare driver e controlli.",
        "preview_title": "Anteprima dal Vivo",
        "install_btn": "⚡ Installa Cannelloni su Scheda SD",
        "installing": "Installazione di Cannelloni...",
        "status_ready": "Pronto per l'installazione",
        "status_unzipping": "Estrazione dei file di sistema Cannelloni ({percent}%)...",
        "status_configuring": "Pre-configurazione dispositivo, lingua e tema...",
        "status_done": "Installazione completata con successo!",
        "success_title": "Installazione Completata! 🍝",
        "success_msg": (
            "Cannelloni è stato installato con successo su {drive}!\n\n"
            "Impostazioni pre-configurate:\n"
            "• Console: {device}\n"
            "• Lingua: {lang}\n"
            "• Accento: {color}\n\n"
            "Puoi rimuovere la scheda SD in sicurezza, inserirla nella tua {device} e accenderla.\n"
            "Buon appetito!"
        ),
        "error_no_drive": "Seleziona un'unità o cartella SD valida.",
        "error_drive_not_found": "La directory selezionata non esiste.",
        "error_no_zip": "Cannelloni.zip non trovato! Posizionalo accanto all'installatore.",
        "warning_fixed": "L'unità '{drive}' sembra essere un disco di sistema fisso.\nSei SICURO di voler installare Cannelloni qui?",
        "eject_hint": "Espelli la scheda in sicurezza prima di rimuoverla.",
    }
}

def format_size(bytes_num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

PAYLOAD_NAMES = ("Cannelloni.zip", "Cannoli.zip")


def find_cannelloni_zip():
    """Prefer the bundled payload beside the installer over development builds."""
    directories = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        directories.extend((exe_dir, os.path.join(exe_dir, "releases")))
        if hasattr(sys, "_MEIPASS"):
            directories.append(sys._MEIPASS)

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    directories.extend((
        curr_dir,
        os.path.join(curr_dir, "releases"),
        os.path.join(curr_dir, "..", "releases"),
        os.getcwd(),
        os.path.join(os.getcwd(), "releases"),
        os.path.join(curr_dir, "..", "build_release", "temp"),
        os.path.join(os.getcwd(), "build_release", "temp"),
    ))
    names = PAYLOAD_NAMES + (f"Cannelloni-{VERSION}.zip", "Cannelloni-Installer.zip")
    for directory in directories:
        for name in names:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        # A completed same-card install retains its source with a suffix that
        # device boot scripts do not mistake for a pending ZIP update.
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for name in names:
            completed = name + ".installed"
            matches = []
            for entry in entries:
                if entry == completed:
                    matches.append((0, entry))
                elif entry.startswith(completed + ".") and entry[len(completed) + 1:].isdigit():
                    matches.append((int(entry[len(completed) + 1:]), entry))
            for _, entry in sorted(matches, reverse=True):
                candidate = os.path.join(directory, entry)
                if os.path.isfile(candidate):
                    return os.path.abspath(candidate)
    return None


def preserve_completed_source(zip_path, target_path):
    """Rename a consumed root ZIP so first boot cannot reinstall its defaults."""
    if not zip_path.lower().endswith(".zip"):
        return  # Already preserved by an earlier successful installation.
    if os.path.realpath(os.path.dirname(zip_path)) != os.path.realpath(target_path):
        return  # Sources on the computer or in another folder remain in place.
    suffix = 0
    while True:
        destination = zip_path + ".installed" + (f".{suffix}" if suffix else "")
        try:
            # Reserve a unique destination before replacing our own empty
            # placeholder; never overwrite an earlier preserved archive.
            with open(destination, "xb"):
                pass
        except FileExistsError:
            suffix += 1
            continue
        try:
            os.replace(zip_path, destination)
        except OSError:
            os.remove(destination)
            raise
        return


@contextmanager
def open_os_payload(zip_path):
    """Open the OS archive, ignoring loose copies in legacy release wrappers.

    Large nested archives spill to temporary storage instead of holding the
    whole OS in RAM. ExitStack also closes every nested archive on failure.
    """
    with ExitStack() as stack:
        archive = stack.enter_context(zipfile.ZipFile(zip_path))
        for depth in range(8):
            nested = next((name for name in PAYLOAD_NAMES if name in archive.namelist()), None)
            if nested is None:
                if not any(name.startswith(".system/") for name in archive.namelist()):
                    raise ValueError("The archive does not contain a Cannelloni OS payload.")
                yield archive
                return
            storage = stack.enter_context(tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024))
            with archive.open(nested) as source:
                shutil.copyfileobj(source, storage)
            storage.seek(0)
            archive = stack.enter_context(zipfile.ZipFile(storage))
        raise ValueError("Too many nested Cannelloni payload archives.")


BOOTSTRAP_ROOTS = {
    "miyoomini": {"miyoo", "miyoo354"},
    "my282": {"miyoo", "miyoo285"},
    "my355": {"miyoo355"},
    "trimuismart": {"trimui"},
    "tg5040": {"trimui"},
    "rg35xx": {"rg35xx"},
    "rg35xxplus": {"rg35xxplus", "dmenu.bin"},
    "gkdpixel": {"gkdpixel"},
    "m17": {"em_ui.sh"},
    "zero28": {"magicx"},
    "magicmini": set(),
    "rgb30": set(),
}
UPDATER_PLATFORMS = {"miyoomini", "my282", "my355", "trimuismart", "tg5040", "zero28"}
ALL_BOOTSTRAP_ROOTS = set().union(*BOOTSTRAP_ROOTS.values())


def supported_emulators(archive, platform):
    """Only expose ROM/BIOS/save folders that have a launcher on this device."""
    tags = set()
    for name in archive.namelist():
        for prefix in (f".system/{platform}/paks/Emus/", f"Emus/{platform}/"):
            if name.startswith(prefix) and name.endswith(".pak/launch.sh"):
                tags.add(name[len(prefix):].split(".pak/", 1)[0])
    return tags


def belongs_to_device(name, device, emulators):
    parts = name.replace("\\", "/").rstrip("/").split("/")
    platform = device["platform"]
    root = parts[0]
    if root in (".system", ".userdata") and len(parts) > 1:
        shared = {"bin", "common", "res", "dat", "version.txt", "commits.txt"} if root == ".system" else {"shared"}
        if parts[1] not in shared and parts[1] != platform:
            return False
        # All accent assets stay available; platform-specific widget binaries do not.
        if parts[:3] == [".system", "res", "themes"] and len(parts) > 5 and parts[4] == "bin":
            return parts[5] == platform
    if root in ("Settings", "Tools", "Emus") and len(parts) > 1:
        return parts[1] == platform
    if root in ALL_BOOTSTRAP_ROOTS and root not in BOOTSTRAP_ROOTS[platform]:
        return False
    if ".tmp_update" in parts:
        if platform not in UPDATER_PLATFORMS:
            return False
        rest = parts[parts.index(".tmp_update") + 1:]
        if rest and rest[0] not in {platform, platform + ".sh", "updater", "device_select.sh", "apply_language.sh"}:
            return False
        if rest[:2] == ["tg5040", "brick"] and device["device"] != "brick":
            return False
    if root in {"miyoo", "miyoo354", "miyoo355", "miyoo285"} and len(parts) > 2 and parts[1] == "app":
        if parts[2].removesuffix(".sh") in {"miyoomini", "my282", "my355"}:
            return parts[2].removesuffix(".sh") == platform
    if root == "trimui" and len(parts) > 2:
        if parts[2] == "main.sh":
            return platform == "trimuismart"
        if parts[2] == "runtrimui.sh":
            return platform == "tg5040"
    if root in {"Roms", "Bios", "Saves"} and len(parts) > 1:
        if root == "Roms":
            match = re.search(r"\(([^)]+)\)$", parts[1])
            tag = match.group(1) if match else None
        else:
            tag = parts[1]
        if tag is not None:
            return tag in emulators
    return True


def payload_members(archive, target_path, device=None):
    """Validate all output paths before copying anything to the SD card."""
    target_root = os.path.realpath(target_path)
    members = []
    for member in archive.infolist():
        name = member.filename
        if name.startswith(("Cannelloni-Installer", "cannelloni_installer")) or name in PAYLOAD_NAMES:
            continue
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or any(":" in part for part in parts):
            raise ValueError(f"Unsafe path in OS payload: {name}")
        destination = os.path.realpath(os.path.join(target_root, *parts))
        if os.path.commonpath((target_root, destination)) != target_root:
            raise ValueError(f"OS payload path escapes the target directory: {name}")
        members.append(member)
    if device is not None:
        if not any(member.filename.startswith(f'.system/{device["platform"]}/') for member in members):
            raise ValueError(f'The OS payload does not contain files for {device["name"]}.')
        emulators = supported_emulators(archive, device["platform"])
        members = [member for member in members if belongs_to_device(member.filename, device, emulators)]
    return members

def detect_drives():
    """Returns list of detected removable/external drives on Windows and Linux."""
    drives = []
    if sys.platform == "win32":
        try:
            import ctypes
            drive_bits = ctypes.windll.kernel32.GetLogicalDrives()
            for c in range(ord('A'), ord('Z') + 1):
                letter = chr(c)
                if drive_bits & (1 << (c - ord('A'))):
                    root_path = f"{letter}:\\"
                    dtype = ctypes.windll.kernel32.GetDriveTypeW(root_path)
                    # 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED
                    is_removable = (dtype == 2)
                    label = ""
                    try:
                        buf = ctypes.create_unicode_buffer(1024)
                        fs = ctypes.create_unicode_buffer(1024)
                        ctypes.windll.kernel32.GetVolumeInformationW(root_path, buf, 1024, None, None, None, fs, 1024)
                        label = buf.value
                    except Exception:
                        pass
                    
                    try:
                        usage = shutil.disk_usage(root_path)
                        total_str = format_size(usage.total)
                        free_str = format_size(usage.free)
                    except Exception:
                        total_str = "Unknown"
                        free_str = "Unknown"
                    
                    display = f"{letter}: "
                    if label:
                        display += f"[{label}] "
                    display += f"({free_str} free / {total_str})"
                    if is_removable:
                        display += " • Removable"

                    # Only suggest C:\ if specifically browsed, skip in auto dropdown to prevent accident
                    if letter.upper() == 'C' and not is_removable:
                        continue

                    drives.append({
                        "path": root_path,
                        "display": display,
                        "label": label,
                        "is_removable": is_removable,
                        "free": free_str
                    })
        except Exception as e:
            print("Windows drive detection error:", e)
    else:
        # Linux / Unix
        seen_mounts = set()
        # Scan /media and /run/media
        user = os.environ.get('USER') or os.environ.get('USERNAME') or ''
        search_dirs = []
        if user:
            search_dirs.extend([f"/media/{user}", f"/run/media/{user}"])
        search_dirs.extend(["/media", "/run/media", "/mnt"])
        for sdir in search_dirs:
            if os.path.isdir(sdir):
                try:
                    for entry in os.listdir(sdir):
                        full = os.path.join(sdir, entry)
                        if (os.path.ismount(full) or sdir.startswith(("/media", "/run/media"))) and full not in seen_mounts and os.path.isdir(full):
                            seen_mounts.add(full)
                            try:
                                usage = shutil.disk_usage(full)
                                free_str = format_size(usage.free)
                                total_str = format_size(usage.total)
                            except Exception:
                                free_str, total_str = "Unknown", "Unknown"
                            drives.append({
                                "path": full,
                                "display": f"{entry} ({full}) • {free_str} free / {total_str} • Removable",
                                "label": entry,
                                "is_removable": True,
                                "free": free_str
                            })
                except Exception:
                    pass

        # Try lsblk if available
        try:
            p = subprocess.run(["lsblk", "-J", "-o", "NAME,MOUNTPOINT,RM,SIZE,LABEL,FSTYPE"],
                               capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                data = json.loads(p.stdout)
                def parse_devs(dev_list):
                    for dev in dev_list:
                        mp = dev.get("mountpoint")
                        rm = dev.get("rm")
                        if mp and mp not in seen_mounts and (rm in (True, 1, "1")):
                            seen_mounts.add(mp)
                            lbl = dev.get("label") or dev.get("name")
                            sz = dev.get("size") or ""
                            drives.append({
                                "path": mp,
                                "display": f"{lbl} ({mp}) • {sz} • Removable",
                                "label": lbl,
                                "is_removable": True,
                                "free": sz
                            })
                        if "children" in dev:
                            parse_devs(dev["children"])
                parse_devs(data.get("blockdevices", []))
        except Exception:
            pass

    # Sort drives: removable drives first!
    drives.sort(key=lambda d: 0 if d.get("is_removable") else 1)
    return drives

def perform_installation(target_path, lang_code, accent_hex, device_id, progress_callback, status_callback):
    """
    Extracts the bundled Cannelloni.zip or Cannoli.zip to target_path and sets up:
    - .userdata/shared/.cannelloni/language.txt
    - .userdata/shared/.cannelloni/accent_color.txt
    - .userdata/shared/.cannelloni/device_model.txt
    - .userdata/shared/.cannelloni/platform.txt
    - .userdata/shared/.cannelloni/device.txt
    - Pre-copies boot splash dat files
    - Pre-copies accent color theme assets and binaries
    - Sets device-specific flags (e.g. .is_plus)
    """
    zip_path = find_cannelloni_zip()
    if not zip_path:
        raise FileNotFoundError("Cannelloni.zip or Cannoli.zip OS payload not found next to the installer.")

    if not os.path.isdir(target_path):
        os.makedirs(target_path, exist_ok=True)

    status_callback("Opening Cannelloni release archive...")
    progress_callback(1)

    # Resolve device object
    dev_obj = next((d for d in DEVICES if d["id"] == device_id), None)
    if dev_obj is None:
        raise ValueError(f"Unknown handheld model: {device_id}")
    target_platform = dev_obj["platform"]
    target_variant = dev_obj["device"]
    target_name = dev_obj["name"]

    # 1. Unzip Cannelloni payload with progress
    with open_os_payload(zip_path) as zf:
        infolist = payload_members(zf, target_path, dev_obj)
        total_items = len(infolist)
        extracted = 0

        for member in infolist:
            destination = zf.extract(member, target_path)
            permissions = (member.external_attr >> 16) & 0o777
            if sys.platform != "win32" and permissions:
                try:
                    os.chmod(destination, permissions)
                except OSError:
                    pass  # FAT cards may not support POSIX permissions.
            extracted += 1
            if extracted % 25 == 0 or extracted == total_items:
                pct = int((extracted / total_items) * 85)
                progress_callback(pct)
                status_callback(f"Extracting {member.filename} ({extracted}/{total_items})...")

    # Installer files are never extracted. The source archive is preserved
    # after successful configuration, including when installing from the card.

    progress_callback(86)
    status_callback("Configuring system preferences and hardware profile...")

    # 2. Pre-configure .userdata/shared/.cannelloni/
    shared_dir = os.path.join(target_path, ".userdata", "shared", ".cannelloni")
    os.makedirs(shared_dir, exist_ok=True)

    with open(os.path.join(shared_dir, "language.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{lang_code}\n")

    with open(os.path.join(shared_dir, "accent_color.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{accent_hex}\n")

    with open(os.path.join(shared_dir, "device_model.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{target_name}\n")

    with open(os.path.join(shared_dir, "platform.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{target_platform}\n")

    if target_variant:
        with open(os.path.join(shared_dir, "device.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{target_variant}\n")

    progress_callback(90)
    status_callback("Applying hardware bootstrap files and flags...")

    # 3. Hardware flags
    if device_id == "miyoominiplus":
        plus_dir = os.path.join(target_path, ".userdata", "miyoomini")
        os.makedirs(plus_dir, exist_ok=True)
        with open(os.path.join(plus_dir, ".is_plus"), "w", encoding="utf-8") as f:
            f.write("")
    elif device_id == "miyoomini":
        plus_flag = os.path.join(target_path, ".userdata", "miyoomini", ".is_plus")
        if os.path.isfile(plus_flag):
            try:
                os.remove(plus_flag)
            except Exception:
                pass

    # 4. Copy boot splash dat files
    boot_dat_src = os.path.join(target_path, ".system", target_platform, "dat")
    boot_dat_dst = os.path.join(target_path, ".system", "dat")
    if os.path.isdir(boot_dat_src):
        os.makedirs(boot_dat_dst, exist_ok=True)
        for item in os.listdir(boot_dat_src):
            sfile = os.path.join(boot_dat_src, item)
            dfile = os.path.join(boot_dat_dst, item)
            if os.path.isfile(sfile):
                try:
                    shutil.copy2(sfile, dfile)
                except Exception:
                    pass

    progress_callback(94)
    status_callback(f"Applying accent theme ({accent_hex})...")

    # 5. Pre-apply accent color spritesheets and external list widgets.
    # The current native frontends read accent_color.txt themselves; stale
    # theme binaries from an older card/archive must never replace them.
    theme_dir = os.path.join(target_path, ".system", "res", "themes", accent_hex)
    res_dir = os.path.join(target_path, ".system", "res")
    if os.path.isdir(theme_dir) and os.path.isdir(res_dir):
        for item in os.listdir(theme_dir):
            if item.startswith("assets@") and item.endswith(".png"):
                try:
                    shutil.copy2(os.path.join(theme_dir, item), os.path.join(res_dir, item))
                except Exception:
                    pass

        theme_bin = os.path.join(theme_dir, "bin", target_platform)
        plat_bin = os.path.join(target_path, ".system", target_platform, "bin")
        if os.path.isdir(theme_bin) and os.path.isdir(plat_bin):
            for bitem in ("cannelloni-list", "minui-list"):
                if not os.path.isfile(os.path.join(theme_bin, bitem)):
                    continue
                try:
                    shutil.copy2(os.path.join(theme_bin, bitem), os.path.join(plat_bin, bitem))
                except Exception:
                    pass

    # 6. Ensure POSIX permissions on non-Windows
    if sys.platform != "win32":
        try:
            for root, dirs, files in os.walk(target_path):
                for f in files:
                    if f.endswith((".sh", ".elf", ".bin")) or f in ("MainUI", "updater", "say.elf", "cannelloni.elf"):
                        p = os.path.join(root, f)
                        os.chmod(p, 0o755)
            if hasattr(os, 'sync'):
                os.sync()
        except Exception:
            pass

    preserve_completed_source(zip_path, target_path)
    progress_callback(100)
    status_callback("Installation Completed Successfully!")
    return True

# -----------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except Exception:
    TKINTER_AVAILABLE = False

if TKINTER_AVAILABLE:
    class CannelloniInstallerApp:
        def __init__(self, root):
            self.root = root
            self.current_lang = "en"
            self.current_color = "#f1c40f"
            self.current_device_id = "miyoominiplus"
            self.selected_drive = None
            self.drives = []
            self.is_installing = False

            # UI Theme Colors
            self.bg_main = "#141417"
            self.bg_card = "#1e1e24"
            self.bg_card_inner = "#272730"
            self.border_card = "#333340"
            self.text_primary = "#f4f4f5"
            self.text_muted = "#9ca3af"

            self.root.title(f"Cannelloni SD Installer {VERSION}")
            self.root.geometry("820x680")
            self.root.minsize(780, 620)
            self.root.configure(bg=self.bg_main)

            # Center window on screen
            self.center_window()

            self.build_ui()
            self.refresh_drives()
            self.apply_language()
            self.apply_accent_color_preview()

        def center_window(self):
            self.root.update_idletasks()
            width = 820
            height = 680
            x = max(0, (self.root.winfo_screenwidth() // 2) - (width // 2))
            y = max(0, (self.root.winfo_screenheight() // 2) - (height // 2) - 20)
            self.root.geometry(f"{width}x{height}+{x}+{y}")

        def t(self, key, **kwargs):
            lang_dict = LANGUAGES.get(self.current_lang, LANGUAGES["en"])
            text = lang_dict.get(key, LANGUAGES["en"].get(key, key))
            if kwargs:
                try:
                    return text.format(**kwargs)
                except Exception:
                    pass
            return text

        def build_ui(self):
            # Top Banner Frame
            banner = tk.Frame(self.root, bg=self.bg_card, height=72)
            banner.pack(fill="x", padx=16, pady=(14, 10))

            title_box = tk.Frame(banner, bg=self.bg_card)
            title_box.pack(side="left", padx=18, pady=10)

            self.lbl_title = tk.Label(
                title_box,
                text="🍝 CANNELLONI SD INSTALLER",
                font=("Segoe UI", 16, "bold"),
                bg=self.bg_card,
                fg=self.current_color
            )
            self.lbl_title.pack(anchor="w")

            self.lbl_subtitle = tk.Label(
                title_box,
                text="Universal Retro Handheld Setup Tool",
                font=("Segoe UI", 9),
                bg=self.bg_card,
                fg=self.text_muted
            )
            self.lbl_subtitle.pack(anchor="w")

            # Quick language pills in header
            lang_header_frame = tk.Frame(banner, bg=self.bg_card)
            lang_header_frame.pack(side="right", padx=18, pady=14)

            self.lang_buttons = {}
            for code in ["en", "es", "fr", "pt_BR", "de", "it"]:
                btn = tk.Button(
                    lang_header_frame,
                    text=code.upper().replace("_BR", ""),
                    font=("Segoe UI", 8, "bold"),
                    bd=0,
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    relief="flat",
                    command=lambda c=code: self.select_language(c)
                )
                btn.pack(side="left", padx=2)
                self.lang_buttons[code] = btn

            # Scrollable / Grid Content Area
            content_frame = tk.Frame(self.root, bg=self.bg_main)
            content_frame.pack(fill="both", expand=True, padx=16)

            # Left Column: Configuration Cards (Drive, Language, Accent, Device)
            left_col = tk.Frame(content_frame, bg=self.bg_main)
            left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

            # Right Column: Visual Live Handheld Mockup & Status
            right_col = tk.Frame(content_frame, bg=self.bg_main, width=280)
            right_col.pack(side="right", fill="both", padx=(0, 0))

            # ---------------- CARD 1: DRIVE SELECTION ----------------
            self.card_drive = self.create_card(left_col)
            self.card_drive.pack(fill="x", pady=(0, 10))

            self.lbl_card1_title = tk.Label(
                self.card_drive,
                text="1. Target SD Card",
                font=("Segoe UI", 11, "bold"),
                bg=self.bg_card,
                fg=self.text_primary
            )
            self.lbl_card1_title.pack(anchor="w", padx=14, pady=(10, 2))

            drive_row = tk.Frame(self.card_drive, bg=self.bg_card)
            drive_row.pack(fill="x", padx=14, pady=(2, 10))

            self.drive_var = tk.StringVar()
            self.drive_combo = ttk.Combobox(
                drive_row,
                textvariable=self.drive_var,
                state="readonly",
                font=("Segoe UI", 9)
            )
            self.drive_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_selected)

            self.btn_refresh = tk.Button(
                drive_row,
                text="🔄 Refresh",
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_card_inner,
                fg=self.text_primary,
                activebackground=self.border_card,
                activeforeground=self.text_primary,
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=self.refresh_drives
            )
            self.btn_refresh.pack(side="left", padx=(0, 4))

            self.btn_browse = tk.Button(
                drive_row,
                text="📁 Browse...",
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_card_inner,
                fg=self.text_primary,
                activebackground=self.border_card,
                activeforeground=self.text_primary,
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=self.browse_drive
            )
            self.btn_browse.pack(side="left")

            # ---------------- CARD 2: ACCENT COLOR ----------------
            self.card_color = self.create_card(left_col)
            self.card_color.pack(fill="x", pady=(0, 10))

            self.lbl_card2_title = tk.Label(
                self.card_color,
                text="2. Accent Color Theme",
                font=("Segoe UI", 11, "bold"),
                bg=self.bg_card,
                fg=self.text_primary
            )
            self.lbl_card2_title.pack(anchor="w", padx=14, pady=(10, 4))

            color_row = tk.Frame(self.card_color, bg=self.bg_card)
            color_row.pack(fill="x", padx=14, pady=(0, 12))

            self.color_swatches = {}
            for col in ACCENT_COLORS:
                hex_code = col["hex"]
                btn = tk.Button(
                    color_row,
                    text="●",
                    font=("Segoe UI", 16, "bold"),
                    fg=hex_code,
                    bg=self.bg_card_inner,
                    activebackground=hex_code,
                    activeforeground=self.bg_card,
                    bd=1,
                    relief="solid",
                    padx=6,
                    pady=0,
                    cursor="hand2",
                    command=lambda h=hex_code: self.select_accent_color(h)
                )
                btn.pack(side="left", padx=4)
                self.color_swatches[hex_code] = btn

            self.lbl_color_name = tk.Label(
                color_row,
                text=ACCENT_COLORS[0]["name"],
                font=("Segoe UI", 9, "bold"),
                bg=self.bg_card,
                fg=self.current_color
            )
            self.lbl_color_name.pack(side="left", padx=(10, 0))

            # ---------------- CARD 3: DEVICE MODEL ----------------
            self.card_device = self.create_card(left_col)
            self.card_device.pack(fill="both", expand=True, pady=(0, 10))

            self.lbl_card3_title = tk.Label(
                self.card_device,
                text="3. Handheld Console Model",
                font=("Segoe UI", 11, "bold"),
                bg=self.bg_card,
                fg=self.text_primary
            )
            self.lbl_card3_title.pack(anchor="w", padx=14, pady=(10, 4))

            device_row = tk.Frame(self.card_device, bg=self.bg_card)
            device_row.pack(fill="x", padx=14, pady=(0, 6))

            self.device_var = tk.StringVar(value=DEVICES[1]["name"])
            device_names = [f"{d['brand']}: {d['name']}" for d in DEVICES]
            self.device_combo = ttk.Combobox(
                device_row,
                textvariable=self.device_var,
                values=device_names,
                state="readonly",
                font=("Segoe UI", 9)
            )
            self.device_combo.pack(fill="x", expand=True)
            self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

            # Device details box
            self.dev_detail_box = tk.Frame(self.card_device, bg=self.bg_card_inner, bd=1, relief="solid")
            self.dev_detail_box.pack(fill="x", padx=14, pady=(4, 10))

            self.lbl_dev_specs = tk.Label(
                self.dev_detail_box,
                text=DEVICES[1]["desc"],
                font=("Segoe UI", 8),
                bg=self.bg_card_inner,
                fg=self.text_muted,
                padx=8,
                pady=6,
                wraplength=380,
                justify="left"
            )
            self.lbl_dev_specs.pack(anchor="w")

            # ---------------- RIGHT COLUMN: LIVE HANDHELD PREVIEW ----------------
            self.card_preview = self.create_card(right_col)
            self.card_preview.pack(fill="both", expand=True, pady=(0, 10))

            self.lbl_preview_header = tk.Label(
                self.card_preview,
                text="Live Handheld Preview",
                font=("Segoe UI", 10, "bold"),
                bg=self.bg_card,
                fg=self.text_primary
            )
            self.lbl_preview_header.pack(anchor="w", padx=12, pady=(10, 6))

            # Canvas Mockup of Cannelloni Handheld UI
            self.preview_canvas = tk.Canvas(
                self.card_preview,
                width=240,
                height=220,
                bg="#09090b",
                highlightthickness=1,
                highlightbackground="#27272a"
            )
            self.preview_canvas.pack(padx=12, pady=(0, 8))

            # Selected config summary under preview
            self.lbl_summary_device = tk.Label(
                self.card_preview,
                text="🎮 Miyoo Mini Plus",
                font=("Segoe UI", 8, "bold"),
                bg=self.bg_card,
                fg=self.text_primary
            )
            self.lbl_summary_device.pack(anchor="w", padx=14, pady=(2, 0))

            self.lbl_summary_lang = tk.Label(
                self.card_preview,
                text="🌐 English (en)",
                font=("Segoe UI", 8),
                bg=self.bg_card,
                fg=self.text_muted
            )
            self.lbl_summary_lang.pack(anchor="w", padx=14, pady=(1, 0))

            self.lbl_summary_color = tk.Label(
                self.card_preview,
                text=f"🎨 {self.current_color}",
                font=("Segoe UI", 8),
                bg=self.bg_card,
                fg=self.current_color
            )
            self.lbl_summary_color.pack(anchor="w", padx=14, pady=(1, 8))

            # ---------------- BOTTOM ACTION AREA ----------------
            bottom_frame = tk.Frame(self.root, bg=self.bg_main)
            bottom_frame.pack(fill="x", padx=16, pady=(0, 14))

            # Progress Bar (Canvas styled)
            self.progress_frame = tk.Frame(bottom_frame, bg=self.bg_main)
            self.progress_frame.pack(fill="x", pady=(0, 8))

            self.lbl_status = tk.Label(
                self.progress_frame,
                text="Ready to install",
                font=("Segoe UI", 9),
                bg=self.bg_main,
                fg=self.text_muted
            )
            self.lbl_status.pack(anchor="w", pady=(0, 4))

            self.progress_canvas = tk.Canvas(
                self.progress_frame,
                height=16,
                bg="#27272a",
                highlightthickness=0
            )
            self.progress_canvas.pack(fill="x")

            # Install Button
            self.btn_install = tk.Button(
                bottom_frame,
                text="⚡ Install Cannelloni to SD Card",
                font=("Segoe UI", 12, "bold"),
                bg=self.current_color,
                fg="#111111",
                activebackground="#ffffff",
                activeforeground="#111111",
                bd=0,
                pady=10,
                cursor="hand2",
                command=self.start_installation
            )
            self.btn_install.pack(fill="x")

        def create_card(self, parent):
            return tk.Frame(parent, bg=self.bg_card, bd=1, relief="solid")

        def update_progress_bar(self, pct):
            w = self.progress_canvas.winfo_width()
            if w <= 1:
                w = 780
            fill_w = int((pct / 100.0) * w)
            self.progress_canvas.delete("all")
            self.progress_canvas.create_rectangle(0, 0, fill_w, 16, fill=self.current_color, outline="")
            self.progress_canvas.create_text(w // 2, 8, text=f"{pct}%", fill="#111111" if pct > 50 else "#ffffff", font=("Segoe UI", 8, "bold"))

        def draw_handheld_preview(self):
            c = self.preview_canvas
            c.delete("all")
            w, h = 240, 220

            # Handheld Shell Outline
            c.create_rectangle(10, 10, w - 10, h - 10, outline="#27272a", fill="#121215", width=2)
            # Screen Bezel
            c.create_rectangle(24, 20, w - 24, h - 30, outline="#3f3f46", fill="#000000", width=1)

            # Top Bar: Cannelloni Title & Clock & Battery
            c.create_text(32, 32, text="Cannelloni", fill="#888888", font=("Segoe UI", 7, "bold"), anchor="w")
            c.create_text(w - 32, 32, text="12:00  [100%]", fill="#888888", font=("Segoe UI", 7), anchor="e")

            # Selection Pill in accent color!
            c.create_rectangle(34, 60, w - 34, 86, fill=self.current_color, outline="")

            # Menu items
            c.create_text(44, 73, text="▶  Games", fill="#111111" if self.current_color in ("#f1c40f", "#2ecc71", "#ffffff") else "#ffffff", font=("Segoe UI", 9, "bold"), anchor="w")
            c.create_text(44, 105, text="   Tools", fill="#aaaaaa", font=("Segoe UI", 9), anchor="w")
            c.create_text(44, 135, text="   Settings", fill="#aaaaaa", font=("Segoe UI", 9), anchor="w")

            # Bottom Keymon Hint Bar
            c.create_rectangle(25, h - 50, w - 25, h - 31, fill="#18181b", outline="")
            c.create_text(w // 2, h - 41, text="(A) Select    (B) Back", fill="#71717a", font=("Segoe UI", 7))

        def select_language(self, code):
            self.current_lang = code
            self.apply_language()

        def apply_language(self):
            # Update Header language button highlights
            for c, btn in self.lang_buttons.items():
                if c == self.current_lang:
                    btn.configure(bg=self.current_color, fg="#111111")
                else:
                    btn.configure(bg=self.bg_card_inner, fg=self.text_primary)

            self.lbl_title.configure(text=f"🍝 {self.t('title').upper()}")
            self.lbl_subtitle.configure(text=f"{self.t('subtitle')} · v{VERSION}")
            self.lbl_card1_title.configure(text=self.t("drive_section"))
            self.btn_refresh.configure(text=self.t("refresh"))
            self.btn_browse.configure(text=self.t("browse"))
            self.lbl_card2_title.configure(text=self.t("color_section"))
            self.lbl_card3_title.configure(text=self.t("device_section"))
            self.lbl_preview_header.configure(text=self.t("preview_title"))
            if not self.is_installing:
                self.btn_install.configure(text=self.t("install_btn"))
                self.lbl_status.configure(text=self.t("status_ready"))

            lang_name = LANGUAGES.get(self.current_lang, {}).get("name", self.current_lang)
            self.lbl_summary_lang.configure(text=f"🌐 {lang_name} ({self.current_lang})")

        def select_accent_color(self, hex_code):
            self.current_color = hex_code
            self.apply_accent_color_preview()

        def apply_accent_color_preview(self):
            # Update Swatches border
            for h, btn in self.color_swatches.items():
                if h == self.current_color:
                    btn.configure(relief="solid", bd=2, bg="#3f3f46")
                else:
                    btn.configure(relief="flat", bd=1, bg=self.bg_card_inner)

            col_obj = next((c for c in ACCENT_COLORS if c["hex"] == self.current_color), ACCENT_COLORS[0])
            self.lbl_color_name.configure(text=col_obj["name"], fg=self.current_color)
            self.lbl_title.configure(fg=self.current_color)
            self.btn_install.configure(bg=self.current_color)
            self.lbl_summary_color.configure(text=f"🎨 {self.current_color} ({col_obj['name']})", fg=self.current_color)

            # Re-highlight active lang button
            if self.current_lang in self.lang_buttons:
                self.lang_buttons[self.current_lang].configure(bg=self.current_color)

            self.draw_handheld_preview()
            self.update_progress_bar(0)

        def on_device_selected(self, event=None):
            idx = self.device_combo.current()
            if 0 <= idx < len(DEVICES):
                dev = DEVICES[idx]
                self.current_device_id = dev["id"]
                self.lbl_dev_specs.configure(text=dev["desc"])
                self.lbl_summary_device.configure(text=f"🎮 {dev['name']}")

        def refresh_drives(self):
            self.drives = detect_drives()
            options = [d["display"] for d in self.drives]
            self.drive_combo['values'] = options
            if options:
                rem_idx = next((i for i, d in enumerate(self.drives) if d.get("is_removable")), 0)
                self.drive_combo.current(rem_idx)
                self.selected_drive = self.drives[rem_idx]["path"]
            else:
                self.drive_var.set(self.t("no_drives"))
                self.selected_drive = None

        def browse_drive(self):
            folder = filedialog.askdirectory(title="Select SD Card Root Directory")
            if folder:
                self.selected_drive = folder
                self.drive_var.set(f"📁 Custom: {folder}")

        def on_drive_selected(self, event=None):
            idx = self.drive_combo.current()
            if 0 <= idx < len(self.drives):
                self.selected_drive = self.drives[idx]["path"]

        def start_installation(self):
            if self.is_installing:
                return

            if not self.selected_drive:
                messagebox.showerror("Error", self.t("error_no_drive"))
                return

            if not os.path.isdir(self.selected_drive):
                messagebox.showerror("Error", self.t("error_drive_not_found"))
                return

            # Warn if user selects internal/fixed drive
            drive_info = next((d for d in self.drives if d.get("path") == self.selected_drive), None)
            is_fixed = (drive_info and not drive_info.get("is_removable", True)) or (
                sys.platform == "win32" and self.selected_drive.upper().startswith("C:")
            )
            if is_fixed:
                confirm = messagebox.askyesno("Warning", self.t("warning_fixed", drive=self.selected_drive))
                if not confirm:
                    return

            zip_found = find_cannelloni_zip()
            if not zip_found:
                messagebox.showerror("Error", self.t("error_no_zip"))
                return

            self.is_installing = True
            self.btn_install.configure(state="disabled", text=self.t("installing"), bg="#555555")
            self.btn_refresh.configure(state="disabled")
            self.btn_browse.configure(state="disabled")

            def worker():
                try:
                    perform_installation(
                        target_path=self.selected_drive,
                        lang_code=self.current_lang,
                        accent_hex=self.current_color,
                        device_id=self.current_device_id,
                        progress_callback=lambda p: self.root.after(0, self.update_progress_bar, p),
                        status_callback=lambda s: self.root.after(0, self.lbl_status.configure, {"text": s})
                    )
                    self.root.after(0, self.on_install_success)
                except Exception as e:
                    self.root.after(0, self.on_install_error, str(e))

            threading.Thread(target=worker, daemon=True).start()

        def on_install_success(self):
            self.is_installing = False
            self.btn_install.configure(state="normal", text=self.t("install_btn"), bg=self.current_color)
            self.btn_refresh.configure(state="normal")
            self.btn_browse.configure(state="normal")
            self.update_progress_bar(100)
            self.lbl_status.configure(text=self.t("status_done"))

            dev_obj = next((d for d in DEVICES if d["id"] == self.current_device_id), DEVICES[0])
            msg = self.t(
                "success_msg",
                drive=self.selected_drive,
                device=dev_obj["name"],
                lang=self.current_lang,
                color=self.current_color
            )
            messagebox.showinfo(self.t("success_title"), msg)

        def on_install_error(self, err_msg):
            self.is_installing = False
            self.btn_install.configure(state="normal", text=self.t("install_btn"), bg=self.current_color)
            self.btn_refresh.configure(state="normal")
            self.btn_browse.configure(state="normal")
            self.lbl_status.configure(text=f"Error: {err_msg}")
            messagebox.showerror("Installation Failed", f"An error occurred during installation:\n\n{err_msg}")

def run_tkinter_gui():
    if not TKINTER_AVAILABLE:
        raise RuntimeError("Tkinter is not available on this system.")
    root = tk.Tk()
    app = CannelloniInstallerApp(root)
    root.mainloop()

# -----------------------------------------------------------------------------
# Local Lightweight Web GUI Fallback
# (Used when Tkinter/X11 is unavailable, e.g. headless or minimal Linux distros)
# -----------------------------------------------------------------------------

installer_state = {
    "status": "Ready",
    "progress": 0,
    "completed": False,
    "error": None
}

WEB_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cannelloni SD Installer</title>
<style>
:root {
  --bg-main: #141417;
  --bg-card: #1e1e24;
  --bg-inner: #272730;
  --border: #333340;
  --text: #f4f4f5;
  --muted: #9ca3af;
  --accent: #f1c40f;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
body { background: var(--bg-main); color: var(--text); padding: 20px; display: flex; justify-content: center; }
.container { max-width: 860px; width: 100%; }
.banner { background: var(--bg-card); border-radius: 10px; padding: 20px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border); margin-bottom: 20px; }
.banner h1 { font-size: 22px; color: var(--accent); margin-bottom: 4px; }
.banner p { font-size: 13px; color: var(--muted); }
.lang-chips { display: flex; gap: 6px; }
.lang-btn { background: var(--bg-inner); border: 1px solid var(--border); color: var(--text); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; }
.lang-btn.active { background: var(--accent); color: #111; border-color: var(--accent); }
.grid { display: grid; grid-template-columns: 1fr 280px; gap: 20px; }
.card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; margin-bottom: 16px; }
.card h2 { font-size: 15px; margin-bottom: 6px; }
.card p { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
select, input[type=text] { width: 100%; background: var(--bg-inner); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 6px; font-size: 14px; margin-bottom: 8px; }
.swatches { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.swatch { width: 34px; height: 34px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; transition: transform 0.15s; }
.swatch:hover { transform: scale(1.1); }
.swatch.active { border-color: #fff; box-shadow: 0 0 10px rgba(255,255,255,0.4); }
.device-desc { background: var(--bg-inner); border: 1px solid var(--border); padding: 10px; border-radius: 6px; font-size: 12px; color: var(--muted); }
.preview-box { background: #09090b; border: 1px solid #27272a; border-radius: 8px; padding: 14px; text-align: center; }
.preview-pill { background: var(--accent); color: #111; font-weight: bold; padding: 6px 12px; border-radius: 12px; margin: 10px 0; font-size: 13px; }
.btn-install { width: 100%; background: var(--accent); color: #111; font-weight: bold; border: none; padding: 14px; border-radius: 8px; font-size: 16px; cursor: pointer; transition: opacity 0.2s; margin-top: 10px; }
.btn-install:disabled { opacity: 0.5; cursor: not-allowed; }
.progress-bar-container { background: var(--bg-inner); border-radius: 6px; height: 16px; width: 100%; overflow: hidden; margin: 10px 0; border: 1px solid var(--border); }
.progress-bar { background: var(--accent); height: 100%; width: 0%; transition: width 0.2s; }
.status-text { font-size: 13px; color: var(--muted); min-height: 20px; }
</style>
</head>
<body>
<div class="container">
  <div class="banner">
    <div>
      <h1 id="app-title">🍝 CANNELLONI SD INSTALLER</h1>
      <p id="app-sub">Universal Retro Handheld Setup Tool</p>
    </div>
    <div class="lang-chips">
      <button class="lang-btn active" data-lang="en" onclick="setLang('en')">EN</button>
      <button class="lang-btn" data-lang="es" onclick="setLang('es')">ES</button>
      <button class="lang-btn" data-lang="fr" onclick="setLang('fr')">FR</button>
      <button class="lang-btn" data-lang="pt_BR" onclick="setLang('pt_BR')">PT</button>
      <button class="lang-btn" data-lang="de" onclick="setLang('de')">DE</button>
      <button class="lang-btn" data-lang="it" onclick="setLang('it')">IT</button>
    </div>
  </div>

  <div class="grid">
    <div class="config-col">
      <div class="card">
        <h2 id="card-drive-title">1. Target SD Card</h2>
        <p id="card-drive-desc">Select the removable drive for your handheld's SD card.</p>
        <select id="drive-select" onchange="onDriveChange()"></select>
        <div id="custom-drive-box" style="display:none;margin-top:6px;">
          <input type="text" id="custom-drive-input" placeholder="e.g. /media/user/SDCARD or E:\" />
        </div>
      </div>

      <div class="card">
        <h2 id="card-color-title">2. Accent Color Theme</h2>
        <p id="card-color-desc">Pick your favorite accent color for menu highlights.</p>
        <div class="swatches" id="color-swatches"></div>
      </div>

      <div class="card">
        <h2 id="card-device-title">3. Handheld Console Model</h2>
        <p id="card-device-desc">Select your exact handheld hardware to optimize drivers and controls.</p>
        <select id="device-select" onchange="onDeviceChange()"></select>
        <div class="device-desc" id="device-specs"></div>
      </div>
    </div>

    <div class="preview-col">
      <div class="card">
        <h2 id="card-preview-title">Live Preview</h2>
        <div class="preview-box">
          <div style="font-size:11px;color:#888;display:flex;justify-content:space-between;">
            <span>Cannelloni</span><span>12:00 [100%]</span>
          </div>
          <div class="preview-pill" id="preview-pill">▶ Games</div>
          <div style="font-size:12px;color:#888;text-align:left;padding-left:14px;line-height:22px;">
            <div>&nbsp;&nbsp;Tools</div>
            <div>&nbsp;&nbsp;Settings</div>
          </div>
        </div>
        <div style="margin-top:14px;font-size:12px;">
          <div id="summary-dev" style="font-weight:bold;margin-bottom:4px;">🎮 Miyoo Mini Plus</div>
          <div id="summary-lang" style="color:var(--muted);margin-bottom:4px;">🌐 English (en)</div>
          <div id="summary-color" style="color:var(--accent);">🎨 #f1c40f</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="status-text" id="status-text">Ready to install</div>
    <div class="progress-bar-container">
      <div class="progress-bar" id="progress-bar"></div>
    </div>
    <button class="btn-install" id="install-btn" onclick="startInstall()">⚡ Install Cannelloni to SD Card</button>
  </div>
</div>

<script>
let currentLang = 'en';
let currentColor = '#f1c40f';
let devices = [];
let colors = [];
let drives = [];
let translations = {};
let version = '';

async function init() {
  const res = await fetch('/api/init');
  const data = await res.json();
  devices = data.devices || [];
  colors = data.colors || [];
  drives = data.drives || [];
  translations = data.languages || {};
  version = data.version || '';
  document.title = 'Cannelloni SD Installer ' + version;
  
  // Render drives
  renderDrives();
  
  // Render colors
  const swatchBox = document.getElementById('color-swatches');
  swatchBox.innerHTML = colors.map(c => `
    <div class="swatch ${c.hex === currentColor ? 'active' : ''}" 
         style="background:${c.hex};" 
         title="${c.name}" 
         onclick="setColor('${c.hex}')"></div>
  `).join('');
  
  // Render devices
  const devSelect = document.getElementById('device-select');
  devSelect.innerHTML = devices.map(d => `<option value="${d.id}">${d.brand}: ${d.name}</option>`).join('');
  devSelect.value = 'miyoominiplus';
  onDeviceChange();
  applyLang();
}

function renderDrives() {
  const driveSelect = document.getElementById('drive-select');
  const customBox = document.getElementById('custom-drive-box');
  let options = '';
  if (drives.length > 0) {
    options = drives.map(d => `<option value="${d.path}">${d.display}</option>`).join('');
    options += `<option value="__custom__">📁 Enter Custom Path / Directory...</option>`;
    driveSelect.innerHTML = options;
    driveSelect.style.display = 'block';
    customBox.style.display = 'none';
  } else {
    driveSelect.innerHTML = `<option value="__custom__">📁 Enter Custom SD Path...</option>`;
    driveSelect.style.display = 'none';
    customBox.style.display = 'block';
  }
}

function onDriveChange() {
  const sel = document.getElementById('drive-select');
  const customBox = document.getElementById('custom-drive-box');
  if (sel.value === '__custom__') {
    customBox.style.display = 'block';
  } else {
    customBox.style.display = 'none';
  }
}

function getSelectedDrive() {
  const sel = document.getElementById('drive-select');
  if (sel.value === '__custom__' || drives.length === 0) {
    return document.getElementById('custom-drive-input').value.trim();
  }
  return sel.value;
}

function setColor(hex) {
  currentColor = hex;
  document.documentElement.style.setProperty('--accent', hex);
  document.querySelectorAll('.swatch').forEach(s => {
    s.classList.toggle('active', s.style.background === hex || s.getAttribute('title').includes(hex));
  });
  document.getElementById('summary-color').textContent = '🎨 ' + hex;
}

function setLang(code) {
  currentLang = code;
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-lang') === code);
  });
  applyLang();
}

function applyLang() {
  const dict = translations[currentLang] || translations['en'] || {};
  const t = (k, def) => dict[k] || def;
  document.getElementById('app-title').textContent = '🍝 ' + (t('title', 'Cannelloni SD Installer')).toUpperCase();
  document.getElementById('app-sub').textContent = t('subtitle', 'Universal Retro Handheld Setup Tool') + ' · v' + version;
  document.getElementById('card-drive-title').textContent = t('drive_section', '1. Target SD Card');
  document.getElementById('card-drive-desc').textContent = t('drive_desc', 'Select the removable drive for your handheld\'s SD card.');
  document.getElementById('card-color-title').textContent = t('color_section', '2. Accent Color Theme');
  document.getElementById('card-color-desc').textContent = t('color_desc', 'Pick your favorite accent color for menu highlights.');
  document.getElementById('card-device-title').textContent = t('device_section', '3. Handheld Console Model');
  document.getElementById('card-device-desc').textContent = t('device_desc', 'Select your exact handheld hardware to optimize drivers and controls.');
  document.getElementById('card-preview-title').textContent = t('preview_title', 'Live Preview');
  document.getElementById('install-btn').textContent = t('install_btn', '⚡ Install Cannelloni to SD Card');
  document.getElementById('summary-lang').textContent = '🌐 ' + (dict.name || currentLang) + ' (' + currentLang + ')';
}

function onDeviceChange() {
  const sel = document.getElementById('device-select');
  const d = devices.find(x => x.id === sel.value);
  if (d) {
    document.getElementById('device-specs').textContent = d.desc;
    document.getElementById('summary-dev').textContent = '🎮 ' + d.name;
  }
}

async function startInstall() {
  const drive = getSelectedDrive();
  const dict = translations[currentLang] || translations['en'] || {};
  if (!drive) {
    alert(dict.error_no_drive || 'Please select a valid SD card drive or folder.');
    return;
  }
  const dev = document.getElementById('device-select').value;
  const btn = document.getElementById('install-btn');
  btn.disabled = true;
  btn.textContent = dict.installing || 'Installing Cannelloni...';
  
  const resp = await fetch('/api/install', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({drive, lang: currentLang, color: currentColor, device: dev})
  });
  if (!resp.ok) {
    const err = await resp.json();
    alert('Error: ' + (err.error || 'Failed to start installation'));
    btn.disabled = false;
    btn.textContent = dict.install_btn || '⚡ Install Cannelloni to SD Card';
    return;
  }
  
  pollProgress();
}

async function pollProgress() {
  const res = await fetch('/api/progress');
  const data = await res.json();
  const dict = translations[currentLang] || translations['en'] || {};
  document.getElementById('status-text').textContent = data.status;
  document.getElementById('progress-bar').style.width = data.progress + '%';
  
  if (data.completed) {
    const msg = (dict.success_msg || 'Installation Complete! Buon appetito!')
      .replace('{drive}', getSelectedDrive())
      .replace('{device}', document.getElementById('device-select').selectedOptions[0].text)
      .replace('{lang}', currentLang)
      .replace('{color}', currentColor);
    alert(dict.success_title + '\n\n' + msg);
    document.getElementById('install-btn').disabled = false;
    document.getElementById('install-btn').textContent = dict.install_btn || '⚡ Install Cannelloni to SD Card';
  } else if (data.error) {
    alert('Error: ' + data.error);
    document.getElementById('install-btn').disabled = false;
    document.getElementById('install-btn').textContent = dict.install_btn || '⚡ Install Cannelloni to SD Card';
  } else {
    setTimeout(pollProgress, 400);
  }
}

init();
</script>
</body>
</html>
"""

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode("utf-8"))
        elif url.path == "/api/init":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "version": VERSION,
                "devices": DEVICES,
                "colors": ACCENT_COLORS,
                "drives": detect_drives(),
                "languages": LANGUAGES,
                "currentLang": "en"
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif url.path == "/api/progress":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(installer_state).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/install":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            params = json.loads(body.decode('utf-8'))
            
            drive = params.get("drive", "").strip()
            if not drive:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Target drive path cannot be empty."}')
                return

            installer_state["status"] = "Starting installation..."
            installer_state["progress"] = 0
            installer_state["completed"] = False
            installer_state["error"] = None

            def worker():
                try:
                    perform_installation(
                        target_path=params["drive"],
                        lang_code=params["lang"],
                        accent_hex=params["color"],
                        device_id=params["device"],
                        progress_callback=lambda p: installer_state.update({"progress": p}),
                        status_callback=lambda s: installer_state.update({"status": s})
                    )
                    installer_state["completed"] = True
                    installer_state["progress"] = 100
                except Exception as e:
                    installer_state["error"] = str(e)

            threading.Thread(target=worker, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "started"}')

def run_web_gui():
    server = HTTPServer(("127.0.0.1", 0), WebHandler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    print(f"\n==========================================")
    print(f" Cannelloni Web Installer running on:")
    print(f" {url}")
    print(f"==========================================\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web installer...")

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

def main():
    if "--web" in sys.argv:
        run_web_gui()
        return

    # Attempt native desktop Tkinter GUI
    try:
        run_tkinter_gui()
    except Exception as e:
        print(f"Tkinter unavailable or failed ({e}). Falling back to local Web GUI...")
        run_web_gui()

if __name__ == "__main__":
    main()
