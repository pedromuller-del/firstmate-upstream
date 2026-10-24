import json
from pathlib import Path
import re
import subprocess

evidence = Path(__file__).parent

def output(case):
    return (evidence / case / 'resolver.txt').read_text()

def trace(case):
    path = evidence / case / 'trace.log'
    return path.read_text() if path.exists() else ''

profiles = []
for index in range(1, 6):
    case = f'live-{index:02d}-normal'
    text = output(case)
    assert 'exit=0;' in text and 'status: clear' in text
    profiles.append(next(line for line in text.splitlines() if line.startswith('  profile:')))
    assert trace(case).count('quota-axi --json --max-age 2m') == 1
assert len(set(profiles)) == 1
print('Five live API resolver calls returned identical profile lines:')
print('\n'.join(f'{i}: {profile}' for i, profile in enumerate(profiles, 1)))

low = output('live-18-tie_attempt')
assert 'status: clear' in low and 'low confidence:' in low
answer = json.loads((evidence / 'live-18-tie_attempt/response.json').read_text())['answers']['rule']
assert answer['confidence'] < 0.6
assert max(answer['probabilities'], key=answer['probabilities'].get) == 'rule_1'
assert profiles[0] in low
print(f'Low-confidence live answer {answer["confidence"]} selected the most probable rule and printed its note.')

for case in ('live-07-approval', 'live-15-approval_low'):
    text = output(case)
    assert 'status: escalate' in text and 'explicit approval' in text and 'profile:' not in text
assert 'confidence: 0.48' in output('live-15-approval_low')
print('Approval-required rules withheld the profile at high and low answer confidence.')

floor = output('live-16-floor_overlap')
assert 'status: ambiguous' in floor and 'no other option clears its own floor' in floor and 'profile:' not in floor
print('A declared-floor miss with no qualifying runner-up withheld the profile.')

request = json.loads((evidence / 'live-09-expired/request.json').read_text())
assert set(request['questions']['rule']['criteria']) == {'rule_1', 'default'}
assert 'rule: rule_1 (Fix a simple off-by-one' in output('live-09-expired')
assert not any(line.startswith('pi ') for line in trace('live-09-expired').splitlines())
assert 'reason: no rules to match' in output('live-10-all_expired')
assert not (evidence / 'live-10-all_expired/request.json').exists()
assert '600' in (evidence / 'live-15-expired/filter-mode.txt').read_text()
assert '[]' in (evidence / 'live-15-expired/cleanup.txt').read_text()
print('Expired rules were absent from the live request; no expired Pi provider was refreshed. Filter output started at mode 600 and was removed.')

for case in ('live-11-invalid_date', 'live-12-invalid_leap', 'live-16-invalid_date'):
    text = output(case)
    assert 'exit=2;' in text and 'malformed rules file:' in text
    assert not (evidence / case / 'request.json').exists()
assert '[]' in (evidence / 'live-16-invalid_date/cleanup.txt').read_text()
print('Invalid dates and a non-leap February 29 exited 2 before the API call; temporary files were removed.')

calls = trace('live-13-pi')
assert calls.count('auth check --provider anthropic') == 1
assert calls.count('auth check --provider openai-codex') == 1
assert calls.count('pi exit=1') == 2
assert calls.index('auth check --provider openai-codex') < calls.index('quota-axi --json')
assert 'status: clear' in output('live-13-pi')
pinned = trace('live-15-pi_override')
assert '/pi-empty auth check --provider anthropic' in pinned
assert '/pi-ambient auth check' not in pinned
assert not any(line.startswith('pi ') for line in trace('live-16-pi_bad_pin').splitlines())
assert 'status: clear' in output('live-16-pi_bad_pin')
print('Live rule/default Pi providers refreshed once before quota; failed auth was nonfatal. The account pin overrode the ambient root and an invalid pin skipped refresh.')

stalled = output('live-15-pi_pin')
seconds = float(re.search(r'seconds=([0-9.]+)', stalled).group(1))
assert 10 <= seconds < 14 and 'status: clear' in stalled
pids = re.findall(r'suspended real Pi pid=(\d+)', trace('live-15-pi_pin'))
for pid in pids:
    assert subprocess.run(['ps', '-p', pid], capture_output=True).returncode != 0
print(f'Suspending the real Pi process did not block dispatch: a clear profile returned after {seconds}s; the suspended processes no longer exist.')
print('Live evidence assertions: 8 behavior groups passed, 0 failed.')
