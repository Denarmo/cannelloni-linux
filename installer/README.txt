Cannelloni 1.0.2 SD Installer

Full illustrated guide:
https://github.com/Denarmo/cannelloni-linux#install-with-the-desktop-installer

1. Extract Cannelloni-Installer.zip into a folder on your computer. Keep the
   bundled Cannelloni.zip and VERSION file beside the installer. Do not extract
   that inner ZIP: it contains the OS, and the installer reads it directly. Legacy payloads
   named Cannoli.zip are also supported.
2. Insert a FAT32 SD card prepared for your handheld. This tool does not format
   it or replace its underlying firmware. Back up existing Saves and .userdata
   first: installation replaces system files and applies fresh settings.
3. Windows: run Cannelloni-Installer.exe (no Python required), or the .bat.
   Linux: run bash Cannelloni-Installer.sh (requires Python 3).
   Source: run python3 cannelloni_installer.py. Tkinter provides the native
   window; --web opens the local browser interface directly.
4. Select your SD card drive or mounted directory, language, accent, and model.
   Check the destination, then select Install Cannelloni to SD Card. Only that
   model's system, emulator packs, tools, and boot files are copied, with shared
   resources and ROM/BIOS/save folders for its complete emulator suite.
5. Wait for the success message. Add your own games to the supplied Roms folders
   and any required BIOS files to Bios. Safely eject the card.
6. Complete the handheld's boot-card setup, insert the card, and power on.

Devices with a separate boot card still need it. For supported Anbernic H700
models, including RG35XX Plus/H/SP, the supplied root dmenu.bin belongs on TF1
when the OS/data card is TF2. The original RG35XX uses different boot files.
RGB30 and MagicX also need a compatible boot environment; this package is not
a replacement firmware image.

When running the installer from the destination card root, a successful install
preserves its source ZIP under .zip.installed (plus a number if needed). That
avoids a second installation at first boot. It can be reused on a later run.
ZIPs outside the destination root keep their original names.

The GitHub release offers one download: Cannelloni-Installer.zip. Its bundled
Cannelloni.zip is also the manual installation and update source.

For a manual first installation, extract that inner Cannelloni.zip to the card
root, including hidden folders. Also copy the compressed Cannelloni.zip itself
to the root so the handheld can complete its installation at first boot. Follow
the model-specific boot setup in the online guide; copying only a ZIP to a blank
card is not sufficient on all devices. Manual extraction includes all devices;
the desktop installer selects only the files needed for your chosen model.

To update an already working Cannelloni card, back up your data and copy the
bundled Cannelloni.zip to the SD root, then boot the handheld.

Source: https://github.com/Denarmo/cannelloni-linux
