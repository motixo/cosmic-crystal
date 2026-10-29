#!/usr/bin/env python3
"""Verify Mica on a private engine/preview.py compositor (renderer 4+)."""
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
ENGINE = Path(os.environ.get("FORGE_ENGINE_DIR", ROOT.parent / "engine"))
RUN = Path(os.environ['CRYSTAL_QA_DIR']).resolve()
STATE = json.loads((RUN / 'state.json').read_text())
assert Path(STATE['env']['XDG_CONFIG_HOME']).resolve() == RUN / 'config'
CONFIG = RUN / 'config/cosmic/com.system76.CosmicComp/v1'
MODE = RUN / 'config/cosmic/com.system76.CosmicTheme.Mode/v1/is_dark'
BACKGROUND = RUN / 'config/cosmic/com.system76.CosmicBackground/v1/all'
ARTIFACTS = RUN / 'mica'
ARTIFACTS.mkdir(exist_ok=True)
SOURCE = (ROOT / 'shaders/mica.frag').read_text()
EFFECT = json.loads((ROOT / 'effects/mica.json').read_text())
SAVED = {p: p.read_bytes() if p.exists() else None
         for p in [CONFIG / 'forge_runtime', CONFIG / 'glass_effect', MODE, BACKGROUND]}
pointer = display.Display(STATE['display'])
processes = []
results = []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.mica')
    pending.write_text(value + '\n')
    pending.replace(path)


def grab(name=None):
    time.sleep(.7)
    im = ImageGrab.grab(xdisplay=STATE['display']).convert('RGB')
    if name:
        im.save(ARTIFACTS / (name + '.png'))
    return im


def select(blur=100, strength=100, source=SOURCE):
    parameters = [dict(key=key, name=name, value=float(blur if name == 'forge_blur' else strength))
                  for name, key in EFFECT['shader']['uniforms'].items()]
    params = ','.join('(key:' + json.dumps(p['key']) + ',name:' + json.dumps(p['name'])
                     + ',value:' + str(p['value']) + ')' for p in parameters)
    write(CONFIG / 'forge_runtime', '(abi:1,id:"mica",base:"glass",backdrop:wallpaper,source:'
          + json.dumps(source) + ',parameters:[' + params + '])')
    write(CONFIG / 'glass_effect', '"mica"')
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
    neutral_source = (ROOT / 'shaders/glass.frag').read_text()
    neutral = select(source=neutral_source)
    left, top = origin(neutral)
    click(left + 650, top + 35)
    body = (left + 350, top + 220, left + 700, top + 420)
    header = (left + 20, top + 8, left + 550, top + 80)
    ink = (left + 45, top + 500, left + 120, top + 505)
    light = None
    for dark in [False, True]:
        write(MODE, str(dark).lower())
        time.sleep(.8)
        neutral = select(source=neutral_source)
        colored = select()
        name = 'dark' if dark else 'light'
        colored.save(ARTIFACTS / ('mica-' + name + '.png'))
        solid = select(strength=0)
        delta = diff(colored, solid, body)
        check(name + ' active surface receives subtle wallpaper color', .3 < delta < 18, difference=delta)
        check(name + ' preserves opaque header and foreground', diff(neutral, colored, header) == 0 and diff(neutral, colored, ink) == 0,
              header_difference=diff(neutral, colored, header), foreground_difference=diff(neutral, colored, ink))
        corner = (left - 5, top - 5, left + 1, top + 1)
        check(name + ' preserves corner clipping', diff(neutral, colored, corner) < .2)
        check(name + ' zero color produces a flat matte surface', max(ImageStat.Stat(solid.crop(body)).stddev) < .6)
        colored = select()
        sharp = select(blur=0)
        delta = diff(colored, sharp, body)
        check(name + ' blur changes diffusion without lens distortion', delta > .1, difference=delta)
        select()
        if dark:
            check('Actual theme mode changes Mica live', diff(light, colored, body) > 140)
        else:
            light = colored

    select()
    auxiliary = subprocess.Popen([str(ENGINE / 'build/bin/test-surface'), '--small-opaque'],
                                 env=STATE['env'], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
    processes.append(auxiliary)
    time.sleep(.8)
    drag(origin(grab(), (50, 60, 70)), (12, 12))
    click(left + 650, top + 35)
    colored = grab('mica-focused')
    click(100, 45)
    inactive = grab('mica-inactive')
    solid = select(strength=0)
    delta = diff(inactive, solid, body)
    check('Inactive windows return to the exact neutral fallback', delta < .1, difference=delta)
    check('Real focus changes remove the wallpaper tint', diff(colored, inactive, body) > .3)
    click(left + 650, top + 35)
    restored = select()
    check('Refocusing restores wallpaper color deterministically', diff(colored, restored, body) < .1)

    saved_wallpaper = BACKGROUND.read_text()
    def luminance(rgb):
        values = [v / 255 for v in rgb]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(linear, [.2126, .7152, .0722]))

    for dark in [False, True]:
        write(MODE, str(dark).lower())
        time.sleep(.8)
        samples = []
        for rgb in [(255, 255, 255), (0, 0, 0), (255, 0, 0), (0, 0, 255)]:
            path = RUN / ('mica-wallpaper-' + '-'.join(map(str, rgb)) + '.png')
            Image.new('RGB', (1280, 900), rgb).save(path)
            write(BACKGROUND, '(output:"all",source:Path(' + json.dumps(str(path)) + '),filter_by_theme:false,rotation_frequency:300,filter_method:Lanczos,scaling_mode:Zoom,sampling_method:Alphanumeric)')
            time.sleep(1)
            im = grab()
            values = ImageStat.Stat(im.crop(body)).mean
            samples.append(values)
            foreground = luminance((242, 247, 255) if dark else (15, 17, 20))
            background = luminance(values)
            contrast = (max(foreground, background) + .05) / (min(foreground, background) + .05)
            check(('Dark' if dark else 'Light') + ' material supports readable text on ' + str(rgb),
                  contrast >= 4.5, contrast=contrast, mean=values)
        check(('Dark' if dark else 'Light') + ' material suppresses wallpaper luminance contrast',
              max(abs(a-b) for a, b in zip(samples[0], samples[1])) < .1)
    write(BACKGROUND, saved_wallpaper)
    click(left + 650, top + 35)
    im = grab('mica-final')
    check('The real compositor stays running', Path(STATE['env']['XDG_RUNTIME_DIR'], 'cosmic-forge-engine-v1').is_file())
finally:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
    for path, content in SAVED.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)
    pointer.close()
