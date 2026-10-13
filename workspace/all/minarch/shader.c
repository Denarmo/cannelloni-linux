/* Portable RGB565 adaptations of Denarmo/cannelloni's bundled GLSL shaders.
 * Upstream: 3175de741c7cea6e1b6c7d5cddf8eeab71ffb687.
 * See skeleton/SYSTEM/common/shaders/README.txt for authors, licenses and
 * differences from the Android GPU implementation. Derived GPL shader code
 * in this file is distributed under GPL-3.0-or-later.
 */
#include "shader.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define I SHADER_PARAM_INTENSITY
#define C SHADER_PARAM_CURVATURE
#define B SHADER_PARAM_BRIGHTNESS
#define M SHADER_PARAM_MASK
#define G SHADER_PARAM_GLOW
static const ShaderPreset presets[SHADER_COUNT] = {
    {"none", "Off", "Original image without a shader.", 0},
    {"line", "Scanlines", "Simple horizontal scanlines.", I | B},
    {"grid", "LCD Grid", "Pixel borders for handheld displays.", I | B},
    {"crt-cannelloni", "CRT-Cannelloni", "Software CRT with curvature, RGB mask,\nphosphor sweep and four-pass glow.", I | C | B | M | G},
    {"crt-cannelloni-lite", "CRT-Cannelloni Lite", "Lightweight curved CRT with triangle\nscanlines, RGB mask and phosphor sweep.", I | C | B | M},
    {"crt-easymode", "CRT-Easymode", "Software EasyMode-style CRT with\nluminance-sensitive scanlines and RGB mask.", I | B | M},
    {"crt-aperture", "CRT-Aperture", "Software aperture grille with\nphosphor glow and scanlines.", I | B | M | G},
    {"crt-geom", "CRT-Geom", "Software curved CRT with rounded\ncorners and alternating phosphor mask.", I | C | B | M},
    {"crt-lottes-fast", "CRT-Lottes Fast", "Software curved CRT with a staggered\nshadow mask and soft scanlines.", I | C | B | M},
    {"zfast-crt", "Zfast-CRT", "Fast polynomial scanlines with\nluminance-dependent mask fading.", I | B | M},
    {"lcd3x", "LCD3x", "RGB subpixels and horizontal lines\nfrom the LCD3x sine-wave pattern.", I | B | M},
    {"zfast-lcd", "Zfast-LCD", "Nearest-neighbor pixels with rounded\nborders and the GBA gamma adjustment.", I | B},
    {"dot", "Dot Matrix", "Soft phosphor dots with neighboring\npixel glow.", I | B | G},
    {"scanline", "Scanline Sine", "Sine-wave scanlines and vertical grid.", I | B | M},
    {"sharp-bilinear-simple", "Sharp Bilinear", "Integer-prescaled bilinear sampling\nwithout a CRT or LCD mask.", 0}
};
#undef I
#undef C
#undef B
#undef M
#undef G

