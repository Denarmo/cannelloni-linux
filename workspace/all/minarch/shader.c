/* Portable RGB565 adaptations of Denarmo/cannelloni's bundled GLSL shaders.
 * Upstream: 3175de741c7cea6e1b6c7d5cddf8eeab71ffb687.
 * See skeleton/SYSTEM/common/shaders/README.txt for authors, licenses and
 * differences from the Android GPU implementation. Derived GPL shader code
 * in this file is distributed under GPL-3.0-or-later.
 *
 * Performance notes (handhelds such as the Miyoo Mini Plus have no usable GPU
 * and a pair of in-order Cortex-A7 cores):
 *  - All floating point work happens when settings or geometry change. Every
 *    per-pixel term that only depends on the output column or row (sample
 *    position, scanline profile, mask channel, ...) lives in a table.
 *  - Pixels stay in a "spread" RGB565 form (0x07E0F81F) so one multiply blends
 *    all three channels, and finish through per-channel lookup tables that
 *    fold in brightness, gamma, clamping and packing.
 *  - Without curvature, the vertical blend runs once per source pixel of each
 *    output row instead of once per output pixel.
 *  - Rows can be split across threads (ShaderContext.threads).
 */
#include "shader.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#ifndef SHADER_NO_THREADS
#include <pthread.h>
#include <unistd.h>
#endif

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

static float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
/* Shader coordinates are finite. Older uClibc targets omit fminf/fmaxf. */
static float minf(float a, float b) { return a < b ? a : b; }
static float maxf(float a, float b) { return a > b ? a : b; }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static float fract(float v) { return v - floorf(v); }
static float smooth(float v) { v=clampf(v,0,1); return v*v*(3-2*v); }
static int q8(float v) { return clampi((int)(v*256+0.5f),0,1023); }

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

/* ---- Spread RGB565 arithmetic -------------------------------------------
 * SP(p) places blue in bits 0-4, red in 11-15 and green in 21-26, leaving five
 * spare bits above each channel. Blending with weights summing to <= 32 keeps
 * channels apart and yields "E" values with five fractional bits: blue 0-9,
 * red 11-20 and green 21-31. */
#define SPMASK 0x07E0F81Fu
#define SPROUND 0x02008010u
#define SP(p) ((((uint32_t)(p)) | ((uint32_t)(p) << 16)) & SPMASK)
#define ER(e) (((e) >> 11) & 0x3FFu)
#define EG(e) ((e) >> 21)
#define EB(e) ((e) & 0x3FFu)
static inline uint16_t ld16(const uint8_t *row, int x) {
    uint16_t p;
    memcpy(&p, row+(size_t)x*2, sizeof(p));
    return p;
}
static inline uint32_t norm5(uint32_t e) { return ((e+SPROUND)>>5)&SPMASK; }
static inline uint16_t pack_e(uint32_t e) { uint32_t s=norm5(e); return (uint16_t)(s | (s>>16)); }

enum { FIN_DIRECT, FIN_LUT };
enum { CURVE_HALF, CURVE_SHARP };

/* One output column or row: source taps i0/i1 blended by wa/wb (sum <= 32),
   a class (mask channel or flag), an 8-bit position and a preset weight. */
typedef struct { uint16_t i0, i1; uint8_t wa, wb, ch, f; uint16_t wt, wt2; } Tap;
typedef struct { uint16_t ix, il, ir; uint8_t fal, far_, fb, fq; uint8_t pad[2]; } DotTap;
/* Per-thread row buffers: source-width blends, then output-width E values,
   weights and glow samples for the finishing pass. */
typedef struct {
    uint32_t *v0, *v1, *gv, *e, *bl;
    uint16_t *ws, *ix, *pyb, *pxb;
    uint8_t *ch, *wx, *fy;
    uint16_t *dot;
    uint8_t *dl;
} Scratch;

struct ShaderState {
    ShaderSettings key;
    int sw, sh, ow, oh, threads;
    int fin, mlin, msq, mcrt, bright, amt, amt_rb, amt_g, band_frame;
    float curve;
    int32_t sharp_x, sharp_r;
    /* Packed finishing tables: index = channel * weight (256 = 1.0). */
    uint16_t lut_r[1024], lut_g[1024], lut_b[1024];
    /* Two-stage presets: transfer to 8-bit linear values, then pack. */
    uint16_t pk_r[1024], pk_g[1024], pk_b[1024];
    uint16_t scan[256];
    uint16_t lscan[64*33];
    int32_t dy[256];
    uint16_t dotc[16*16*8];
    /* Geometry-sized arrays live in one allocation. */
    void *arena;
    size_t arena_size;
    Tap *cols, *rows, *gcols, *grows;
    DotTap *dcols;
    int32_t *cx2;
    uint16_t *cw, *ex, *ey, *band, *eyb;
    uint8_t *colch;
    int16_t *drow;
    Scratch scratch[2];
#ifndef SHADER_NO_THREADS
    pthread_t thread;
    pthread_mutex_t lock;
    pthread_cond_t wake, done;
    int worker, generation, finished, quit;
    const void *job;
    int job_y0, job_y1;
#endif
};

typedef struct {
    const struct ShaderState *st;
    const uint8_t *src;
    int pitch;
    const uint32_t *glow;
    uint8_t *dst;
    int dst_pitch;
    int sw, sh, ow, oh;
} Job;

/* ---- Sampling geometry --------------------------------------------------- */
enum { SAMPLE_NEAREST, SAMPLE_HALF, SAMPLE_SHARP, SAMPLE_ZFAST_X, SAMPLE_ZFAST_Y };

/* Continuous source coordinate the original bilinear() call used for p. */
static float sample_coord(int mode, float p, float scale) {
    float d=fract(p)-0.5f, r;
    switch (mode) {
        case SAMPLE_HALF: return p-0.5f;
        case SAMPLE_SHARP:
            r=0.5f-0.5f/scale;
            return floorf(p)+(d-clampf(d,-r,r))*scale;
        case SAMPLE_ZFAST_X: return floorf(p)+(4*d*d*d)+(d-4*d*d*d)*0.3f;
        case SAMPLE_ZFAST_Y: return floorf(p)+4*d*d*d;
        default: return p;
    }
}
static void build_axis(Tap *t, int n_out, int n_src, int mode, float scale) {
    for (int k=0; k<n_out; ++k) {
        float p=(k+0.5f)/n_out*n_src;
        Tap *a=&t[k];
        memset(a,0,sizeof(*a));
        a->f=(uint8_t)clampi((int)(fract(p)*256),0,255);
        if (mode==SAMPLE_NEAREST) {
            a->i0=a->i1=(uint16_t)clampi((int)p,0,n_src-1);
            a->wa=32;
            continue;
        }
        float x=clampf(sample_coord(mode,p,scale),0,n_src-1);
        int i=(int)x;
        int wb=clampi((int)((x-i)*32+0.5f),0,32);
        a->i0=(uint16_t)i;
        a->i1=(uint16_t)(i<n_src-1 ? i+1 : i);
        a->wa=(uint8_t)(32-wb); a->wb=(uint8_t)wb;
    }
}
/* Fold a non-negative weight (<= 1) into a tap's blend weights. */
static void scale_tap(Tap *a, float w) {
    w=clampf(w,0,1);
    int total=(int)(32*w+0.5f), wb=(int)(a->wb*w+0.5f);
    if (wb>total) wb=total;
    a->wb=(uint8_t)wb; a->wa=(uint8_t)(total-wb);
}
static float sharp_scale(int out, int src) { return maxf(floorf((float)out/src),1); }

/* ---- Lookup tables ------------------------------------------------------- */
enum { XFER_LINEAR, XFER_LCD, XFER_CRT };
static float transfer(int mode, float v) {
    if (mode==XFER_LCD) return v*(0.6f+0.4f*v);
    /* gamma(c*c*W) = c^(10/9) * W^(5/9); the weight carries sqrt(W). */
    if (mode==XFER_CRT) return powf(v,10.0f/9);
    return v;
}
static void build_luts(struct ShaderState *st, int mode, float brightness) {
    for (int i=0; i<1024; ++i) {
        float rb=clampf(transfer(mode,i/248.0f)*brightness,0,1);
        float g=clampf(transfer(mode,i/252.0f)*brightness,0,1);
        st->lut_r[i]=(uint16_t)((int)(rb*31+0.5f)<<11);
        st->lut_g[i]=(uint16_t)((int)(g*63+0.5f)<<5);
        st->lut_b[i]=(uint16_t)(int)(rb*31+0.5f);
        float o=clampf(i/255.0f*brightness,0,1);
        st->pk_r[i]=(uint16_t)((int)(o*31+0.5f)<<11);
        st->pk_g[i]=(uint16_t)((int)(o*63+0.5f)<<5);
        st->pk_b[i]=(uint16_t)(int)(o*31+0.5f);
    }
}
static float wave_at(float fy) { return (1+sinf(6.28318530718f*(fy+0.25f)))*0.5f; }

