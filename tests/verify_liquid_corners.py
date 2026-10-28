#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check Liquid Glass corners on the engine's private headless preview.

Start engine/preview.py --headless, then set CRYSTAL_QA_DIR to its run directory.
Pass --source to check another shader against the same regression checks.
"""
import argparse
import json
import os
from pathlib import Path
import time

from PIL import ImageChops, ImageGrab, ImageStat

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'shaders/liquid-glass.frag')
    args = parser.parse_args()
    source = args.source.read_text()
    effect = json.loads((ROOT / 'effects/liquid-glass.json').read_text())
    run = Path(os.environ['CRYSTAL_QA_DIR'])
    state = json.loads((run / 'state.json').read_text())
    config = run / 'config/cosmic/com.system76.CosmicComp/v1'
    saved = {key: (config / key).read_bytes() if (config / key).exists() else None
             for key in ['forge_runtime', 'glass_effect']}
    values = {control['key']: control['default'] for control in effect['controls']}
    values.update(forge_liquid_blur=0, forge_liquid_highlights=0,
                  forge_liquid_dispersion=0, forge_liquid_color=0)
    results = []

    def select(shader=source, **changes):
        current = values | changes
        parameters = ','.join('(key:' + json.dumps(key) + ',name:' + json.dumps(name)
                              + ',value:' + str(float(current[key])) + ')'
                              for name, key in effect['shader']['uniforms'].items())
        entries = {'forge_runtime': '(abi:1,id:"liquid-glass",base:"glass",source:'
                   + json.dumps(shader) + ',parameters:[' + parameters + '])',
                   'glass_effect': '"liquid-glass"'}
        for key, value in entries.items():
            temporary = config / ('.' + key + '.new')
            temporary.write_text(value + '\n')
            temporary.replace(config / key)
        time.sleep(0.8)
        return ImageGrab.grab(xdisplay=state['display']).convert('RGB')

    def check(name, condition, **measurements):
        results.append(dict(test=name, passed=bool(condition), **measurements))
        (run / 'liquid-corners-results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(('PASS ' if condition else 'FAIL ') + name + ' ' + json.dumps(measurements), flush=True)
        assert condition, name

    def difference(first, second, box):
        return sum(ImageStat.Stat(ImageChops.difference(first.crop(box), second.crop(box))).mean) / 3

    try:
        neutral = select(forge_liquid_refraction=0)
        points = [(x, y) for y in range(neutral.height) for x in range(neutral.width)
                  if neutral.getpixel((x, y)) == (11, 14, 20)]
        assert points, 'Calibration header not found'
        left, top = min(x for x, _ in points), min(y for _, y in points)
        body = (left, top + 90, left + 820, top + 540)
        header = (left + 20, top + 8, left + 800, top + 80)
        foreground = (left + 45, top + 500, left + 120, top + 505)
        # Render the actual GLSL lens field to expose plateaus and derivative seams.
        diagnostic = source.replace('    gl_FragColor = color;',
                                    '    gl_FragColor = vec4(vec3(lens_curve), 1.0) * mask * alpha;')
        assert diagnostic != source
        field = select(diagnostic, forge_liquid_clear_center=0)
        for name, direction in [('left', 1), ('right', -1)]:
            edge_x = left if direction == 1 else left + 819
            samples = [field.getpixel((edge_x + direction * d, top + 539 - int(d * 0.4)))[0]
                       for d in range(16, 77)]
            check(name + ' corner lens changes before the former 150px arc',
                  samples[4] - samples[16] > 5, change=samples[4] - samples[16])
            jump = max(abs(a - b) for a, b in zip(samples, samples[1:]))
            check(name + ' corner has no internal circular seam', jump <= 6, maximum_step=jump)

        for center in [0, 40, 90]:
            field = select(diagnostic, forge_liquid_clear_center=center)
            for name, x in [('left', left + 10), ('right', left + 809)]:
                check(name + ' corner retains lensing at Clear center ' + str(center),
                      field.getpixel((x, top + 529))[0] > 0)
        clear = select(forge_liquid_clear_center=100)
        check('Clear center 100 disables all lensing', difference(clear, neutral, body) < 0.1)
        thin = select(forge_liquid_thickness=0)
        check('Thickness zero disables all lensing', difference(thin, neutral, body) < 0.1)
        refracted = select()
        refracted.save(run / 'liquid-corners.png')
        for name, box in [('left', (left + 8, top + 510, left + 28, top + 532)),
                          ('right', (left + 792, top + 510, left + 812, top + 532))]:
            check(name + ' corner refracts the backdrop', difference(refracted, neutral, box) > 1)
        blurred = select(forge_liquid_blur=100)
        blur_change = difference(refracted, blurred, body)
        check('Blur still changes the backdrop', blur_change > 1, difference=blur_change)
        check('Opaque header and controls remain unchanged',
              difference(neutral, blurred, header) == 0 and difference(neutral, blurred, foreground) == 0)
        log = (run / 'compositor.log').read_text()
        check('Shader compiles without fallback', 'Forge shader rejected' not in log and 'panicked' not in log)
    finally:
        for key, data in saved.items():
            path = config / key
            if data is None:
                path.unlink(missing_ok=True)
            else:
                temporary = config / ('.' + key + '.new')
                temporary.write_bytes(data)
                temporary.replace(path)


if __name__ == '__main__':
    main()
