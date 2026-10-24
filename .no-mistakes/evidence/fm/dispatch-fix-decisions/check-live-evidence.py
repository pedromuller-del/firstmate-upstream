import json
from pathlib import Path

evidence = Path(__file__).parent

def result(name):
    return json.loads((evidence / f'{name}.json').read_text())

def stdout(name):
    return result(name)['stdout']

profiles = []
for repeat in range(1, 6):
    name = f'live-repeat-{repeat}'
    record = result(name)
    assert record['exit_code'] == 0
    assert '  status: clear\n' in record['stdout']
    profiles.append(next(line for line in record['stdout'].splitlines() if line.startswith('  profile:')))
assert len(set(profiles)) == 1
print('PASS: five live Typesafe requests returned the identical profile line')

response = json.loads((evidence / 'live-top-tie.response.json').read_text())
answer = response['answers']['rule']
assert answer['confidence'] < 0.6
assert answer['probabilities']['rule_1'] > answer['probabilities']['rule_2']
assert '  status: clear\n' in stdout('live-top-tie')
assert 'low confidence:' in stdout('live-top-tie')
assert profiles[0] in stdout('live-top-tie')
print('PASS: a live low-confidence answer selected the highest-probability rule and disclosed low confidence')

assert '  status: escalate\n' in stdout('live-approval-low-confidence')
assert "captain's explicit approval" in stdout('live-approval-low-confidence')
assert '  profile:' not in stdout('live-approval-low-confidence')
assert '  status: ambiguous\n' in stdout('live-declared-floor-miss')
assert 'no other option clears its own floor' in stdout('live-declared-floor-miss')
assert '  profile:' not in stdout('live-declared-floor-miss')
print('PASS: live approval and declared-confidence floors withheld a profile')

request = json.loads((evidence / 'live-repeat-1.request.json').read_text())
criteria = request['questions']['rule']['criteria']
assert set(criteria) == {'rule_1', 'rule_2', 'default'}
assert all('Expired' not in value and 'New feature' not in value for value in criteria.values())
assert 'no rules to match' in stdout('live-all-expired')
for name in ('live-all-expired', 'live-invalid-calendar', 'live-invalid-past'):
    assert not (evidence / f'{name}.request.json').exists()
    assert not (evidence / f'{name}.calls').exists()
for name in ('live-invalid-calendar', 'live-invalid-past'):
    assert result(name)['exit_code'] == 2
    assert result(name)['stdout'] == ''
    assert 'malformed rules file' in result(name)['stderr']
assert '  status: clear\n' in stdout('live-valid-leap-day')
print('PASS: expiry removed rules before transport, invalid calendars exited 2, and a valid leap day resolved')

calls = (evidence / 'live-repeat-1.calls').read_text().splitlines()
assert len(calls) == 5
assert calls[0].endswith('argv=auth check --provider anthropic')
assert calls[2].endswith('argv=auth check --provider openai-codex')
assert '/.validation-tmp/pi argv=' in calls[0]
assert '/.validation-tmp/pi argv=' in calls[2]
assert calls[1] == calls[3] == 'pi exit=1'
assert calls[4] == 'quota-axi argv=--json --max-age 2m'
assert (evidence / 'live-pin-refusal.calls').read_text().splitlines() == ['quota-axi argv=--json --max-age 2m']
assert '  status: clear\n' in stdout('live-pin-refusal')
assert '  status: clear\n' in stdout('live-refresh-timeout')
assert 10 <= result('live-refresh-timeout')['seconds'] < 14
assert 'stopped real pi child=' in (evidence / 'live-refresh-timeout.calls').read_text()
print('PASS: real Pi checks covered the default and rule providers, honored the pin, and stayed nonfatal on failure and timeout')

assert (evidence / 'live-refresh-timeout.filter-mode').read_text().strip() == '0o600'
assert result('live-refresh-timeout')['temporary_files_after_exit'] == []
print('PASS: the expiry output was mode 0600 before jq wrote it, and the resolver removed its temporary files')

transcript = [
    'Live dispatch validation',
    '',
    'The real resolver called the live Typesafe API and the installed Pi and quota-axi CLIs.',
    'Quota input was synthetic data supplied through QUOTA_AXI_SNAPSHOT; this is not live vendor quota or normal cache-reuse proof.',
    'Pi used an empty disposable account. Successful OAuth renewal and pi-signed were not exercised.',
    'PATH wrappers forwarded calls unchanged and captured only synthetic requests and non-secret outputs.',
    'The timeout scenario sent SIGSTOP to the real Pi child and observed the resolver continue after its 10-second bound.',
    '',
]
for name in [*(f'live-repeat-{n}' for n in range(1, 6)), 'live-top-tie', 'live-approval-low-confidence',
             'live-declared-floor-miss', 'live-all-expired', 'live-invalid-calendar', 'live-invalid-past',
             'live-valid-leap-day', 'live-pin-refusal', 'live-refresh-timeout']:
    record = result(name)
    transcript += [name, f"exit={record['exit_code']} elapsed={record['seconds']}s", record['stdout'] or record['stderr']]
    calls_file = evidence / f'{name}.calls'
    if calls_file.exists():
        transcript.append(calls_file.read_text())
(evidence / 'live-cli-transcript.txt').write_text('\n'.join(transcript) + '\n')
