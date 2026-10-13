# Cannelloni 1.0.0

Cannelloni now uses semantic version numbers. This release brings the SD installer, Nintendo DS launcher, and in-game shader menu together with builds from the current source.

## What's new

- **One installer payload.** The desktop installer reads the bundled `Cannelloni.zip` directly; the installer package no longer includes duplicate loose OS files. Legacy `Cannoli.zip` payloads are also recognized. Language, accent, and device selections are applied after extraction.
- **Nintendo DS in the OS menu.** DS games default to a libretro core through minarch. Builds use melonDS where the compiler supports it and DeSmuME2015 on older toolchains. Old packaged DraStic defaults migrate to libretro; standalone DraStic remains an explicit option under Settings → Emulators.
- **Working in-game shaders.** Open MENU → Shaders to choose a preset and edit its supported parameters. CRT-Cannelloni, Lite, CRT, LCD, dot-matrix, scanline, and sharp-bilinear effects are portable software adaptations of the Android Cannelloni shader work. Save settings for a game or console, or set shared defaults in Settings → Shaders.
- **Consistent 1.0.0 branding.** Installer, OS version information, release filenames, and build workflow read the same version source.
- **Updated documentation.** The README includes an installer walkthrough, screenshots, device notes, and the new features. MagicX installer profiles now correctly identify XU Mini M and include Mini Zero 28.
- **Source-built release frontends.** Packaging requires freshly compiled launcher and minarch binaries plus architecture-checked DS cores. Accent themes cannot replace the frontends with stale copies.

## Download and install

**Recommended: `Cannelloni-Installer.zip`**

1. Back up your SD card and use the partition/stock boot setup required by your handheld. The installer copies files; it does not format or partition the card.
2. Extract the installer package into a folder on your computer. Keep `Cannelloni.zip` and `VERSION` beside the installer; do not unpack the inner ZIP.
3. On Windows, run `Cannelloni-Installer.exe`. On Linux, run `bash Cannelloni-Installer.sh` with Python 3 installed (Tkinter is recommended; a local browser interface is available as fallback).
4. Select the correct SD card, language, accent color, and handheld model. Click **Install Cannelloni to SD Card** and wait for completion.
5. Safely eject the card and follow the model-specific boot instructions in the README.

For manual setup, `Cannelloni-1.0.0.zip` and `Cannelloni.zip` are the unified release wrapper. Extract that outer archive at the SD-card root and follow its device-specific bootstrap instructions. Existing installations can use the inner payload for an update.

[Full installer and device guide](https://github.com/Denarmo/cannelloni-linux#installation)

## Compatibility notes

- Software shaders are off by default. Full CRT/glow effects use more CPU; Lite and Zfast presets are available for slower devices. Handheld performance still needs testing per model.
- Libretro and standalone DraStic save states use different formats. Keep a backup before switching emulator paths.
- Host regression tests and release archive verification cover packaging, routing, configuration, and rendering. These checks do not replace testing on physical handhelds.
- ROMs and BIOS files are not included. Original shader notices and component licenses are included.
