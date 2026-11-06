import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

root = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH')
evidence = Path(__file__).parent
lab = Path(tempfile.mkdtemp(prefix='p', dir=evidence))
env = os.environ.copy()
for key in ['NO_MISTAKES_GATE', 'FM_GATE_REFUSE_BYPASS', 'FM_ROOT_OVERRIDE', 'FM_STATE_OVERRIDE', 'FM_DATA_OVERRIDE', 'FM_CONFIG_OVERRIDE', 'FM_PROJECTS_OVERRIDE']:
    env.pop(key, None)
env.update(TMUX_TMPDIR=str(lab / 'tmux'), FM_HOME=str(lab), LC_ALL='C')
command = ['tmux', '-L', 'fm-lab']
record = {'lab': str(lab), 'command': command + ['new-session', '-d', '-x', '120', '-y', '40', '-s', 'primary', '-c', str(root), '-e', 'FM_HOME=' + str(lab), 'claude']}
started = False
try:
    create = subprocess.run(['bash', 'bin/fm-lab-home.sh', 'create', str(lab)], cwd=root, env=env, capture_output=True, text=True)
    record['create'] = {'exit_code': create.returncode, 'stdout': create.stdout, 'stderr': create.stderr}
    if create.returncode:
        raise RuntimeError('Lab creation refused')
    (lab / 'tmux').mkdir()
    (lab / 'config/supervision-host').touch()
    launch = subprocess.run(record['command'], cwd=root, env=env, text=True, capture_output=True)
    record['launch'] = {'exit_code': launch.returncode, 'stdout': launch.stdout, 'stderr': launch.stderr}
    if launch.returncode:
        raise RuntimeError('Primary launch refused')
    started = True
    time.sleep(12)
    capture = subprocess.run(command + ['capture-pane', '-p', '-t', 'primary', '-S', '-100'], cwd=root, env=env, capture_output=True, text=True)
    record['capture'] = {'exit_code': capture.returncode, 'stdout': capture.stdout, 'stderr': capture.stderr}
    (evidence / 'primary-pane.txt').write_text(capture.stdout + capture.stderr)
    print(capture.stdout + capture.stderr, flush=True)
finally:
    if started:
        stop = subprocess.run(command + ['kill-server'], cwd=root, env=env, capture_output=True, text=True)
        record['stop'] = {'exit_code': stop.returncode, 'stdout': stop.stdout, 'stderr': stop.stderr}
    shutil.rmtree(lab)
    record['lab_removed'] = not lab.exists()
    (evidence / 'primary-probe.json').write_text(json.dumps(record, indent=2))
