# Changelog

## glass-v7 — 2026-10-29

- Add Mica, a visual reconstruction of the Windows 11 matte wallpaper material.
- Place Mica immediately above Aero in the official catalog order.
- Add independent Mica Blur and Wallpaper color controls; keep Opacity shared.
- Adapt to actual system light/dark mode and return inactive windows to a neutral surface.
- Require Forge 0.11+ and renderer revision 4 for Mica. Menu placement requires the Forge update that honors official pack order.
- Preserve the other effects and their saved controls.

Validated with packaging tests, shader compilation variants and 25 checks on real isolated compositor output. Mica is not a pixel-exact port of Microsoft's native implementation.
