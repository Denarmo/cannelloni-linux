# Cannelloni 1.0.2

This bug-fix release stops Nintendo DS games crashing on Miyoo Mini/Plus and TrimUI Smart, including the crash when opening the in-game menu.

## Fixes

- **DS frames fit the screen.** A portrait DS frame (256x384) could be scaled to a surface larger than the fixed video page on Miyoo Mini Plus and TrimUI Smart, so the first frame wrote past it and the game crashed before the in-game menu could open. The scaler now steps down until the frame fits.
- **Tall frames are cropped, not overrun.** Native mode crops tall frames to the screen. Miyoo Mini and RG35XX apply the crop offset, and TrimUI Smart crops before rotating.
- **DS layout changes apply live.** Changing the screen layout in the core options updates the aspect ratio and scaler instead of keeping the old geometry.
- **Games with a raw `.sav` start.** When `Saves/NDS/<game>.sav` exists without a `.dsv` (for example a save written by melonDS on earlier builds), DeSmuME 2015 no longer crashes while importing it. The save is still converted.
- **DS core loads on 128MB devices.** The DeSmuME 2015 ARM JIT reserved about 256MB of memory up front, so Miyoo Mini could refuse to load the core and return to the launcher. The table is now allocated lazily.
- **Smaller stability fixes.** The DS loading message no longer reads freed memory, save states no longer close an uninitialized file when a large state cannot be allocated, and unbound buttons no longer trigger an invalid shift.

## Download and install

The only download is **Cannelloni-Installer.zip**. Extract it on your computer, keep its bundled `Cannelloni.zip` and `VERSION` beside the installer, select your device and SD card, and install. Windows includes an executable; Linux uses `bash Cannelloni-Installer.sh` with Python 3.

For a manual first installation, extract the bundled `Cannelloni.zip` to the SD root, including hidden files and the boot files needed by your device. Also copy the compressed `Cannelloni.zip` to the root so the device can perform its first-boot installation steps. Complete any separate boot-card setup before starting. Existing working cards can update by copying the bundled compressed archive to the root and booting. The desktop installer selects device-specific files automatically.

Back up saves and settings first. The installer does not format the card. Previous unrelated platform folders already on the card are preserved; a fresh target receives only the selected device’s files.

[Full installer and device guide](https://github.com/Denarmo/cannelloni-linux#installation)

## Validation and compatibility

Release publication requires host regression tests, all 12 platform builds, a Windows installer build, and verification of the exact packaged binaries and emulator cores. These fixes address identified source defects; physical Miyoo Mini/Plus and TrimUI Smart testing is still needed to confirm the DS crashes are resolved on hardware.

DS speed and compatibility depend on the game and device. ROMs and BIOS files are not included. Libretro and standalone DraStic save states are not interchangeable.
