**Ember** and **Snow** join the official shader pack, and **Void** now follows
your current monitor automatically.

- **Void:** the engine supplies display dimensions and window position, so the
  tunnel stays straight when centered and adjusts when moving between monitors.
  Rotation and fractional scaling are handled automatically. Manual Display
  width/height controls are removed; the other controls are preserved. Void
  continues to redraw on demand without continuous idle animation.
- **Ember:** rising orange and red flames with independent Background opacity,
  Flame strength, Flame size, Theme color and Blur. Adapted from
  [trinketMage's Shadertoy effect](https://www.shadertoy.com/view/3tcBzH), with
  upstream attribution and licensing notices retained.
- **Snow:** natural, layered snowfall with varied speed, size and sideways drift.
  Snow settles from the bottom on each window's own clock, with subtle powder
  texture. Adjust Fill time, Snowfall, Flake size and Blur, or turn Snow
  accumulation off to keep only the falling flakes.

Ember and Snow support animated rendering. Forge builds with the per-effect
**Animation** switch can make them still and stop continuous redraws. That app
control is not included in stable Forge 0.11.2.

**Install [engine 0.6.0](https://github.com/motixo/cosmic-forge-engine/releases/tag/engine-v0.6.0)
(renderer revision 7) through Settings → Patches, then sign out and back in.**
After that, use **Check for updates** to install pack 9. Shader updates and engine
installation are separate. Existing effects and shared Opacity are preserved.

If you imported development packs containing `ember` or `snow`, back up and
remove those local packs before installing this official update; duplicate effect
ids cannot coexist.

Details: [CHANGELOG.md](https://github.com/motixo/cosmic-forge-shaders/blob/glass-v9/CHANGELOG.md)
and [shader credits](https://github.com/motixo/cosmic-forge-shaders/blob/glass-v9/CREDITS.md).
