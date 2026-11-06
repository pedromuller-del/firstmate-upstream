import json
import os
from pathlib import Path
import subprocess
import time

root = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH')
evidence = Path(__file__).parent
env = os.environ.copy()
env['LC_ALL'] = 'C'
for key in ['TYPESAFE_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'FM_DISPATCH_API_KEY']:
    env.pop(key, None)
selections = [
    ('fm-secondmate-harness', 'test_harness_resolution', [
        'test_config_reread_cleanup_runs_after_mixed_delivery_failure',
        'test_config_reread_stops_after_failed_generation',
        'test_config_reread_skips_when_unchanged_and_reads_after_push',
        'test_config_reread_bootstrap_path_and_spawn_flexibility',
        'test_bootstrap_respawns_before_config_reread',
        'test_spawn_quarantines_pending_rereads_on_cleanup_failure',
        'test_bootstrap_detect_only_does_not_create_state',
    ]),
    ('fm-bootstrap', 'test_bootstrap_reporting', ['test_crew_dispatch_validation']),
]
results = []
for name, first_call, selected in selections:
    source = (root / 'tests' / (name + '.test.sh')).read_text()
    definitions, calls = source.rsplit('\n' + first_call + '\n', 1)
    definitions = definitions.replace('$(dirname "${BASH_SOURCE[0]}")/lib.sh', str(root / 'tests/lib.sh'))
    program = definitions + '\n' + '\n'.join(selected) + '\n'
    started = time.monotonic()
    with (evidence / (name + '-remaining.log')).open('w') as log:
        run = subprocess.run(['bash'], cwd=root, env=env, input=program, text=True, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    text = (evidence / (name + '-remaining.log')).read_text()
    row = {'suite': 'tests/' + name + '.test.sh', 'selected_existing_cases': selected, 'exit_code': run.returncode, 'passed': sum(s.startswith('ok -') for s in text.splitlines()), 'failed': sum(s.startswith('not ok') for s in text.splitlines()), 'seconds': round(time.monotonic()-started, 2)}
    results.append(row)
    (evidence / 'remaining-tests.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(row), flush=True)
