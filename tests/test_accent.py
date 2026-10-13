"""Render real UI sprites with SDL; exercise repeated changes and PNG formats."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    return re.search(r"^(?:static )?[^\n;]+\b" + name + r"\([^\n]*\)\s*\{.*?^\}",
                     source, re.M | re.S)[0]


class AccentTests(unittest.TestCase):
    def test_palette_matches_installer_and_theme_assets(self):
        source = (ROOT / "workspace/all/cannelloni/cannelloni.c").read_text()
        presets = source.split("static AccentPreset accent_presets[] = {", 1)[1].split("};", 1)[0]
        colors = re.findall(r'"(#[0-9a-f]{6})"', presets)
        spec = importlib.util.spec_from_file_location("accent_installer", ROOT / "installer/cannelloni_installer.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(set(colors), {color["hex"] for color in module.ACCENT_COLORS})
        for color in colors:
            for scale in range(1, 5):
                self.assertTrue((ROOT / f"skeleton/SYSTEM/res/themes/{color}/assets@{scale}x.png").is_file())

    def test_real_sdl_tinting_and_accent_config(self):
        compiler = shutil.which("gcc")
        if not compiler:
            self.skipTest("GCC required")
        env = dict(os.environ)
        if os.name == "nt":
            spec = importlib.util.find_spec("pygame")
            include = ROOT / "build_release/syntax"
            if not spec or not (include / "SDL2/SDL.h").is_file():
                self.skipTest("Windows needs pygame SDL DLLs and SDL2 headers")
            runtime = Path(spec.origin).parent
            flags = ["-I", str(include), str(runtime / "SDL2.dll"), str(runtime / "SDL2_image.dll")]
            env["PATH"] = str(runtime) + os.pathsep + env.get("PATH", "")
        else:
            try:
                flags = shlex.split(subprocess.check_output(
                    ["pkg-config", "--cflags", "--libs", "sdl2", "SDL2_image"], text=True, stderr=subprocess.PIPE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.skipTest("SDL2 and SDL2_image development packages required")
        with tempfile.TemporaryDirectory(prefix="accent regression ") as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "skeleton/SYSTEM/res/themes/#ffffff", root / "themes/#ffffff")
            # Simulate a red installer selection; native drawing must ignore it.
            for path in (ROOT / "skeleton/SYSTEM/res/themes/#e74c3c").glob("assets@*.png"):
                shutil.copyfile(path, root / path.name)
            api = (ROOT / "workspace/all/common/api.c").read_text()
            source = r'''
#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>
#include <assert.h>
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MAX_PATH 1024
#define LOG_error(...) ((void)0)
static int test_scale;
#define FIXED_SCALE test_scale
static struct {SDL_Surface *screen, *assets, *assets_orig;} gfx;
enum {ASSET_WHITE_PILL, ASSET_BAR, ASSET_BUTTON};
static SDL_Rect asset_rects[3];
static uint32_t asset_rgbs[3], RGB_ACCENT;
static SDL_Color COLOR_ACCENT_CURRENT;
static int exists(const char *p) {FILE *f=fopen(p,"rb");if(f)fclose(f);return f!=NULL;}
static void getFile(const char *p,char *out,int cap) {FILE*f=fopen(p,"rb");assert(f);size_t n=fread(out,1,cap-1,f);out[n]=0;fclose(f);}
''' + "\n#define RES_PATH " + json.dumps(root.as_posix()) + "\n#define ACCENT_COLOR_PATH RES_PATH \"/accent.txt\"\n"
            source += "\n".join(function(api, name) for name in (
                "GFX_tintAssetRect", "GFX_initAssets", "GFX_setAccentColor", "GFX_loadAccentColor"))
            source += r'''
static uint32_t pixel(SDL_Surface *surface,int x,int y) {
    return *(uint32_t*)((uint8_t*)surface->pixels+y*surface->pitch+x*4);
}
static void expect_color(int r,int g,int b) {
    assert(COLOR_ACCENT_CURRENT.r==r && COLOR_ACCENT_CURRENT.g==g && COLOR_ACCENT_CURRENT.b==b);
    uint8_t pr,pg,pb,pa;
    SDL_GetRGBA(pixel(gfx.assets,15*test_scale,15*test_scale),gfx.assets->format,&pr,&pg,&pb,&pa);
    assert(pr==r && pg==g && pb==b && pa==255);
    assert(RGB_ACCENT==SDL_MapRGB(gfx.screen->format,r,g,b));
    for(int i=0;i<3;i++)assert(asset_rgbs[i]==RGB_ACCENT);
}
static void config(const char *text,int r,int g,int b) {
    FILE*f=fopen(ACCENT_COLOR_PATH,"wb");assert(f);fputs(text,f);fclose(f);
    GFX_loadAccentColor();expect_color(r,g,b);
}
int main(void) {
    SDL_SetMainReady();assert(SDL_Init(0)==0);
    gfx.screen=SDL_CreateRGBSurface(0,640,480,16,0xf800,0x07e0,0x001f,0);
    for(test_scale=1;test_scale<=4;test_scale++) {
        int s=test_scale;
        asset_rects[0]=(SDL_Rect){s,s,30*s,30*s};
        asset_rects[1]=(SDL_Rect){33*s,58*s,4*s,4*s};
        asset_rects[2]=(SDL_Rect){s,33*s,20*s,20*s};
        GFX_initAssets();assert(gfx.assets && gfx.assets_orig);
        assert(gfx.assets->format->BytesPerPixel==4);
        GFX_setAccentColor(52,152,219);expect_color(52,152,219);
        size_t size=gfx.assets->pitch*gfx.assets->h;
        void *blue=malloc(size);memcpy(blue,gfx.assets->pixels,size);
        GFX_setAccentColor(241,196,15);expect_color(241,196,15);
        GFX_setAccentColor(255,255,255);expect_color(255,255,255);
        // Alpha edges and corners must not accumulate old color or opacity.
        assert(!memcmp(gfx.assets->pixels,gfx.assets_orig->pixels,size));
        GFX_setAccentColor(52,152,219);
        assert(!memcmp(blue,gfx.assets->pixels,size));free(blue);
        config("#e74c3c\r\n",231,76,60);
        config("3498db\n",52,152,219);
        config("46,204,113\n",46,204,113);
        config("999,0,0",241,196,15);
        config("#3498dbgarbage",241,196,15);
        SDL_FreeSurface(gfx.assets);SDL_FreeSurface(gfx.assets_orig);
    }
    // An indexed asset must be expanded before direct pixel tinting.
    test_scale=1;
    asset_rects[0]=(SDL_Rect){1,1,30,30};
    asset_rects[1]=(SDL_Rect){33,58,4,4};
    asset_rects[2]=(SDL_Rect){1,33,20,20};
    SDL_Surface *indexed=SDL_CreateRGBSurface(0,128,128,8,0,0,0,0);
    SDL_Color white={255,255,255,255};SDL_SetPaletteColors(indexed->format->palette,&white,0,1);
    SDL_FillRect(indexed,NULL,0);
    assert(SDL_SaveBMP(indexed,RES_PATH "/themes/#ffffff/assets@1x.png")==0);
    SDL_FreeSurface(indexed);
    GFX_initAssets();assert(gfx.assets->format->BytesPerPixel==4);
    GFX_setAccentColor(52,152,219);expect_color(52,152,219);
    SDL_FreeSurface(gfx.assets);SDL_FreeSurface(gfx.assets_orig);SDL_FreeSurface(gfx.screen);
    return 0;
}
'''
            code = root / "accent.c"
            code.write_text(source)
            executable = root / "accent.exe"
            result = subprocess.run([compiler, "-std=c99", "-Wall", str(code), *flags, "-o", str(executable)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(executable)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
