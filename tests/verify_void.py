#!/usr/bin/env python3
"""Exercise Void on a real compositor in private XDG, including actual window drags."""
import json
import os
from pathlib import Path
import time

from PIL import ImageChops, ImageGrab, ImageOps, ImageStat
from Xlib import X, XK, display
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ['VOID_QA_DIR']).resolve()
STATE = json.loads((RUN / 'state.json').read_text())
assert Path(STATE['env']['XDG_CONFIG_HOME']).resolve() == RUN / 'config'
CONFIG = RUN / 'config/cosmic/com.system76.CosmicComp/v1'
MODE = RUN / 'config/cosmic/com.system76.CosmicTheme.Mode/v1/is_dark'
ARTIFACTS = RUN / 'void'
ARTIFACTS.mkdir(exist_ok=True)
SOURCE = (ROOT / 'shaders/void.frag').read_text()
EFFECT = json.loads((ROOT / 'effects/void.json').read_text())
SAVED = {p: p.read_bytes() if p.exists() else None
         for p in [CONFIG / 'forge_runtime', CONFIG / 'glass_effect', MODE]}
pointer = display.Display(STATE['display'])
move_key = pointer.keysym_to_keycode(XK.string_to_keysym('Super_L'))
results = []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.void')
    pending.write_text(value + '\n')
    pending.replace(path)


def grab(name=None):
    im = ImageGrab.grab(xdisplay=STATE['display']).convert('RGB')
    if name:
        im.save(ARTIFACTS / (name + '.png'))
    return im


def select(blur=30, depth=26, glow=85, motion=80, spacing=100, color=0, source=SOURCE, animated=None):
    values = dict(forge_void_blur=blur, forge_void_depth=depth,
                  forge_void_glow=glow, forge_void_parallax=motion, forge_void_spacing=spacing, forge_void_color=color)
    params = ','.join('(key:' + json.dumps(key) + ',name:' + json.dumps(name)
                      + ',value:' + str(float(values[key])) + ')'
                      for name, key in EFFECT['shader']['uniforms'].items())
    if animated is None:
        animated = EFFECT['shader'].get('animated', False)
    write(CONFIG / 'forge_runtime', '(abi:1,id:"void",base:"glass",animated:' + str(animated).lower() + ',source:'
          + json.dumps(source) + ',parameters:[' + params + '])')
    write(CONFIG / 'glass_effect', '"void"')
    time.sleep(.8)
    return grab()


def origin(im):
    masks = [im.getchannel(i).point([255 if v == c else 0 for v in range(256)])
             for i, c in enumerate((11, 14, 20))]
    data = ImageChops.multiply(ImageChops.multiply(masks[0], masks[1]), masks[2]).tobytes()
    rows = [data[y * im.width:(y + 1) * im.width] for y in range(im.height)]
    counts = [row.count(255) for row in rows]
    width = max(counts)
    assert width >= 24, 'Test surface header is missing'
    row = rows[counts.index(width)]
    run = max(row.split(b'\x00'), key=len)
    return row.find(run), next(y for y, count in enumerate(counts) if count >= width * .75)