/* Rank-1 fit f(x)*g(y) of exp(-a*|(x,y)|) on a 1/32 grid, by power iteration. */
static void fit_falloff(float a, float x0, int nx, float y0, int ny, float *f, float *g) {
    float w[32*96];
    for (int i=0; i<nx; ++i) for (int j=0; j<ny; ++j) {
        float x=x0+(i+0.5f)/32, y=y0+(j+0.5f)/32;
        w[i*ny+j]=expf(-a*sqrtf(x*x+y*y));
    }
    for (int j=0; j<ny; ++j) g[j]=1;
    for (int it=0; it<24; ++it) {
        float norm=0;
        for (int i=0; i<nx; ++i) {
            float sum=0;
            for (int j=0; j<ny; ++j) sum+=w[i*ny+j]*g[j];
            f[i]=sum;
        }
        for (int j=0; j<ny; ++j) {
            float sum=0;
            for (int i=0; i<nx; ++i) sum+=w[i*ny+j]*f[i];
            g[j]=sum; norm+=sum*sum;
        }
        norm=sqrtf(norm);
        for (int j=0; j<ny; ++j) g[j]=norm>0 ? g[j]/norm : 0;
    }
    /* f = W g with |g| = 1 gives W ~ f g'; move the scale so max f = 1. */
    float peak=0;
    for (int i=0; i<nx; ++i) {
        float sum=0;
        for (int j=0; j<ny; ++j) sum+=w[i*ny+j]*g[j];
        f[i]=sum; peak=maxf(peak,sum);
    }
    for (int i=0; i<nx; ++i) f[i]=peak>0 ? f[i]/peak : 0;
    for (int j=0; j<ny; ++j) g[j]*=peak;
}
static int grid(float v, float v0, int n) { return clampi((int)((v-v0)*32),0,n-1); }

/* ---- Arena --------------------------------------------------------------- */
static size_t align8(size_t n) { return (n+7)&~(size_t)7; }
static int layout(struct ShaderState *st, int sw, int sh, int ow, int oh, int threads) {
    size_t sizes[]={
        sizeof(Tap)*ow, sizeof(Tap)*oh, sizeof(Tap)*ow, sizeof(Tap)*oh,
        sizeof(DotTap)*ow, sizeof(int32_t)*ow, sizeof(uint16_t)*ow*3,
        sizeof(uint16_t)*(4*sw+4), sizeof(uint16_t)*(4*sh+4), sizeof(uint16_t)*(4*sh+4),
        sizeof(uint16_t)*(4*sh+4),
        sizeof(int16_t)*oh*8, (size_t)ow
    };
    size_t scratch=align8(sizeof(uint32_t)*(sw+1))*3+align8(sizeof(uint16_t)*sw*9)+align8(sw)+
        align8(sizeof(uint32_t)*ow)*2+align8(sizeof(uint16_t)*ow)*4+align8(ow)*3;
    size_t total=0;
    for (size_t n=0; n<sizeof(sizes)/sizeof(*sizes); ++n) total+=align8(sizes[n]);
    total+=scratch*threads;
    if (total>st->arena_size) {
        void *next=realloc(st->arena,total);
        if (!next) return 0;
        st->arena=next; st->arena_size=total;
    }
    uint8_t *p=st->arena;
    void **slots[]={
        (void **)&st->cols, (void **)&st->rows, (void **)&st->gcols, (void **)&st->grows,
        (void **)&st->dcols, (void **)&st->cx2, (void **)&st->cw,
        (void **)&st->ex, (void **)&st->ey, (void **)&st->band, (void **)&st->eyb, (void **)&st->drow,
        (void **)&st->colch
    };
    for (size_t n=0; n<sizeof(sizes)/sizeof(*sizes); ++n) { *slots[n]=p; p+=align8(sizes[n]); }
    for (int t=0; t<2; ++t) {
        Scratch *s=&st->scratch[t];
        if (t>=threads) { memset(s,0,sizeof(*s)); continue; }
        s->v0=(uint32_t *)p; p+=align8(sizeof(uint32_t)*(sw+1));
        s->v1=(uint32_t *)p; p+=align8(sizeof(uint32_t)*(sw+1));
        s->gv=(uint32_t *)p; p+=align8(sizeof(uint32_t)*(sw+1));
        s->dot=(uint16_t *)p; p+=align8(sizeof(uint16_t)*sw*9);
        s->dl=p; p+=align8(sw);
        s->e=(uint32_t *)p; p+=align8(sizeof(uint32_t)*ow);
        s->bl=(uint32_t *)p; p+=align8(sizeof(uint32_t)*ow);
        s->ws=(uint16_t *)p; p+=align8(sizeof(uint16_t)*ow);
        s->ix=(uint16_t *)p; p+=align8(sizeof(uint16_t)*ow);
        s->pyb=(uint16_t *)p; p+=align8(sizeof(uint16_t)*ow);
        s->pxb=(uint16_t *)p; p+=align8(sizeof(uint16_t)*ow);
        s->ch=p; p+=align8(ow);
        s->wx=p; p+=align8(ow);
        s->fy=p; p+=align8(ow);
    }
    return 1;
}

/* ---- Per-settings setup ----------------------------------------------------
 * Every float formula below is the per-pixel expression of the previous
 * implementation, evaluated once per column, row or table entry. */
