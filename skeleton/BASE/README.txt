Cannelloni 1.0.0

Cannelloni is a focused retro gaming launcher and libretro frontend for supported Linux handhelds. The release includes separate platform builds, a desktop SD installer, Nintendo DS integration, and configurable software shader effects.

Source:
https://github.com/Denarmo/cannelloni-linux

----------------------------------------
Installing

DESKTOP INSTALLER (WINDOWS / LINUX)

Download Cannelloni-Installer.zip from:
https://github.com/Denarmo/cannelloni-linux/releases/tag/v1.0.0

1. Extract the installer package to a folder on your computer. Keep its bundled
   Cannelloni.zip beside the installer, compressed. Cannoli.zip is also accepted.
   This archive is the only OS payload; no loose duplicate OS files are needed.
2. Prepare a FAT32 SD card for your device. The installer does not format the
   card or replace its underlying firmware. Back up existing Saves and .userdata
   first; installation replaces system files and applies fresh settings.
3. Windows: launch Cannelloni-Installer.exe (no Python required), or the .bat.
   Linux: run bash Cannelloni-Installer.sh (requires Python 3).
   Python source: run python3 cannelloni_installer.py.
   Install Tkinter for the native window, or add --web for the local browser UI.
4. Select the SD card drive/mount directory, language, accent color, and handheld.
5. Check the destination, then click Install Cannelloni to SD Card.
6. Wait for success. Add your games and BIOS files, safely eject the card, and
   complete any separate boot-card setup before starting the handheld.

If the source ZIP is in the destination SD root, a successful installation
renames it to .zip.installed (adding a number when needed). Its bytes are
preserved, and it will not trigger another installation at first boot. The
installer can reuse it later. ZIPs on your computer keep their original names.

MANUAL FIRST INSTALLATION

1. Download Cannelloni-1.0.0.zip and extract the outer archive to the card root,
   including hidden folders. Leave the inner Cannelloni.zip compressed.
2. Retain the supplied boot files appropriate to your device. A blank card with
   only a ZIP is not sufficient on all handhelds.
3. Complete the device boot setup and start the handheld. Where supported, its
   updater extracts the OS payload and starts the device setup screen.

SUPPORTED PLATFORM TARGETS

- Miyoo Mini / Mini Plus (miyoomini), A30 (my282), Flip (my355)
- TrimUI Smart (trimuismart), Smart Pro / Brick (tg5040)
- Original Anbernic RG35XX (rg35xx)
- Anbernic H700 RG*XX family, including Plus / H / SP / CubeXX / 28XX (rg35xxplus)
- Powkiddy RGB30 (rgb30)
- MagicX XU Mini M (magicmini), Mini Zero 28 (zero28)
- GKD Pixel (gkdpixel), M17 (m17)

TWO-CARD DEVICES

Cannelloni is a frontend/data-card installation, not a replacement firmware
image. Devices such as RGB30 and MagicX require their compatible boot card.
On a two-card Anbernic setup, install the OS/data to TF2 and use the matching
boot files on TF1. The supplied root dmenu.bin is for supported H700 models,
including RG35XX Plus/H/SP; do not use it for the original RG35XX.

FEATURES AND SETTINGS

- Nintendo DS defaults to a libretro core through minarch and the OS menu.
  Builds use melonDS with modern C++17 toolchains and DeSmuME2015 with older
  toolchains. Compatibility and speed depend on the core and handheld.
- Old packaged DraStic defaults migrate to libretro. On Miyoo Mini devices with
  DraStic installed, Settings -> Emulators explicitly selects standalone mode.
  DraStic and libretro save states are not interchangeable.
- In-game MENU -> Shaders selects CRT, LCD, scanline, and pixel effects. Parameters
  exposes the selected preset's intensity, curvature, brightness, mask, and glow
  controls. Resume to see changes. Save for game/console saves all current
  frontend/core options, including shaders; Reset shaders restores defaults.
- Settings -> Shaders chooses shared defaults, below saved console/game choices.
  Effects are software adaptations of Denarmo/cannelloni, not GPU GLSL execution.
  They start disabled; heavy effects may reduce performance. See
  .system/common/shaders/README.txt for adaptation details and licenses.
- Change accent color, language, model, and A/B or X/Y mapping from Settings.
- Wi-Fi controls and Nonna's Kitchen are available on supported network devices.

----------------------------------------
Updating

Back up Saves and .userdata before updating. Extract the downloaded release or
installer package on your computer. Copy the INNER OS payload Cannelloni.zip,
without unzipping it, to the root of your already working Cannelloni card and
boot the handheld. The downloadable release asset named Cannelloni.zip is an
alias of the OUTER package; extract that package first to obtain the payload.

