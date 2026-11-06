import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path.cwd()
lab = root / '.dispatch-version-lab'
evidence = Path(__file__).parent
for name in ['home/config', 'home/data', 'home/state', 'home/projects', 'tmp', 'bin']:
    (lab / name).mkdir(parents=True, exist_ok=True)
(lab / 'bin/node').symlink_to(shutil.which('node'))
records = []
try:
    for label, version in [('old', '0.1.53'), ('min', '0.1.54')]:
        env = {
            'PATH': f'{lab / label / "node_modules/.bin"}:{lab / "bin"}:/opt/homebrew/bin:/usr/bin:/bin',
            'HOME': str(lab / 'home'), 'FM_HOME': str(lab / 'home'),
            'TMPDIR': str(lab / 'tmp'), 'LC_ALL': 'C', 'LANG': 'C',
            'FM_BOOTSTRAP_DETECT_ONLY': '1', 'FM_BOOTSTRAP_NETWORK': 'skip',
            'XDG_CONFIG_HOME': str(lab / 'home/config'),
            'XDG_CACHE_HOME': str(lab / 'home/cache'),
        }
        actual = subprocess.check_output(['quota-axi', '--version'], env=env, text=True).strip()
        assert actual == version, actual
        command = ['bash', 'bin/fm-bootstrap.sh']
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=45)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        quota_lines = [line for line in output.splitlines() if 'quota-axi' in line]
        if label == 'old':
            assert quota_lines == ['OUTDATED: quota-axi (installed: 0.1.53; requires 0.1.54; upgrade: quota-axi update)'], quota_lines
        else:
            assert not quota_lines, quota_lines
        records.append({'command': command, 'environment': env, 'quota_version': actual,
                        'exit_code': result.returncode, 'quota_diagnostics': quota_lines,
                        'output': output, 'passed': True})
        print(json.dumps({'quota_version': actual, 'exit_code': result.returncode, 'quota_diagnostics': quota_lines}), flush=True)
finally:
    shutil.rmtree(lab)
    (evidence / 'live-version-floor.json').write_text(json.dumps(records, indent=2) + '\n')
assert len(records) == 2