static void setup(struct ShaderState *st, const ShaderSettings *s, int sw, int sh, int ow, int oh) {
    unsigned parameters=presets[s->preset].parameters;
    float in=s->intensity/100.0f, mask=s->mask/100.0f, glow=s->glow/100.0f;
    float brightness=(parameters&SHADER_PARAM_BRIGHTNESS)?s->brightness/100.0f:1;
    float curve=(parameters&SHADER_PARAM_CURVATURE)?s->curvature/50.0f:0;
    st->curve=curve;
    st->fin=brightness!=1 ? FIN_LUT : FIN_DIRECT;
    st->mlin=q8(1-mask);
    st->msq=q8(sqrtf(1-mask));
    /* CRT presets: gamma(c*c*scan*mask) = T(c) * scan^(5/9) * mask^(5/9). */
    st->mcrt=clampi(q8(powf(1-mask,5.0f/9)),0,255);
    st->mlin=clampi(st->mlin,0,255);
    st->amt=q8(glow);
    int glowing=(parameters&SHADER_PARAM_GLOW) && s->glow && s->preset!=SHADER_DOT;
    /* Brightness folds into the 1/128 weights unless glow is blended first. */
    float fold=glowing ? 1 : brightness;
    st->bright=(int)(brightness*128+0.5f);
    st->band_frame=-1;
    /* Screen-blend glow: blur channel (E units) * amount -> 8-bit. */
    st->amt_rb=(int)(glow*255*1024/992.0f+0.5f);
    st->amt_g=(int)(glow*255*2048/2016.0f+0.5f);
    float sx=sharp_scale(ow,sw), sy=sharp_scale(oh,sh);
    int xfer=XFER_LINEAR;
    switch (s->preset) {
        case SHADER_NONE:
            build_axis(st->cols,ow,sw,SAMPLE_NEAREST,1);
            build_axis(st->rows,oh,sh,SAMPLE_NEAREST,1);
            break;
        case SHADER_LINE:
            build_axis(st->cols,ow,sw,SAMPLE_NEAREST,1);
            build_axis(st->rows,oh,sh,SAMPLE_NEAREST,1);
            for (int y=0; y<oh; ++y) {
                float fy=fract((y+0.5f)/oh*sh);
                st->rows[y].wa=(uint8_t)(int)(32*(1-in*(fy<0.5f))+0.5f);
            }
            break;
        case SHADER_GRID:
            build_axis(st->cols,ow,sw,SAMPLE_NEAREST,1);
            build_axis(st->rows,oh,sh,SAMPLE_NEAREST,1);
            for (int x=0; x<ow; ++x) st->cols[x].ch=fract((x+0.5f)/ow*sw)<0.22f;
            for (int y=0; y<oh; ++y) {
                st->rows[y].ch=fract((y+0.5f)/oh*sh)<0.22f;
                st->rows[y].wb=(uint8_t)(int)(32*(1-in)+0.5f);
            }
            break;
        case SHADER_SCANLINE:
        case SHADER_LCD3X:
            build_axis(st->cols,ow,sw,SAMPLE_HALF,1);
            build_axis(st->rows,oh,sh,SAMPLE_HALF,1);
            /* Scanline Sine factors go negative above 50%: keep the sign in
               ch, since two negative factors multiply back to light. */
            for (int y=0; y<oh; ++y) {
                float wave=sinf(6.28318530718f*fract((y+0.5f)/oh*sh));
                float w=s->preset==SHADER_SCANLINE ? 1-in*(1-wave) : 1-in*(1-wave)*0.5f;
                st->rows[y].ch=w<0;
                scale_tap(&st->rows[y],fabsf(w));
            }
            for (int x=0; x<ow; ++x) {
                float px=(x+0.5f)/ow*sw;
                if (s->preset==SHADER_SCANLINE) {
                    float w=1-mask*(1-sinf(6.28318530718f*fract(px)));
                    st->cols[x].ch=w<0;
                    scale_tap(&st->cols[x],fabsf(w));
                    continue;
                }
                for (int ch=0; ch<3; ++ch) st->cw[x*3+ch]=(uint16_t)q8(
                    1-mask*(1-sinf(6.28318530718f*fract(px+0.25f-ch/3.0f)))*0.5f);
            }
            break;
        case SHADER_SHARP_BILINEAR:
            build_axis(st->cols,ow,sw,SAMPLE_SHARP,sx);
            build_axis(st->rows,oh,sh,SAMPLE_SHARP,sy);
            break;
        case SHADER_ZFAST_LCD:
            xfer=XFER_LCD;
            build_axis(st->cols,ow,sw,SAMPLE_NEAREST,1);
            build_axis(st->rows,oh,sh,SAMPLE_NEAREST,1);
            /* 1-40I(d^4-2.7d^6) falls monotonically with d = max(|dx|,|dy|),
               so the 2D weight is the minimum of the per-axis weights. */
            for (int n=0; n<ow+oh; ++n) {
                Tap *t=n<ow ? &st->cols[n] : &st->rows[n-ow];
                float f=n<ow ? fract((n+0.5f)/ow*sw) : fract((n-ow+0.5f)/oh*sh);
                float d=fabsf(f-0.5f), d2=d*d, d4=d2*d2;
                t->wt=(uint16_t)q8(1-40*in*(d4-2.7f*d4*d2));
            }
            break;
        case SHADER_ZFAST_CRT:
            build_axis(st->cols,ow,sw,SAMPLE_ZFAST_X,1);
            build_axis(st->rows,oh,sh,SAMPLE_ZFAST_Y,1);
            for (int x=0; x<ow; ++x) st->cols[x].ch=x%3==0;
            for (int y=0; y<oh; ++y) {
                float dy=fract((y+0.5f)/oh*sh)-0.5f, d2=dy*dy, d4=d2*d2;
                /* Both profiles dip below zero at high intensity; keep the sign. */
                st->rows[y].wt=(uint16_t)(int16_t)(int)floorf(256*(1-10*in*(d2-2.05f*d4))+0.5f);
                st->rows[y].wt2=(uint16_t)(int16_t)(int)floorf(256*(1-13.3333f*in*(d4-2.8f*d4*d2))+0.5f);
            }
            break;
        case SHADER_EASYMODE:
        case SHADER_APERTURE:
            build_axis(st->cols,ow,sw,SAMPLE_SHARP,sx);
            build_axis(st->rows,oh,sh,SAMPLE_SHARP,sy);
            build_axis(st->gcols,ow,sw,SAMPLE_HALF,1);
            build_axis(st->grows,oh,sh,SAMPLE_HALF,1);
            for (int x=0; x<ow; ++x) st->colch[x]=(uint8_t)(x%3);
            for (int y=0; y<oh; ++y)
                st->rows[y].f=(uint8_t)clampi((int)(fract((y+0.5f)/oh*sh)*64),0,63);
            xfer=XFER_CRT;
            break;
        case SHADER_GEOM:
        case SHADER_LOTTES:
        case SHADER_CANNELLONI:
            xfer=XFER_CRT;
            /* fall through */
        case SHADER_CANNELLONI_LITE: {
            int mode=s->preset==SHADER_CANNELLONI_LITE ? SAMPLE_HALF : SAMPLE_SHARP;
            st->sharp_x=(int32_t)sx;
            st->sharp_r=(int32_t)((0.5f-0.5f/sx)*65536+0.5f);
            for (int n=0; n<256; ++n) {
                float f=(n+0.5f)/256;
                st->dy[n]=(int32_t)floorf((sample_coord(mode,f,sy)-floorf(f))*65536+0.5f);
            }
            for (int x=0; x<ow; ++x) {
                float cx=(x+0.5f)/ow*2-1;
                st->cx2[x]=(int32_t)(cx*cx*16384+0.5f);
            }
            for (int x=0; x<4*sw+4; ++x) {
                float ux=minf((x+0.5f)/(4.0f*sw),1);
                st->ex[x]=(uint16_t)q8(smooth(ux/0.14f)*smooth((1-ux)/0.14f));
            }
            for (int y=0; y<4*sh+4; ++y) {
                float vy=minf((y+0.5f)/(4.0f*sh),1);
                st->ey[y]=(uint16_t)q8(smooth(vy/0.14f)*smooth((1-vy)/0.14f));
            }
            break;
        }
        case SHADER_DOT: {
            /* Neighbor taps use a separable fit of exp(-4I*distance); the
               center tap keeps its exact radial, luminance-aware falloff. */
            float a=4*in, fa[32], ga[96], fb[32], gb[32];
            fit_falloff(a,0.5f,32,-1.5f,96,fa,ga);
            fit_falloff(a,-0.5f,32,0.5f,32,fb,gb);
            float center=glow+1.2f*(1-glow);
            for (int fy=0; fy<16; ++fy) for (int fx=0; fx<16; ++fx) for (int l=0; l<8; ++l) {
                float ax=(fx+0.5f)/16-0.5f, ay=(fy+0.5f)/16-0.5f;
                float falloff=clampf(a*sqrtf(ax*ax+ay*ay)*(1.05f-0.1f*(l+0.5f)/8),0,12);
                st->dotc[(fy*16+fx)*8+l]=(uint16_t)q8(expf(-falloff)*center);
            }
            for (int x=0; x<ow; ++x) {
                float px=(x+0.5f)/ow*sw, f=px-(int)px;
                DotTap *t=&st->dcols[x];
                int ix=clampi((int)px,0,sw-1);
                t->ix=(uint16_t)ix;
                t->il=(uint16_t)clampi(ix-1,0,sw-1);
                t->ir=(uint16_t)clampi(ix+1,0,sw-1);
                t->fal=(uint8_t)clampi(q8(fa[grid(f+0.5f,0.5f,32)]),0,255);
                t->far_=(uint8_t)clampi(q8(fa[grid(1.5f-f,0.5f,32)]),0,255);
                t->fb=(uint8_t)clampi(q8(fb[grid(f-0.5f,-0.5f,32)]),0,255);
                t->fq=(uint8_t)clampi((int)(f*16),0,15);
            }
            for (int y=0; y<oh; ++y) {
                float py=(y+0.5f)/oh*sh, f=py-(int)py;
                int16_t *r=&st->drow[y*8];
                r[0]=(int16_t)clampi((int)py,0,sh-1);
                r[1]=(int16_t)q8(ga[grid(f+0.5f,-1.5f,96)]*glow);
                r[2]=(int16_t)q8(ga[grid(f-0.5f,-1.5f,96)]*glow);
                r[3]=(int16_t)q8(ga[grid(f-1.5f,-1.5f,96)]*glow);
                r[4]=(int16_t)q8(gb[grid(f+0.5f,0.5f,32)]*glow);
                r[5]=(int16_t)q8(gb[grid(1.5f-f,0.5f,32)]*glow);
                r[6]=(int16_t)clampi((int)(f*16),0,15);
            }
            break;
        }
        default: break;
    }
    /* Scanline profiles indexed by the 8-bit fraction of the source row. */
    for (int n=0; n<256; ++n) {
        float fy=(n+0.5f)/256, w=1;
        if (s->preset==SHADER_CANNELLONI_LITE) w=1-(1-fabsf(fy*2-1))*in;
        if (s->preset==SHADER_GEOM) w=powf(maxf(1-in*wave_at(fy)*wave_at(fy),0),5.0f/9);
        if (s->preset==SHADER_LOTTES) w=powf(maxf(1-in*4*(fy-0.5f)*(fy-0.5f),0),5.0f/9);
        st->scan[n]=(uint16_t)clampi((int)(w*fold*128+0.5f),0,256);
    }
    /* Luminance-sensitive scanlines (EasyMode, Aperture, Cannelloni). */
    for (int n=0; n<64; ++n) for (int l=0; l<33; ++l) {
        float wave=wave_at((n+0.5f)/64), bright=minf(l/31.0f,1);
        st->lscan[n*33+l]=(uint16_t)clampi((int)(powf(maxf(1-wave*in*(1-bright*0.35f),0),5.0f/9)*fold*128+0.5f),0,256);
    }
    build_luts(st,xfer,brightness);
}