----------------------------------------
Shortcuts

For devices without a dedicated MENU button

	RGB30: use L3 or R3 for MENU
	M17:   use + or - for MENU

RGB30 / MIYOO MINI PLUS / RG35XX (PLUS) / TRIMUI SMART PRO / TRIMUI BRICK / GKD PIXEL / MIYOO A30 / MAGICX XU MINI M / MIYOO FLIP / MAGICX MINI ZERO 28
  
  Brightness: MENU + VOLUME UP
                  or VOLUME DOWN
  
MIYOO MINI / TRIMUI SMART / M17

  Volume: SELECT + L or R
  Brightness: START + L or R

RGB30 / MIYOO MINI (PLUS) / RG35XX (PLUS) / TRIMUI SMART PRO / TRIMUI BRICK / GKD PIXEL / MIYOO A30 / MAGICX XU MINI M / MIYOO FLIP / MAGICX MINI ZERO 28
  
  Sleep: POWER
  Wake: POWER
  
TRIMUI SMART / M17
  
  Sleep: MENU (twice)
  Wake: MENU

TRIMUI SMART PRO / TRIMUI BRICK

  Mute: FN switch (volume and rumble)

----------------------------------------
Quicksave & auto-resume

Cannelloni will create a quicksave when powering off in-game. The next time you power on the device it will automatically resume from where you left off. A quicksave is created when powering off manually or automatically after a short sleep. On devices without a POWER button (eg. the Trimui Smart or M17) press the MENU button twice to put the device to sleep before flipping the POWER switch.

----------------------------------------
Roms

Included in this zip is a "Roms" folder containing folders for each console Cannelloni currently supports. You can rename these folders but you must keep the uppercase tag name in parentheses in order to retain the mapping to the correct emulator (eg. "Nintendo Entertainment System (FC)" could be renamed to "Nintendo (FC)", "NES (FC)", or "Famicom (FC)"). 

When one or more folder share the same display name (eg. "Game Boy Advance (GBA)" and "Game Boy Advance (MGBA)") they will be combined into a single menu item containing the roms from both folders (continuing the previous example, "Game Boy Advance"). This allows opening specific roms with an alternate pak.

----------------------------------------
Bios

Some emulators require or perform much better with official bios. Cannelloni is strictly BYOB. Place the bios for each system in a folder that matches the tag in the corresponding "Roms" folder name (eg. bios for "Sony PlayStation (PS)" roms goes in "/Bios/PS/"),

Bios file names are case-sensitive:

   FC: disksys.rom
   GB: gb_bios.bin
  GBA: gba_bios.bin
  GBC: gbc_bios.bin
   MD: bios_CD_E.bin
       bios_CD_J.bin
       bios_CD_U.bin
  NDS: bios7.bin
       bios9.bin
       firmware.bin
   PS: psxonpsp660.bin

----------------------------------------
Settings Menu, Wi-Fi & Accent Color

