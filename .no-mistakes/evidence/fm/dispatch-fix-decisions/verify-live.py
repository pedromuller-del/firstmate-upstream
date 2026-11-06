import json
from pathlib import Path

evidence = Path(__file__).parent
results = []

def load(name):
    return json.loads((evidence / (name + '.json')).read_text())

def check(name, files, assertion):
    records = [load(f) for f in files]
    assertion(records)
    results.append({'name': name, 'result': 'pass', 'live': True, 'files': [f + '.json' for f in files]})

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def clear(records):
    r = records[0]
    require(r['exit_code'] == 0 and 'status: clear' in r['stdout'], 'clear result missing')
    require("profile: --harness 'codex' --model 'gpt-6.1-sol' --effort 'medium'" in r['stdout'], 'profile changed')
    require([e['tool'] for e in r['events']] == ['curl'], 'shared quota read a provider')

def low(records):
    r = records[0]
    answer = next(e['response']['answers']['rule'] for e in r['events'] if e['tool'] == 'curl')
    require(answer['confidence'] < .6, 'not a low-confidence response')
    require(answer['choice'] == max(answer['probabilities'], key=answer['probabilities'].get), 'choice is not the probability leader')
    require('status: clear' in r['stdout'] and 'low confidence:' in r['stdout'], 'low-confidence output missing')

def guard(records, status):
    for r in records:
        require(r['exit_code'] == 0 and 'status: ' + status in r['stdout'], 'guard status missing')
        require('  profile:' not in r['stdout'], 'guard yielded a profile')
    answer = next(e['response']['answers']['rule'] for e in records[-1]['events'] if e['tool'] == 'curl')
    require(answer['confidence'] < .6, 'guard was not exercised below the global floor')

def expiry(records):
    active, expired = records
    request = next(e['request'] for e in active['events'] if e['tool'] == 'curl')
    require(set(request['questions']['rule']['criteria']) == {'rule_1', 'default'}, 'expired rule sent to model')
    require("profile: --harness 'codex'" in active['stdout'], 'future leap-day rule not selected')
    require('status: escalate' in expired['stdout'] and 'no rules to match' in expired['stdout'], 'all-expired not escalated')
    require(not any(e['tool'] in ['curl', 'pi', 'quota-axi'] for e in expired['events']), 'all-expired called a service')

def invalid(records):
    for r in records:
        require(r['exit_code'] == 2 and 'until must be' in r['stderr'], 'invalid timestamp accepted')
        require(not any(e['tool'] in ['curl', 'pi', 'quota-axi'] for e in r['events']), 'invalid timestamp called a service')

def private(records):
    r = records[0]
    created = [e for e in r['events'] if e['tool'] == 'mktemp']
    require(len(created) >= 2 and all(e['mode'] == '0o600' for e in created), 'temporary file created with unsafe mode')
    during = next(e['temp_permissions'] for e in r['events'] if e['tool'] == 'curl')
    require(any(e['mode'] == '0o400' for e in during), 'rules not read-only in flight')
    require(all(int(e['mode'], 8) & 0o077 == 0 for e in during), 'private data exposed in flight')
    require(r['remaining_recorded_temps'] == [], 'temporary files remain')

def refresh(records):
    r = records[0]
    events = [e for e in r['events'] if e['tool'] != 'mktemp']
    require([e['tool'] for e in events] == ['curl', 'pi', 'pi', 'quota-axi'], 'wrong refresh order or multiplicity')
    require([e['args'][-1] for e in events[1:3]] == ['anthropic', 'openai-codex'], 'default missing or expired provider refreshed')
    require(all(e['root'].endswith('/pi') and e['exit_code'] == 1 and 'not_ready' in e['stdout'] for e in events[1:3]), 'wrong pinned root or not a real failed auth check')
    require(events[-1]['args'] == ['--json', '--max-age', '2m'], 'bounded reuse request missing')
    require(r['exit_code'] == 0 and 'quota-axi --json failed' in r['stdout'], 'failed refresh did not continue to quota')

def pin(records):
    r = records[0]
    require(not any(e['tool'] == 'pi' for e in r['events']), 'invalid pin fell back to ambient Pi')
    require(any(e['tool'] == 'quota-axi' for e in r['events']) and r['exit_code'] == 0, 'invalid refresh pin blocked quota')

check('Resolve a known bug to its exact profile without quota calls under shared quota', ['live-clear'], clear)
check('Resolve a below-global-floor answer to its probability leader with a low-confidence note', ['live-borderline-4'], low)
check('Require captain approval even when the selected answer has low confidence', ['live-captain-approval', 'live-low-captain-approval'], lambda r: guard(r, 'escalate'))
check('Withhold a profile when its declared confidence floor has no qualifying alternative', ['live-declared-floor', 'live-low-declared-floor'], lambda r: guard(r, 'ambiguous'))
check('Remove expired rules, retain a future leap-day rule, and stop when all rules expire', ['live-expired-rule', 'live-all-expired'], expiry)
check('Reject malformed and calendar-invalid expiry values before calling any service', ['live-invalid-until-' + str(i) for i in range(1, 6)], invalid)
check('Create private rule snapshots and remove them after resolution', ['live-private-snapshots'], private)
check('Check each live Pi provider and the root default through the pinned account, then read quota despite auth failure', ['live-pi-refresh-failure'], refresh)
check('Avoid ambient-account refresh when the configured Pi account root is invalid', ['live-invalid-account-pin'], pin)

(evidence / 'live-verified.json').write_text(json.dumps(results, indent=2))
lines = ['# Dispatch live validation', '', 'Target: `88404c222c9cf4a2e8f49efa3b3b20b182296359`.', '', 'The real resolver called TypeSafe and the installed Pi and quota-axi CLIs. All inputs were synthetic. Forwarding observers recorded requests, responses, process exits, and file modes without replacing product behavior.', '', 'Quota was restricted to an empty Codex profile with `--profile-only --no-credential-refresh`. It returned missing-credentials exit 1. This proves that failed Pi checks reach the quota read; it does not prove a healthy reading, OAuth renewal, or cache reuse.', '']
for result in results:
    lines.extend(['## ' + result['name'], '', 'Result: pass, live.', ''])
    for filename in result['files']:
        r = json.loads((evidence / filename).read_text())
        lines.extend(['Evidence: `' + filename + '`.', '', '```text', 'exit=' + str(r['exit_code']), r['stdout'].rstrip(), r['stderr'].rstrip(), '```', ''])
lines.extend(['## Live limitations', '', 'The previously accepted six-scenario exception remains. A real provider did not emit an exact probability tie, an unoffered choice, or a non-leading raw choice. Those branches passed the offline resolver suite. Empty isolated Pi roots have no renewable OAuth identity. The installed quota-axi supports the reuse flag, but healthy reuse requires authorized credentials. Pi-signed is absent from PATH and the repository supplies no build or installer for that signed wrapper. OpenRouter and OpenAI keys are absent. The real Claude primary reached its workspace-trust dialog on a 120-column by 40-row terminal; approving it would modify the operator trust store outside the allowed boundary. The private tmux server was stopped and the lab removed.', '', 'No product GUI or layout changed. Evidence is the CLI output, captured API protocol, file permissions, and primary terminal transcript.'])
(evidence / 'live-report.md').write_text('\n'.join(lines) + '\n')
print('9 live scenarios passed; 0 failed. Exact assertions and product outputs are in live-verified.json and live-report.md.')