/* Phosphor sweep: 1 + 0.35 * band, indexed by quarter source rows. */
static void update_band(struct ShaderState *st, int sh, unsigned frame) {
    int phase=(int)(frame%360);
    if (st->band_frame==phase) return;
    st->band_frame=phase;
    float pos=1-phase/360.0f;
    for (int y=0; y<4*sh+4; ++y) {
        float vy=minf((y+0.5f)/(4.0f*sh),1);
        st->band[y]=(uint16_t)q8(1+smooth(1-fabsf(vy-pos)/0.04f)*0.35f);
        /* Cannelloni: (0.5 + 0.5 ex ey) band = (128 band + ex eyb) / 256. */
        st->eyb[y]=(uint16_t)((st->ey[y]*st->band[y])>>9);
    }
}

/* ---- Glow ------------------------------------------------------------------
 * Four Kawase passes from crt-cannelloni, preserving the upstream 0.5, 1.5,
 * 2.5, 3.5 texel radii. The four bilinear diagonal samples are separable:
 * average their four horizontal taps, then the four vertical taps. */
#define SUM4ROUND 0x00401002u
static inline uint32_t avg4(uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    return ((a+b+c+d+SUM4ROUND)>>2)&SPMASK;
}
static const uint32_t *glow_source(ShaderContext *c, const uint8_t *src, int pitch, int sw, int sh) {
    size_t count=(size_t)sw*sh;
    uint32_t *in=c->blur, *tmp=c->blur+count, *out=c->blur+count*2;
    for (int y=0; y<sh; ++y) {
        const uint8_t *row=src+(size_t)y*pitch;
        uint32_t *d=in+(size_t)y*sw;
        for (int x=0; x<sw; ++x) d[x]=SP(ld16(row,x));
    }
    for (int pass=0; pass<4; ++pass) {
        int lo=pass+1, hi=sw-pass-2;
        for (int y=0; y<sh; ++y) {
            const uint32_t *r=in+(size_t)y*sw;
            uint32_t *h=tmp+(size_t)y*sw;
            int x=0;
            for (; x<sw && x<lo; ++x)
                h[x]=avg4(r[clampi(x-pass-1,0,sw-1)],r[clampi(x-pass,0,sw-1)],
                    r[clampi(x+pass,0,sw-1)],r[clampi(x+pass+1,0,sw-1)]);
            for (; x<=hi; ++x) h[x]=avg4(r[x-pass-1],r[x-pass],r[x+pass],r[x+pass+1]);
            for (; x<sw; ++x)
                h[x]=avg4(r[clampi(x-pass-1,0,sw-1)],r[clampi(x-pass,0,sw-1)],
                    r[clampi(x+pass,0,sw-1)],r[clampi(x+pass+1,0,sw-1)]);
        }
        for (int y=0; y<sh; ++y) {
            const uint32_t *a=tmp+(size_t)clampi(y-pass-1,0,sh-1)*sw;
            const uint32_t *b=tmp+(size_t)clampi(y-pass,0,sh-1)*sw;
            const uint32_t *d=tmp+(size_t)clampi(y+pass,0,sh-1)*sw;
            const uint32_t *e=tmp+(size_t)clampi(y+pass+1,0,sh-1)*sw;
            uint32_t *o=out+(size_t)y*sw;
            for (int x=0; x<sw; ++x) o[x]=avg4(a[x],b[x],d[x],e[x]);
        }
        uint32_t *swap=in; in=out; out=swap;
    }
    return in;
}

/* ---- Row helpers ----------------------------------------------------------- */
static inline const uint8_t *src_row(const Job *j, int y) { return j->src+(size_t)y*j->pitch; }
static inline uint16_t *dst_row(const Job *j, int y) { return (uint16_t *)(j->dst+(size_t)y*j->dst_pitch); }
/* Spread source row scaled by w (<= 32): E values with five fractional bits. */
static void vrow_scaled(uint32_t *v, const uint8_t *row, int sw, unsigned w) {
    for (int x=0; x<sw; ++x) v[x]=SP(ld16(row,x))*w;
}
/* Vertical blend of two source rows into whole spread pixels. */
static void vrow_blend(uint32_t *v, const uint8_t *a, const uint8_t *b, int sw, unsigned wa, unsigned wb) {
    if (!wb) { for (int x=0; x<sw; ++x) v[x]=norm5(SP(ld16(a,x))*wa); return; }
    for (int x=0; x<sw; ++x) v[x]=norm5(SP(ld16(a,x))*wa+SP(ld16(b,x))*wb);
}
static void vrow_blend32(uint32_t *v, const uint32_t *a, const uint32_t *b, int sw, unsigned wa, unsigned wb) {
    for (int x=0; x<sw; ++x) v[x]=norm5(a[x]*wa+b[x]*wb);
}
static inline uint16_t lut_e(const struct ShaderState *st, uint32_t e) {
    return st->lut_r[ER(e)>>2] | st->lut_g[EG(e)>>3] | st->lut_b[EB(e)>>2];
}
static inline uint16_t lut_w(const struct ShaderState *st, uint32_t e, unsigned wr, unsigned wg, unsigned wb) {
    return st->lut_r[(ER(e)*wr)>>10] | st->lut_g[(EG(e)*wg)>>11] | st->lut_b[(EB(e)*wb)>>10];
}
static inline unsigned mod3(unsigned v) { return v-3*((v*0xAAABu)>>17); }
static inline unsigned luma5(uint32_t e) { return (ER(e)*56+EG(e)*94+EB(e)*19)>>13; }

/* ---- Finishing passes ------------------------------------------------------
 * Plain 16-bit loops over one row with no tables, so compilers vectorize them
 * (NEON on ARM handles eight pixels per instruction). Channels come from E
 * values on a 248 (red/blue) or 252 (green) scale with weights in 1/128 steps
 * (<= 256); the mask (<= 255/256) attenuates the channels a column does not
 * light. CRT presets apply T(c) = c^(10/9) as c*(0.834+0.166c), within 0.008. */
