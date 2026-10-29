Adds **Mica**, a matte material inspired by Windows 11, immediately above Aero in the official catalog.

- Uses only the desktop wallpaper, excluding windows and panels underneath.
- Follows the system light/dark theme and returns to a neutral surface when the window is inactive.
- Includes independent **Blur** and **Wallpaper color** controls, both defaulting to 100%. Opacity remains shared with the other effects.
- The light theme deliberately retains only a faint wallpaper tint. This is a visual reconstruction, not Microsoft's native implementation or a pixel-exact port.
- Preserves Crystal, Aero, Liquid Glass and their existing controls and preferences.

**Requirements:** Mica needs Forge 0.11+ and engine renderer revision 4. Displaying Mica above Aero also needs the Forge update that honors official pack order; earlier versions append new effects after the built-in presets. Older apps that do not understand wallpaper backdrops will reject the new pack and retain their installed pack.

Install through **COSMIC Forge → Check for updates** after updating Forge and its engine as needed. The shader pack itself does not install or replace a compositor.

Validation: seven packaging tests, 25 checks on real isolated COSMIC compositor output, and GLES shader compilation variants. The render checks cover blur, wallpaper tint, light/dark mode, focus fallback, foreground preservation, clipping and text contrast. Pixel-for-pixel comparison with Windows and other GPU drivers were not separately tested.
