Cannelloni shader collection and Linux software renderer

Imported from https://github.com/Denarmo/cannelloni
Revision: 3175de741c7cea6e1b6c7d5cddf8eeab71ffb687
Source directory: app/src/main/assets/shaders
The bundled GLSL and GLSLP files match that revision, apart from line endings.
The Lite preset lives at crt-cannelloni/crt-cannelloni-lite.glslp.

Linux rendering
---------------
Minarch's Shaders menu selects a portable RGB565 software adaptation implemented
in workspace/all/minarch/shader.c. It works with both SDL1 framebuffer devices
and SDL2 renderers. It renders at the game's destination resolution so masks and
scanlines remain visible after scaling. The GLSL files are preserved as upstream
source/reference assets; minarch does not compile them or execute GPU shaders.

Each preset has a distinct rendering path. Controls shown for a preset affect
the rendered pixels immediately. Intensity controls scanlines or pixel borders;
curvature controls tube warping; mask controls RGB/subpixel attenuation; glow
controls light spreading; brightness controls the final image gain. Settings
are percentages, rather than exposing every upstream uniform. The GPU-only
tilt, individual gamma, noise, beam-width and mask-geometry options are not
exposed. The fixed phosphor sweep advances once per rendered frame.

The Cannelloni full preset retains its four Kawase blur passes with radii 0.5,
1.5, 2.5 and 3.5 source pixels, screen-blended glow, curvature, vignette, mask
and sweep. Lite retains the triangle scanline pattern, mask, curvature and
sweep. LCD3x, Zfast LCD/CRT and Sharp Bilinear follow the corresponding upstream
sampling/mask formulas with common controls. Dot Matrix uses its nine-tap
phosphor falloff. Legacy Scanlines and LCD Grid remain available.

This is not a pixel-identical GLSL implementation. Intermediate buffers use
RGB565. Full CRT variants replace Lanczos/Gaussian GPU filters with sharpened
bilinear sampling; CRT-Geom uses the Cannelloni warp instead of a spherical
projection. EasyMode, Aperture and Lottes use simplified scanline/mask kernels.
The full Cannelloni preset omits noise and fixes gamma/vignette/sweep settings.
Scanline Sine uses a periodic grid in both axes. Glow and Dot Matrix cost more
CPU; Lite and Zfast presets are preferable on slower devices. Performance and
presentation still need validation on each target handheld.

Performance
-----------
The renderer is written for handhelds without a usable GPU, such as the Miyoo
Mini Plus (two Cortex-A7 cores with NEON). Floating point only runs when the
settings or frame geometry change: per-column and per-row tables hold sample
taps, scanline profiles and mask phases. Pixels are blended in a packed RGB565
form, and each row finishes in plain 16-bit loops that compilers vectorize.
Without curvature the vertical blend runs once per source pixel; with
curvature it runs once per source column at that column's warped row. When the
core is not already threaded, minarch splits rows across two CPUs. Shaders are
built separately at -O3 (with NEON on the Miyoo Mini) and, on the Miyoo Mini,
written straight into the screen.

Further approximations made for speed, all below one RGB565 step on average:
CRT gamma uses c^(10/9) = c(0.834 + 0.166c) after folding the scanline and mask
weights out of the power; Dot Matrix fits its neighbour falloff with separable
functions and keeps the exact radial falloff for the centre tap; glow and
Cannelloni's vignette and sweep are sampled from quarter-texel tables.

Attribution and licenses
------------------------
CRT Cannelloni: Denarmo/Cannelloni contributors; CRT base derived from EasyMode
(GPL). Denarmo's original additions are MIT; combined derivative remains GPL.
CRT EasyMode and CRT Aperture: EasyMode, GPL.
CRT Geom: cgwg, Themaister and DOLLS, GPL-2.0-or-later.
Zfast CRT/LCD: Greg Hogan (SoltanGris42), GPL-2.0-or-later.
CRT Lottes Fast: Timothy Lottes, RetroArch adaptation by hunterk, public domain.
LCD3x: Gigaherz, public domain.
Dot Matrix: Themaister, public domain.
Sharp Bilinear: Themaister, public domain.
Scanline: upstream bundled scanline shader; retained attribution/license file.

Original notices remain in the GLSL sources. Additional upstream license text
is in licenses/shaders in the source distribution. The portable renderer's
combined shader adaptations are provided under GPL-3.0-or-later.