def local(im, box=(170, 220, 740, 420)):
    x, y = origin(im)
    return im.crop((box[0] + x, box[1] + y, box[2] + x, box[3] + y))


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def check(name, condition, **measurements):
    results.append(dict(test=name, passed=bool(condition), **measurements))
    (ARTIFACTS / 'render-results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(('PASS ' if condition else 'FAIL ') + name + ' ' + json.dumps(measurements), flush=True)
    assert condition, name


def drag(dx, dy):
    x, y = origin(grab())
    xtest.fake_input(pointer, X.MotionNotify, x=x + 350, y=y + 40)
    xtest.fake_input(pointer, X.KeyPress, move_key)
    xtest.fake_input(pointer, X.ButtonPress, 1)
    pointer.sync()
    time.sleep(.15)
    for step in range(1, 17):
        xtest.fake_input(pointer, X.MotionNotify, x=x + 350 + int(dx * step / 16),
                         y=y + 40 + int(dy * step / 16))
        pointer.sync()
        time.sleep(.03)
    xtest.fake_input(pointer, X.ButtonRelease, 1)
    xtest.fake_input(pointer, X.KeyRelease, move_key)
    pointer.sync()
    time.sleep(.5)


try:
    neutral = select(source=(ROOT / 'shaders/glass.frag').read_text())
    actual = select()
    actual.save(ARTIFACTS / 'void-initial.png')
    delta = diff(local(neutral), local(actual))
    check('Void renders on the compositor rather than falling back', delta > .2, difference=delta)
    check('The background remains glass without a black backing', delta < 10, difference=delta)
    untinted = select(color=0)
    tinted = select(color=100)
    delta = diff(local(untinted), local(tinted))
    check('Theme color tints the glass using the actual system palette', delta > 5, difference=delta)
    tinted.save(ARTIFACTS / 'void-theme-color.png')
    actual = select()
    check('Opaque foreground pixels remain unchanged',
          diff(local(neutral, (20, 8, 800, 80)), local(actual, (20, 8, 800, 80))) == 0)
    time.sleep(.35)
    check('Reflections remain still while the window is stationary', diff(local(actual), local(grab())) < .05)
    shallow = select(depth=8)
    deep = select(depth=32)
    delta = diff(local(shallow), local(deep))
    check('Depth changes the number of visible reflections', delta > .1, difference=delta)
    no_glow = select(glow=0)
    glow = select(glow=100)
    delta = diff(local(no_glow), local(glow))
    check('Glow adjusts the light around the sharp outlines', delta > .1, difference=delta)
    extreme_glow = select(glow=1000)
    delta = diff(local(glow), local(extreme_glow))
    check('The new maximum glow is visibly stronger than the old maximum', delta > 2, difference=delta)
    extreme_glow.save(ARTIFACTS / 'void-max-glow.png')
    close = select(spacing=25)
    wide = select(spacing=200)
    delta = diff(local(close), local(wide))
    check('Line spacing changes the reflected frame separation', delta > .5, difference=delta)
    close.save(ARTIFACTS / 'void-close-lines.png')
    clear = select(blur=0)
    blurred = select(blur=100)
    delta = diff(local(clear), local(blurred))
    check('Blur adjusts the background independently', delta > .1, difference=delta)
    field = SOURCE.replace('vec3 material = mix(glass, theme_accent, illumination);',
                           'vec3 material = vec3(illumination);')
    assert field != SOURCE
    untinted = select(source=field, color=0)
    tinted = select(source=field, color=100)
    check('Theme color preserves line geometry and intensity', diff(local(untinted), local(tinted)) < .05)
    clear = select(blur=0, source=field)
    blurred = select(blur=100, source=field)
    delta = diff(local(clear), local(blurred))
    check('Blur softens the procedural light outlines as well', delta > .2, difference=delta)
    clear.save(ARTIFACTS / 'void-lines-crisp.png')
    blurred.save(ARTIFACTS / 'void-lines-blurred.png')
    before = select(source=field)
    start = origin(before)
    drag(145, 65)
    after = grab('void-motion-mask')
    end = origin(after)
    check('The native window really moved', end[0] - start[0] > 100 and end[1] - start[1] > 30,
          start=start, end=end)
    delta = diff(local(before), local(after))
    check('Moving the window changes the actual tunnel perspective', delta > .5, difference=delta)
    before = select(motion=0, source=field)
    drag(-145, -65)
    after = grab()
    delta = diff(local(before), local(after))
    check('Motion zero anchors the tunnel to the window', delta < .1, difference=delta)
    x, y = origin(after)
    # The first opaque header pixel is one pixel inside the surface geometry.
    drag(231 - x, 181 - y)
    centered = select(source=field)
    straight = select(motion=0, source=field)
    delta = diff(local(centered), local(straight))
    check('A centered window looks straight down the tunnel', delta < .2, difference=delta)
    spaced = select(blur=0, glow=0, motion=0, depth=12, spacing=100, source=field)
    x, y = origin(spaced)
    hits = [column for column in range(400) if spaced.getpixel((x + column, y + 269))[0] > 18]
    runs = []
    for column in hits:
        if not runs or column > runs[-1][-1] + 1:
            runs.append([])
        runs[-1].append(column)
    centers = [sum(run) / len(run) for run in runs]
    gaps = [b - a for a, b in zip(centers, centers[1:])]
    check('Visible line gaps increase only slightly toward the far end of the tunnel',
          len(gaps) >= 10 and all(b >= a - 1.5 for a, b in zip(gaps, gaps[1:])) and gaps[0] * 1.05 < gaps[-1] < gaps[0] * 1.4,
          gaps=gaps)
    spaced.save(ARTIFACTS / 'void-progressive-spacing.png')
    select(source=field)
    grab('void-centered-mask')
    drag(-100, 0)
    left = grab()
    drag(200, 0)
    right = grab()
    delta = diff(ImageOps.mirror(local(left, (169, 220, 649, 420))), local(right, (169, 220, 649, 420)))
    check('Equal left and right offsets produce mirrored perspectives', delta < .2, difference=delta)
    drag(-100, 0)
    for dark in [False, True]:
        write(MODE, str(dark).lower())
        time.sleep(.8)
        select().save(ARTIFACTS / ('void-' + ('dark' if dark else 'light') + '.png'))
    check('The compositor accepts the final shader',
          'Forge shader rejected' not in (RUN / 'compositor.log').read_text())
finally:
    xtest.fake_input(pointer, X.ButtonRelease, 1)
    xtest.fake_input(pointer, X.KeyRelease, move_key)
    pointer.sync()
    pointer.close()
    for path, content in SAVED.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)
