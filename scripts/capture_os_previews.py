"""Capture the real minarch shader menus without emulating a handheld.

The C harness compiles unchanged menu and drawing functions extracted from the
current source, with the repository's font and sprites. Only the platform/input
hooks are fixtures: 640x480, Wi-Fi connected, battery 80%, gold accent, and a
scripted selection. These are source-rendered desktop previews, not device tests.

Windows prerequisites: GCC, pygame's SDL2 runtime DLLs, and official SDL2,
SDL2_image and SDL2_ttf headers under <include>/SDL2. Example:
  python scripts/capture_os_previews.py --sdl-include build_release/syntax
Linux prerequisites: GCC and SDL2/image/ttf development packages plus pkg-config.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    match = re.search(r"^(?:static )?(?:inline )?[^\n;]+\b" + name
                      + r"\([^\n]*\)\s*\{.*?^\}", source, re.M | re.S)
    if not match:
        raise ValueError(f"Source function not found: {name}")
    return match[0]


def generate(build):
    menu = (ROOT / "workspace/all/minarch/minarch.c").read_text()
    api = (ROOT / "workspace/all/common/api.c").read_text()
    (build / "platform.h").write_text("""#ifndef PLATFORM_H
#define PLATFORM_H
#define FIXED_SCALE 2
#define FIXED_WIDTH 640
#define FIXED_HEIGHT 480
#define FIXED_BPP 2
#define FIXED_DEPTH 16
#define FIXED_PITCH 1280
#define FIXED_SIZE (640*480*2)
#define SDCARD_PATH "."
#define BTN_MOD_VOLUME BTN_SELECT
#define BTN_MOD_BRIGHTNESS BTN_START
#endif
""")
    harness = r'''#define SDL_MAIN_HANDLED
#define USE_SDL2
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <pthread.h>
#include "defines.h"
#include "api.h"
#include "shader.h"
#undef RES_PATH
#undef FONT_PATH
#define RES_PATH "skeleton/SYSTEM/res"
#define FONT_PATH RES_PATH "/BPreplayBold-unhinted.otf"
static char* output_file;
static SDL_Surface* screen;
static int frame, desired_row;
static void Menu_beforeSleep(void) {}
static void Menu_afterSleep(void) {}
static void hdmimon(void) {}
static void OptionSaveChanges_updateDesc(void) {}
static int exists(const char* p) {FILE*f=fopen(p,"rb");if(f)fclose(f);return f!=NULL;}
static void getFile(const char*p,char*out,int cap) {FILE*f=fopen(p,"rb");if(f){size_t n=fread(out,1,cap-1,f);out[n]=0;fclose(f);}}
void LOG_note(int n,const char*fmt,...) {}
void PLAT_initLid(void) {}
SDL_Surface* PLAT_initVideo(void) {return SDL_CreateRGBSurface(0,640,480,16,0xF800,0x07E0,0x001F,0);}
void PLAT_clearVideo(SDL_Surface*s) {SDL_FillRect(s,NULL,0);}
void PLAT_pollInput(void) {frame++;}
int PAD_justRepeated(int b) {return b==BTN_DOWN && frame>1 && frame<=desired_row+1;}
int PAD_justPressed(int b) {return b==BTN_B && frame>desired_row+1;}
int PAD_justReleased(int b) {return 0;}
void PWR_update(int*d,int*s,PWR_callback_t b,PWR_callback_t a) {}
int GetHDMI(void) {return 0;}
int GetBrightness(void) {return 6;}
int GetVolume(void) {return 8;}
int PLAT_isOnline(void) {return 1;}
void GFX_startFrame(void) {}
void GFX_sync(void) {}
void GFX_flip(SDL_Surface*s) {if(IMG_SavePNG(s,output_file)) {fprintf(stderr,"save: %s\n",IMG_GetError());exit(1);}}
'''
    # These constants and all visible rendering/layout code come from source.
    for source, name in ((api, "MAX_TEXT_LINES"), (menu, "OPTION_PADDING")):
        harness += re.search(r"^#define " + name + r" .+$", source, re.M)[0] + "\n"
    harness += api[api.index("uint32_t RGB_WHITE;"):api.index("static int _;")]
    harness += "\n".join(function(api, name) for name in (
        "GFX_tintAssetRect", "GFX_initAssets", "GFX_setAccentColor", "GFX_loadAccentColor", "GFX_init",
        "GFX_setMode", "GFX_blitAsset", "GFX_blitPill", "GFX_blitBattery",
        "GFX_blitHardwareGroup", "GFX_sizeText", "GFX_blitText"))
    start = menu.index("typedef struct Option {")
    end = menu.index("\n};", menu.index("\tFE_OPT_COUNT,", start)) + 3
    harness += menu[start:end]
    start = menu.index("\t.frontend = {", menu.index("static struct Config"))
    end = menu.index("\t.core = {", start)
    harness += '''static char* overclock_labels[]={"Powersave","Normal","Performance",NULL};
static char* gamepad_labels[]={"Standard","DualShock",NULL};
static char* gamepad_values[]={"1","517",NULL};
static char* button_labels[]={"NONE",NULL};
static struct {OptionList frontend;} config={
''' + menu[start:end] + "};\n"
    harness += menu[menu.index("typedef struct MenuList MenuList;"):
                    menu.index("static int Menu_message(")]
    harness += '''static int Menu_options(MenuList* list);
static int screen_effect = SHADER_CANNELLONI;
static int Menu_message(char*m,char**p){return 0;}
static int OptionShaders_choosePreset(MenuList*l,int i){return 0;}
static int OptionShaders_changed(MenuList*l,int i){return 0;}
static int OptionShaders_saveConsole(MenuList*l,int i){return 0;}
static int OptionShaders_saveGame(MenuList*l,int i){return 0;}
static int OptionShaders_reset(MenuList*l,int i){return 0;}
'''
    harness += "\n".join(function(menu, name) for name in (
        "OptionShaders_presets", "OptionShaders_parameters", "OptionShaders_openMenu", "Menu_options"))
    harness += r'''int main(int argc,char**argv) {
if(argc<3)return 2;
output_file=argv[2]; desired_row=argc>3?atoi(argv[3]):0;
SDL_SetMainReady(); SDL_Init(0); screen=GFX_init(MODE_MENU); pwr.charge=80;
if(!screen||!gfx.assets||!font.small){fprintf(stderr,"init: %s / %s\n",SDL_GetError(),TTF_GetError());return 1;}
if(!strcmp(argv[1],"shaders"))OptionShaders_openMenu(NULL,0);
else if(!strcmp(argv[1],"parameters"))OptionShaders_parameters(NULL,0);
else if(!strcmp(argv[1],"presets")) {MenuItem item={0};MenuList l={.items=&item};OptionShaders_presets(&l,0);}
return 0;
}
'''
    source = build / "capture.c"
    source.write_text(harness)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdl-include", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".github/resources/screenshots")
    args = parser.parse_args()
    build = ROOT / "build_release/os_preview"
    build.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    source = generate(build)
    executable = build / ("capture.exe" if os.name == "nt" else "capture")
    command = [shutil.which("gcc") or "gcc", "-std=gnu99", "-O2", "-I", str(build),
               "-I", str(ROOT / "workspace/all/common"),
               "-I", str(ROOT / "workspace/all/minarch"), str(source),
               str(ROOT / "workspace/all/minarch/shader.c")]
    env = dict(os.environ)
    if os.name == "nt":
        spec = importlib.util.find_spec("pygame")
        if not spec or not args.sdl_include:
            parser.error("Windows needs pygame and --sdl-include pointing to official SDL2 headers")
        runtime = Path(spec.origin).parent
        command += ["-I", str(args.sdl_include.resolve())]
        command += [str(runtime / name) for name in ("SDL2.dll", "SDL2_image.dll", "SDL2_ttf.dll")]
        env["PATH"] = str(runtime) + os.pathsep + env.get("PATH", "")
    else:
        flags = subprocess.check_output(["pkg-config", "--cflags", "--libs", "sdl2",
                                         "SDL2_image", "SDL2_ttf"], text=True)
        command += shlex.split(flags)
    command += ["-lm", "-o", str(executable)]
    subprocess.run(command, cwd=ROOT, check=True)
    for menu, filename, selected in (("shaders", "os-shaders.png", 0),
                                     ("presets", "os-shader-presets.png", 3),
                                     ("parameters", "os-shader-parameters.png", 4)):
        path = args.output.resolve() / filename
        subprocess.run([str(executable), menu, str(path), str(selected)], cwd=ROOT, env=env, check=True)
        print(path)


if __name__ == "__main__":
    main()
