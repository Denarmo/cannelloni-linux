# Cannelloni 1.0.1

This bug-fix release corrects device installation, theme colors, network tools, and emulator video handling.

## Fixes

- **Correct accent colors.** Native menus tint an immutable neutral spritesheet, avoiding double tinting and color buildup around rounded corners. Installer and on-device presets now match.
- **Visible Wi-Fi progress.** Connection screens show the current stage and result, with managed status messages that do not cover the network picker or keyboard.
- **Nonna’s Kitchen file browser.** The web API handles encoded filenames on legacy BusyBox, runs CGI from executable temporary storage, reports request failures, and reads file metadata without scanning entire ROMs.
- **Kitchen shutdown.** Closing its screen stops the exact web-server process it started. Settings and Tools open the same service.
- **Only the selected device’s files.** The installer filters platform binaries, tools, settings, boot files, theme widgets, and emulator folders. Existing unrelated files on a card are preserved.
- **Complete Miyoo emulator selection.** Base and optional upstream emulator packs are included with their matching cores and ROM/BIOS/save folders, instead of exposing only GBA, DS, and PlayStation.
- **GBA and in-game overlay crash fix.** A malformed menu-loop condition could read past the end of the menu items. The loop now stops at the correct item. The frontend also owns the last video frame, declines unsupported direct framebuffer requests, and handles missing frames and changed geometry.
- **Miyoo Nintendo DS startup.** Mini/Plus explicitly use DeSmuME2015 with its supported ARM JIT build instead of the generic melonDS selection. DS startup displays progress and reports a core that fails to produce a frame within 60 seconds, returning to the launcher instead of leaving an indefinite black screen.

## Download and install

The only download is **Cannelloni-Installer.zip**. Extract it on your computer, keep its bundled `Cannelloni.zip` and `VERSION` beside the installer, select your device and SD card, and install. Windows includes an executable; Linux uses `bash Cannelloni-Installer.sh` with Python 3.

For a manual first installation, extract the bundled `Cannelloni.zip` to the SD root, including hidden files and the boot files needed by your device. Also copy the compressed `Cannelloni.zip` to the root so the device can perform its first-boot installation steps. Complete any separate boot-card setup before starting. Existing working cards can update by copying the bundled compressed archive to the root and booting. The desktop installer selects device-specific files automatically.

Back up saves and settings first. The installer does not format the card. Previous unrelated platform folders already on the card are preserved; a fresh target receives only the selected device’s files.

[Full installer and device guide](https://github.com/Denarmo/cannelloni-linux#installation)

## Validation and compatibility

Release publication requires host regression tests, all 12 platform builds, a Windows installer build, and verification of the exact packaged binaries and emulator cores. Physical Miyoo Mini/Plus testing is still needed to confirm the reported GBA and DS failures are resolved on hardware; these changes address identified source defects and build configuration, not a device-reproduced crash trace.

Software shaders remain off by default. DS speed and compatibility depend on the game and device. ROMs and BIOS files are not included. Libretro and standalone DraStic save states are not interchangeable.
