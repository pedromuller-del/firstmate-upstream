import copy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


ROOT = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M3VSZ7YKHZJ7FVPQ6PW6QDZG')
EVIDENCE = Path(__file__).parent
BASH = shutil.which('bash')
CURL = shutil.which('curl')
MODEL = 'openai-codex/gpt-5.6-sol'
SIBLING = 'openai-codex-work/gpt-5.6-luna'
records = []


def row(provider, account, remaining, priority):
    return {'provider': provider, 'accountKey': account, 'quotaSemantics': {
        'status': 'known', 'effectiveAvailability': [{'scope': 'all_models', 'status': 'known',
        'effectivePercentRemaining': remaining,
        'runway': {'status': 'through_reset' if remaining else 'exhausted_now'},
        'selection': {'spendPriority': priority}}]}}


def drive(case, harness):
    with tempfile.TemporaryDirectory(prefix='.quota-live-', dir=ROOT) as scratch:
        lab = Path(scratch)
        fm = lab / 'fm-home'
        home = lab / 'user-home'
        ordinary = home / '.pi/agent'
        alternate = lab / 'alternate-account'
        fakebin = lab / 'fixture-bin'
        for directory in (fm / 'config', ordinary, alternate, fakebin, lab / 'tmp'):
            directory.mkdir(parents=True)
        (fakebin / 'quota-axi').write_text('#!/usr/bin/env bash\n'
            'printf "%s\\n" "$*" >> "$QUOTA_CALLS"\n'
            '[ "$#" = 1 ] && [ "$1" = --json ] || exit 2\n'
            'cat "$QUOTA_FIXTURE"\n')
        (fakebin / 'quota-axi').chmod(0o755)
        (fakebin / 'curl').write_text('#!/usr/bin/env bash\n'
            'printf "real curl invoked\\n" >> "$HTTP_CALLS"\n'
            f'exec {shlex.quote(CURL)} "$@"\n')
        (fakebin / 'curl').chmod(0o755)
        snapshot = {'generatedAt': '2026-10-04T00:00:00Z', 'schemaVersion': 6, 'providers': [
            row('codex', 'codex-home', 97, 0.8),
            row('codex', 'openai-codex-work', 0, -1.4),
            row('codex', 'default', 0, -1.4), row('cursor', 'default', 24, 0.3)]}
        primary = {'harness': harness, 'model': MODEL, 'provider': 'codex'}
        sibling = {'harness': harness, 'model': SIBLING, 'provider': 'codex'}
        cursor = {'harness': 'cursor', 'model': 'default'}
        profiles = [primary, sibling, cursor]
        pin = 'ordinary\nopenai-codex openai-codex-work codex-native\n'
        ambient = alternate
        expected = 'home'
        selected = primary
        helper_selected = f'{harness} {MODEL}'
        if case.startswith('unpinned'):
            pin = None
            ambient = ordinary if case == 'unpinned-home' else alternate
            expected = 'unknown'
        elif case == 'alternate-pin':
            pin = f'{alternate}\nopenai-codex\n'
            ambient = ordinary
            expected = 'unknown'
        elif case == 'provider-not-permitted':
            pin = 'ordinary\nanthropic\n'
            expected = 'unknown'
        elif case == 'provider-prefix-not-permitted':
            pin = 'ordinary\nanthropic openai-codex-work\n'
            expected = 'unknown'
        elif case == 'exact-exhausted':
            snapshot['providers'].append(row('codex', 'openai-codex', 0, -5))
            snapshot['providers'].reverse()
            expected = 'exhausted'
        elif case == 'default-only':
            snapshot['providers'] = [row('codex', 'default', 97, 0.8), row('cursor', 'default', 24, 0.3)]
            expected = 'unknown'
            selected = sibling
        elif case == 'schema5':
            snapshot['schemaVersion'] = 5
            snapshot['providers'] = [row('codex', 'unused', 97, 0.8), row('cursor', 'unused', 24, 0.3)]
            for provider in snapshot['providers']:
                del provider['accountKey']
            profiles.append({'harness': 'codex', 'model': 'gpt-5.6-sol'})
            expected = 'tie'
        elif case == 'native-adapter':
            pin = f'{alternate}\nopenai-codex openai-codex-work codex-native\n'
            primary['model'] = 'codex-native/gpt-6-astra'
            helper_selected = f'{harness} {primary["model"]}'
        elif case in ('malformed-pin', 'invalid-default', 'non-pi-invalid'):
            pin = 'ordinary\n'
            expected = 'invalid'
        elif case == 'missing-root':
            pin = f'{lab / "missing-account"}\nopenai-codex\n'
            expected = 'invalid'
        elif case == 'directory-pin':
            pin = None
            (fm / 'config/pi-account').mkdir()
            expected = 'invalid'
        if expected in ('unknown', 'exhausted'):
            if case != 'default-only':
                selected = cursor
            helper_selected = 'cursor default'
        if expected == 'invalid':
            profiles = [cursor, primary]
        if case == 'non-pi-invalid':
            profiles = [cursor]
            selected = cursor
            expected = 'non-pi'
            helper_selected = 'cursor default'
        if pin is not None:
            (fm / 'config/pi-account').write_text(pin)
        rules = {'rules': [{'when': 'Fix a software bug with a stated root cause.', 'use': profiles}]}
        if case == 'invalid-default':
            rules['rules'][0]['use'] = cursor
            rules['default'] = [cursor, primary]
        (fm / 'config/crew-dispatch.json').write_text(json.dumps(rules))
        brief = lab / 'brief.md'
        brief.write_text('# Task\nFix a software bug with a stated root cause. The pager uses <= instead of <. Change it to <.\n')
        fixture = lab / 'quota.json'
        fixture.write_text(json.dumps(snapshot))
        env = {k:v for k,v in os.environ.items() if not (
            k.startswith('FM_') or k.startswith('QUOTA_') or k.startswith('PI_') or k.startswith('XDG_'))}
        env.update(HOME=str(home), FM_HOME=str(fm), TMPDIR=str(lab / 'tmp'), LC_ALL='C', LANG='C',
            PI_CODING_AGENT_DIR=str(ambient), PATH=str(fakebin) + os.pathsep + os.environ['PATH'],
            QUOTA_FIXTURE=str(fixture), QUOTA_CALLS=str(lab / 'quota.calls'), HTTP_CALLS=str(lab / 'http.calls'))
        record = {'case': case, 'harness': harness, 'snapshot': snapshot, 'rules': rules,
            'pin': pin, 'environment': {k:env[k] for k in ['HOME', 'FM_HOME', 'TMPDIR', 'LC_ALL', 'PI_CODING_AGENT_DIR', 'PATH']},
            'notes': 'Real resolver and real Typesafe HTTPS API. Only quota-axi is stubbed. Account directories are empty; no login or credential files are copied or read.',
            'commands': [], 'checks': []}

        def execute(argv):
            result = subprocess.run(argv, env=env, text=True, capture_output=True, timeout=25)
            record['commands'].append({'argv': argv, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
            return result

        def check(name, condition):
            record['checks'].append({'name': name, 'pass': bool(condition)})

        result = execute([BASH, str(ROOT / 'bin/fm-dispatch-resolve.sh'), str(brief)])
        check('resolver exit code', result.returncode == (2 if expected == 'invalid' else 0))
        quota_calls = (lab / 'quota.calls').read_text().splitlines() if (lab / 'quota.calls').exists() else []
        http_calls = (lab / 'http.calls').read_text().splitlines() if (lab / 'http.calls').exists() else []
        record.update(quota_calls=quota_calls, http_calls=http_calls)
        if expected == 'invalid':
            check('invalid pin is named with no selection', not result.stdout and 'error: config/pi-account' in result.stderr)
            check('configuration refusal precedes HTTP and quota', not quota_calls and not http_calls)
        else:
            check('one real HTTP call and one fixture quota read', len(http_calls) == 1 and quota_calls == ['--json'])
            if expected == 'tie':
                check('single-provider schema 5 stays tied', 'status: escalate' in result.stdout and 'genuine spendPriority tie' in result.stdout)
                for candidate in (primary, sibling, profiles[-1]):
                    check(f'schema 5 row for {candidate["harness"]}:{candidate["model"]}',
                        f'candidate: {candidate["harness"]}:{candidate["model"]}  provider=codex  scope=all_models  remaining=97%' in result.stdout)
            else:
                check('expected concrete selection', 'status: clear' in result.stdout and
                    f"profile: --harness '{selected['harness']}' --model '{selected['model']}'" in result.stdout)
                candidate_line = next((x for x in result.stdout.splitlines() if f'candidate: {harness}:{primary["model"]}  ' in x), '')
                if expected == 'unknown':
                    check('Pi is eligible but explicitly unranked', 'eligible, unranked:' in candidate_line and 'disclosed uncertainty' in candidate_line)
                elif expected == 'exhausted':
                    check('exact exhausted row vetoes home', 'remaining=0%' in candidate_line and 'not eligible: runway exhausted_now' in candidate_line)
                elif expected == 'home':
                    check('home row supplies headroom', 'remaining=97%' in candidate_line and 'spendPriority=0.8' in candidate_line)
            if case == 'home-preferred':
                check('sibling keeps its own exhausted row', f'candidate: {harness}:{SIBLING}  provider=codex  scope=all_models  remaining=0%' in result.stdout)
            if case == 'default-only':
                check('other lanes retain default fallback', f'candidate: {harness}:{SIBLING}  provider=codex  scope=all_models  remaining=97%' in result.stdout)
        helper_snapshot = copy.deepcopy(snapshot)
        for provider in helper_snapshot['providers']:
            if provider['provider'] == 'codex':
                provider['provider'] = 'pi'
        record['helper_note'] = 'The helper retains its documented primary-provider mapping: Pi candidates consume provider=pi. JSON and TOON carry identical rows with that provider.'
        helper_json = lab / 'helper.json'
        helper_json.write_text(json.dumps(helper_snapshot))
        columns = ['provider'] + (['accountKey'] if snapshot['schemaVersion'] == 6 else []) + ['scope', 'effectivePercentRemaining', 'spendPriority', 'runway', 'confidence', 'limitedBy', 'resetsAt']
        lines = [f'quota[{len(helper_snapshot["providers"])}]{{{",".join(columns)}}}:']
        for provider in helper_snapshot['providers']:
            values = [provider['provider']] + ([provider['accountKey']] if snapshot['schemaVersion'] == 6 else [])
            availability = provider['quotaSemantics']['effectiveAvailability'][0]
            values += ['all_models', str(availability['effectivePercentRemaining']), str(availability['selection']['spendPriority']), availability['runway']['status'], 'established', 'weekly', '"2026-10-07T00:00:00Z"']
            lines.append('  ' + ','.join(values))
        lines += ['exhaustion[0]:', 'attention[0]:']
        helper_toon = lab / 'helper.toon'
        helper_toon.write_text('bin: quota-axi\ngeneratedAt: "2026-10-04T00:00:00Z"\n' + '\n'.join(lines) + '\n')
        helper_candidates = [f'{harness}:{primary["model"]}', 'cursor:default']
        if expected == 'invalid':
            helper_candidates.reverse()
        if expected == 'non-pi':
            helper_candidates = ['cursor:default']
        for path in (helper_json, helper_toon):
            result = execute([BASH, str(ROOT / 'bin/fm-quota-choose.sh'), '--snapshot', str(path)] + helper_candidates)
            check(f'{path.suffix} helper exit code', result.returncode == (2 if expected == 'invalid' else 0))
            if expected == 'invalid':
                check(f'{path.suffix} helper refuses before selecting Cursor', not result.stdout and 'error: config/pi-account' in result.stderr)
            else:
                check(f'{path.suffix} helper selects expected candidate', result.stdout.strip() == helper_selected)
        record['pass'] = all(x['pass'] for x in record['checks'])
        records.append(record)
        (EVIDENCE / 'quota-live-results.json').write_text(json.dumps(records, indent=2) + '\n')
        print(f'{"PASS" if record["pass"] else "FAIL"} {harness} {case}', flush=True)
        for check_result in record['checks']:
            if not check_result['pass']:
                print('  ' + check_result['name'], flush=True)


if not os.environ.get('TYPESAFE_API_KEY'):
    raise SystemExit('TYPESAFE_API_KEY must already be supplied through the runtime.')
cases = ['home-preferred', 'unpinned-home', 'unpinned-alternate', 'alternate-pin',
    'provider-not-permitted', 'provider-prefix-not-permitted', 'exact-exhausted',
    'default-only', 'schema5', 'native-adapter', 'malformed-pin', 'missing-root',
    'directory-pin', 'invalid-default']
for harness in ('pi', 'pi-signed'):
    for case in cases:
        drive(case, harness)
drive('non-pi-invalid', 'pi')
transcript = ['Real quota CLI validation', 'Target: 92a21b6105b642a33664de5ff376ac00b0c5810e',
    'Every case uses a distinct disposable FM_HOME and HOME inside the gate worktree.',
    'TYPESAFE_API_KEY is inherited without disclosure. The HTTP wrapper forwards to the real curl.',
    'Only the quota producer is stubbed, as authorized; all decision logic is the real product.',
    'All temporary directories are removed after each case.']
for record in records:
    transcript += ['', f'=== {record["harness"]}: {record["case"]} ===',
        'Result: ' + ('PASS' if record['pass'] else 'FAIL'), 'Account pin: ' + repr(record['pin']),
        'Environment: ' + json.dumps(record['environment']), 'Snapshot: ' + json.dumps(record['snapshot']),
        'Rules: ' + json.dumps(record['rules']), record['helper_note']]
    for command in record['commands']:
        transcript += ['$ ' + shlex.join(command['argv']), command['stdout'],
            'stderr: ' + (command['stderr'] or '(empty)'), 'exit code: ' + str(command['exit'])]
    transcript += ['quota calls: ' + repr(record['quota_calls']), 'real HTTP calls: ' + repr(record['http_calls'])]
(EVIDENCE / 'quota-live-transcript.txt').write_text('\n'.join(transcript) + '\n')
passed = sum(record['pass'] for record in records)
print(f'{passed}/{len(records)} cases passed; {len(records) * 3} product command invocations', flush=True)
raise SystemExit(0 if passed == len(records) else 1)
