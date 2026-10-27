// SPDX-License-Identifier: GPL-3.0-only
// Aero glass: smooth transmission, diagonal reflections and a double glass rim.
// Geometry clipping follows COSMIC's clipped_surface.frag.
#version 100
//_DEFINES_
#if defined(EXTERNAL)
#extension GL_OES_EGL_image_external : require
#endif
precision highp float;
#if defined(EXTERNAL)
uniform samplerExternalOES tex;
#else
uniform sampler2D tex;
#endif
uniform sampler2D sharp_tex;
uniform float alpha;
varying vec2 v_coords;
#if defined(DEBUG_FLAGS)
uniform float tint;
#endif
uniform vec2 geo_size;
uniform vec4 corner_radius;
uniform mat3 input_to_geo;
uniform float blur_amount;
uniform float aero_color;
uniform float aero_reflections;
uniform vec3 theme_tint;
uniform vec3 theme_accent;

float band(float x, float left, float right, float feather) {
    return smoothstep(left - feather, left + feather, x)
        * (1.0 - smoothstep(right - feather, right + feather, x));
}

uniform float forge_prism;

void main() {
    if (alpha <= 0.0) discard;
    vec2 g = (input_to_geo * vec3(v_coords, 1.0)).xy;
    if (g.x < 0.0 || g.y < 0.0 || g.x > 1.0 || g.y > 1.0) discard;
    vec2 p = g * geo_size;
    float radius = g.x < 0.5
        ? (g.y < 0.5 ? corner_radius.x : corner_radius.w)
        : (g.y < 0.5 ? corner_radius.y : corner_radius.z);
    vec2 center = p - geo_size * 0.5;
    vec2 q = abs(center) - geo_size * 0.5 + radius;
    float inside = -(length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - radius);
    float mask = smoothstep(-0.5, 0.5, inside);
    if (mask <= 0.0) discard;

    vec4 color = texture2D(tex, v_coords);
    // The compositor supplies a continuously adjustable Kawase-blurred backdrop.
    // A little original transmission preserves Aero's clear glass at low blur.
    if (blur_amount > 0.0 && blur_amount < 1.0) {
        float diffusion = smoothstep(0.0, 0.35, blur_amount);
        color = mix(texture2D(sharp_tex, v_coords), color, diffusion);
    }
    #if defined(NO_ALPHA)
    color.a = 1.0;
    #endif
    vec3 transmitted = clamp(color.rgb / max(color.a, 0.0001), 0.0, 1.0);
    float light_theme = step(0.5, dot(theme_tint, vec3(0.2126, 0.7152, 0.0722)));
    // Follow both the active accent and the light/dark surface palette. No blue
    // is baked into the effect; changing the system theme updates this live.
    vec3 glass_tint = mix(theme_tint, theme_accent, mix(0.38, 0.26, light_theme));
    float tint_amount = clamp(aero_color, 0.0, 1.0) * 0.78;
    transmitted = mix(transmitted, glass_tint, tint_amount);

    // Fixed, unequal soft bands imitate the reflected environment in Aero's
    // glass atlas. Surface-local coordinates keep them stable while moving;
    // logical units keep their width consistent at different output scales.
    float x = (p.x - 0.52 * p.y) / 760.0;
    float reflection = 0.16 * band(x, -0.13, -0.055, 0.010)
        + 0.095 * band(x, -0.025, 0.12, 0.018)
        + 0.24 * band(x, 0.155, 0.195, 0.006)
        + 0.11 * band(x, 0.225, 0.37, 0.024)
        + 0.18 * band(x, 0.62, 0.69, 0.012)
        + 0.065 * band(x, 0.73, 1.02, 0.035);
    float shade = 0.075 * band(x, 0.125, 0.15, 0.006)
        + 0.06 * band(x, 0.40, 0.54, 0.025);
    float sheen = (1.0 - smoothstep(0.0, 80.0, p.y)) * 0.09;
    float strength = clamp(aero_reflections, 0.0, 1.0);
    transmitted *= 1.0 - shade * strength;
    transmitted = mix(transmitted, vec3(1.0), (reflection + sheen) * strength);

    // A dark outside hairline and a white inset reflection make the thin rim
    // readable against both light and dark backgrounds, including rounded corners.
    float outer_rim = 1.0 - smoothstep(0.0, 0.9, inside);
    float inner_rim = band(inside, 1.0, 2.0, 0.45);
    float bevel = 1.0 - smoothstep(2.0, 8.0, inside);
    transmitted *= 1.0 - 0.32 * outer_rim * strength;
    transmitted = mix(transmitted, vec3(1.0), (0.48 * inner_rim + 0.055 * bevel) * strength);
    transmitted = mix(transmitted, transmitted.brg, clamp(forge_prism / 100.0, 0.0, 1.0));
    color.rgb = clamp(transmitted, 0.0, 1.0) * color.a;
    color *= mask * alpha;
    #if defined(DEBUG_FLAGS)
    if (tint == 1.0) color = vec4(0.0, 0.2, 0.0, 0.2) + color * 0.8;
    #endif
    gl_FragColor = color;
}