static inline uint16_t xfer_crt(uint16_t c, uint16_t b) {
    return (uint16_t)((c*(uint16_t)(214+(uint16_t)((uint16_t)(b*c)>>8)))>>8);
}
static inline uint16_t screen(uint16_t o, uint16_t glow, uint16_t amt, int16_t top) {
    int16_t v=(int16_t)o, ba=(int16_t)((uint16_t)(glow*amt)>>9);
    v=(int16_t)(v+(int16_t)((int16_t)(ba*(int16_t)(top-v))>>7));
    return (uint16_t)(v<0 ? 0 : v);
}
static inline __attribute__((always_inline)) void finish_body(uint16_t *restrict out,
    const uint32_t *restrict e, const uint16_t *restrict ws, const uint8_t *restrict ch,
    const uint32_t *restrict bl, int n, unsigned x0, uint16_t mk, uint16_t amt, uint16_t bright,
    const int crt, const int pair, const int glow) {
    for (int i=0; i<n; ++i) {
        uint16_t lr, lg, lb;
        if (pair) { uint16_t odd=(uint16_t)((x0+i)&1); lr=!odd; lg=odd; lb=!odd; }
        else { lr=ch[i]==0; lg=ch[i]==1; lb=ch[i]==2; }
        uint32_t E=e[i];
        uint16_t r=(uint16_t)((E>>13)&0xFF), g=(uint16_t)(E>>24), b=(uint16_t)((E>>2)&0xFF);
        if (crt) { r=xfer_crt(r,44); g=xfer_crt(g,43); b=xfer_crt(b,44); }
        uint16_t w=ws[i], m=(uint16_t)((uint16_t)(w*mk)>>8);
        r=(uint16_t)((uint16_t)(r*(lr?w:m))>>7);
        g=(uint16_t)((uint16_t)(g*(lg?w:m))>>7);
        b=(uint16_t)((uint16_t)(b*(lb?w:m))>>7);
        if (glow) {
            /* Screen blend o + glow * (1 - o), then brightness. */
            uint32_t L=bl[i];
            r=screen(r,(uint16_t)((L>>13)&0xFF),amt,248);
            g=screen(g,(uint16_t)(L>>24),amt,252);
            b=screen(b,(uint16_t)((L>>2)&0xFF),amt,248);
            r=r>320 ? 320 : r; g=g>320 ? 320 : g; b=b>320 ? 320 : b;
            r=(uint16_t)((uint16_t)(r*bright)>>7);
            g=(uint16_t)((uint16_t)(g*bright)>>7);
            b=(uint16_t)((uint16_t)(b*bright)>>7);
        }
        r=(uint16_t)((r+4)>>3); g=(uint16_t)((g+2)>>2); b=(uint16_t)((b+4)>>3);
        r=r>31 ? 31 : r; g=g>63 ? 63 : g; b=b>31 ? 31 : b;
        out[i]=(uint16_t)(r<<11 | g<<5 | b);
    }
}
static void finish_lin(uint16_t *out, const Scratch *sc, const uint8_t *ch, int n, uint16_t mk) {
    finish_body(out,sc->e,sc->ws,ch,NULL,n,0,mk,0,0,0,0,0);
}
static void finish_crt(uint16_t *out, const Scratch *sc, const uint8_t *ch, int n, uint16_t mk) {
    finish_body(out,sc->e,sc->ws,ch,NULL,n,0,mk,0,0,1,0,0);
}
static void finish_crt_pair(uint16_t *out, const Scratch *sc, int n, unsigned x0, uint16_t mk) {
    finish_body(out,sc->e,sc->ws,NULL,NULL,n,x0,mk,0,0,1,1,0);
}
static void finish_crt_glow(uint16_t *out, const Scratch *sc, const uint8_t *ch, int n,
    uint16_t mk, uint16_t amt, uint16_t bright) {
    finish_body(out,sc->e,sc->ws,ch,sc->bl,n,0,mk,amt,bright,1,0,1);
}

/* ---- Separable presets ------------------------------------------------------ */
static void rows_none(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    (void)sc;
    for (int y=y0; y<y1; ++y) {
        const uint8_t *row=src_row(j,st->rows[y].i0);
        uint16_t *out=dst_row(j,y);
        if (j->ow==j->sw) { memcpy(out,row,(size_t)j->ow*2); continue; }
        for (int x=0; x<j->ow; ++x) out[x]=ld16(row,st->cols[x].i0);
    }
}
/* Nearest presets: Scanlines, LCD Grid and Zfast-LCD. */
static void rows_nearest(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    const Tap *cols=st->cols;
    int preset=st->key.preset, ow=j->ow;
    for (int y=y0; y<y1; ++y) {
        const Tap *r=&st->rows[y];
        const uint8_t *row=src_row(j,r->i0);
        uint16_t *out=dst_row(j,y);
        if (preset==SHADER_ZFAST_LCD) {
            vrow_scaled(sc->v0,row,j->sw,32);
            unsigned wy=r->wt;
            for (int x=0; x<ow; ++x) {
                unsigned w=cols[x].wt<wy ? cols[x].wt : wy;
                out[x]=lut_w(st,sc->v0[cols[x].i0],w,w,w);
            }
            continue;
        }
        const uint32_t *a=sc->v0, *b=sc->v0;
        if (preset==SHADER_GRID) {
            vrow_scaled(sc->v0,row,j->sw,r->ch ? r->wb : 32);
            if (!r->ch) { vrow_scaled(sc->v1,row,j->sw,r->wb); b=sc->v1; }
        } else vrow_scaled(sc->v0,row,j->sw,r->wa);
        if (st->fin==FIN_DIRECT)
            for (int x=0; x<ow; ++x) out[x]=pack_e((cols[x].ch ? b : a)[cols[x].i0]);
        else
            for (int x=0; x<ow; ++x) out[x]=lut_e(st,(cols[x].ch ? b : a)[cols[x].i0]);
    }
}
/* Bilinear presets with folded weights: Scanline Sine and Sharp Bilinear. */
static void rows_bilinear(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    const Tap *cols=st->cols;
    uint32_t *v=sc->v0;
    for (int y=y0; y<y1; ++y) {
        const Tap *r=&st->rows[y];
        vrow_blend(v,src_row(j,r->i0),src_row(j,r->i1),j->sw,r->wa,r->wb);
        uint16_t *out=dst_row(j,y);
        /* A sign mismatch between row and column factors clamps to black. */
        uint32_t sign=r->ch;
        if (st->fin==FIN_DIRECT)
            for (int x=0; x<j->ow; ++x) {
                const Tap *c=&cols[x];
                out[x]=c->ch==sign ? pack_e(v[c->i0]*c->wa+v[c->i1]*c->wb) : 0;
            }
        else
            for (int x=0; x<j->ow; ++x) {
                const Tap *c=&cols[x];
                out[x]=c->ch==sign ? lut_e(st,v[c->i0]*c->wa+v[c->i1]*c->wb) : 0;
            }
    }
}
static void rows_lcd3x(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    const Tap *cols=st->cols;
    const uint16_t *cw=st->cw;
    uint32_t *v=sc->v0;
    for (int y=y0; y<y1; ++y) {
        const Tap *r=&st->rows[y];
        vrow_blend(v,src_row(j,r->i0),src_row(j,r->i1),j->sw,r->wa,r->wb);
        uint16_t *out=dst_row(j,y);
        for (int x=0; x<j->ow; ++x) {
            const Tap *c=&cols[x];
            out[x]=lut_w(st,v[c->i0]*c->wa+v[c->i1]*c->wb,cw[x*3],cw[x*3+1],cw[x*3+2]);
        }
    }
}
static void rows_zfast_crt(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    const Tap *cols=st->cols;
    uint32_t *v=sc->v0;
    for (int y=y0; y<y1; ++y) {
        const Tap *r=&st->rows[y];
        vrow_blend(v,src_row(j,r->i0),src_row(j,r->i1),j->sw,r->wa,r->wb);
        int low=(int16_t)r->wt, high=(int16_t)r->wt2, low_mask=(low*st->mlin)/256;
        uint16_t *out=dst_row(j,y);
        for (int x=0; x<j->ow; ++x) {
            const Tap *c=&cols[x];
            uint32_t e=v[c->i0]*c->wa+v[c->i1]*c->wb;
            /* clamp((r+g+b)*0.2667, 0, 1) in 1/256 steps */
            int t=(int)(((ER(e)+(EG(e)>>1)+EB(e))*4511u)>>16);
            if (t>256) t=256;
            int l=c->ch ? low_mask : low;
            int w=l+(((high-l)*t)>>8);
            out[x]=w>0 ? lut_w(st,e,(unsigned)w,(unsigned)w,(unsigned)w) : 0;
        }
    }
}
/* CRT-Easymode and CRT-Aperture: sharp sampling, luminance-sensitive
   scanlines, RGB mask, gamma; Aperture adds screen-blended glow. */
