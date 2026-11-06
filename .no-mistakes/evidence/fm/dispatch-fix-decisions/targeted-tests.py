import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH')
evidence = Path(__file__).parent
env = os.environ.copy()
env['LC_ALL'] = 'C'
for key in ['TYPESAFE_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'FM_DISPATCH_API_KEY']:
    env.pop(key, None)
results = []
suffix = '-retry' if len(sys.argv) > 1 else ''
names = sys.argv[1:] or ['fm-procevent-quota', 'fm-startup-memory-budget', 'fm-secondmate-sync', 'fm-secondmate-harness', 'fm-secondmate-liveness', 'fm-shared-captain-inheritance', 'fm-quota-choose', 'fm-bootstrap', 'fm-spawn-dispatch-profile']
for name in names:
    command = ['bash', 'tests/' + name + '.test.sh']
    started = time.monotonic()
    with (evidence / (name + suffix + '.log')).open('w') as log:
        proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            status = proc.wait(timeout=600)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            status = 'timeout'
    text = (evidence / (name + suffix + '.log')).read_text()
    row = {'command': ' '.join(command), 'exit_code': status, 'passed': sum(line.startswith('ok -') or line.startswith('ok ') for line in text.splitlines()), 'failed': sum(line.startswith('not ok') for line in text.splitlines()), 'seconds': round(time.monotonic() - started, 2)}
    results.append(row)
    (evidence / ('targeted-tests' + suffix + '.json')).write_text(json.dumps(results, indent=2))
    print(json.dumps(row), flush=True)
