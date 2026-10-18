import copy
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
LAB = ROOT / '.quota-validation'
for directory in ['home', 'home/config', 'tmp', 'xdg-config', 'xdg-cache', 'xdg-data']:
    (LAB / directory).mkdir(parents=True, exist_ok=True)
ENV = {
    'PATH': os.environ['PATH'], 'HOME': str(LAB / 'home'), 'LC_ALL': 'C',
    'FM_HOME': str(LAB / 'home'), 'TMPDIR': str(LAB / 'tmp'),
    'XDG_CONFIG_HOME': str(LAB / 'xdg-config'),
    'XDG_CACHE_HOME': str(LAB / 'xdg-cache'),
    'XDG_DATA_HOME': str(LAB / 'xdg-data'),
    'CLAUDE_CONFIG_DIR': str(LAB / 'home/claude'),
    'CODEX_HOME': str(LAB / 'home/codex'),
    'PI_CODING_AGENT_DIR': str(LAB / 'home/pi'),
    'TYPESAFE_API_KEY': os.environ.get('TYPESAFE_API_KEY', ''),
}
NOW = datetime.datetime.now(datetime.timezone.utc)

def iso(value):
    return value.isoformat().replace('+00:00', 'Z')

def row(key=None, aliases=None, remaining=80, provider='codex'):
    value = {
        'provider': provider, 'label': provider.title(), 'source': 'oauth',
        'windows': [{
            'id': 'five_hour', 'label': 'session', 'kind': 'session',
            'windowSeconds': 18000, 'percentUsed': 100 - remaining,
            'percentRemaining': remaining,
            'startsAt': iso(NOW - datetime.timedelta(seconds=9000)),
            'resetsAt': iso(NOW + datetime.timedelta(seconds=9000)),
        }],
        'state': {'status': 'fresh', 'sourcesTried': ['oauth'], 'refreshedAt': iso(NOW)},
    }
    if key is not None:
        value['accountKey'] = key
    if aliases is not None:
        value['reuse'] = {
            'context': '0' * 64, 'inputs': [], 'inputsDigest': '0' * 64,
            'readingAt': iso(NOW), 'lanes': 1, 'lane': 0, 'accountKeys': aliases,
        }
    return value

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')

def codex_row(data):
    return next(value for value in data['providers'] if value['provider'] == 'codex')

def run(label, args, env=None, stdin=None):
    result = subprocess.run(args, cwd=ROOT, env=env or ENV, input=stdin,
                            capture_output=True, text=True, timeout=30)
    text = '$ ' + shlex.join(args) + '\n'
    text += f'exit: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}\n'
    (EVIDENCE / f'{label}.txt').write_text(text)
    return result

def snapshot(label, rows):
    cache = EVIDENCE / f'{label}.cache.json'
    write_json(cache, {'schemaVersion': 3, 'generatedAt': iso(NOW), 'providers': rows})
    env = ENV | {'QUOTA_AXI_SNAPSHOT': str(cache)}
    result = run(label + '-producer', ['quota-axi', '--json'], env)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    data = json.loads(result.stdout)
    output = EVIDENCE / f'{label}.snapshot.json'
    write_json(output, data)
    return output, data, env

def resolve(label, env, model='gpt-5.6-sol', harness='codex', executable='bin/fm-dispatch-resolve.sh'):
    candidate = {'harness': harness, 'model': model, 'provider': 'codex'}
    write_json(LAB / 'home/config/crew-dispatch.json', {
        'rules': [{'when': 'A simple bug fix with a stated root cause.', 'use': [candidate]}],
        'default': [candidate],
    })
    brief = LAB / 'brief.md'
    brief.write_text('# Task\nFix the off-by-one bug in a pager. The root cause is a <= comparison; replace it with <.\n')
    return run(label + '-resolver', ['bash', executable, str(brief)], env)

def choose(label, snapshot_path, expected, code=0):
    result = run(label + '-helper', [
        'bash', 'bin/fm-quota-choose.sh', '--snapshot', str(snapshot_path),
        '--candidate', 'codex:default',
    ])
    assert (result.returncode, result.stdout.strip()) == (code, expected), result.stdout + result.stderr
    return result

def check_resolver(result, expected, forbidden=()):
    assert result.returncode == 0, result.stderr
    assert all(text in result.stdout for text in expected), result.stdout
    assert all(text not in result.stdout for text in forbidden), result.stdout

RESULTS = []

def record(label, description, artifacts):
    RESULTS.append({'name': label, 'description': description, 'result': 'pass', 'artifacts': artifacts})
    print('PASS ' + label, flush=True)

