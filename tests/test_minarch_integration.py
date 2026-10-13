"""Compile the actual minarch config/menu/video functions with small host stubs."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MINARCH = ROOT / "workspace/all/minarch"


def function(source, name):
    match = re.search(r"^static [^\n]+\b" + name + r"\([^\n]*\)\s*\{.*?^\}", source, re.S | re.M)
    if not match:
        raise AssertionError(f"Function not found: {name}")
    return match.group(0)


@unittest.skipUnless(shutil.which("gcc"), "Native gcc is required")
class MinarchIntegrationTests(unittest.TestCase):
    def build_and_run(self, source, shader=False, files=None):
        with tempfile.TemporaryDirectory(prefix="minarch integration ") as directory:
            root = Path(directory)
            code = root / "harness.c"
            code.write_text(source, encoding="utf-8")
            binary = root / "harness.exe"
            command = [shutil.which("gcc"), "-std=c99", "-I", str(MINARCH), str(code), "-o", str(binary)]
            if shader:
                command += [str(MINARCH / "shader.c"), "-lm"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name, content in (files or {}).items():
                path = root / ".cannelloni" / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(content)
            result = subprocess.run([str(binary), str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_config_precedence_legacy_values_and_menu_parameters(self):
        source = (MINARCH / "minarch.c").read_text()
        utils = (ROOT / "workspace/all/common/utils.c").read_text()
        start = source.index("typedef struct Option {")
        enum_end = source.index("\n};", source.index("\tFE_OPT_COUNT,", start)) + 3
        option_types = source[start:enum_end]
        frontend_start = source.index("\t.frontend = {", source.index("static struct Config"))
        frontend_end = source.index("\t.core = {", frontend_start)
        menu_types = source[source.index("typedef struct MenuList MenuList;"):source.index("static int Menu_message(")]
        config_functions = "\n".join(function(source, name) for name in (
            "Config_getValue", "Config_syncFrontend", "Config_readOptionsString", "Config_readShaderFile", "Config_readOptions"))
        menu_functions = "\n".join(function(source, name) for name in (
            "OptionFrontend_optionChanged", "OptionShaders_changed", "OptionShaders_choosePreset", "OptionShaders_parameters"))
        newline_functions = "\n".join(re.search(r"^void " + name + r"\(.*?^\}", utils, re.S | re.M).group(0)
                                      for name in ("normalizeNewline", "trimTrailingNewlines"))
        harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shader.h"
#define MAX_PATH 1024
#define LOG_info(...) ((void)0)
#define SHARPNESS_SHARP 0
#define VSYNC_LENIENT 1
#define EFFECT_NONE 0
#define SCALE_NATIVE 0
static char *shared;
#define SHARED_USERDATA_PATH shared
static int screen_effect, screen_scaling, screen_sharpness, prevent_tearing;
static int thread_video, was_threaded, toggle_thread, overclock, show_debug, max_ff_speed;
static int has_custom_controllers, gamepad_type, platform_effect = -1;
static char *gamepad_values[] = {"1", "517"};
static char *overclock_labels[] = {"Powersave", "Normal", "Performance", NULL};
static ShaderSettings shader_settings = {SHADER_NONE, 50, 0, 100, 50, 25};
static struct { int dst_p; } renderer;
static struct { const char *tag; void (*set_controller_port_device)(int, int); } core;
static int exactMatch(char *a, char *b) { return !strcmp(a, b); }
static void GFX_setSharpness(int value) { (void)value; }
static void GFX_setEffect(int value) { platform_effect = value; }
''' + option_types + '''
static struct { OptionList frontend, core; char *system_cfg, *default_cfg, *user_cfg; } config = {
''' + source[frontend_start:frontend_end] + '''
    .core = {.options = (Option[]){{0}}}
};
static void OptionList_setOptionValue(OptionList *list, const char *key, const char *value) { assert(0); }
static Option *OptionList_getOption(OptionList *list, const char *key) {
    for (int i=0; list->options[i].key; i++) if (!strcmp(list->options[i].key,key)) return &list->options[i];
    return NULL;
}
''' + newline_functions + config_functions + menu_types + r'''
static int visible_parameters, messages;
static int Menu_message(char *message, char **pairs) { messages++; return MENU_CALLBACK_NOP; }
static int Menu_options(MenuList *list) {
    visible_parameters = 0;
    for (int i=0; list->items[i].name; i++) visible_parameters++;
    return 0;
}
''' + menu_functions + r'''
int main(int argc, char **argv) {
    shared = argv[1]; core.tag = "NDS";
    char defaults[] = "minarch_screen_effect = \"3\"\r\ncannelloni_shader_intensity = \"2\"\r\n";
    Config_readOptionsString(defaults);
    assert(screen_effect == SHADER_CANNELLONI && shader_settings.intensity == 75);
    char invalid[] = "minarch_screen_effect = not-a-preset\ncannelloni_shader_intensity = 999\n";
    Config_readOptionsString(invalid);
    assert(screen_effect == SHADER_CANNELLONI && shader_settings.intensity == 75);
    char labels[] = "minarch_screen_effect = LCD3x\r\ncannelloni_shader_mask = 75%\r\n";
    Config_readOptionsString(labels);
    assert(screen_effect == SHADER_LCD3X && shader_settings.mask == 75);
    assert(platform_effect == EFFECT_NONE);

    config.default_cfg = defaults;
    Config_readOptions();
    assert(screen_effect == SHADER_ZFAST_LCD && shader_settings.intensity == 50);
    char user[] = "minarch_screen_effect = CRT-Cannelloni\ncannelloni_shader_brightness = 125%\n";
    config.user_cfg = user;
    Config_readOptions();
    assert(screen_effect == SHADER_CANNELLONI && shader_settings.brightness == 125);
    config.frontend.options[FE_OPT_EFFECT].lock = 1;
    Config_readShaderFile("shader.conf");
    assert(screen_effect == SHADER_CANNELLONI);
    OptionShaders_choosePreset(NULL, SHADER_DOT);
    assert(screen_effect == SHADER_CANNELLONI);
    config.frontend.options[FE_OPT_EFFECT].lock = 0;
    OptionShaders_choosePreset(NULL, SHADER_DOT);
    assert(screen_effect == SHADER_DOT);

    OptionShaders_parameters(NULL, 0);
    assert(visible_parameters == 3); /* intensity, brightness, glow */
    config.frontend.options[FE_OPT_GLOW].lock = 1;
    OptionShaders_parameters(NULL, 0);
    assert(visible_parameters == 2);
    OptionShaders_choosePreset(NULL, SHADER_NONE);
    OptionShaders_parameters(NULL, 0);
    assert(messages == 1);
    return 0;
}
'''
        self.build_and_run(harness, shader=True, files={
            "shader.conf": b"preset=lcd3x\r\nintensity=25\r\n",
            "shader_nds.conf": b"preset=zfast-lcd\r\nintensity=50\r\n",
        })

    def test_config_save_preserves_existing_files_on_failure(self):
        source = (MINARCH / "minarch.c").read_text()
        save_functions = "\n".join(function(source, name) for name in (
            "Config_getPath", "Config_write"))
        callbacks = "\n".join(function(source, name) for name in (
            "OptionShaders_saveConsole", "OptionShaders_saveGame", "OptionSaveChanges_onConfirm"))
        harness = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <io.h>
#define native_unlink _unlink
#else
#include <unistd.h>
#define native_unlink unlink
#endif
#undef MAX_PATH
#define MAX_PATH 1024
#define LOG_info(...) ((void)0)
#define LOCAL_BUTTON_COUNT 2
enum { CONFIG_WRITE_ALL, CONFIG_WRITE_GAME };
enum { CONFIG_NONE, CONFIG_CONSOLE, CONFIG_GAME };
enum { MENU_CALLBACK_NOP, MENU_CALLBACK_EXIT };
typedef struct { char *key; char **values; int value; } Option;
typedef struct { Option *options; } OptionList;
typedef struct { char *name; int local, mod; } ButtonMapping;
typedef struct { int unused; } MenuList;
static char *effect_values[] = {"None", "CRT-Cannelloni", NULL};
static char *brightness_values[] = {"100%", "125%", NULL};
static char *core_values[] = {"disabled", "enabled", NULL};
static Option frontend_options[] = {{"minarch_screen_effect", effect_values, 1},
    {"cannelloni_shader_brightness", brightness_values, 1}, {0}};
static Option core_options[] = {{"test_core_option", core_values, 1}, {0}};
static ButtonMapping controls[] = {{"A", 0, 0}, {0}};
static ButtonMapping shortcuts[] = {{"Save State", -1, 0}, {0}};
static char *button_labels[] = {"NONE", "A", "B", NULL};
static int has_custom_controllers = 1, gamepad_type;
static struct { char *config_dir; } core;
static struct { char *name; } game = {"Test Game"};
static struct {
    char *device_tag; int loaded; OptionList frontend, core;
    ButtonMapping *controls, *shortcuts;
} config = {"unit", CONFIG_GAME, {frontend_options}, {core_options}, controls, shortcuts};
static int fail_open, fail_stream, fail_close, fail_rename, fail_unlink;
static FILE *save_fopen(const char *path, const char *mode) {
    if (fail_open) { errno = EACCES; return NULL; }
    return fopen(path, mode);
}
static int save_ferror(FILE *file) { return fail_stream || ferror(file); }
static int save_fclose(FILE *file) {
    int result = fclose(file); return fail_close ? EOF : result;
}
static int save_rename(const char *source, const char *target) {
    if (fail_rename) { errno = EACCES; return -1; }
#ifdef _WIN32
    /* Match the device's POSIX rename replacement semantics on this host. */
    if (!MoveFileExA(source, target, MOVEFILE_REPLACE_EXISTING)) {
        errno = EACCES; return -1;
    }
    return 0;
#else
    return rename(source, target);
#endif
}
static int save_unlink(const char *path) {
    if (fail_unlink && !strstr(path, ".tmp")) { errno = EACCES; return -1; }
    return native_unlink(path);
}
static void save_sync(void) {}
#define fopen save_fopen
#define ferror save_ferror
#define fclose save_fclose
#define rename save_rename
#define unlink save_unlink
#define sync save_sync
''' + save_functions + r'''
#undef fopen
#undef ferror
#undef fclose
#undef rename
#undef unlink
#undef sync
static char last_message[128];
static int descriptions;
static int Menu_message(char *message, char **pairs) {
    snprintf(last_message, sizeof(last_message), "%s", message); return MENU_CALLBACK_NOP;
}
static void Config_restore(void) { assert(0); }
static void OptionSaveChanges_updateDesc(void) { descriptions++; }
''' + callbacks + r'''
static char console_path[MAX_PATH], game_path[MAX_PATH], temporary[MAX_PATH+5];
static void write_file(const char *path, const char *text) {
    FILE *file = fopen(path, "wb"); assert(file);
    assert(fputs(text, file) >= 0); assert(!fclose(file));
}
static int file_exists(const char *path) {
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    fclose(file); return 1;
}
static void expect_file(const char *path, const char *expected) {
    char data[2048] = {0}; FILE *file = fopen(path, "rb"); assert(file);
    size_t size = fread(data, 1, sizeof(data)-1, file);
    assert(!ferror(file)); assert(!fclose(file));
    assert(size == strlen(expected) && !strcmp(data, expected));
}
static void reset_files(void) {
    fail_open = fail_stream = fail_close = fail_rename = fail_unlink = 0;
    config.loaded = CONFIG_GAME;
    write_file(console_path, "old console\n"); write_file(game_path, "old game\n");
    snprintf(temporary, sizeof(temporary), "%s.tmp", console_path); native_unlink(temporary);
}
static void expect_failure_preserved(void) {
    assert(config.loaded == CONFIG_GAME);
    expect_file(console_path, "old console\n"); expect_file(game_path, "old game\n");
    assert(!file_exists(temporary));
}
int main(int argc, char **argv) {
    core.config_dir = argv[1];
    Config_getPath(console_path, CONFIG_WRITE_ALL); Config_getPath(game_path, CONFIG_WRITE_GAME);
    const char *saved = "minarch_screen_effect = CRT-Cannelloni\n"
        "cannelloni_shader_brightness = 125%\n"
        "test_core_option = enabled\nminarch_gamepad_type = 0\n"
        "bind A = A\nbind Save State = NONE\n";
    reset_files(); fail_open = 1;
    assert(!Config_write(CONFIG_WRITE_ALL)); expect_failure_preserved();
    reset_files(); fail_stream = 1;
    assert(!Config_write(CONFIG_WRITE_ALL)); expect_failure_preserved();
    reset_files(); fail_close = 1;
    assert(!Config_write(CONFIG_WRITE_ALL)); expect_failure_preserved();
    reset_files(); fail_rename = 1;
    assert(!Config_write(CONFIG_WRITE_ALL)); expect_failure_preserved();
    reset_files();
    assert(Config_write(CONFIG_WRITE_GAME)); assert(config.loaded == CONFIG_GAME);
    expect_file(game_path, saved); expect_file(console_path, "old console\n");
    reset_files();
    assert(Config_write(CONFIG_WRITE_ALL));
    assert(config.loaded == CONFIG_CONSOLE && !file_exists(game_path));
    expect_file(console_path, saved); assert(!file_exists(temporary));
    reset_files(); fail_unlink = 1;
    assert(!Config_write(CONFIG_WRITE_ALL)); assert(config.loaded == CONFIG_GAME);
    expect_file(game_path, "old game\n"); expect_file(console_path, saved);
    reset_files(); fail_open = 1;
    OptionShaders_saveConsole(NULL, 0);
    assert(strstr(last_message, "Could not save")); expect_failure_preserved();
    OptionShaders_saveGame(NULL, 0);
    assert(strstr(last_message, "Could not save")); expect_failure_preserved();
    OptionSaveChanges_onConfirm(NULL, 0);
    assert(strstr(last_message, "Could not save")); expect_failure_preserved();
    OptionSaveChanges_onConfirm(NULL, 1);
    assert(strstr(last_message, "Could not save")); expect_failure_preserved();
    assert(descriptions == 2);
    reset_files();
    OptionShaders_saveConsole(NULL, 0);
    assert(!strcmp(last_message, "Saved for console."));
    assert(config.loaded == CONFIG_CONSOLE && !file_exists(game_path));
    OptionShaders_saveGame(NULL, 0);
    assert(!strcmp(last_message, "Saved for game.")); expect_file(game_path, saved);
    return 0;
}
'''
        self.build_and_run(harness)

    def test_pixel_format_negotiation_padded_frames_and_debug_overlay(self):
        source = (MINARCH / "minarch.c").read_text()
        buffer_functions = "\n".join(function(source, name) for name in ("buffer_dealloc", "buffer_realloc", "buffer_downsample"))
        callback = function(source, "video_refresh_callback_main")
        environment = function(source, "environment_callback")
        # Compile the production negotiation branch without unrelated core APIs.
        pixel_format = environment[environment.index("\tcase RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:"):
                                   environment.index("\tcase RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:")]
        harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define FIXED_BPP 2
#define LOG_info(...) ((void)0)
#define RETRO_ENVIRONMENT_SET_PIXEL_FORMAT 10
enum retro_pixel_format {
    RETRO_PIXEL_FORMAT_0RGB1555 = 0,
    RETRO_PIXEL_FORMAT_XRGB8888 = 1,
    RETRO_PIXEL_FORMAT_RGB565 = 2
};
static void *buffer;
static size_t buffer_size;
static int downsample, fast_forward, show_debug, thread_video, fps_ticks;
static double fps_double, cpu_double;
static int use_double, resizes, debug_writes, expected_pitch = 4;
static struct { int true_w,true_h,src_p,dst_p,src_x,src_y,src_w,src_h,dst_x,dst_y,dst_w,dst_h,scale; void *src,*dst; } renderer;
static struct { void *pixels; } screen_data, *screen = &screen_data;
static void Special_render(void) {}
static uint32_t SDL_GetTicks(void) { return 50; }
static void GFX_clearAll(void) {}
static void GFX_flip(void *s) {}
static void blitBitmapText(char *s,int x,int y,uint16_t *p,int pitch,int w,int h) {
    assert(downsample && p == buffer && pitch == 2 && w == 2 && h == 2);
    p[0] = 0;
    debug_writes++;
}
static bool environment_callback(unsigned cmd,void *data) {
    switch (cmd) {
''' + pixel_format + r'''
    default: return false;
    }
    return true;
}
''' + buffer_functions + r'''
static void selectScaler(int w,int h,int pitch) {
    if (downsample) buffer_realloc(w,h,pitch);
    resizes++;
    renderer.true_w=w; renderer.true_h=h; renderer.src_p=pitch; renderer.dst_p=640;
}
static void Shader_blit(void) {
    uint16_t expected[] = {0xf800,0x07e0,0x001f,0xffff};
    if (show_debug) expected[0] = 0;
    assert(renderer.src_p == expected_pitch);
    for(int y=0;y<2;y++) for(int x=0;x<2;x++) {
        uint16_t actual;
        memcpy(&actual,(char*)renderer.src+y*renderer.src_p+x*2,2);
        assert(actual == expected[y*2+x]);
    }
}
''' + callback + r'''
int main(void) {
    enum retro_pixel_format rgb565 = RETRO_PIXEL_FORMAT_RGB565;
    enum retro_pixel_format xrgb8888 = RETRO_PIXEL_FORMAT_XRGB8888;
    enum retro_pixel_format unsupported = RETRO_PIXEL_FORMAT_0RGB1555;
    enum retro_pixel_format unknown = (enum retro_pixel_format)99;
    uint16_t native[] = {0xf800,0x07e0,0x001f,0xffff};
    assert(environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&rgb565));
    assert(!downsample);
    video_refresh_callback_main(native,2,2,4);
    assert(resizes == 1 && !buffer && renderer.src == native);
    assert(!environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&unsupported));
    assert(!environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&unknown));
    assert(!environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,NULL));
    assert(!downsample && renderer.dst_p == 640);

    /* melonDS requests XRGB8888 during load_game. Its converted pitch matches
       the preceding RGB565 frame, but negotiation must still allocate storage. */
    assert(environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&xrgb8888));
    assert(downsample && renderer.dst_p == 0);
    assert(!environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&unsupported));
    assert(downsample);
    /* Two pixels per row plus one padding word from the libretro core. */
    uint32_t input[] = {0x00ff0000,0x0000ff00,0xdeadbeef,0x000000ff,0x00ffffff,0xdeadbeef};
    uint32_t original[6]; memcpy(original,input,sizeof(input));
    video_refresh_callback_main(input,2,2,12);
    assert(resizes == 2 && buffer && renderer.src == buffer);
    void *preview_pixels = buffer;
    uint16_t saved[4]; memcpy(saved,buffer,sizeof(saved));
    buffer_realloc(2,2,4);
    assert(buffer == preview_pixels && !memcmp(buffer,saved,sizeof(saved)));
    assert(environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&xrgb8888));
    video_refresh_callback_main(input,2,2,12);
    assert(resizes == 2);
    show_debug = 1;
    video_refresh_callback_main(input,2,2,12);
    assert(debug_writes == 4 && !memcmp(input,original,sizeof(input)));
    show_debug = 0;

    assert(environment_callback(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT,&rgb565));
    assert(!downsample && renderer.dst_p == 0);
    video_refresh_callback_main(native,2,2,4);
    assert(resizes == 3 && renderer.src == native);
    /* Native RGB565 cores may change stride without changing width/height. */
    uint16_t padded[] = {0xf800,0x07e0,0xdead,0x001f,0xffff,0xbeef};
    expected_pitch = 6;
    video_refresh_callback_main(padded,2,2,6);
    assert(resizes == 4 && renderer.src == padded);
    expected_pitch = 4;
    video_refresh_callback_main(native,2,2,4);
    assert(resizes == 5 && renderer.src == native);
    buffer_dealloc();
    return 0;
}
'''
        self.build_and_run(harness)

    def test_shader_blit_scaling_presentation_and_transitions(self):
        source = (MINARCH / "minarch.c").read_text()
        renderer_types = (ROOT / "workspace/all/common/api.h").read_text()
        renderer_types = re.search(r"typedef struct GFX_Renderer \{.*?\} GFX_Renderer;",
                                   renderer_types, re.S).group(0)
        wrapper = function(source, "Shader_blit")
        harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "shader.h"
#define MIN(a,b) ((a)<(b)?(a):(b))
#define CEIL_DIV(a,b) (((a)+(b)-1)/(b))
#define HDMI_WIDTH 1280
#define SDL_SWSURFACE 0
#define RGBA_MASK_565 0xf800,0x07e0,0x001f,0
#define LOG_error(...) ((void)0)
enum { SCALE_NATIVE, SCALE_ASPECT, SCALE_FULLSCREEN, SCALE_CROPPED };
enum { FE_OPT_EFFECT };
typedef struct {
    int w,h,pitch;
    void *pixels;
    uint8_t *allocation;
    size_t length;
} SDL_Surface;
static int allocations, frees, presentations;
static SDL_Surface *SDL_CreateRGBSurface(int flags,int w,int h,int depth,
        unsigned r,unsigned g,unsigned b,unsigned a) {
    assert(depth==16 && r==0xf800 && g==0x07e0 && b==0x001f);
    SDL_Surface *s=calloc(1,sizeof(*s));
    assert(s);
    s->w=w; s->h=h; s->pitch=w*2+6; /* Padding is intentionally nonzero. */
    s->length=(size_t)s->pitch*h;
    s->allocation=malloc(s->length+32);
    assert(s->allocation);
    memset(s->allocation,0xa5,s->length+32);
    s->pixels=s->allocation+16;
    allocations++;
    return s;
}
static void assert_surface_guards(SDL_Surface *s) {
    for(int n=0;n<16;n++) {
        assert(s->allocation[n]==0xa5);
        assert(s->allocation[16+s->length+n]==0xa5);
    }
    for(int y=0;y<s->h;y++) for(int n=s->w*2;n<s->pitch;n++)
        assert(((uint8_t *)s->pixels)[y*s->pitch+n]==0xa5);
}
static void SDL_FreeSurface(SDL_Surface *s) {
    if (!s) return;
    assert_surface_guards(s);
    free(s->allocation); free(s); frees++;
}
static void SDL_FillRect(SDL_Surface *s,void *rect,int color) {
    assert(color==0 && !rect);
    for(int y=0;y<s->h;y++) memset((uint8_t *)s->pixels+y*s->pitch,0,s->w*2);
}
''' + renderer_types + r'''
static GFX_Renderer renderer, shader_renderer, *presented;
static SDL_Surface *screen, *shader_screen;
static ShaderContext shader_context;
static ShaderSettings shader_settings;
static unsigned shader_frame;
static int screen_effect, screen_scaling, DEVICE_WIDTH=16, DEVICE_HEIGHT=12;
static struct { double aspect_ratio; } core;
static struct { struct { struct { char *key; } options[1]; } frontend; } config;
static void Config_syncFrontend(char *key,int value) { screen_effect=value; }
static void *GFX_getScaler(GFX_Renderer *r) { return r; }
static void GFX_blitRenderer(GFX_Renderer *r) {
    /* SDL2 retains the pointer and consumes its pixels after Shader_blit. */
    presented=r; presentations++;
}
''' + wrapper + r'''
static uint16_t raw[13*8], snapshot[13*8];
static void expect_rect(int scaling,double aspect,int sx,int sy,int sw,int sh,
                        int dx,int dy,int dw,int dh) {
    screen_scaling=scaling; core.aspect_ratio=aspect;
    GFX_Renderer original=renderer;
    int prior_presentations=presentations;
    Shader_blit();
    assert(presentations==prior_presentations+1);
    assert(presented==&shader_renderer && presented!=&renderer);
    assert(presented->src==shader_screen->pixels && presented->dst==screen->pixels);
    assert(presented->true_w==DEVICE_WIDTH && presented->true_h==DEVICE_HEIGHT);
    assert(presented->src_w==DEVICE_WIDTH && presented->src_h==DEVICE_HEIGHT);
    assert(presented->dst_w==DEVICE_WIDTH && presented->dst_h==DEVICE_HEIGHT);
    assert(presented->src_p==shader_screen->pitch && presented->dst_p==screen->pitch);
    assert(presented->aspect==-1 && presented->scale==1);
    assert(!presented->src_x && !presented->src_y && !presented->dst_x && !presented->dst_y);
    assert(!memcmp(&original,&renderer,sizeof(renderer)));
    assert(!memcmp(raw,snapshot,sizeof(raw)));

    /* Fixed expected rectangles exercise wrapper geometry, not its formula.
       Compare their pixels with the real shader operating on that crop. */
    ShaderContext expected_context={0};
    const uint16_t *expected=Shader_process(&expected_context,&shader_settings,
        raw+sy*13+sx,sw,sh,26,dw,dh,0);
    assert(expected);
    for(int y=0;y<DEVICE_HEIGHT;y++) for(int x=0;x<DEVICE_WIDTH;x++) {
        uint16_t actual;
        memcpy(&actual,(uint8_t *)presented->src+y*presented->src_p+x*2,2);
        if(x>=dx && x<dx+dw && y>=dy && y<dy+dh)
            assert(actual==expected[(y-dy)*dw+x-dx]);
        else assert(actual==0);
    }
    assert_surface_guards(shader_screen);
    assert_surface_guards(screen);
    Shader_destroy(&expected_context);
}
int main(void) {
    for(int y=0;y<8;y++) for(int x=0;x<13;x++)
        raw[y*13+x]=x>=10 ? 0xf81f : (uint16_t)((x+1)<<11 | (y+1)<<5 | 17);
    memcpy(snapshot,raw,sizeof(raw));
    renderer=(GFX_Renderer){.src=raw,.true_w=10,.true_h=8,.src_w=10,.src_h=8,.src_p=26};
    screen=SDL_CreateRGBSurface(0,16,12,16,RGBA_MASK_565);
    screen_effect=SHADER_SHARP_BILINEAR;
    shader_settings=Shader_defaults(screen_effect);
    expect_rect(SCALE_FULLSCREEN,1.25,0,0,10,8,0,0,16,12);
    SDL_Surface *saved_surface=shader_screen;
    void *saved_pixels=presented->src;
    expect_rect(SCALE_ASPECT,1.0,0,0,10,8,2,0,12,12);
    expect_rect(SCALE_ASPECT,2.0,0,0,10,8,0,2,16,8);
    expect_rect(SCALE_NATIVE,1.25,0,0,10,8,3,2,10,8);
    expect_rect(SCALE_CROPPED,1.25,1,1,8,6,0,0,16,12);
    assert(shader_screen==saved_surface && presented->src==saved_pixels);
    assert(allocations==2 && frees==0);

    /* Off presents the raw renderer and leaves the processed buffer alive.
       Turning it on again can reuse that buffer without stale black bars. */
    unsigned saved_frame=shader_frame;
    screen_effect=SHADER_NONE;
    Shader_blit();
    assert(presented==&renderer && renderer.src==raw && renderer.dst==screen->pixels);
    assert(shader_frame==saved_frame && shader_screen==saved_surface);
    screen_effect=SHADER_SHARP_BILINEAR;
    expect_rect(SCALE_FULLSCREEN,1.25,0,0,10,8,0,0,16,12);
    assert(allocations==2 && frees==0);

    /* A smaller display crops a source that cannot fit even at scale 1. */
    SDL_FreeSurface(screen);
    DEVICE_WIDTH=8; DEVICE_HEIGHT=6;
    screen=SDL_CreateRGBSurface(0,8,6,16,RGBA_MASK_565);
    expect_rect(SCALE_NATIVE,1.25,1,1,8,6,0,0,8,6);
    assert(shader_screen->w==8 && shader_screen->h==6 && frees==2);

    /* Odd display sizes retain centering and destination stride. */
    SDL_FreeSurface(screen);
    DEVICE_WIDTH=17; DEVICE_HEIGHT=13;
    screen=SDL_CreateRGBSurface(0,17,13,16,RGBA_MASK_565);
    expect_rect(SCALE_NATIVE,1.25,0,0,10,8,3,2,10,8);
    expect_rect(SCALE_CROPPED,1.25,1,1,8,6,0,0,16,12);
    assert(!memcmp(raw,snapshot,sizeof(raw)));
    SDL_FreeSurface(screen); SDL_FreeSurface(shader_screen);
    assert(allocations==frees);
    Shader_destroy(&shader_context);
    return 0;
}
'''
        self.build_and_run(harness, shader=True)


if __name__ == "__main__":
    unittest.main()
