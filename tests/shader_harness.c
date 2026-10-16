#include "shader.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { WIDTH=31, HEIGHT=23, STRIDE=36, OUT_W=95, OUT_H=71 };
static unsigned long hash_pixels(const uint16_t *p, size_t count) {
    unsigned long hash=2166136261u;
    for (size_t i=0; i<count; ++i) hash=(hash^p[i])*16777619u;
    return hash;
}
static unsigned long render_hash(ShaderContext *c, ShaderSettings *s, uint16_t *source) {
    const uint16_t *out=Shader_process(c,s,source,WIDTH,HEIGHT,STRIDE*2,OUT_W,OUT_H,117);
    assert(out);
    return hash_pixels(out,OUT_W*OUT_H);
}
int main(void) {
    ShaderContext context={0};
    uint16_t source[STRIDE*HEIGHT], snapshot[STRIDE*HEIGHT];
    for (int y=0; y<HEIGHT; ++y) for (int x=0; x<STRIDE; ++x)
        source[y*STRIDE+x]=(uint16_t)(((x*5+y*3)%32)<<11 | ((x*2+y*7)%64)<<5 | ((x*3+y*5)%32));
    memcpy(snapshot,source,sizeof(source));
    ShaderSettings s=Shader_defaults(SHADER_NONE);
    const uint16_t *out=Shader_process(&context,&s,source,WIDTH,HEIGHT,STRIDE*2,WIDTH,HEIGHT,0);
    assert(out);
    for (int y=0; y<HEIGHT; ++y) for (int x=0; x<WIDTH; ++x)
        assert(out[y*WIDTH+x]==source[y*STRIDE+x]);
    /* A crop retains the original row pitch and addresses the correct pixel. */
    out=Shader_process(&context,&s,source+STRIDE+3,WIDTH-3,HEIGHT-1,STRIDE*2,WIDTH-3,HEIGHT-1,0);
    assert(out);
    assert(out[0]==source[STRIDE+3]);
    assert(out[WIDTH-3]==source[STRIDE*2+3]);

    unsigned long preset_hashes[SHADER_COUNT];
    for (int preset=0; preset<SHADER_COUNT; ++preset) {
        s=Shader_defaults(preset);
        const ShaderPreset *metadata=Shader_getPreset(preset);
        assert(metadata->id && metadata->name && metadata->description);
        preset_hashes[preset]=render_hash(&context,&s,source);
        for (int before=0; before<preset; ++before) {
            if (preset_hashes[preset]==preset_hashes[before])
                fprintf(stderr,"Duplicate output: %s and %s\n",metadata->id,Shader_getPreset(before)->id);
            assert(preset_hashes[preset]!=preset_hashes[before]);
        }
        /* Every control offered by the UI must change real output. */
        unsigned flags[]={SHADER_PARAM_INTENSITY,SHADER_PARAM_CURVATURE,
            SHADER_PARAM_BRIGHTNESS,SHADER_PARAM_MASK,SHADER_PARAM_GLOW};
        for (int p=0; p<5; ++p) {
            if (!(metadata->parameters&flags[p])) continue;
            s=Shader_defaults(preset);
            int *fields[]={&s.intensity,&s.curvature,&s.brightness,&s.mask,&s.glow};
            *fields[p]=p==2 ? 50 : 0;
            unsigned long low=render_hash(&context,&s,source);
            *fields[p]=p==2 ? 150 : 100;
            unsigned long high=render_hash(&context,&s,source);
            if (low==high) fprintf(stderr,"Inactive control %d for %s\n",p,metadata->id);
            assert(low!=high);
        }
        s=Shader_defaults(preset);
        uint16_t pixel=0x7bef;
        assert(Shader_process(&context,&s,&pixel,1,1,2,7,5,0));
    }
    assert(!memcmp(source,snapshot,sizeof(source)));

    /* Curvature creates black corners, and the CRT phosphor sweep animates. */
    s=Shader_defaults(SHADER_CANNELLONI_LITE);
    uint16_t white[WIDTH*HEIGHT];
    for (int n=0; n<WIDTH*HEIGHT; ++n) white[n]=0xffff;
    out=Shader_process(&context,&s,white,WIDTH,HEIGHT,WIDTH*2,OUT_W,OUT_H,0);
    assert(out && out[0]==0 && out[(OUT_H/2)*OUT_W+OUT_W/2]!=0);
    unsigned long frame0=hash_pixels(out,OUT_W*OUT_H);
    out=Shader_process(&context,&s,white,WIDTH,HEIGHT,WIDTH*2,OUT_W,OUT_H,100);
    assert(frame0!=hash_pixels(out,OUT_W*OUT_H));

    /* Reuse allocations and reject malformed geometry without touching input. */
    uint16_t *allocation=context.pixels;
    s=Shader_defaults(SHADER_NONE);
    assert(Shader_process(&context,&s,source,WIDTH,HEIGHT,STRIDE*2,10,10,0)==allocation);
    assert(!Shader_process(NULL,&s,source,WIDTH,HEIGHT,STRIDE*2,10,10,0));
    assert(!Shader_process(&context,NULL,source,WIDTH,HEIGHT,STRIDE*2,10,10,0));
    assert(!Shader_process(&context,&s,NULL,WIDTH,HEIGHT,STRIDE*2,10,10,0));
    assert(!Shader_process(&context,&s,source,WIDTH,HEIGHT,WIDTH*2-1,10,10,0));
    assert(!Shader_process(&context,&s,source,0,HEIGHT,STRIDE*2,10,10,0));
    assert(!Shader_process(&context,&s,source,WIDTH,HEIGHT,STRIDE*2,1000000,10,0));
    assert(!Shader_process(&context,&s,context.pixels,10,10,20,10,10,0));
    s=(ShaderSettings){999,-3,200,-1,300,-5};
    Shader_sanitize(&s);
    assert(s.preset==SHADER_NONE && s.intensity==0 && s.curvature==100 &&
           s.brightness==50 && s.mask==100 && s.glow==0);
    assert(Shader_getPreset(-1)==Shader_getPreset(SHADER_NONE));
    /* Splitting rows across threads renders exactly the same frame. */
    enum { BIG_W=200, BIG_H=150, BIG_OW=640, BIG_OH=480 };
    static uint16_t big[BIG_W*BIG_H], single[BIG_OW*BIG_OH];
    for (int n=0; n<BIG_W*BIG_H; ++n) big[n]=(uint16_t)(n*2654435761u>>13);
    for (int preset=0; preset<SHADER_COUNT; ++preset) {
        ShaderContext one={0}, two={0};
        two.threads=2;
        s=Shader_defaults(preset);
        for (unsigned frame=0; frame<3; ++frame) {
            out=Shader_process(&one,&s,big,BIG_W,BIG_H,BIG_W*2,BIG_OW,BIG_OH,frame*50);
            assert(out);
            memcpy(single,out,sizeof(single));
            out=Shader_process(&two,&s,big,BIG_W,BIG_H,BIG_W*2,BIG_OW,BIG_OH,frame*50);
            assert(out && !memcmp(single,out,sizeof(single)));
        }
        Shader_destroy(&one); Shader_destroy(&two);
    }
    s=Shader_defaults(SHADER_NONE);
    Shader_destroy(&context);
    assert(!context.pixels && !context.blur && !context.capacity && !context.tables_ready);
    Shader_destroy(&context);
    puts("Shader rendering, parameter, crop, source-integrity, threading and allocation checks passed.");
    return 0;
}