typedef struct { float r, g, b; } Color;
typedef struct { const uint8_t *pixels; int w, h, pitch; } Source;
static float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
/* Shader coordinates are finite. Older uClibc targets omit fminf/fmaxf. */
static float minf(float a, float b) { return a < b ? a : b; }
static float maxf(float a, float b) { return a > b ? a : b; }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static float fract(float v) { return v - floorf(v); }
static float mixf(float a, float b, float f) { return a + (b - a) * f; }
static Color mixcolor(Color a, Color b, float f) {
    return (Color){mixf(a.r,b.r,f), mixf(a.g,b.g,f), mixf(a.b,b.b,f)};
}
static Color multiply(Color a, float f) { return (Color){a.r*f, a.g*f, a.b*f}; }
static Color unpack(uint16_t p) {
    return (Color){(p>>11)/31.0f, ((p>>5)&63)/63.0f, (p&31)/31.0f};
}
static Color read_pixel(Source s, int x, int y) {
    uint16_t p;
    x = clampi(x,0,s.w-1); y = clampi(y,0,s.h-1);
    memcpy(&p, s.pixels+(size_t)y*s.pitch+(size_t)x*2, sizeof(p));
    return unpack(p);
}
static uint16_t pack(Color c) {
    return (uint16_t)(((int)(clampf(c.r,0,1)*31+0.5f)<<11) |
        ((int)(clampf(c.g,0,1)*63+0.5f)<<5) | (int)(clampf(c.b,0,1)*31+0.5f));
}
static Color bilinear(Source s, float x, float y) {
    x=clampf(x,0,s.w-1); y=clampf(y,0,s.h-1);
    int ix=(int)x, iy=(int)y;
    int nx=ix<s.w-1 ? ix+1 : ix, ny=iy<s.h-1 ? iy+1 : iy;
    float fx=x-ix, fy=y-iy;
    const uint8_t *row=s.pixels+(size_t)iy*s.pitch, *next=s.pixels+(size_t)ny*s.pitch;
    uint16_t a,b,d,e;
    memcpy(&a,row+ix*2,2); memcpy(&b,row+nx*2,2);
    memcpy(&d,next+ix*2,2); memcpy(&e,next+nx*2,2);
    return mixcolor(mixcolor(unpack(a),unpack(b),fx),mixcolor(unpack(d),unpack(e),fx),fy);
}
static float sine(ShaderContext *c, float phase) {
    return c->sine[(int)(fract(phase)*1024)&1023];
}
static float gamma_output(ShaderContext *c, float v) {
    return c->gamma[(int)(clampf(v,0,1)*1023)];
}
static float smooth(float v) { v=clampf(v,0,1); return v*v*(3-2*v); }
static float luma(Color c) { return c.r*0.2126f+c.g*0.7152f+c.b*0.0722f; }
static Color mask_color(Color c, int channel, float strength) {
    if (channel != 0) c.r *= 1-strength;
    if (channel != 1) c.g *= 1-strength;
    if (channel != 2) c.b *= 1-strength;
    return c;
}

const ShaderPreset *Shader_getPreset(int preset) {
    return &presets[preset >= 0 && preset < SHADER_COUNT ? preset : SHADER_NONE];
}
ShaderSettings Shader_defaults(int preset) {
    ShaderSettings s = {preset,50,0,100,30,25};
    switch (preset) {
        case SHADER_CANNELLONI: s.intensity=75; s.curvature=85; s.brightness=120; break;
        case SHADER_CANNELLONI_LITE: s.intensity=65; s.curvature=85; s.mask=20; s.brightness=120; break;
        case SHADER_EASYMODE: s.intensity=75; s.brightness=120; break;
        case SHADER_APERTURE: s.intensity=65; s.brightness=150; s.glow=15; break;
        case SHADER_GEOM: s.intensity=60; s.curvature=65; break;
        case SHADER_LOTTES: s.curvature=35; s.mask=50; break;
        case SHADER_ZFAST_CRT: s.intensity=60; s.mask=25; s.brightness=125; break;
        case SHADER_LCD3X: s.intensity=12; s.mask=40; break;
        case SHADER_ZFAST_LCD: s.intensity=35; break;
        case SHADER_DOT: s.intensity=60; s.glow=65; break;
        case SHADER_SCANLINE: s.intensity=50; s.mask=15; break;
        default: break;
    }
    Shader_sanitize(&s);
    return s;
}
void Shader_sanitize(ShaderSettings *s) {
    if (!s) return;
    if (s->preset < 0 || s->preset >= SHADER_COUNT) s->preset=SHADER_NONE;
    s->intensity=clampi(s->intensity,0,100);
    s->curvature=clampi(s->curvature,0,100);
    s->brightness=clampi(s->brightness,50,150);
    s->mask=clampi(s->mask,0,100);
    s->glow=clampi(s->glow,0,100);
}

static int reserve(uint16_t **buffer, size_t *capacity, size_t count) {
    if (*capacity >= count) return 1;
    uint16_t *next=realloc(*buffer,count*sizeof(*next));
    if (!next) return 0;
    *buffer=next; *capacity=count;
    return 1;
}