static void rows_easymode(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    const Tap *cols=st->cols, *gcols=st->gcols;
    uint32_t *v=sc->v0, *gv=sc->gv, *e=sc->e, *bl=sc->bl;
    uint16_t *ws=sc->ws;
    int ow=j->ow;
    for (int y=y0; y<y1; ++y) {
        const Tap *r=&st->rows[y];
        vrow_blend(v,src_row(j,r->i0),src_row(j,r->i1),j->sw,r->wa,r->wb);
        const uint16_t *scan=&st->lscan[r->f*33];
        for (int x=0; x<ow; ++x) {
            const Tap *c=&cols[x];
            uint32_t E=v[c->i0]*c->wa+v[c->i1]*c->wb;
            e[x]=E; ws[x]=scan[luma5(E)];
        }
        uint16_t *out=dst_row(j,y);
        if (!j->glow) { finish_crt(out,sc,st->colch,ow,(uint16_t)st->mcrt); continue; }
        const Tap *g=&st->grows[y];
        vrow_blend32(gv,j->glow+(size_t)g->i0*j->sw,j->glow+(size_t)g->i1*j->sw,j->sw,g->wa,g->wb);
        for (int x=0; x<ow; ++x) bl[x]=gv[gcols[x].i0]*gcols[x].wa+gv[gcols[x].i1]*gcols[x].wb;
        finish_crt_glow(out,sc,st->colch,ow,(uint16_t)st->mcrt,(uint16_t)st->amt,(uint16_t)st->bright);
    }
}
/* Dot Matrix: nine-tap phosphor falloff with neighboring pixel glow.
 * Per row, a vectorizable pass blends the three source rows for every source
 * column: V (all three rows, for the left and right neighbours), V0 (rows
 * above and below, for the centre column) and the expanded centre pixel. */
static inline uint16_t x5(uint16_t v) { return (uint16_t)((v<<3)|(v>>2)); }
static inline uint16_t x6(uint16_t v) { return (uint16_t)((v<<2)|(v>>4)); }
static void dot_row(uint16_t *restrict vr, uint16_t *restrict vg, uint16_t *restrict vb,
    uint16_t *restrict wr, uint16_t *restrict wg, uint16_t *restrict wb,
    uint16_t *restrict cr, uint16_t *restrict cg, uint16_t *restrict cb, uint8_t *restrict l,
    const uint16_t *restrict up, const uint16_t *restrict mid, const uint16_t *restrict dn, int sw,
    uint16_t a0, uint16_t a1, uint16_t a2, uint16_t b0, uint16_t b1) {
    for (int x=0; x<sw; ++x) {
        uint16_t u=up[x], m=mid[x], n=dn[x];
        uint16_t ur=x5(u>>11), ug=x6((u>>5)&63), ub=x5(u&31);
        uint16_t mr=x5(m>>11), mg=x6((m>>5)&63), mb=x5(m&31);
        uint16_t nr=x5(n>>11), ng=x6((n>>5)&63), nb=x5(n&31);
        vr[x]=(uint16_t)(((uint16_t)(a0*ur+128)>>8)+((uint16_t)(a1*mr+128)>>8)+((uint16_t)(a2*nr+128)>>8));
        vg[x]=(uint16_t)(((uint16_t)(a0*ug+128)>>8)+((uint16_t)(a1*mg+128)>>8)+((uint16_t)(a2*ng+128)>>8));
        vb[x]=(uint16_t)(((uint16_t)(a0*ub+128)>>8)+((uint16_t)(a1*mb+128)>>8)+((uint16_t)(a2*nb+128)>>8));
        wr[x]=(uint16_t)(((uint16_t)(b0*ur+128)>>8)+((uint16_t)(b1*nr+128)>>8));
        wg[x]=(uint16_t)(((uint16_t)(b0*ug+128)>>8)+((uint16_t)(b1*ng+128)>>8));
        wb[x]=(uint16_t)(((uint16_t)(b0*ub+128)>>8)+((uint16_t)(b1*nb+128)>>8));
        cr[x]=mr; cg[x]=mg; cb[x]=mb;
        l[x]=(uint8_t)((uint16_t)(((mr*27)>>4)+((mg*92)>>4)+((mb*9)>>4))>>8);
    }
}
/* 8-bit channels (<= 1023) times brightness (1/128 steps) to RGB565. */
static void pack_rgb(uint16_t *restrict out, const uint16_t *restrict r, const uint16_t *restrict g,
    const uint16_t *restrict b, int n, uint16_t bright) {
    for (int i=0; i<n; ++i) {
        uint16_t vr=r[i]>320 ? 320 : r[i], vg=g[i]>320 ? 320 : g[i], vb=b[i]>320 ? 320 : b[i];
        vr=(uint16_t)((uint16_t)(vr*bright)>>7); vg=(uint16_t)((uint16_t)(vg*bright)>>7);
        vb=(uint16_t)((uint16_t)(vb*bright)>>7);
        vr=vr>255 ? 255 : vr; vg=vg>255 ? 255 : vg; vb=vb>255 ? 255 : vb;
        out[i]=(uint16_t)(((uint16_t)(vr*249+1024)>>11)<<11 | ((uint16_t)(vg*253+512)>>10)<<5 |
            (uint16_t)(vb*249+1024)>>11);
    }
}
static void rows_dot(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    int sw=j->sw, sh=j->sh;
    const uint16_t *d=sc->dot;
    const uint16_t *vr=d, *vg=d+sw, *vb=d+sw*2, *wr=d+sw*3, *wg=d+sw*4, *wb=d+sw*5;
    const uint16_t *cr=d+sw*6, *cg=d+sw*7, *cb=d+sw*8;
    const uint8_t *lum=sc->dl;
    uint16_t *pr=sc->ws, *pg=sc->ix, *pb=sc->pyb;
    for (int y=y0; y<y1; ++y) {
        const int16_t *r=&st->drow[y*8];
        int iy=r[0];
        /* Rows are 2-byte aligned RGB565 (as the callers' frame buffers are). */
        const uint16_t *up=(const uint16_t *)src_row(j,clampi(iy-1,0,sh-1));
        const uint16_t *mid=(const uint16_t *)src_row(j,iy);
        const uint16_t *dn=(const uint16_t *)src_row(j,clampi(iy+1,0,sh-1));
        uint16_t *dd=sc->dot;
        dot_row(dd,dd+sw,dd+sw*2,dd+sw*3,dd+sw*4,dd+sw*5,dd+sw*6,dd+sw*7,dd+sw*8,sc->dl,up,mid,dn,sw,(uint16_t)r[1],(uint16_t)r[2],(uint16_t)r[3],
            (uint16_t)r[4],(uint16_t)r[5]);
        const uint16_t *center=&st->dotc[r[6]*16*8];
        uint16_t *out=dst_row(j,y);
        for (int x=0; x<j->ow; ++x) {
            const DotTap *t=&st->dcols[x];
            int il=t->il, ir=t->ir, ix=t->ix, fal=t->fal, far_=t->far_, fb=t->fb;
            int wc=center[t->fq*8+lum[ix]];
            int ro=(fal*vr[il]+far_*vr[ir]+fb*wr[ix]+wc*cr[ix]+128)>>8;
            int go=(fal*vg[il]+far_*vg[ir]+fb*wg[ix]+wc*cg[ix]+128)>>8;
            int bo=(fal*vb[il]+far_*vb[ir]+fb*wb[ix]+wc*cb[ix]+128)>>8;
            pr[x]=(uint16_t)(ro<1023 ? ro : 1023); pg[x]=(uint16_t)(go<1023 ? go : 1023);
            pb[x]=(uint16_t)(bo<1023 ? bo : 1023);
        }
        pack_rgb(out,pr,pg,pb,j->ow,(uint16_t)st->bright);
    }
}

/* ---- Curved presets ------------------------------------------------------------
 * Per row, the warped x coordinate is linear in the output column and the
 * warped y coordinate is the row's coefficient times a per-column cx^2. */
