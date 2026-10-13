Cannelloni 1.0.0 SD Installer

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
   Check the destination, then select Install Cannelloni to SD Card.
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

For a manual first installation, download Cannelloni-1.0.0.zip and extract the
outer package to the card root, including hidden folders. Leave its inner
Cannelloni.zip compressed with the device boot files. Follow the model notes
in the online guide; copying only a ZIP to a blank card is not sufficient on
all devices.

To update an already working Cannelloni card, back up your data and copy the
inner Cannelloni.zip payload from this package to the SD root, then boot the
handheld. The release asset also named Cannelloni.zip is an outer package;
extract it on your computer first to obtain that inner payload.

Source: https://github.com/Denarmo/cannelloni-linux
