# COSMIC Forge Shaders

Glass effects for **COSMIC Forge**: Crystal, Aero and the definition for COSMIC's
native Frosted Glass. This is the former `cosmic-crystal` repository, renamed with
its history and releases intact.

This repository contains effect data and GLSL, plus a Python pack builder. It does
not patch, build or install the compositor or COSMIC Settings. Renderer setup and
restoration belong to the Forge app. Existing standalone Crystal installers are
retained in [v0.8.0](https://github.com/motixo/cosmic-forge-shaders/tree/v0.8.0).

## Contents

- `effects.json`: built-in effect descriptions and controls.
- `shaders/crystal.frag`: Crystal refraction, frost and Everyday mode.
- `shaders/aero.frag`: Aero glass, reflections and theme tint.
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
`aero` or `crystal` as the base pipeline. Custom control keys and uniform names
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