static uint16_t average4(uint16_t a, uint16_t b, uint16_t c, uint16_t d) {
    unsigned rb=(a&0xf81f)+(b&0xf81f)+(c&0xf81f)+(d&0xf81f);
    unsigned g=(a&0x07e0)+(b&0x07e0)+(c&0x07e0)+(d&0x07e0);
    return (uint16_t)((((rb+0x1002)>>2)&0xf81f) | (((g+0x0040)>>2)&0x07e0));
}

/* Four Kawase passes from crt-cannelloni, preserving the upstream 0.5, 1.5,
 * 2.5, 3.5 texel radii. The four bilinear diagonal samples are separable:
 * average their four horizontal taps, then the four vertical taps. RGB565
 * integer intermediates avoid sixteen floating-point samples per pixel. */
static Source glow_source(ShaderContext *c, Source source) {
    Source input=source;
    size_t count=(size_t)source.w*source.h;
    for (int pass=0; pass<4; ++pass) {
        uint16_t *output=c->blur+(pass&1)*count;
        uint16_t *horizontal=c->blur+count*2;
        for (int y=0; y<source.h; ++y) {
            const uint8_t *row=input.pixels+(size_t)y*input.pitch;
            for (int x=0; x<source.w; ++x) {
                uint16_t a,b,d,e;
                memcpy(&a,row+clampi(x-pass-1,0,source.w-1)*2,2);
                memcpy(&b,row+clampi(x-pass,0,source.w-1)*2,2);
                memcpy(&d,row+clampi(x+pass,0,source.w-1)*2,2);
                memcpy(&e,row+clampi(x+pass+1,0,source.w-1)*2,2);
                horizontal[(size_t)y*source.w+x]=average4(a,b,d,e);
            }
        }
        for (int y=0; y<source.h; ++y) {
            const uint16_t *a=horizontal+(size_t)clampi(y-pass-1,0,source.h-1)*source.w;
            const uint16_t *b=horizontal+(size_t)clampi(y-pass,0,source.h-1)*source.w;
            const uint16_t *d=horizontal+(size_t)clampi(y+pass,0,source.h-1)*source.w;
            const uint16_t *e=horizontal+(size_t)clampi(y+pass+1,0,source.h-1)*source.w;
            for (int x=0; x<source.w; ++x)
                output[(size_t)y*source.w+x]=average4(a[x],b[x],d[x],e[x]);
        }
        input=(Source){(const uint8_t *)output,source.w,source.h,source.w*2};
    }
    return input;
}

static Color sharp_bilinear(Source s, float px, float py, int ow, int oh) {
    float sx=maxf(floorf((float)ow/s.w),1), sy=maxf(floorf((float)oh/s.h),1);
    float dx=fract(px)-0.5f, dy=fract(py)-0.5f;
    float rx=0.5f-0.5f/sx, ry=0.5f-0.5f/sy;
    return bilinear(s,floorf(px)+(dx-clampf(dx,-rx,rx))*sx,
                     floorf(py)+(dy-clampf(dy,-ry,ry))*sy);
}

