# COSMIC Forge Shaders

Keep this repository limited to glass effect definitions, GLSL, examples and pack tooling.
Compositor patches, builders and installers belong to the COSMIC Forge app.
Never modify desktop configuration or launchers to test a pack.
Keep pack format 1 and the official `cosmic-glass` id compatible with Forge ABI 1.
Run `python -m unittest discover -s tests -v` and build the pack before publishing.
Each published pack must have a larger positive revision; do not replace old release assets.
Preserve the `v0.8.0` legacy Crystal tag and release.
