// SPDX-License-Identifier: GPL-3.0-only
// COSMIC Crystal. Geometry clipping adapted from COSMIC's clipped_surface.frag.
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
uniform float alpha;
varying vec2 v_coords;
#if defined(DEBUG_FLAGS)
uniform float tint;
#endif
uniform vec2 geo_size;
uniform vec4 corner_radius;
uniform mat3 input_to_geo;
uniform vec2 uv_per_pixel;
uniform float refraction_strength;
uniform float facet_density;
uniform sampler2D sharp_tex;
uniform float blur_amount;
uniform float crystal_thickness;
uniform float everyday_mode;
uniform vec3 theme_tint;
uniform float forge_crystal_color;
uniform float forge_crystal_dispersion;

vec2 hash2(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

float polish_noise(vec2 p) {
    vec2 cell = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash2(cell).x, hash2(cell + vec2(1.0, 0.0)).x, f.x),
               mix(hash2(cell + vec2(0.0, 1.0)).x, hash2(cell + vec2(1.0)).x, f.x), f.y);
}

// A weighted Voronoi cut: scattered sites and unequal weights produce irregular
// polygon faces of different sizes, without a repeated triangular lattice.
// Keep sites in surface coordinates so the random cuts stay still on movement.
vec4 facet(vec2 p, out vec3 cut_edge) {
    vec2 position = p * facet_density / vec2(170.0, 155.0);
    vec2 cell = floor(position);
    float nearest = 100.0;
    float second = 100.0;
    vec2 closest_site = vec2(0.0);
    vec2 next_site = vec2(0.0);
    vec2 closest_id = vec2(0.0);
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            vec2 id = cell + vec2(float(x), float(y));
            vec2 site = id + 0.05 + hash2(id + 7.13) * 0.9;
            vec2 delta = position - site;
            float score = dot(delta, delta) - hash2(id + 46.7).x * 0.9;
            if (score < nearest) {
                second = nearest;
                next_site = closest_site;
                nearest = score;
                closest_site = site;
                closest_id = id;
            } else if (score < second) {
                second = score;
                next_site = site;
            }
        }
    }
    float seam = (second - nearest) / max(2.0 * distance(closest_site, next_site), 0.01);
    cut_edge = vec3(normalize(next_site - closest_site), seam * 160.0 / facet_density);
    vec2 slope = (hash2(closest_id + 93.2) - 0.5) * 0.8;
    return vec4(slope, 1.0 - smoothstep(0.0015, 0.006, seam), hash2(closest_id + 152.7).y);
}

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
    float distance_inside = -(length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - radius);
    float mask = smoothstep(-0.5, 0.5, distance_inside);
    if (mask <= 0.0) discard;

    vec2 edge_normal = (q.x > 0.0 && q.y > 0.0)
        ? normalize(max(q, vec2(0.0001))) * sign(center)
        : (q.x > q.y ? vec2(sign(center.x), 0.0) : vec2(0.0, sign(center.y)));
    float bevel = 1.0 - smoothstep(0.0, 20.0, distance_inside);
    // Keep broad reading surfaces quiet, with refraction near their perimeter.
    // Compact surfaces retain a little more glass across their interior.
    float short_side = min(geo_size.x, geo_size.y);
    float edge_span = clamp(short_side * 0.18, 14.0, 80.0);
    float edge_focus = 1.0 - smoothstep(4.0, edge_span, distance_inside);
    float compact = 1.0 - smoothstep(96.0, 420.0, short_side);
    float crystal_weight = mix(1.0, 0.60 * edge_focus + 0.20 * compact, everyday_mode);
    vec3 cut_edge;
    vec4 cut = facet(p, cut_edge);
    vec3 normal = normalize(vec3(cut.xy + edge_normal * bevel * 0.85, 1.0));
    // Snell refraction at air / crystal (IOR 1.52), with bounded optical depth.
    vec3 ray = refract(vec3(0.0, 0.0, -1.0), normal, 1.0 / 1.52);
    float optical_depth = 80.0 * (1.0 + 0.90 * crystal_thickness);
    vec2 displacement = ray.xy / max(-ray.z, 0.5) * optical_depth * refraction_strength;
    // Keep all sampled rays inside the compositor's captured background margin.
    displacement *= min(1.0, 40.0 * refraction_strength / max(length(displacement), 0.0001));
    displacement *= crystal_weight;
    vec2 safe_min = uv_per_pixel * 0.5;
    vec2 safe_max = vec2(1.0) - safe_min;
    float dispersion = clamp(forge_crystal_dispersion, 0.0, 10.0) / 40.0;
    vec2 red_displacement = displacement * (1.0 + dispersion);
    // Stronger separation must stay inside the existing background capture.
    red_displacement *= min(1.0, 41.0 * refraction_strength / max(length(red_displacement), 0.0001));
    vec2 red_uv = clamp(v_coords + red_displacement * uv_per_pixel, safe_min, safe_max);
    vec2 green_uv = clamp(v_coords + displacement * uv_per_pixel, safe_min, safe_max);
    vec2 blue_uv = clamp(v_coords + displacement * (1.0 - dispersion) * uv_per_pixel, safe_min, safe_max);
    vec4 middle = texture2D(tex, green_uv);
    vec4 color = vec4(texture2D(tex, red_uv).r, middle.g, texture2D(tex, blue_uv).b, middle.a);
    float surface_roughness = blur_amount > 0.0 ? 1.0 : 0.0;
    if (blur_amount > 0.0 && blur_amount < 1.0) {
        // Scattered unpolished patches vary both between cuts and within a cut.
        // Surface-local coordinates keep the polish pattern still while moving.
        vec2 local = p * facet_density;
        float polish = 0.60 * polish_noise(local / vec2(94.0, 105.0) + 23.7)
            + 0.30 * cut.w
            + 0.10 * polish_noise(local / vec2(28.0, 31.0) + 9.4);
        float roughness = smoothstep(0.32, 0.68, polish);
        // Preserve irregular polish between the endpoints, but make the entire
        // surface clear at zero and entirely frosted at maximum blur.
        float variation = 4.0 * blur_amount * (1.0 - blur_amount);
        roughness = clamp(blur_amount + (roughness - 0.5) * variation, 0.0, 1.0);
        if (everyday_mode > 0.5) {
            // A broad, smooth gradient frosts the reading center while keeping
            // corner facets clearer. Both endpoints remain uniform.
            vec2 from_center = abs(g * 2.0 - 1.0);
            float center_focus = 1.0 - smoothstep(0.20, 1.20, length(from_center));
            float corner_focus = smoothstep(0.20, 0.85, from_center.x * from_center.y);
            float local_blur = clamp(blur_amount + variation
                * (0.45 * center_focus - 0.45 * corner_focus - 0.20 * edge_focus), 0.0, 1.0);
            float local_variation = 4.0 * local_blur * (1.0 - local_blur);
            float polish_roughness = smoothstep(0.32, 0.68, polish);
            roughness = clamp(local_blur + (polish_roughness - 0.5) * local_variation * 0.45, 0.0, 1.0);
            float reading_floor = clamp(local_blur * (1.0 + 1.5 * (1.0 - local_blur)), 0.0, 1.0);
            reading_floor = min(1.0, reading_floor
                + 0.65 * crystal_thickness * local_blur * (1.0 - local_blur));
            roughness = max(roughness, reading_floor * (1.0 - edge_focus));
        }
        roughness = max(roughness, blur_amount * crystal_thickness * 0.55);
        vec4 sharp_middle = texture2D(sharp_tex, green_uv);
        vec4 sharp = vec4(texture2D(sharp_tex, red_uv).r, sharp_middle.g,
                          texture2D(sharp_tex, blue_uv).b, sharp_middle.a);
        color = mix(sharp, color, roughness);
        surface_roughness = roughness;
    }
    #if defined(NO_ALPHA)
    color.a = 1.0;
    #endif

    vec3 light = normalize(vec3(-0.45, -0.65, 0.7));
    float facing = dot(normal, light);
    // Frost hides the background discontinuities at facet borders. Strengthen
    // surface reflections as it rises so the crystal cuts remain readable.
    float frost = blur_amount * blur_amount;
    float face_light = (facing - light.z) * (0.15 + 0.20 * frost) * crystal_weight;
    float sparkle = pow(max(facing, 0.0), 26.0) * 0.18 * crystal_weight;
    float rim = (1.0 - smoothstep(0.3, 1.7, distance_inside)) * 0.22;
    float bevel_light = bevel * max(dot(edge_normal, normalize(vec2(-0.6, -0.8))), 0.0) * 0.16;
    // Reflect light on selected, softly beveled stretches instead of outlining
    // every polygon. Direction and broad surface variation break up the glints.
    float edge_polish = polish_noise(p * facet_density / vec2(48.0, 59.0) + 73.5);
    float edge_bevel = 1.0 - smoothstep(0.0, mix(1.5, 4.5, edge_polish), cut_edge.z);
    float edge_facing = dot(cut_edge.xy, normalize(vec2(-0.6, -0.8)));
    float reflection_patch = smoothstep(0.40, 0.68, edge_polish) * edge_bevel;
    float cut_glint = cut.z * 0.012 * (1.0 - frost)
        + pow(max(edge_facing, 0.0), 3.0) * reflection_patch * 0.08 * frost;
    float cut_shade = max(-edge_facing, 0.0) * reflection_patch * 0.025 * frost;
    // Faint secondary transmission gives selected chips internal depth. Reuse
    // the same roughness so a fully frosted surface never reveals sharp rays.
    vec2 internal_uv = clamp(v_coords - displacement * 0.55 * uv_per_pixel, safe_min, safe_max);
    vec4 internal_color = texture2D(tex, internal_uv);
    if (blur_amount > 0.0 && blur_amount < 1.0) {
        internal_color = mix(texture2D(sharp_tex, internal_uv), internal_color, surface_roughness);
    }
    color = mix(color, internal_color, reflection_patch * crystal_weight * 0.075
        * crystal_thickness);
    // Thickness progressively reveals up to three internal fracture depths.
    for (int layer = 0; layer < 3; layer++) {
        float depth = float(layer);
        float presence = smoothstep(0.10 + depth * 0.25, 0.35 + depth * 0.25, crystal_thickness);
        if (presence > 0.001) {
            if (crystal_weight > 0.001) {
                float angle = depth * 0.85 - 0.60;
                mat2 turn = mat2(cos(angle), -sin(angle), sin(angle), cos(angle));
                vec2 inside_ray = turn * displacement * (0.25 + depth * 0.16);
                vec2 inside_uv = clamp(v_coords + inside_ray * uv_per_pixel, safe_min, safe_max);
                vec4 transmission = texture2D(tex, inside_uv);
                if (blur_amount > 0.0 && blur_amount < 1.0) {
                    transmission = mix(texture2D(sharp_tex, inside_uv), transmission, surface_roughness);
                }
                color = mix(color, transmission, presence * crystal_weight * 0.035);
            }
        }
    }
    // Frost is clean diffuse transmission. Internal depth comes from the
    // refracted background rays above, without a grain or scratch overlay.
    cut_glint *= crystal_weight;
    cut_shade *= crystal_weight;
    color.rgb = clamp(color.rgb * (1.0 + face_light - cut_shade)
        + vec3(sparkle + rim + bevel_light + cut_glint) * color.a, vec3(0.0), vec3(color.a));
    float tone_mode = max(everyday_mode, crystal_thickness * crystal_thickness);
    if (tone_mode > 0.0 && blur_amount > 0.0) {
        // A theme-aware, bounded backdrop tone supports the system's foreground
        // colors. This does not inspect text or recolor application pixels.
        vec3 straight = clamp(color.rgb / max(color.a, 0.0001), 0.0, 1.0);
        vec3 linear_color = pow(straight, vec3(2.2));
        vec3 linear_tint = pow(clamp(theme_tint, 0.0, 1.0), vec3(2.2));
        vec3 toned = mix(linear_color, linear_tint, 0.18);
        float luminance = dot(toned, vec3(0.2126, 0.7152, 0.0722));
        if (dot(theme_tint, vec3(0.2126, 0.7152, 0.0722)) < 0.5) {
            toned *= min(1.0, 0.10 / max(luminance, 0.0001));
        } else {
            toned = vec3(1.0) - (vec3(1.0) - toned)
                * min(1.0, 0.32 / max(1.0 - luminance, 0.0001));
        }
        float protection = blur_amount * (2.0 - blur_amount) * (1.0 - 0.20 * edge_focus) * tone_mode;
        // A thicker crystal volume absorbs busy transmission as well as
        // scattering it. The clear endpoint stays fully clear.
        float absorption = crystal_thickness * smoothstep(0.0, 0.70, blur_amount);
        protection += (1.0 - protection) * absorption * tone_mode;
        color.rgb = mix(straight, pow(toned, vec3(1.0 / 2.2)), protection) * color.a;
    }
    color.rgb = mix(color.rgb, clamp(theme_tint, 0.0, 1.0) * color.a,
        clamp(forge_crystal_color / 100.0, 0.0, 1.0) * 0.65);
    color *= mask * alpha;
    #if defined(DEBUG_FLAGS)
    if (tint == 1.0) color = vec4(0.0, 0.2, 0.0, 0.2) + color * 0.8;
    #endif
    gl_FragColor = color;
}
