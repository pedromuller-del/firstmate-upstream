import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M34TK4VA89AXEHF5K3G9JPEV')
EVIDENCE = Path(__file__).parent

def row(account, percent, priority=0.8):
    availability = [] if percent is None else [{
        'scope': 'all_models', 'status': 'known',
        'effectivePercentRemaining': percent,
        'runway': {'status': 'exhausted_now' if percent == 0 else 'through_reset'},
        'selection': {'spendPriority': priority}}]
    return {'provider': 'codex', 'accountKey': account,
            'quotaSemantics': {'status': 'unknown' if percent is None else 'known',
                               'effectiveAvailability': availability}}

home = 'pi:openai-codex/gpt-5.6-sol'
sibling = 'pi:openai-codex-muller-labs/gpt-5.6-luna'
home_profile = "profile: --harness 'pi' --model 'openai-codex/gpt-5.6-sol'"
sibling_profile = "profile: --harness 'pi' --model 'openai-codex-muller-labs/gpt-5.6-luna'"
unranked = home + '  provider=codex  -> eligible, unranked:'
blocked = home + '  provider=codex  scope=all_models  remaining=0%  spendPriority=-  runway=exhausted_now  -> not eligible:'
healthy = row('codex-home', 97)
empty_sibling = row('openai-codex-muller-labs', 0)
cases = [
    ('home fallback', 6, [healthy, empty_sibling], [home_profile, 'remaining=97%']),
    ('exact exhausted row overrides healthy home', 6, [healthy, row('openai-codex', 0), row('openai-codex-muller-labs', 42)], [blocked, sibling_profile]),
    ('exact unknown row does not borrow healthy home', 6, [healthy, row('openai-codex', None), empty_sibling], [unranked, 'status: escalate', 'provider codex unmeasured (unknown)']),
    ('no named home row stays unranked', 6, [row('openai-codex-muller-labs', 42)], [unranked, 'has no quota row for account openai-codex:', sibling_profile]),
    ('exhausted home cannot borrow sibling quota', 6, [row('codex-home', 0), row('openai-codex-muller-labs', 72)], [blocked, sibling_profile]),
    ('row order does not change home fallback', 6, [empty_sibling, healthy], [home_profile, 'remaining=97%']),
    ('schema 5 binds every Codex lane to its single row', 5, [row('unused', 23)], ['status: escalate', 'genuine spendPriority tie', home + '  provider=codex  scope=all_models  remaining=23%', sibling + '  provider=codex  scope=all_models  remaining=23%'])]

logs = ['Controlled dependency fixtures: these checks are not live.']
with tempfile.TemporaryDirectory(prefix='.quota-lane-adversarial-', dir=ROOT) as temp:
    lab = Path(temp)
    (lab / 'config').mkdir()
    (lab / 'fakebin').mkdir()
    (lab / 'brief.md').write_text('Fix an off-by-one shell-script bug.\n')
    profiles = [{'harness': 'pi', 'model': candidate.split(':', 1)[1], 'provider': 'codex'} for candidate in (home, sibling)]
    (lab / 'config/crew-dispatch.json').write_text(json.dumps({'rules': [{'when': 'Bug fixes.', 'use': profiles}]}))
    (lab / 'response.json').write_text(json.dumps({'model': 'fixture', 'answers': {'rule': {'choice': 'rule_1', 'confidence': 0.99, 'probabilities': {'rule_1': 1, 'default': 0}}}}))
    (lab / 'fakebin/curl').write_text('#!/usr/bin/env bash\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then out=$2; shift 2; else shift; fi; done\ncat >/dev/null\ncp "$CHECK_RESPONSE" "$out"\nprintf 200\n')
    (lab / 'fakebin/quota-axi').write_text('#!/usr/bin/env bash\ncat "$CHECK_QUOTA"\n')
    for tool in (lab / 'fakebin').iterdir():
        tool.chmod(0o755)
    env = os.environ | {'LC_ALL': 'C', 'PATH': str(lab / 'fakebin') + ':' + os.environ['PATH'], 'FM_HOME': str(lab), 'FM_CONFIG_OVERRIDE': str(lab / 'config'), 'TYPESAFE_API_KEY': 'nonsecret-test-key', 'CHECK_RESPONSE': str(lab / 'response.json'), 'CHECK_QUOTA': str(lab / 'quota.json'), 'TMPDIR': str(lab)}
    for label, schema, rows, expectations in cases:
        if schema == 5:
            rows = [{k: v for k, v in item.items() if k != 'accountKey'} for item in rows]
        (lab / 'quota.json').write_text(json.dumps({'schemaVersion': schema, 'providers': rows}))
        result = subprocess.run([str(ROOT / 'bin/fm-dispatch-resolve.sh'), str(lab / 'brief.md')], env=env, text=True, capture_output=True)
        logs += ['\nCASE: ' + label, 'input: ' + (lab / 'quota.json').read_text(), result.stdout, 'exit_code=' + str(result.returncode)]
        assert result.returncode == 0, result.stderr
        for expected in expectations:
            assert expected in result.stdout, (label, expected, result.stdout)
        if 'status: escalate' in expectations:
            assert '  profile:' not in result.stdout, (label, result.stdout)
        logs.append('ASSERTIONS: PASS')
        print('ok - ' + label)
(EVIDENCE / 'adversarial-dispatch.txt').write_text('\n'.join(logs) + '\n')
print('7 cases passed; exit_code=0')
