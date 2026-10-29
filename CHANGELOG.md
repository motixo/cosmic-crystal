# Changelog

## glass-v8 — 2026-10-29

- Add **Minecraft Glass**: a thin outer frame and sparse connected-glass pixel
  reflections, with no internal grid. Pixel reflections use the selected Accent
  and stay sharp when the background is blurred. Include independent Blur,
  Pixel size, Texture and Theme color controls.
- Add **Void**: transparent infinity-mirror glass with Accent light frames,
  window-position parallax and a straight tunnel when the window is centered.
  Include Blur for both glass and lines, Glow up to 1000%, Theme color,
  Reflections, Line spacing and Motion controls. Gaps widen only slightly with depth.
- Make Void redraw on demand and evaluate only neighboring reflections instead
  of shading every frame at every pixel. Preserve clipping and opaque foregrounds.
- Add Void Display width/height calibration for different resolutions and output
  scales. Dimensions are configured manually; different-resolution monitors may
  need different values. Require standard fragment derivatives.
- Append Minecraft Glass and Void after Liquid Glass, preserving Mica above Aero
  and keeping all existing effect ids, controls and shared Opacity preferences.

The full pack retains the Forge 0.11+ / renderer revision 4 requirement from Mica;
optional wallpaper-only backdrop selection needs renderer revision 5. Updating
the shaders does not replace the compositor. GLES variants, real private-XDG
compositor rendering, window motion, blur, tint, spacing and idle behavior are
checked before release. GPU timing is shader-only and does not predict total
desktop GPU utilization; other GPU drivers are not separately benchmarked.

## glass-v7 — 2026-10-29

- Add Mica, a visual reconstruction of the Windows 11 matte wallpaper material.
- Place Mica immediately above Aero in the official catalog order.
- Add independent Mica Blur and Wallpaper color controls; keep Opacity shared.
- Adapt to actual system light/dark mode and return inactive windows to a neutral surface.
- Require Forge 0.11+ and renderer revision 4 for Mica. Menu placement requires the Forge update that honors official pack order.
- Preserve the other effects and their saved controls.

Validated with packaging tests, shader compilation variants and 25 checks on real isolated compositor output. Mica is not a pixel-exact port of Microsoft's native implementation.
