// SPDX-License-Identifier: GPL-3.0-only
// Liquid Glass-inspired optics, using only the generic glass inputs.
// Optical reference: https://github.com/bea4dev/liquid-glass-config-shojiwm
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
uniform vec2 uv_per_pixel;
uniform float blur_amount;
uniform vec3 theme_tint;
uniform vec3 theme_accent;
uniform float forge_liquid_thickness;
uniform float forge_liquid_refraction;
uniform float forge_liquid_clear_center;
uniform float forge_liquid_dispersion;
uniform float forge_liquid_highlights;
uniform float forge_liquid_color;

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
    vec2 rounded = max(q, vec2(0.0));
    float outside = length(rounded);
    float inside = -(outside + min(max(q.x, q.y), 0.0) - radius);
    float mask = smoothstep(-0.5, 0.5, inside);
    if (mask <= 0.0) discard;

    vec2 normal = sign(center) * (outside > 0.0001
        ? rounded / max(outside, 0.0001)
        : (q.x > q.y ? vec2(1.0, 0.0) : vec2(0.0, 1.0)));
    float thickness = clamp(forge_liquid_thickness / 100.0, 0.0, 1.0);
    float refraction = clamp(forge_liquid_refraction / 100.0, 0.0, 1.0);
    float highlights = clamp(forge_liquid_highlights / 100.0, 0.0, 1.0);
    float short_side = min(geo_size.x, geo_size.y);
    float bevel_width = max(1.0, min(mix(7.0, 54.0, thickness), short_side * 0.22));
    float edge = 1.0 - smoothstep(0.0, bevel_width, inside);
    float clear_center = clamp(forge_liquid_clear_center / 100.0, 0.0, 1.0);
    float lens_width = max(0.5, short_side * 0.5 * (1.0 - clear_center));
    // The optical lens is rounder than the window's clipping outline.
    float lens_radius = max(radius, min(150.0, short_side * 0.5));
    vec2 lens_q = abs(center) - geo_size * 0.5 + lens_radius;
    float lens_inside = lens_radius - length(max(lens_q, vec2(0.0)))
        - min(max(lens_q.x, lens_q.y), 0.0);
    float lens_position = clamp(1.0 - max(lens_inside, 0.0) / lens_width, 0.0, 1.0);
    // Extend the lens through the corners; only the real window mask clips it.
    float lens_curve = (1.0 - sqrt(max(0.0, 1.0 - lens_position * lens_position)))
        * (1.0 - step(1.0, clear_center));
    vec2 radial = center / max(max(geo_size.x, geo_size.y), 1.0);
    vec2 lens_direction = radial / max(length(radial), 0.0001);
    float lens_amount = refraction * thickness * lens_curve;
    // shortcut: bend rays inward to stay within the generic base's capture;
    // outward refraction needs an engine-provided capture margin.
    vec2 offset = lens_direction * geo_size * 0.5 * lens_amount * uv_per_pixel;
    float dispersion = min(clamp(forge_liquid_dispersion, 0.0, 10.0), short_side * 0.1);
    vec2 split = lens_direction * dispersion * lens_amount * uv_per_pixel;
    vec2 green_uv = clamp(v_coords - offset, vec2(0.0), vec2(1.0));
    vec2 red_uv = clamp(v_coords - offset - split, vec2(0.0), vec2(1.0));
    vec2 blue_uv = clamp(v_coords - offset + split, vec2(0.0), vec2(1.0));
    vec4 middle = texture2D(tex, green_uv);
    vec4 color = vec4(texture2D(tex, red_uv).r, middle.g,
                      texture2D(tex, blue_uv).b, middle.a);
    if (blur_amount > 0.0) {
        vec4 sharp_middle = texture2D(sharp_tex, green_uv);
        vec4 sharp = vec4(texture2D(sharp_tex, red_uv).r, sharp_middle.g,
                          texture2D(sharp_tex, blue_uv).b, sharp_middle.a);
        float diffusion = smoothstep(0.0, 0.45, blur_amount) * mix(1.0, 0.45, edge);
        color = mix(sharp, color, diffusion);
    }
    #if defined(NO_ALPHA)
    color.a = 1.0;
    #endif
    vec3 transmitted = clamp(color.rgb / max(color.a, 0.0001), 0.0, 1.0);
    vec3 glass_tint = mix(theme_tint, theme_accent, 0.12);
    transmitted = mix(transmitted, glass_tint,
        clamp(forge_liquid_color / 100.0, 0.0, 1.0) * 0.65);

    // A fixed soft light follows the curved bevel, without time or pointer input.
    float light = max(dot(normal, normalize(vec2(-0.55, -0.83))), 0.0);
    float return_light = max(dot(normal, normalize(vec2(0.75, 0.66))), 0.0);
    float rim = 1.0 - smoothstep(0.4, 1.6, inside);
    float inner_rim = exp(-pow((inside - 2.0) / 0.9, 2.0));
    float caustic = exp(-pow((inside - bevel_width * 0.55)
        / max(1.0, bevel_width * 0.16), 2.0));
    transmitted *= 1.0 - highlights * (0.13 * rim + 0.085 * edge * (1.0 - light));
    float sheen = highlights * (rim * (0.18 + 0.48 * light + 0.20 * return_light)
        + inner_rim * 0.12 + caustic * thickness * (0.03 + 0.11 * light));
    transmitted = mix(transmitted, vec3(1.0), clamp(sheen, 0.0, 0.85));
    color.rgb = clamp(transmitted, 0.0, 1.0) * color.a;
    color *= mask * alpha;
    #if defined(DEBUG_FLAGS)
    if (tint == 1.0) color = vec4(0.0, 0.2, 0.0, 0.2) + color * 0.8;
    #endif
    gl_FragColor = color;
}
