import json
import os
from pathlib import Path

evidence = Path(__file__).parent / 'round2'
names = [
    'clear-profile', 'low-confidence', 'captain-approval', 'low-confidence-approval',
    'declared-floor', 'expired-rule', 'future-leap-day', 'all-expired',
    *[f'invalid-until-{i}' for i in range(7)], 'private-filter',
    'tie-attempt', 'unoffered-choice-attempt', 'effective-rule-attempt', 'openrouter-availability', 'openai-availability',
]
lines = [
    '# Live dispatch CLI evidence', '',
    'All resolver calls use the target worktree and disposable configuration. Successful model calls use the real TypeSafe endpoint. No provider responses were mocked.', '',
    'Routing cases declare shared_quota=true to isolate the decision policy from private subscription accounts.', '',
    'The exact-tie and unoffered-choice attempts did not produce those response shapes. Their outputs are attempts, not passed boundary checks.', '',
    'The effective-rule attempt also returned the highest-probability rule as its raw choice, so it did not exercise substitution evidence.', '',
    'OpenRouter and OpenAI could not run because their API credentials were absent. No operator credential store was copied or changed.', '',
]
for name in names:
    record = json.loads((evidence / f'live-{name}.json').read_text())
    lines.extend([f'## {name}', '', f"Exit code: {record['exit_code']}", '',
                  f"Input: {record['brief']}", '', '```text', record['output'].rstrip(), '```', ''])
observations = [json.loads(line) for line in (evidence / 'live-private-filter.jsonl').read_text().splitlines()]
assert observations and all(row['mode'] == '0o600' for row in observations)
lines += ['## Temporary rule file permissions', '',
          'The observer delegated to real jq and checked stdout before the filter wrote rule data. Every recorded observation was mode 0600.', '',
          '```json', (evidence / 'live-private-filter.jsonl').read_text().rstrip(), '```', '',
          'After each observed exit, the temporary directory contained only the Node compile-cache directory; no rule snapshot remained.', '']
for name in ['pi', 'pi-timeout']:
    record = json.loads((evidence / f'live-{name}.json').read_text())
    lines += [f'## {name}', '', record['isolation'], '',
              f"Exit code: {record['exit_code']}; elapsed seconds: {record['elapsed_seconds']}", '',
              '```text', record['output'].rstrip(), '```', '',
              '```json', json.dumps(record['trace'], indent=2), '```', '',
              'The quota read reports missing credentials. This proves the invocation and continuation, not healthy token renewal, ranking, or cache reuse.', '']
lines += ['## Real quota-axi version boundary', '',
          'Both npm releases ran locally in disposable directories. Bootstrap used detect-only mode with network checks disabled.', '']
for record in json.loads((evidence / 'live-version-floor.json').read_text()):
    lines += [f"### quota-axi {record['quota_version']}", '',
              f"Command: bash bin/fm-bootstrap.sh; exit code: {record['exit_code']}", '',
              '```text', '\n'.join(record['quota_diagnostics']) or '(no quota-axi warning)', '```', '']
(evidence / 'live-cli-transcript.md').write_text('\n'.join(lines))
secrets = [v for k,v in os.environ.items() if k.endswith('_API_KEY') and v]
leaks = []
for path in evidence.iterdir():
    if path.is_file():
        text = path.read_text(errors='replace')
        if any(secret in text for secret in secrets):
            leaks.append(path.name)
print(json.dumps({'api_key_leak_files': leaks, 'cli_evidence': 'live-cli-transcript.md'}))
