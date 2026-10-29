#!/usr/bin/env python3
"""Verify sharp Minecraft glass texture on a private compositor."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from PIL import Image, ImageChops, ImageGrab, ImageStat
from Xlib import X, XK, display
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ['CRYSTAL_QA_DIR']).resolve()
STATE = json.loads((RUN / 'state.json').read_text())
assert Path(STATE['env']['XDG_CONFIG_HOME']).resolve() == RUN / 'config'
CONFIG = RUN / 'config/cosmic/com.system76.CosmicComp/v1'
MODE = RUN / 'config/cosmic/com.system76.CosmicTheme.Mode/v1/is_dark'
BACKGROUND = RUN / 'config/cosmic/com.system76.CosmicBackground/v1/all'
ARTIFACTS = RUN / "minecraft-glass"
ARTIFACTS.mkdir(exist_ok=True)
SOURCE = (ROOT / 'shaders/minecraft-glass.frag').read_text()
EFFECT = json.loads((ROOT / 'effects/minecraft-glass.json').read_text())
SAVED = {p: p.read_bytes() if p.exists() else None
         for p in [CONFIG / 'forge_runtime', CONFIG / 'glass_effect', MODE, BACKGROUND]}
pointer = display.Display(STATE['display'])
processes = []
results = []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.minecraft')
    pending.write_text(value + '\n')
    pending.replace(path)


def grab(name=None):
    time.sleep(.7)
    im = ImageGrab.grab(xdisplay=STATE['display']).convert('RGB')
    if name:
        im.save(ARTIFACTS / (name + '.png'))
    return im


def select(blur=35, strength=80, pixel_size=8, color=10, source=SOURCE):
    values = {'forge_minecraft_blur': blur, 'forge_minecraft_texture': strength,
              'forge_minecraft_pixel_size': pixel_size, 'forge_minecraft_color': color}
    params = ','.join('(key:' + json.dumps(key) + ',name:' + json.dumps(name)
                      + ',value:' + str(float(values[key])) + ')'
                      for name, key in EFFECT['shader']['uniforms'].items())
    write(CONFIG / 'forge_runtime', '(abi:1,id:"minecraft-glass",base:"glass",source:'
          + json.dumps(source) + ',parameters:[' + params + '])')
    write(CONFIG / 'glass_effect', '"minecraft-glass"')
    return grab()


def origin(im, rgb=(11, 14, 20)):
    masks = [im.getchannel(i).point([255 if v == c else 0 for v in range(256)])
             for i, c in enumerate(rgb)]
    data = ImageChops.multiply(ImageChops.multiply(masks[0], masks[1]), masks[2]).tobytes()
    rows = [data[y * im.width:(y + 1) * im.width] for y in range(im.height)]
    counts = [row.count(255) for row in rows]
    width = max(counts)
    assert width >= 24, 'Test surface header is missing'
    row = rows[counts.index(width)]
    run = max(row.split(b'\x00'), key=len)
    return row.find(run), next(y for y, count in enumerate(counts) if count >= width * .75)


def diff(a, b, box):
    return sum(ImageStat.Stat(ImageChops.difference(a.crop(box), b.crop(box))).mean) / 3


def check(name, condition, **measurements):
    results.append(dict(test=name, passed=bool(condition), **measurements))
    (ARTIFACTS / 'render-results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(('PASS ' if condition else 'FAIL ') + name + ' ' + json.dumps(measurements), flush=True)
    assert condition, name


def click(x, y):
    xtest.fake_input(pointer, X.MotionNotify, x=x, y=y)
    xtest.fake_input(pointer, X.ButtonPress, 1)
    xtest.fake_input(pointer, X.ButtonRelease, 1)
    pointer.sync()


def drag(start, target):
    move_key = pointer.keysym_to_keycode(XK.string_to_keysym('Super_L'))
    x, y = start[0] + 20, start[1] + 35
    xtest.fake_input(pointer, X.MotionNotify, x=x, y=y)
    xtest.fake_input(pointer, X.KeyPress, move_key)
    xtest.fake_input(pointer, X.ButtonPress, 1)
    pointer.sync()
    time.sleep(.15)
    for step in range(1, 13):
        xtest.fake_input(pointer, X.MotionNotify, x=x + int((target[0] - start[0]) * step / 12),
                         y=y + int((target[1] - start[1]) * step / 12))
        pointer.sync()
        time.sleep(.025)
    xtest.fake_input(pointer, X.ButtonRelease, 1)
    xtest.fake_input(pointer, X.KeyRelease, move_key)
    pointer.sync()


try:
    plain = select(strength=0)
    left, top = origin(plain)
    click(left + 650, top + 35)
    body = (left + 200, top + 220, left + 700, top + 420)
    header = (left + 20, top + 8, left + 550, top + 80)
    ink = (left + 45, top + 500, left + 120, top + 505)
    textured = select()
    check('Pixel texture is visible on the actual compositor', diff(plain, textured, body) > .05,
          difference=diff(plain, textured, body))
    check('Opaque foreground and header remain unchanged', diff(plain, textured, header) == 0 and diff(plain, textured, ink) == 0)
    sharp = select(blur=0)
    blurred = select(blur=100)
    check('Background blur changes independently of texture', diff(sharp, blurred, body) > 1,
          difference=diff(sharp, blurred, body))
    untinted = select(color=0)
    tinted = select(color=100)
    check('Theme color changes the material independently', diff(untinted, tinted, body) > 5,
          difference=diff(untinted, tinted, body))
    field = SOURCE.replace('    color.rgb = clamp(material, 0.0, 1.0) * color.a;',
                           '    color.rgb = vec3(pattern_mask) * color.a;')
    assert field != SOURCE
    mask_clear = select(blur=0, source=field)
    mask_blurred = select(blur=100, source=field)
    mask_blurred.save(ARTIFACTS / 'pixel-mask.png')
    field_tinted = select(color=100, source=field)
    check('Theme color preserves the sharp texture layout', diff(mask_blurred, field_tinted, body) == 0)
    check('Texture coverage stays identical at blur 0 and 100', diff(mask_clear, mask_blurred, body) == 0)
    # No glyphs are drawn in this region of the native test surface.
    colors = mask_blurred.crop(body).getcolors(100000)
    check('Texture edges stay binary without filtering', colors is not None and len(colors) == 2,
          unique_colors=len(colors) if colors else 0)
    row = [mask_blurred.getpixel((x, top + 410))[0] for x in range(left + 220, left + 670)]
    runs = []
    count = 1
    for a, b in zip(row, row[1:]):
        if a == b:
            count += 1
        else:
            runs.append(count)
            count = 1
    check('Small interior highlights align to 4 display pixels', len(runs) > 4 and all(n % 4 == 0 for n in runs[1:]), run_lengths=runs)
    values = [mask_blurred.getpixel((x, y))[0] for y in range(body[1], body[3]) for x in range(body[0], body[2])]
    dark_value = min(values)
    coverage = sum(v > dark_value + 10 for v in values) / len(values)
    check('Interior reflections occupy less than one percent of the pane', 0 < coverage < .01, coverage=coverage)
    boundary = [mask_blurred.getpixel((left + 256, y))[0] for y in range(top + 220, top + 420)]
    check('Internal tile boundaries have no glass frame', max(boundary) - min(boundary) == 0)
    edge = mask_blurred.getpixel((left + 2, top + 410))[0]
    check('The outer window frame remains visible', edge > dark_value + 100)
    little = select(pixel_size=2, source=field)
    big = select(pixel_size=16, source=field)
    check('Pixel size changes the pane grid live', diff(little, big, body) > .2)
    outline = (left - 5, top - 5, left + 1, top + 1)
    check('Texture stays inside the surface clipping', diff(plain, textured, outline) < .2)
    texture_only = SOURCE.replace('    vec3 material = mix(transmitted, pattern_color, texture_alpha);',
                                 '    vec3 material = pattern_color * pattern_mask;')
    assert texture_only != SOURCE
    for dark in [False, True]:
        write(MODE, str(dark).lower())
        time.sleep(.8)
        im = select(source=texture_only)
        im.save(ARTIFACTS / ('texture-' + ('dark' if dark else 'light') + '.png'))
        if dark:
            points = [(x, y) for y in range(body[1], body[3]) for x in range(body[0], body[2])
                      if mask_blurred.getpixel((x, y))[0] > dark_value + 10]
            dark_origin = origin(im)
            theme_delta = sum(sum(abs(a-b) for a, b in zip(
                light_ink.getpixel((point[0] - left + light_origin[0], point[1] - top + light_origin[1])),
                im.getpixel((point[0] - left + dark_origin[0], point[1] - top + dark_origin[1]))))
                for point in points) / (3 * len(points))
            check('Texture ink adapts to the actual light and dark theme', theme_delta > 10,
                  difference=theme_delta)
        else:
            light_ink = im
            light_origin = origin(im)
        select().save(ARTIFACTS / ('minecraft-' + ('dark' if dark else 'light') + '.png'))
    check('Compositor remains running with the custom shader', Path(STATE['env']['XDG_RUNTIME_DIR'], 'cosmic-forge-engine-v1').is_file())
finally:
    for path, content in SAVED.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)
    pointer.close()
