#!/usr/bin/env python3
"""Compare real compositor CPU activity with and without forced Void animation."""
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(os.environ['VOID_QA_DIR']).resolve()
STATE = json.loads((RUN / 'state.json').read_text())
assert Path(STATE['env']['XDG_CONFIG_HOME']).resolve() == RUN / 'config'
CONFIG = RUN / 'config/cosmic/com.system76.CosmicComp/v1'
SAVED = {p: p.read_bytes() if p.exists() else None
         for p in [CONFIG / 'forge_runtime', CONFIG / 'glass_effect']}
SOURCE = (ROOT / 'shaders/void.frag').read_text()
EFFECT = json.loads((ROOT / 'effects/void.json').read_text())
defaults = {c['key']: c['default'] for c in EFFECT['controls']}
defaults.update(forge_void_display_width=1280, forge_void_display_height=900)
params = ','.join('(key:' + json.dumps(key) + ',name:' + json.dumps(name)
                  + ',value:' + str(float(defaults[key])) + ')'
                  for name, key in EFFECT['shader']['uniforms'].items())
pid = int((RUN / 'sockets/cosmic-forge-engine-v1').read_text())


def cpu_time():
    fields = Path(f'/proc/{pid}/stat').read_text().split(')', 1)[1].split()
    return (int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK')


def write(path, value):
    pending = path.with_name('.' + path.name + '.idle')
    pending.write_text(value + '\n')
    pending.replace(path)


try:
    measured = {}
    for animated in [True, False]:
        write(CONFIG / 'forge_runtime', '(abi:1,id:"void",base:"glass",animated:'
              + str(animated).lower() + ',source:' + json.dumps(SOURCE) + ',parameters:[' + params + '])')
        write(CONFIG / 'glass_effect', '"void"')
        time.sleep(.8)
        before = cpu_time()
        time.sleep(2)
        measured['animated' if animated else 'on_demand'] = cpu_time() - before
    measured['sample_wall_seconds'] = 2
    (RUN / 'void-idle-results.json').write_text(json.dumps(measured, indent=2) + '\n')
    assert measured['animated'] > .1, measured
    assert measured['on_demand'] < max(.02, measured['animated'] * .1), measured
    print('PASS Void stops forcing compositor work at rest: ' + json.dumps(measured))
finally:
    for path, content in SAVED.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)