def main():
    alias_rows = [row('credential-primary', ['codex-home', 'credential-alias']), row('default', remaining=0)]
    path, data, env = snapshot('unique-alias', alias_rows)
    check_resolver(resolve('unique-alias', env), ['status: clear', 'remaining=80%', "profile: --harness 'codex'"])
    choose('unique-alias', path, 'codex default')
    check_resolver(resolve('pi-alias', env, 'credential-alias/gpt-6-astra', 'pi'),
                   ['status: clear', 'remaining=80%', "profile: --harness 'pi'"])
    check_resolver(resolve('pi-native-alias', env, 'codex-native/gpt-6-astra', 'pi'),
                   ['status: clear', 'remaining=80%', "profile: --harness 'pi'"])
    record('unique-alias', 'Codex, Pi, and Pi native credentials bind through one covered-key row before default.',
           ['unique-alias-resolver.txt', 'unique-alias-helper.txt', 'pi-alias-resolver.txt', 'pi-native-alias-resolver.txt'])

    base_bin = LAB / 'base/bin'
    for name in ['fm-quota-choose.sh', 'fm-dispatch-resolve.sh', 'fm-control-lib.sh',
                 'fm-env-lib.sh', 'fm-timing-lib.sh', 'fm-brief-heading-lib.sh']:
        link = base_bin / name
        if not link.exists():
            link.symlink_to(ROOT / 'bin' / name)
    baseline = resolve('base-alias', env, executable=str(base_bin / 'fm-dispatch-resolve.sh'))
    check_resolver(baseline, ['status: escalate', 'remaining=0%', 'not eligible:'], ['profile:'])
    baseline_helper = run('base-alias-helper', ['bash', str(base_bin / 'fm-quota-choose.sh'),
                                              '--snapshot', str(path), '--candidate', 'codex:default'])
    assert (baseline_helper.returncode, baseline_helper.stdout.strip()) == (1, 'none'), baseline_helper.stdout
    no_default_path, _, no_default_env = snapshot('alias-without-default', alias_rows[:1])
    baseline = resolve('base-unranked-alias', no_default_env, executable=str(base_bin / 'fm-dispatch-resolve.sh'))
    check_resolver(baseline, ['status: escalate', 'eligible, unranked: provider codex has no quota row for account codex-home'], ['profile:'])
    check_resolver(resolve('alias-without-default', no_default_env), ['status: clear', 'remaining=80%'])
    record('base-regression', 'The base revision leaves an alias unranked or reads an exhausted default; the target selects the 80% row.',
           ['base-unranked-alias-resolver.txt', 'alias-without-default-resolver.txt', 'base-alias-resolver.txt', 'base-alias-helper.txt'])

    exact_rows = [row('credential-primary', ['codex-home']), row('other', ['codex-home']),
                  row('codex-home', remaining=0), row('default')]
    for reverse in [False, True]:
        label = 'exact-first' + ('-reversed' if reverse else '')
        path, _, env = snapshot(label, list(reversed(exact_rows)) if reverse else exact_rows)
        check_resolver(resolve(label, env), ['remaining=0%', 'not eligible:', 'status: escalate'], ['profile:'])
        choose(label, path, 'none', 1)
    record('exact-first', 'An exhausted exact account wins over two healthy aliases and a healthy default in either row order.',
           ['exact-first-resolver.txt', 'exact-first-helper.txt', 'exact-first-reversed-resolver.txt'])

    ambiguous_rows = [row('credential-primary', ['codex-home']), row('other', ['codex-home']), row('default')]
    for reverse in [False, True]:
        label = 'ambiguous' + ('-reversed' if reverse else '')
        path, _, env = snapshot(label, list(reversed(ambiguous_rows)) if reverse else ambiguous_rows)
        check_resolver(resolve(label, env), ['status: escalate', 'eligible, unranked:', 'no quota row for account codex-home'], ['profile:', 'not eligible:'])
        choose(label, path, 'none', 1)
    record('ambiguous', 'Conflicting aliases remain eligible and unranked even with a healthy default; the helper selects none.',
           ['ambiguous-resolver.txt', 'ambiguous-helper.txt', 'ambiguous-reversed-resolver.txt'])

    scoped_rows = [row('credential-primary', ['codex-home', 'codex-home']),
                   row('other-provider', ['codex-home'], remaining=0, provider='claude')]
    for reverse in [False, True]:
        label = 'provider-scope' + ('-reversed' if reverse else '')
        path, _, env = snapshot(label, list(reversed(scoped_rows)) if reverse else scoped_rows)
        check_resolver(resolve(label, env), ['status: clear', 'remaining=80%'])
        choose(label, path, 'codex default')
    record('provider-scope', 'The same alias on another provider does not conflict, independently of row order.',
           ['provider-scope-resolver.txt', 'provider-scope-helper.txt', 'provider-scope-reversed-resolver.txt'])

    path, _, env = snapshot('whitespace-alias', [row('codex-home', ['codex-home', 'work account'])])
    check_resolver(resolve('whitespace-alias', env), ['status: clear', 'remaining=80%'])
    choose('whitespace-alias', path, 'codex default')
    poll = run('whitespace-procevent', ['bash', 'bin/fm-procevent-quota.sh', 'poll', '--provider', 'codex',
                                      '--threshold', '100', '--interval', '0.01', '--timeout', '5'], env)
    assert poll.returncode == 0 and 'status: low' in poll.stdout and 'condition_polls: 1' in poll.stdout, poll.stdout
    record('whitespace-alias', 'Whitespace aliases remain valid for the resolver, worker helper, and quota event consumer.',
           ['whitespace-alias-resolver.txt', 'whitespace-alias-helper.txt', 'whitespace-procevent.txt'])

    for label, rows, schema, expected in [
        ('missing-alias-exact', [row('codex-home')], 6, 'codex default'),
        ('default-fallback', [row('unrelated', remaining=0), row('default')], 6, 'codex default'),
        ('missing-account', [row('unrelated')], 6, 'none'),
        ('schema5', [row()], 5, 'codex default'),
    ]:
        path, data, env = snapshot(label, rows)
        assert data['schemaVersion'] == schema, data['schemaVersion']
        result = resolve(label, env)
        if expected == 'none':
            check_resolver(result, ['status: escalate', 'eligible, unranked:'], ['profile:'])
        else:
            check_resolver(result, ['status: clear', 'remaining=80%'])
        choose(label, path, expected, 1 if expected == 'none' else 0)
    record('compatibility', 'Exact rows, default fallback, missing rows, and schema 5 retain their behavior.',
           [label + '-resolver.txt' for label in ['missing-alias-exact', 'default-fallback', 'missing-account', 'schema5']])

    original = json.loads((EVIDENCE / 'unique-alias.snapshot.json').read_text())
    malformed = [None, 'codex-home', {}, 9, False, [''], [1], [None], [False], [{}], [[]], ['codex-home', '']]
    for index, aliases in enumerate(malformed):
        data = copy.deepcopy(original)
        codex_row(data)['accountKeys'] = aliases
        path = EVIDENCE / f'malformed-{index}.snapshot.json'
        write_json(path, data)
        result = run(f'malformed-{index}-helper', ['bash', 'bin/fm-quota-choose.sh', '--snapshot', str(path), '--candidate', 'codex:default'])
        assert result.returncode == 2 and not result.stdout and 'invalid quota-axi provider data' in result.stderr, result.stdout + result.stderr
    data = copy.deepcopy(original)
    codex_row(data)['accountKey'] = 'work account'
    path = EVIDENCE / 'invalid-account-key.snapshot.json'
    write_json(path, data)
    result = run('invalid-account-key-helper', ['bash', 'bin/fm-quota-choose.sh', '--snapshot', str(path), '--candidate', 'codex:default'])
    assert result.returncode == 2 and 'invalid quota-axi provider data' in result.stderr, result.stdout + result.stderr
    record('malformed', 'The real helper rejects all 12 malformed alias shapes and still rejects whitespace in accountKey.',
           [f'malformed-{index}-helper.txt' for index in range(len(malformed))] + ['invalid-account-key-helper.txt'])

    for label, aliases, key, expected, code in [
        ('empty-alias-array', [], 'codex-home', 'codex default', 0),
        ('empty-alias-fallback', [], 'unrelated', 'none', 1),
        ('duplicate-alias', ['codex-home', 'codex-home'], 'credential-primary', 'codex default', 0),
        ('whitespace-only-alias', [' ', '\t', '\n'], 'codex-home', 'codex default', 0),
    ]:
        data = copy.deepcopy(original)
        codex_row(data)['accountKeys'] = aliases
        codex_row(data)['accountKey'] = key
        path = EVIDENCE / f'{label}.snapshot.json'
        write_json(path, data)
        choose(label, path, expected, code)
    data = json.loads((EVIDENCE / 'schema5.snapshot.json').read_text())
    codex_row(data)['accountKeys'] = False
    path = EVIDENCE / 'schema5-ignores-alias-field.snapshot.json'
    write_json(path, data)
    choose('schema5-ignores-alias-field', path, 'codex default')
    record('valid-edge-inputs', 'Empty arrays, repeated aliases in one row, whitespace strings, and schema-5 field handling remain valid.',
           [label + '-helper.txt' for label in ['empty-alias-array', 'empty-alias-fallback', 'duplicate-alias', 'whitespace-only-alias', 'schema5-ignores-alias-field']])
    write_json(EVIDENCE / 'live-results.json', RESULTS)
    print(f'{len(RESULTS)} scenario groups passed; 0 failed', flush=True)

def absent_alias_checks():
    artifacts = []
    for source, expected in [('missing-alias-exact', 'codex default'),
                             ('default-fallback', 'codex default'), ('missing-account', 'none')]:
        data = json.loads((EVIDENCE / f'{source}.snapshot.json').read_text())
        for provider in data['providers']:
            provider.pop('accountKeys', None)
        label = source + '-without-accountKeys'
        path = EVIDENCE / f'{label}.snapshot.json'
        write_json(path, data)
        choose(label, path, expected, 1 if expected == 'none' else 0)
        artifacts.append(label + '-helper.txt')
    prior = json.loads((EVIDENCE / 'live-results.json').read_text())
    for result in prior:
        if result['name'] == 'compatibility':
            result['description'] = 'Exact rows, default fallback, missing rows, and schema 5 retain their behavior, including absent accountKeys.'
            result['artifacts'].extend(artifacts)
    write_json(EVIDENCE / 'live-results.json', prior)
    print('3 absent-accountKeys helper checks passed; 0 failed', flush=True)

if __name__ == '__main__':
    if sys.argv[1:] == ['--absent-alias-checks']:
        absent_alias_checks()
    else:
        main()
