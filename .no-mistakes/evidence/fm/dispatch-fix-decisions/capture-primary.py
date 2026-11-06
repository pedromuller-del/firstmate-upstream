import json
import os
from pathlib import Path
import subprocess

root = Path.cwd()
evidence = Path(__file__).parent
lab = root / '.dispatch-primary-lab'
socket_dir = (lab / 'state/.fm-lab-tmux-dir').read_text().strip()
env = os.environ | {'TMUX_TMPDIR': socket_dir, 'LC_ALL': 'C'}
capture = subprocess.run(['tmux', '-L', 'fm-lab', 'capture-pane', '-p', '-S', '-', '-t', 'primary'],
                         env=env, capture_output=True, text=True, check=True)
(evidence / 'primary-transcript.txt').write_text(capture.stdout)
for name in ['dispatch-resolver-repeat.stdout', 'dispatch-resolver-repeat.stderr']:
    (evidence / f'primary-{name}').write_text((lab / name).read_text())
stop = subprocess.run(['tmux', '-L', 'fm-lab', 'kill-server'], env=env, capture_output=True, text=True)
cleanup = subprocess.run(['bin/fm-lab-home.sh', 'teardown', str(lab)], env=env, capture_output=True, text=True)
(evidence / 'primary-lab-result.json').write_text(json.dumps({
    'grid': {'columns': 120, 'rows': 40},
    'cli': 'codex 0.166.0, normal existing login, no credential edits',
    'result': 'untested',
    'reason': 'The live primary could not create resolver temporary files. Its command sandbox returned Operation not permitted at the default macOS temporary directory, even after an explicit TMPDIR=$FM_HOME prefix. No clear profile was produced; its initial config-based spawn attempt is not evidence for forwarding a clear profile.',
    'stop_exit_code': stop.returncode, 'teardown_exit_code': cleanup.returncode,
    'teardown_output': cleanup.stdout + cleanup.stderr,
}, indent=2) + '\n')
print(f'Captured primary transcript; stop={stop.returncode}, teardown={cleanup.returncode}')