const uint16_t *Shader_process(ShaderContext *c, const ShaderSettings *settings,
    const void *pixels, int sw, int sh, int pitch, int ow, int oh, unsigned frame) {
    if (!c || !settings || !pixels || sw<=0 || sh<=0 || ow<=0 || oh<=0 ||
        sw>8192 || sh>8192 || ow>8192 || oh>8192 || pitch<sw*2 ||
        (size_t)sw*sh>16777216 || (size_t)ow*oh>16777216) return NULL;
    if (c->pixels && (uintptr_t)pixels >= (uintptr_t)c->pixels &&
        (uintptr_t)pixels < (uintptr_t)c->pixels+c->capacity*2) return NULL;
    ShaderSettings s=*settings;
    Shader_sanitize(&s);
    if (!reserve(&c->pixels,&c->capacity,(size_t)ow*oh)) return NULL;
    Source source={(const uint8_t *)pixels,sw,sh,pitch}, glow=source;
    unsigned parameters=presets[s.preset].parameters;
    if ((parameters&SHADER_PARAM_GLOW) && s.glow && s.preset!=SHADER_DOT) {
        if (!reserve(&c->blur,&c->blur_capacity,(size_t)sw*sh*3)) return NULL;
        glow=glow_source(c,source);
    }
    if (!c->tables_ready) {
        for (int n=0; n<1024; ++n) {
            c->sine[n]=sinf(n*6.28318530718f/1024);
            c->gamma[n]=powf(n/1023.0f,1.0f/1.8f);
            c->falloff[n]=expf(-n*12.0f/1023);
        }
        c->tables_ready=1;
    }
    float intensity=s.intensity/100.0f, mask=s.mask/100.0f;
    float brightness=(parameters&SHADER_PARAM_BRIGHTNESS)?s.brightness/100.0f:1;
    float curve=(parameters&SHADER_PARAM_CURVATURE)?s.curvature/50.0f:0;
    for (int y=0; y<oh; ++y) {
        float v=(y+0.5f)/oh;
        for (int x=0; x<ow; ++x) {
            float u=(x+0.5f)/ow, ux=u, vy=v;
            if (curve) {
                float cx=u*2-1, cy=v*2-1;
                ux += cx*cy*cy*0.0138f*curve;
                vy += cy*cx*cx*0.0207f*curve;
            }
            uint16_t *out=&c->pixels[(size_t)y*ow+x];
            if (ux<0 || ux>1 || vy<0 || vy>1 ||
                (curve && minf(ux,1-ux)*minf(vy,1-vy)<0.0001f)) {
                *out=0; continue;
            }
            float px=ux*sw, py=vy*sh, fx=px-(int)px, fy=py-(int)py;
            Color col;
            switch (s.preset) {
                case SHADER_NONE:
                    col=read_pixel(source,(int)px,(int)py);
                    break;
                case SHADER_SHARP_BILINEAR:
                    col=sharp_bilinear(source,px,py,ow,oh);
                    break;
                case SHADER_LINE:
                    col=multiply(read_pixel(source,(int)px,(int)py),1-intensity*(fy<0.5f));
                    break;
                case SHADER_GRID:
                    col=multiply(read_pixel(source,(int)px,(int)py),
                        1-intensity*(fx<0.22f || fy<0.22f));
                    break;
                case SHADER_ZFAST_LCD: {
                    float d=maxf(fabsf(fx-0.5f),fabsf(fy-0.5f));
                    float d2=d*d, d4=d2*d2;
                    col=multiply(read_pixel(source,(int)px,(int)py),1-40*intensity*(d4-2.7f*d4*d2));
                    col=(Color){col.r*(0.6f+0.4f*col.r),col.g*(0.6f+0.4f*col.g),col.b*(0.6f+0.4f*col.b)};
                    break;
                }
                case SHADER_LCD3X:
                    col=bilinear(source,px-0.5f,py-0.5f);
                    col=multiply(col,1-intensity*(1-sine(c,py))*0.5f);
                    col.r *= 1-mask*(1-sine(c,px+0.25f))*0.5f;
                    col.g *= 1-mask*(1-sine(c,px+0.25f-1.0f/3))*0.5f;
                    col.b *= 1-mask*(1-sine(c,px+0.25f-2.0f/3))*0.5f;
                    break;
                case SHADER_DOT: {
                    col=(Color){0,0,0};
                    Color center={0,0,0};
                    for (int dy=-1; dy<=1; ++dy) for (int dx=-1; dx<=1; ++dx) {
                        Color tap=read_pixel(source,(int)px+dx,(int)py+dy);
                        float ax=fx-dx-0.5f, ay=fy-dy-0.5f;
                        float distance=sqrtf(ax*ax+ay*ay);
                        float falloff=4*intensity*distance*(1.05f-0.1f*luma(tap));
                        float weight=c->falloff[(int)(clampf(falloff,0,12)*(1023.0f/12))];
                        tap=multiply(tap,weight);
                        if (!dx && !dy) center=multiply(tap,1.2f);
                        col.r+=tap.r; col.g+=tap.g; col.b+=tap.b;
                    }
                    col=mixcolor(center,col,s.glow/100.0f);
                    break;
                }
                case SHADER_SCANLINE:
                    col=bilinear(source,px-0.5f,py-0.5f);
                    col=multiply(col,(1-intensity*(1-sine(c,py)))*(1-mask*(1-sine(c,px))));
                    break;
                case SHADER_ZFAST_CRT: {
                    float dx=fx-0.5f, dy=fy-0.5f;
                    col=bilinear(source,floorf(px)+mixf(4*dx*dx*dx,dx,0.3f),floorf(py)+4*dy*dy*dy);
                    float d2=dy*dy, d4=d2*d2;
                    float low=1-10*intensity*(d2-2.05f*d4);
                    float high=1-13.3333f*intensity*(d4-2.8f*d4*d2);
                    float stripe=((int)(ux*ow)%3==0)?1-mask:1;
                    col=multiply(col,mixf(low*stripe,high,clampf((col.r+col.g+col.b)*0.2667f,0,1)));
                    break;
                }
                case SHADER_CANNELLONI_LITE: {
                    col=bilinear(source,px-0.5f,py-0.5f);
                    col=multiply(col,1-(1-fabsf(fy*2-1))*intensity);
                    col=mask_color(col,(int)(ux*ow)%3,mask);
                    float band=smooth(1-fabsf(vy-(1-(frame%360)/360.0f))/0.04f);
                    col=multiply(col,1+band*0.35f);
                    break;
                }
                default: {
                    /* Full GPU kernels (Lanczos, spherical projection) are
                       replaced by sharper bilinear sampling in this CPU port. */
                    col=sharp_bilinear(source,px,py,ow,oh);
                    float bright=luma(col), wave=(1+sine(c,py+0.25f))*0.5f;
                    float scan=1-wave*intensity*(1-bright*0.35f);
                    if (s.preset==SHADER_LOTTES) scan=1-intensity*4*(fy-0.5f)*(fy-0.5f);
                    if (s.preset==SHADER_GEOM) scan=1-intensity*wave*wave;
                    col=(Color){col.r*col.r,col.g*col.g,col.b*col.b};
                    col=multiply(col,scan);
                    int channel=(int)(ux*ow)%3;
                    if (s.preset==SHADER_LOTTES) channel=((int)(ux*ow)+(y%2)*1)%3;
                    if (s.preset==SHADER_GEOM) {
                        if (x&1) { col.r*=1-mask; col.b*=1-mask; }
                        else col.g*=1-mask;
                    } else col=mask_color(col,channel,mask);
                    col=(Color){gamma_output(c,col.r),gamma_output(c,col.g),gamma_output(c,col.b)};
                    if (s.preset==SHADER_CANNELLONI) {
                        float edge=smooth(ux/0.14f)*smooth((1-ux)/0.14f)*smooth(vy/0.14f)*smooth((1-vy)/0.14f);
                        float band=smooth(1-fabsf(vy-(1-(frame%360)/360.0f))/0.04f);
                        col=multiply(col,mixf(1,edge,0.5f)*(1+band*0.35f));
                    }
                    if ((parameters&SHADER_PARAM_GLOW) && s.glow) {
                        Color blur=bilinear(glow,px-0.5f,py-0.5f);
                        float amount=s.glow/100.0f;
                        col=(Color){1-(1-col.r)*(1-blur.r*amount),1-(1-col.g)*(1-blur.g*amount),1-(1-col.b)*(1-blur.b*amount)};
                    }
                    break;
                }
            }
            *out=pack(multiply(col,brightness));
        }
    }
    return c->pixels;
}
void Shader_destroy(ShaderContext *c) {
    if (!c) return;
    free(c->pixels); free(c->blur);
    memset(c,0,sizeof(*c));
}
