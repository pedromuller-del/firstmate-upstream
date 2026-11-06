import json
from pathlib import Path
import shutil
import subprocess

root = Path.cwd()
evidence = Path(__file__).parent
first = json.loads((evidence / 'targeted-tests-results.json').read_text())
rerun = json.loads((evidence / 'targeted-tests-rerun-results.json').read_text())
final = {item['command']: item for item in first}
final.update({item['command']: item for item in rerun})
refreshed = json.loads((evidence / 'round2/targeted-tests-rerun-results.json').read_text())
final.update({item['command']: item for item in refreshed})
assert len(final) == 10
assert all(item['exit_code'] == 0 and item['failed'] == 0 for item in final.values())
result = {
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'final_suites': list(final.values()),
    'passed_groups': sum(item['passed'] for item in final.values()),
    'failed_groups': sum(item['failed'] for item in final.values()),
    'initial_setup_failures': [
        'The initial dispatch run inherited TYPESAFE_API_KEY: 21 groups passed, 1 failed, exit 1. Cleared inherited keys before the successful rerun.',
        'The initial quota run inherited unsupported LC_ALL=C.UTF-8: 7 groups passed, 1 failed, exit 1. Bootstrap also reported a locale-caused failure; the baseline runner was interrupted before its exit could be collected. Successful reruns used LC_ALL=C.',
        'Three clean-environment suites initially placed secondmate fixtures inside this repository, violating their home-isolation guard. Harness: 9 passed, 1 failed; liveness: 4 passed, 1 failed; spawn profile: 9 passed, 1 failed. All exited 1. The reruns used /tmp for incidental disposable test-toolchain files.',
    ],
    'optional_skip': 'The spawn-profile suite skipped the native fish-pane launch because fish is not on PATH; this unchanged shell variant is outside the dispatch-routing change.',
    'source_changes': [],
    'refreshed_suites': refreshed,
    'live_evidence': 'round2/live-cli-transcript.md',
    'live_version_floor': 'Real quota-axi 0.1.53 rejected and 0.1.54 accepted by detect-only bootstrap; both commands exited 0. Disposable packages were removed.',
    'live_limits': 'Exact probability ties, invalid raw choices, raw/effective choice disagreement, successful expired-token renewal, healthy quota reuse, Pi-signed-only refresh, alternate provider credentials, and autonomous profile forwarding remain unproved live. The recorded live-validation exception remains unchanged.',
}
for name in ['.dispatch-live-lab', '.dispatch-primary-lab', '.dispatch-test-lab']:
    path = root / name
    if path.exists():
        shutil.rmtree(path)
status = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, check=True)
result['working_tree_status_after_cleanup'] = status.stdout
assert not status.stdout, status.stdout
(evidence / 'final-test-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