static int visible(float u, float v, float curve) {
    float cx=u*2-1, cy=v*2-1;
    float ux=u+cx*cy*cy*0.0138f*curve, vy=v+cy*cx*cx*0.0207f*curve;
    return !(ux<0 || ux>1 || vy<0 || vy>1 ||
        (curve && minf(ux,1-ux)*minf(vy,1-vy)<0.0001f));
}
static inline void split_fp(int32_t X, int32_t max, int *i, int *n, unsigned *w, int last) {
    X=X<0 ? 0 : X>max ? max : X;
    *i=X>>16; *w=((X&0xFFFF)+1024)>>11; *n=*i+(*i<last);
}
/* Per-pixel warped coordinates for one row, in a loop compilers vectorize. */
static inline __attribute__((always_inline)) void curve_taps_body(
    uint16_t *restrict ix, uint8_t *restrict wx, uint8_t *restrict fy, uint16_t *restrict pyb,
    uint16_t *restrict pxb, uint8_t *restrict ch, const int32_t *restrict cx2, int xs, int n,
    int32_t px0, int32_t dpx, int32_t py0, int32_t sbq8, int32_t r, int32_t scale,
    int32_t pxmax, int32_t pymax, int32_t xmax, int32_t q0, int32_t dq, unsigned odd3, const int half) {
    for (int i=0; i<n; ++i) {
        int32_t x=xs+i;
        int32_t px=px0+x*dpx, py=py0+((sbq8*cx2[x])>>6);
        px=px<0 ? 0 : px>pxmax ? pxmax : px;
        py=py<0 ? 0 : py>pymax ? pymax : py;
        int32_t X;
        if (half) X=px-32768;
        else {
            /* Sharp bilinear: hold the texel centre, blend only near edges. */
            int32_t d=(px&0xFFFF)-32768, c=d<-r ? -r : d>r ? r : d;
            X=(px&~0xFFFF)+(d-c)*scale;
        }
        X=X<0 ? 0 : X>xmax ? xmax : X;
        ix[i]=(uint16_t)(X>>16);
        wx[i]=(uint8_t)(((X&0xFFFF)+1024)>>11);
        fy[i]=(uint8_t)((py>>8)&255);
        pyb[i]=(uint16_t)(py>>14);
        pxb[i]=(uint16_t)(px>>14);
        int32_t q=q0+x*dq;
        uint32_t k=(uint32_t)(q<0 ? 0 : q>>16)+odd3;
        ch[i]=(uint8_t)(k-3*((k*0xAAABu)>>17));
    }
}
static void curve_taps(Scratch *sc, int xs, int n, const int32_t *cx2, int32_t px0, int32_t dpx,
    int32_t py0, int32_t sbq8, int32_t r, int32_t scale, int32_t pxmax, int32_t pymax,
    int32_t xmax, int32_t q0, int32_t dq, unsigned odd3, int half) {
    if (half) curve_taps_body(sc->ix,sc->wx,sc->fy,sc->pyb,sc->pxb,sc->ch,cx2,xs,n,
        px0,dpx,py0,sbq8,r,scale,pxmax,pymax,xmax,q0,dq,odd3,1);
    else curve_taps_body(sc->ix,sc->wx,sc->fy,sc->pyb,sc->pxb,sc->ch,cx2,xs,n,
        px0,dpx,py0,sbq8,r,scale,pxmax,pymax,xmax,q0,dq,odd3,0);
}
static void luma_row(uint8_t *restrict l, const uint32_t *restrict e, int n) {
    for (int i=0; i<n; ++i) l[i]=(uint8_t)luma5(e[i]);
}
static void rows_curved(const Job *j, Scratch *sc, int y0, int y1) {
    const struct ShaderState *st=j->st;
    int preset=st->key.preset, sw=j->sw, sh=j->sh, ow=j->ow, oh=j->oh;
    int half=preset==SHADER_CANNELLONI_LITE;
    float curve=st->curve;
    int32_t pxmax=sw<<16, pymax=sh<<16, xmax=(sw-1)<<16, ymax=(sh-1)<<16;
    uint32_t *v=sc->v0, *gv=sc->gv;
    for (int y=y0; y<y1; ++y) {
        uint16_t *out=dst_row(j,y);
        float fv=(y+0.5f)/oh, cy=fv*2-1;
        int xs=0, xe=ow;
        while (xs<ow && !visible((xs+0.5f)/ow,fv,curve)) out[xs++]=0;
        while (xe>xs && !visible((xe-0.5f)/ow,fv,curve)) out[--xe]=0;
        if (xs>=xe) continue;
        double a=(double)cy*cy*0.0138f*curve, b=(double)cy*0.0207f*curve;
        double gain=1+2*a;
        int32_t px0=(int32_t)floor(sw*(0.5*gain/ow-a)*65536+0.5);
        int32_t dpx=(int32_t)floor(sw*gain/ow*65536+0.5);
        int32_t py0=(int32_t)floor(sh*(double)fv*65536+0.5);
        int32_t sb=(int32_t)floor(sh*b*65536+0.5);
        int32_t q0=(int32_t)floor((0.5*gain-a*ow)*65536+0.5);
        int32_t dq=(int32_t)floor(gain*65536+0.5);
        unsigned odd3=preset==SHADER_LOTTES ? (unsigned)(y&1) : 0;
        /* Vertical blend once per source column, at the warped row its
           centre maps to; the warp moves less than 0.1 source rows across
           the few output pixels that share a column. */
        int lo=clampi(((px0+xs*dpx)>>16)-1,0,sw-1), hi=clampi(((px0+(xe-1)*dpx)>>16)+2,0,sw-1);
        double c1=2.0*65536/((double)dpx*ow), c0=2*((32768.0-px0)/dpx+0.5)/ow-1;
        for (int sx=lo; sx<=hi; ++sx) {
            double cx=c0+c1*sx;
            int32_t py=(int32_t)(py0+sb*cx*cx);
            py=py<0 ? 0 : py>pymax ? pymax : py;
            int32_t Y=half ? py-32768 : (py&~0xFFFF)+st->dy[(py>>8)&255];
            int iy, ny; unsigned wy;
            split_fp(Y,ymax,&iy,&ny,&wy,sh-1);
            uint32_t top=SP(ld16(src_row(j,iy),sx));
            v[sx]=wy ? norm5(top*(32-wy)+SP(ld16(src_row(j,ny),sx))*wy) : top;
            if (j->glow) {
                split_fp(py-32768,ymax,&iy,&ny,&wy,sh-1);
                gv[sx]=norm5(j->glow[(size_t)iy*sw+sx]*(32-wy)+j->glow[(size_t)ny*sw+sx]*wy);
            }
        }
        int n=xe-xs;
        v[hi+1]=v[hi]; gv[hi+1]=gv[hi];
        int32_t sbq8=(int32_t)floor(sh*b*256+0.5);
        if (half) curve_taps(sc,xs,n,st->cx2,px0,dpx,py0,sbq8,0,0,pxmax,pymax,xmax,q0,dq,odd3,1);
        else curve_taps(sc,xs,n,st->cx2,px0,dpx,py0,sbq8,st->sharp_r,st->sharp_x,pxmax,pymax,xmax,q0,dq,odd3,0);
        uint32_t *e=sc->e, *bl=sc->bl;
        uint16_t *ws=sc->ws;
        const uint16_t *ix=sc->ix, *pyb=sc->pyb, *pxb=sc->pxb;
        uint8_t *wx=sc->wx;
        const uint8_t *fy=sc->fy;
        uint8_t *chs=sc->ch;
        switch (preset) {
            case SHADER_CANNELLONI_LITE:
                for (int i=0; i<n; ++i) {
                    unsigned w=wx[i], k=ix[i];
                    e[i]=v[k]*(32-w)+v[k+1]*w;
                    w=(st->scan[fy[i]]*st->band[pyb[i]])>>8;
                    ws[i]=(uint16_t)(w<256 ? w : 256);
                }
                break;
            case SHADER_CANNELLONI:
                for (int i=0; i<n; ++i) {
                    unsigned w=wx[i], k=ix[i];
                    e[i]=v[k]*(32-w)+v[k+1]*w;
                }
                luma_row(sc->wx,e,n);
                for (int i=0; i<n; ++i) {
                    unsigned y4=pyb[i], m=((unsigned)st->band[y4]<<7)+st->ex[pxb[i]]*st->eyb[y4];
                    unsigned w=(st->lscan[(fy[i]>>2)*33+wx[i]]*(m>>8))>>8;
                    ws[i]=(uint16_t)(w<256 ? w : 256);
                }
                if (j->glow) for (int i=0; i<n; ++i) {
                    /* Bilinear glow at px - 0.5, from the quarter-texel position:
                       the blur is far smoother than that step. */
                    int32_t g=(int32_t)((uint32_t)pxb[i]<<14)-32768;
                    unsigned gw=(((uint32_t)g&0xFFFF)+1024)>>11, k;
                    if (g<0) { k=0; gw=0; } else k=(unsigned)g>>16;
                    bl[i]=gv[k]*(32-gw)+gv[k+1]*gw;
                }
                break;
            default:
                for (int i=0; i<n; ++i) {
                    unsigned w=wx[i], k=ix[i];
                    e[i]=v[k]*(32-w)+v[k+1]*w;
                    ws[i]=st->scan[fy[i]];
                }
                break;
        }
        out+=xs;
        switch (preset) {
            case SHADER_CANNELLONI_LITE: finish_lin(out,sc,chs,n,(uint16_t)st->mlin); break;
            case SHADER_GEOM: finish_crt_pair(out,sc,n,(unsigned)xs,(uint16_t)st->mcrt); break;
            default:
                if (j->glow) finish_crt_glow(out,sc,chs,n,(uint16_t)st->mcrt,(uint16_t)st->amt,(uint16_t)st->bright);
                else finish_crt(out,sc,chs,n,(uint16_t)st->mcrt);
                break;
        }
    }
}

