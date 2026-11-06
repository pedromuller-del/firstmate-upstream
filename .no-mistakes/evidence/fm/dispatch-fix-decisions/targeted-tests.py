import json
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
evidence = Path(__file__).parent / 'round2'
evidence.mkdir(exist_ok=True)
scratch = root / '.dispatch-test-lab'
scratch.mkdir(exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
env = os.environ.copy()
env['TMPDIR'] = '/tmp'
env['LC_ALL'] = 'C'
env['LANG'] = 'C'
for key in list(env):
    if key.endswith('_API_KEY') or key.startswith('FM_DISPATCH_') or key.startswith('QUOTA_AXI_'):
        env.pop(key)
names = sys.argv[1:] or [
    'fm-dispatch-resolve', 'fm-quota-choose', 'fm-bootstrap',
    'fm-procevent-quota', 'fm-startup-memory-budget',
    'fm-secondmate-sync', 'fm-secondmate-harness',
    'fm-secondmate-liveness', 'fm-shared-captain-inheritance',
    'fm-spawn-dispatch-profile',
]
results = []
for name in names:
    command = ['bash', f'tests/{name}.test.sh']
    with (evidence / f'{name}-isolated.log').open('w') as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    output = (evidence / f'{name}-isolated.log').read_text()
    lines = output.splitlines()
    record = {'command': ' '.join(command), 'exit_code': result.returncode,
              'passed': sum(line.startswith('ok -') for line in lines),
              'failed': sum(line.startswith('not ok') for line in lines)}
    results.append(record)
    print(json.dumps(record), flush=True)
(evidence / 'targeted-tests-rerun-results.json').write_text(json.dumps(results, indent=2) + '\n')
