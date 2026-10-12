Cannelloni is a minimal launcher for the Trimui Smart (and Pro) and Brick, the Miyoo Mini (and Plus), A30, and Flip, the Powkiddy RGB30, the M17, the MagicX XU Mini M and Mini Zero 28, and the Anbernic RG*XX family--all from the same SD card. Why? Why not?

Source:
https://github.com/Denarmo/cannelloni-linux

----------------------------------------
Installing

UNIVERSAL ONE-ZIP INSTALLATION

Cannelloni features a universal single-zip installation method. You are no longer required to identify or manually copy device-specific folders!

1. Format your SD card as FAT32 (MBR).
2. Simply extract the unified Cannelloni release zip (or copy the release zip / Cannelloni.zip) directly to the root of your SD card.
   - All bootstrap files (.tmp_update, miyoo, trimui, dmenu.bin, etc.) and system packages are bundled together.
3. Insert the SD card into your device and power it on.
4. On initial boot, Cannelloni presents an interactive on-screen Device Selector.
   - Use the D-pad to highlight your console model and press A (INSTALL).
   - Cannelloni will automatically configure the exact hardware drivers, display settings, and platform files.
5. If you ever want to reconfigure your hardware or switch devices, simply navigate to Settings -> Device Model.

SUPPORTED HARDWARE:
- Miyoo Mini (v1 / v2 / v3)
- Miyoo Mini Plus (v4 / Wi-Fi)
- Miyoo A30 (my282)
- Miyoo Flip (my355)
- TrimUI Smart
- TrimUI Smart Pro
- TrimUI Brick
- Anbernic RG35XX (Original)
- Anbernic RG35XX Plus / H / SP / CubeXX / 28XX
- Powkiddy RGB30
- MagicX XU Mini M
- MagicX Mini Zero 28
- GKD Pixel
- M17

TWO-CARD DEVICES (RG35XX / RGB30 / MagicX):
- For devices using two SD cards, the primary Cannelloni installation goes on the TF2 card.
- For RG35XX Plus/H/SP, dmenu.bin is included in the root of the archive and can be placed on the TF1 card.

FEATURES & SETTINGS:
- Shaders: 12 high-performance CRT, scanline, and LCD shaders from Denarmo/cannelloni, configurable under Settings -> Shaders.
- Secure Wi-Fi: Network credentials are obfuscated and stored securely in .userdata/shared/.cannelloni/network.conf with 0600 permissions.
- Theme Accents: Solid accent colors configurable under Settings -> Accent Color.
- Emulators: Choose between Libretro core and DraStic for NDS under Settings -> Emulators.
- Button Swapping: Swap A/B and X/Y under Settings -> Button Mapping.

----------------------------------------
Updating

ALL

Copy "Cannelloni.zip" (without unzipping) to the root of the SD card containing your Roms.

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
 
