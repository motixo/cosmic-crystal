Adds **Void** and **Minecraft Glass** to the official COSMIC Forge shader pack.

- **Minecraft Glass:** one thin outer frame with sparse Accent-colored pixel
  reflections and no internal grid. Background Blur leaves the pixel texture
  sharp; Pixel size, Texture and Theme color have separate controls.
- **Void:** transparent infinity-mirror glass with Accent lights and parallax
  that follows window movement. Center the window to look straight down the
  tunnel. Adjust Reflections, Line spacing, Motion, Theme color and Glow up to
  1000%; Blur softens both the backdrop and the light lines. Gaps widen gently
  toward the far end.
- Void redraws on demand instead of requesting continuous idle frames, and
  shades only neighboring reflections. Set **Display width/height** to your
  display's physical pixel resolution (defaults: 1920 × 1080); different-resolution
  displays currently require manual adjustment. Standard fragment derivatives
  are required.
- Keeps Mica above Aero, appends the two new effects after Liquid Glass, and
  preserves existing effect controls and shared Opacity.

**Requirements:** the complete pack retains Forge 0.11+ and renderer revision 4
from Mica. Renderer revision 5 is needed for optional wallpaper-only backdrops.
The shader update itself does not install or replace a compositor.

Install through **COSMIC Forge → Check for updates**. If you previously imported
development packs with the same `void` or `minecraft-glass` ids, back up and remove
those local packs first; duplicate effect ids cannot coexist with the official pack.

Validation covers packaging, GLES shader variants, real isolated compositor
rendering, blur, tint, pixel sharpness, window movement, centering, spacing and
Void idle behavior. NVIDIA GPU timer checks cover orientation and shader cost;
total desktop GPU usage and performance on other drivers vary.

Full details: [CHANGELOG.md](https://github.com/motixo/cosmic-forge-shaders/blob/glass-v8/CHANGELOG.md).
