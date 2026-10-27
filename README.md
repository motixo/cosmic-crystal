# COSMIC Forge Shaders

Glass effects for **COSMIC Forge**: Crystal, Aero, Liquid Glass and the definition for COSMIC's
native Frosted Glass. This is the former `cosmic-crystal` repository, renamed with
its history and releases intact.

[Install COSMIC Forge](https://github.com/motixo/cosmic-forge#install) with the
one-line installer or native DEB, RPM and Arch packages, then select or import effects in the app.

This repository contains effect data and GLSL, plus a Python pack builder. It does
not patch, build or install the compositor or COSMIC Settings. Renderer setup and
restoration belong to the Forge app. Existing standalone Crystal installers are
retained in [v0.8.0](https://github.com/motixo/cosmic-forge-shaders/tree/v0.8.0).

## Contents

- `effects.json`: built-in effect descriptions and controls.
- `shaders/crystal.frag`: Crystal refraction, frost and Everyday mode.
- `shaders/aero.frag`: Aero glass, reflections and theme tint.
- `shaders/liquid-glass.frag`: curved refraction and soft edge highlights on the generic glass base.
- `shaders/glass.frag`: neutral generic glass template with independent blur.
- `effects/*.json`: optional additional glass effect definitions.
- `examples/`: an importable Prism pack and a separate JSON + `.frag` example.
- `scripts/package_effects.py`: combines metadata and GLSL into a release asset.

Frosted Glass uses COSMIC's native pipeline, so it has no `.frag` file here.

## Build a pack

Requires Python 3.11+; no third-party Python dependencies.

```sh
python -m unittest discover -s tests -v
python scripts/package_effects.py --revision 1
```

The generated official pack is installed through Forge's verified GitHub update
feed; its reserved pack id cannot be imported as a local community pack.

To add a glass effect, add its definition to `effects/<id>.json` and GLSL to
`shaders/<id>.frag`. The definition follows an entry in `effects.json`, including
`id`, `name`, `tagline`, `description`, `preview`, `controls` and an optional
`shader.uniforms` map from custom float uniform names to control keys. Choose
`glass`, `aero` or `crystal` as the base pipeline. Custom control keys and uniform names
start with `forge_`; source is limited to 64 KiB. See the Prism example for a
complete definition. A complete pack can also be imported through Forge settings,
or select its JSON metadata and `.frag` together.

Community authors can build a separate pack:

```sh
python scripts/package_effects.py --catalog examples/prism-files/prism.json \
  --shader-dir examples/prism-files --pack-id prism-demo --revision 1 \
  --output build/prism.json
cosmic-forge --import-pack build/prism.json
```

## Publish an update

Increase the positive pack revision for each change, then tag the tested source:

```sh
git tag glass-v2
git push origin glass-v2
```

The release workflow builds `cosmic-forge-glass.json` using that revision and
publishes it on the tagged stable GitHub release. Forge checks this repository on
startup and every six hours while open, and verifies the asset's SHA-256 digest
before installation. Users can also choose **Check for updates** in Forge settings.
The official pack id remains `cosmic-glass`; community packs are kept separately.
Compatible shader updates do not rebuild the compositor or change desktop launchers.

Forge's source checkout includes this repository as the `shaders` Git submodule.
Its pinned commit supplies built-in definitions at compile time; installed apps
download release packs independently of Git.

GPL-3.0-only. Independent project; COSMIC is developed by System76 and its contributors.

## Generic glass

Forge 0.5+ and engine renderer revision 2 add `shader.base: "glass"`. The neutral
template supplies sharp/blurred background textures, geometry, output scale and
theme colors. It has no fixed tint, reflections or facets. Map `forge_blur` to a
unique per-effect integer control key in 0–100; it controls the blur pipeline and
defaults to 45 if absent. Opacity stays shared. Other custom float uniforms work
as usual. An invalid source falls back to neutral glass.

```sh
cosmic-forge --import-pack examples/plain-glass/plain-glass.json \
  examples/plain-glass/plain-glass.frag
python scripts/package_effects.py --catalog examples/plain-glass/plain-glass.json \
  --shader-dir examples/plain-glass --pack-id plain-glass --revision 1 \
  --output build/plain-glass.json
```

The example stays outside the official catalog so the existing release feed
remains compatible with older Forge apps. Glass packs require Forge 0.5+.
Detailed shader inputs and creation steps are documented in
[adding effects](https://github.com/motixo/cosmic-forge/blob/main/docs/adding-effects.md).

Liquid Glass uses this base for broad, curved refraction inspired by
[this ShojiWM configuration](https://github.com/bea4dev/liquid-glass-config-shojiwm).
The lens displacement scales with the surface size, with adjustable chromatic
dispersion near the rim. Lensing adjusts the geometric distortion, from 0% (no
distortion) to 100% (full lensing), without changing its tint or opacity.
Clear center sets the size of the undistorted middle: lower values let lensing
reach further inward; higher values restrict it to the edges. At 100% the entire
surface is free of lens distortion. Blur remains independent.
Blur, thickness, dispersion and highlights have independent controls;
opacity remains shared. This is a shader-only interpretation, without pointer
tracking or morphing animations. Try the source pair in Forge 0.5+ with renderer 2:

```sh
cosmic-forge --import-pack effects/liquid-glass.json shaders/liquid-glass.frag
```
