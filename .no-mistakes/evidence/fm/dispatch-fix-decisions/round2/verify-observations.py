import json
import os
from pathlib import Path
import subprocess

evidence = Path(__file__).parent
records = json.loads((evidence / 'live-results.json').read_text())
expected = [row for row in records if row['name'] not in {
    'tie-attempt', 'openrouter-availability', 'openai-availability'
}]
assert len(expected) == 14
assert all(row['passed'] for row in expected)
approval = json.loads((evidence / 'live-low-confidence-approval.json').read_text())
assert approval['exit_code'] == 0
assert 'status: escalate' in approval['output']
assert 'explicit approval' in approval['output']
assert 'profile:' not in approval['output']
privacy = [json.loads(line) for line in (evidence / 'live-private-filter.jsonl').read_text().splitlines()]
assert privacy and all(row['mode'] == '0o600' for row in privacy)
assert all(set(row['remaining_temporary_files']) <= {'node-compile-cache'} for row in records)
for name in ['pi', 'pi-timeout']:
    record = json.loads((evidence / f'live-{name}.json').read_text())
    tools = [row for row in record['trace'] if row['tool'] != 'fault-injection']
    assert [row['tool'] for row in tools] == ['pi', 'pi', 'quota-axi']
    assert [row['argv'][-1] for row in tools[:2]] == ['anthropic', 'openai-codex']
    assert all(row['root'].endswith('/.dispatch-live-lab/pi-pinned') for row in tools[:2])
    assert tools[2]['argv'] == ['--json', '--max-age', '2m']
    assert record['exit_code'] == 0
    assert record['probe_exit_code'] == 1
    assert 'credentials_not_configured' in record['probe_output']
    if name == 'pi-timeout':
        assert 10 <= record['elapsed_seconds'] < 20
        stopped = [row for row in record['trace'] if row['tool'] == 'fault-injection']
        assert len(stopped) == 1
        assert subprocess.run(['ps', '-p', str(stopped[0]['pid']), '-o', 'pid='],
                              capture_output=True).returncode == 1
secrets = [value for key, value in os.environ.items() if key.endswith('_API_KEY') and value]
paths = subprocess.check_output(['rg', '--files', str(evidence.parent)], text=True).splitlines()
leaks = [path for path in paths if any(secret in Path(path).read_text(errors='replace') for secret in secrets)]
assert not leaks, 'A credential appeared in evidence; do not publish.'
print(json.dumps({
    'live_routing_and_date_observations': len(expected),
    'approval_guard': 'pass',
    'private_filter_mode': '0600',
    'pi_pinned_default_order_and_deduplication': 'pass',
    'pi_timeout_and_child_cleanup': 'pass',
    'quota_invocation': '--json --max-age 2m',
    'credential_leak_files': leaks,
    'limits': 'No healthy quota account, successful token renewal, or cache hit was observed. Exact response-edge attempts did not reach their target conditions.'
}, indent=2))