Press the MENU button in the launcher to open the Settings menu. Here you can:
- Toggle Nonna's Kitchen (Web management server on port 1091) on or off
- View Wi-Fi status and connect/reconnect on supported devices
- Customize the accent color (default: Cannelloni Gold #f1c40f)
- Swap A/B or X/Y button mappings
- Select default emulators (e.g. Libretro melonDS / DeSmuME vs standalone DraStic)
- View system hardware model, release, and commit info

To manually set a custom accent color, place the color definition in "/.userdata/shared/.cannelloni/accent_color.txt".

----------------------------------------
Nonna's Kitchen (Web Management Service)

Nonna's Kitchen hosts a built-in web management interface running on port 1091 (matching the Cannelloni web interface at https://github.com/Denarmo/cannelloni). It allows managing ROMs, saves, states, and BIOS files directly from any web browser on your phone, tablet, or PC without removing your SD card.

To use:
1. Ensure your device is connected to Wi-Fi.
2. Launch "Nonna's Kitchen" from the Tools menu.
3. Open any web browser on your computer or phone and navigate to:
   http://<DEVICE_IP>:1091
4. Enjoy drag-and-drop file upload, file browsing, and instant storage management.


----------------------------------------
Disc-based games

To streamline launching multi-file disc-based games with Cannelloni place your bin/cue (and/or iso/wav files) in a folder with the same name as the cue file. Cannelloni will automatically launch the cue file instead of navigating into the folder when selected, eg. 

  Harmful Park (English v1.0)/
    Harmful Park (English v1.0).bin
    Harmful Park (English v1.0).cue

For multi-disc games, put all the files for all the discs in a single folder. Then create an m3u file in that folder (just a text file containing the relative path to each disc's cue file on a separate line) with the same name as the folder. Instead of showing the entire messy contents of the folder, Cannelloni will launch the appropriate cue file, eg. For a "Policenauts" folder structured like this:

  Policenauts (English v1.0)/
    Policenauts (English v1.0).m3u
    Policenauts (Japan) (Disc 1).bin
    Policenauts (Japan) (Disc 1).cue
    Policenauts (Japan) (Disc 2).bin
    Policenauts (Japan) (Disc 2).cue

The m3u file would contain just:

  Policenauts (Japan) (Disc 1).cue
  Policenauts (Japan) (Disc 2).cue

When a multi-disc game is detected the in-game menu's Continue item will also show the current disc. Press left or right to switch between discs.

Cannelloni also supports chd files and official pbp files (multi-disc pbp files larger than 2GB are not supported). Regardless of the multi-disc file format used, every disc of the same game share the same memory card and save state slots.

----------------------------------------
Collections

A collection is just a text file containing an ordered list of full paths to rom, cue, or m3u files. These text files live in the "Collections" folder at the root of your SD card, eg. "/Collections/Metroid series.txt" might look like this:

  /Roms/GBA/Metroid Zero Mission.gba
  /Roms/GB/Metroid II.gb
  /Roms/SNES (SFC)/Super Metroid.sfc
  /Roms/GBA/Metroid Fusion.gba

----------------------------------------

Display names

Certain (unsupported arcade) cores require roms to use arcane file names. You can override the display name used throughout Cannelloni by creating a map.txt in the same folder as the files you want to rename. One line per file, `rom.ext` followed by a single tab followed by `Display Name`. You can hide a file by adding a `.` at the beginning of the display name. eg.
	
  neogeo.zip	.Neo Geo Bios
  mslug.zip	Metal Slug
  sf2.zip	Street Fighter II

----------------------------------------
Simple mode

Not simple enough for you (or maybe your kids)? Cannelloni has a simple mode that hides the Tools folder and replaces Options in the in-game menu with Reset. Perfect for handing off to littles (and olds too I guess). Just create an empty file named "enable-simple-mode" (no extension) in "/.userdata/shared/".

----------------------------------------
Advanced

Cannelloni can automatically run a user-authored shell script on boot. Just place a file named "auto.sh" in "/.userdata/<DEVICE>/". If you're on Windows, make sure your text editor uses Unix line-endings (eg. `\n`), these devices usually choke on Windows line-endings (eg. `\r\n`).

----------------------------------------
Thanks

To eggs, for his NEON scalers, years of top-notch example code, and patience in the face of my endless questions.

Check out eggs' releases (includes source code): 

  RG35XX https://www.dropbox.com/sh/3av70t99ffdgzk1/AAAKPQ4y0kBtTsO3e_Xlrhqha
  Miyoo Mini https://www.dropbox.com/sh/hqcsr1h1d7f8nr3/AABtSOygIX_e4mio3rkLetWTa
  Trimui Model S https://www.dropbox.com/sh/5e9xwvp672vt8cr/AAAkfmYQeqdAalPiTramOz9Ma

To neonloop, for putting together the original Trimui toolchain from which I learned everything I know about docker and buildroot and is the basis for every toolchain I've put together since, and for picoarch, the inspiration for minarch.

Check out neonloop's repos: 

  https://git.crowdedwood.com

To adixial and acmeplus and the entire muOS community, for sharing their discoveries for the h700 family of Anbernic devices.

Check out muOS and Knulli:

	https://muos.dev
	https://knulli.org

To fewt and the entire JELOS community, for JELOS (without which Cannelloni would not exist on the RGB30) and for sharing their knowledge with this perpetual Linux kernel novice.

Check out JELOS:

  https://github.com/JustEnoughLinuxOS/distribution

To Steward, for maintaining exhaustive documentation on a plethora of devices:

	https://steward-fu.github.io/website/

To Gamma, for his efforts unlocking more performance on the MagicX XU Mini M (before we all realized its RG3562 was surreptitiously an RK3266).

Check out his repos (including GammaOS):

	https://github.com/TheGammaSqueeze/

To BlackSeraph, for introducing me to chroot.

Check out the GarlicOS repos:

	https://github.com/GarlicOS

To Jim Gray, for commiserating during development, for early alpha testing, and for providing the soundtrack for much of Cannelloni's development.

Check out Jim's music: 

  https://ourghosts.bandcamp.com/music
  https://www.patreon.com/ourghosts/
