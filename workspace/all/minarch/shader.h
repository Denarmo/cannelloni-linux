#ifndef CANNELLONI_SHADER_H
#define CANNELLONI_SHADER_H

#include <stddef.h>
#include <stdint.h>

/* Keep IDs compatible with existing minarch_screen_effect settings. */
enum {
    SHADER_NONE, SHADER_LINE, SHADER_GRID, SHADER_CANNELLONI,
    SHADER_CANNELLONI_LITE, SHADER_EASYMODE, SHADER_APERTURE,
    SHADER_GEOM, SHADER_LOTTES, SHADER_ZFAST_CRT, SHADER_LCD3X,
    SHADER_ZFAST_LCD, SHADER_DOT, SHADER_SCANLINE, SHADER_SHARP_BILINEAR,
    SHADER_COUNT
};

enum {
    SHADER_PARAM_INTENSITY = 1 << 0,
    SHADER_PARAM_CURVATURE = 1 << 1,
    SHADER_PARAM_BRIGHTNESS = 1 << 2,
    SHADER_PARAM_MASK = 1 << 3,
    SHADER_PARAM_GLOW = 1 << 4
};

typedef struct {
    const char *id;
    const char *name;
    const char *description;
    unsigned parameters;
} ShaderPreset;

typedef struct {
    int preset;
    /* Percentages: intensity/mask/glow 0..100, brightness 50..150.
       Curvature 0..100 corresponds to upstream Cannelloni 0.0..2.0. */
    int intensity;
    int curvature;
    int brightness;
    int mask;
    int glow;
} ShaderSettings;

struct ShaderState;

/* Caller zero-initializes; owns/reuses this context until Shader_destroy().
   threads: rows rendered in parallel (0 or 1 = calling thread only). It is
   clamped to the online CPU count; set it before any call, or between calls. */
typedef struct {
    uint16_t *pixels;
    size_t capacity;
    uint32_t *blur;
    size_t blur_capacity;
    int tables_ready;
    int threads;
    struct ShaderState *state;
} ShaderContext;

const ShaderPreset *Shader_getPreset(int preset);
ShaderSettings Shader_defaults(int preset);
void Shader_sanitize(ShaderSettings *settings);

/* Renders packed RGB565 into caller memory (destination pitch in bytes).
   Source may point at an already cropped region with its original byte pitch.
   Returns 0 on invalid geometry/allocation failure; source is never modified.
   CPU adaptations render at output resolution, before platform presentation. */
int Shader_render(ShaderContext *context, const ShaderSettings *settings,
    const void *source, int source_width, int source_height, int source_pitch,
    void *destination, int destination_pitch,
    int output_width, int output_height, unsigned frame);

/* As Shader_render, into a buffer owned by context (pitch = output_width * 2).
   Returns NULL on failure. */
const uint16_t *Shader_process(ShaderContext *context,
    const ShaderSettings *settings, const void *source,
    int source_width, int source_height, int source_pitch,
    int output_width, int output_height, unsigned frame);
void Shader_destroy(ShaderContext *context);

#endif