typedef void (*RowFunc)(const Job *, Scratch *, int, int);
static RowFunc row_func(int preset) {
    switch (preset) {
        case SHADER_NONE: return rows_none;
        case SHADER_LINE: case SHADER_GRID: case SHADER_ZFAST_LCD: return rows_nearest;
        case SHADER_SCANLINE: case SHADER_SHARP_BILINEAR: return rows_bilinear;
        case SHADER_LCD3X: return rows_lcd3x;
        case SHADER_ZFAST_CRT: return rows_zfast_crt;
        case SHADER_EASYMODE: case SHADER_APERTURE: return rows_easymode;
        case SHADER_DOT: return rows_dot;
        default: return rows_curved;
    }
}

/* ---- Threads ------------------------------------------------------------------- */
#ifndef SHADER_NO_THREADS
static void *worker_main(void *arg) {
    struct ShaderState *st=arg;
    int seen=0;
    pthread_mutex_lock(&st->lock);
    for (;;) {
        while (!st->quit && st->generation==seen) pthread_cond_wait(&st->wake,&st->lock);
        if (st->quit) break;
        seen=st->generation;
        const Job *job=st->job;
        int y0=st->job_y0, y1=st->job_y1;
        pthread_mutex_unlock(&st->lock);
        row_func(job->st->key.preset)(job,&st->scratch[1],y0,y1);
        pthread_mutex_lock(&st->lock);
        st->finished=seen;
        pthread_cond_signal(&st->done);
    }
    pthread_mutex_unlock(&st->lock);
    return NULL;
}
static int start_worker(struct ShaderState *st) {
    if (st->worker) return 1;
    if (pthread_mutex_init(&st->lock,NULL)) return 0;
    if (pthread_cond_init(&st->wake,NULL)) { pthread_mutex_destroy(&st->lock); return 0; }
    if (pthread_cond_init(&st->done,NULL)) {
        pthread_cond_destroy(&st->wake); pthread_mutex_destroy(&st->lock); return 0;
    }
    st->quit=st->generation=st->finished=0;
    if (pthread_create(&st->thread,NULL,worker_main,st)) {
        pthread_cond_destroy(&st->done); pthread_cond_destroy(&st->wake);
        pthread_mutex_destroy(&st->lock);
        return 0;
    }
    st->worker=1;
    return 1;
}
static void stop_worker(struct ShaderState *st) {
    if (!st->worker) return;
    pthread_mutex_lock(&st->lock);
    st->quit=1;
    pthread_cond_signal(&st->wake);
    pthread_mutex_unlock(&st->lock);
    pthread_join(st->thread,NULL);
    pthread_cond_destroy(&st->done); pthread_cond_destroy(&st->wake);
    pthread_mutex_destroy(&st->lock);
    st->worker=0;
}
static int wanted_threads(int requested) {
    if (requested<2) return 1;
    long cpus=sysconf(_SC_NPROCESSORS_ONLN);
    return cpus>1 ? 2 : 1;
}
#else
static int wanted_threads(int requested) { (void)requested; return 1; }
#endif

static void run_rows(struct ShaderState *st, const Job *job, int oh) {
    RowFunc rows=row_func(st->key.preset);
#ifndef SHADER_NO_THREADS
    /* Below this size the hand-off costs more than it saves. */
    if (st->threads>1 && oh>=32 && (long)job->ow*oh>=16384 && start_worker(st)) {
        int split=oh/2;
        pthread_mutex_lock(&st->lock);
        st->job=job; st->job_y0=split; st->job_y1=oh;
        int generation=++st->generation;
        pthread_cond_signal(&st->wake);
        pthread_mutex_unlock(&st->lock);
        rows(job,&st->scratch[0],0,split);
        pthread_mutex_lock(&st->lock);
        while (st->finished!=generation) pthread_cond_wait(&st->done,&st->lock);
        pthread_mutex_unlock(&st->lock);
        return;
    }
#endif
    rows(job,&st->scratch[0],0,oh);
}

static int reserve(void **buffer, size_t *capacity, size_t count, size_t size) {
    if (*capacity >= count) return 1;
    void *next=realloc(*buffer,count*size);
    if (!next) return 0;
    *buffer=next; *capacity=count;
    return 1;
}

int Shader_render(ShaderContext *c, const ShaderSettings *settings,
    const void *pixels, int sw, int sh, int pitch,
    void *dst, int dst_pitch, int ow, int oh, unsigned frame) {
    if (!c || !settings || !pixels || !dst || sw<=0 || sh<=0 || ow<=0 || oh<=0 ||
        sw>8192 || sh>8192 || ow>8192 || oh>8192 || pitch<sw*2 || dst_pitch<ow*2 ||
        (size_t)sw*sh>16777216 || (size_t)ow*oh>16777216) return 0;
    ShaderSettings s=*settings;
    Shader_sanitize(&s);
    if (!c->state) {
        c->state=calloc(1,sizeof(*c->state));
        if (!c->state) return 0;
    }
    struct ShaderState *st=c->state;
    int threads=wanted_threads(c->threads);
    if (!c->tables_ready || memcmp(&st->key,&s,sizeof(s)) || st->sw!=sw || st->sh!=sh ||
        st->ow!=ow || st->oh!=oh || st->threads!=threads) {
        c->tables_ready=0;
        if (!layout(st,sw,sh,ow,oh,threads)) return 0;
        st->key=s; st->sw=sw; st->sh=sh; st->ow=ow; st->oh=oh; st->threads=threads;
        setup(st,&s,sw,sh,ow,oh);
        c->tables_ready=1;
    }
    Job job={st,(const uint8_t *)pixels,pitch,NULL,(uint8_t *)dst,dst_pitch,sw,sh,ow,oh};
    if (s.preset==SHADER_CANNELLONI || s.preset==SHADER_CANNELLONI_LITE) update_band(st,sh,frame);
    if ((presets[s.preset].parameters&SHADER_PARAM_GLOW) && s.glow && s.preset!=SHADER_DOT) {
        if (!reserve((void **)&c->blur,&c->blur_capacity,(size_t)sw*sh*3,sizeof(*c->blur))) return 0;
        job.glow=glow_source(c,job.src,pitch,sw,sh);
    }
    run_rows(st,&job,oh);
    return 1;
}

const uint16_t *Shader_process(ShaderContext *c, const ShaderSettings *settings,
    const void *pixels, int sw, int sh, int pitch, int ow, int oh, unsigned frame) {
    if (!c || ow<=0 || oh<=0 || ow>8192 || oh>8192 || (size_t)ow*oh>16777216) return NULL;
    if (c->pixels && pixels && (uintptr_t)pixels >= (uintptr_t)c->pixels &&
        (uintptr_t)pixels < (uintptr_t)c->pixels+c->capacity*2) return NULL;
    if (!settings || !pixels || sw<=0 || sh<=0 || pitch<sw*2) return NULL;
    if (!reserve((void **)&c->pixels,&c->capacity,(size_t)ow*oh,sizeof(*c->pixels))) return NULL;
    if (!Shader_render(c,settings,pixels,sw,sh,pitch,c->pixels,ow*2,ow,oh,frame)) return NULL;
    return c->pixels;
}
void Shader_destroy(ShaderContext *c) {
    if (!c) return;
    if (c->state) {
#ifndef SHADER_NO_THREADS
        stop_worker(c->state);
#endif
        free(c->state->arena);
        free(c->state);
    }
    free(c->pixels); free(c->blur);
    memset(c,0,sizeof(*c));
}
