import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M35CR0J4T5R92RG3Z28Z5KF2')
EVIDENCE = Path(__file__).parent
SCRATCH = ROOT / '.quota-test-phase'


def row(provider, account, remaining, priority):
    result = {
        'provider': provider,
        'quotaSemantics': {'status': 'known', 'effectiveAvailability': [{
            'scope': 'all_models', 'status': 'known',
            'effectivePercentRemaining': remaining,
            'runway': {'status': 'exhausted_now' if remaining == 0 else 'through_reset'},
            'selection': {'spendPriority': priority},
        }]},
    }
    if account is not None:
        result['accountKey'] = account
    return result


HOME = {'harness': 'pi', 'model': 'openai-codex/gpt-5.6-sol', 'provider': 'codex'}
LABS = {'harness': 'pi', 'model': 'openai-codex-muller-labs/gpt-5.6-sol', 'provider': 'codex'}
NATIVE = {'harness': 'codex', 'model': 'gpt-5.6-sol'}
PI_NATIVE = {'harness': 'pi', 'model': 'codex-native/gpt-6-astra', 'provider': 'codex', 'effort': 'ultra'}
SIGNED = {**HOME, 'harness': 'pi-signed'}
CLAUDE = {'harness': 'claude', 'model': 'sonnet'}


def candidate(profile, remaining=None, priority=None, unranked=False):
    prefix = f"candidate: {profile['harness']}:{profile['model']}  provider={profile.get('provider', profile['harness'])}"
    if unranked:
        return prefix + '  -> eligible, unranked: provider codex has no quota row for account openai-codex: disclosed uncertainty'
    runway = 'exhausted_now' if remaining == 0 else 'through_reset'
    score = '-' if remaining == 0 else str(priority)
    ending = 'not eligible: runway exhausted_now at all_models' if remaining == 0 else 'eligible'
    return prefix + f'  scope=all_models  remaining={remaining}%  spendPriority={score}  runway={runway}  -> {ending}'


cases = [
    ('home-fallback', 6, [HOME, LABS], [row('codex', 'codex-home', 97, 0.8), row('codex', 'openai-codex-muller-labs', 0, -1), row('codex', 'default', 100, 0.95)], [
        'status: clear', candidate(HOME, 97, 0.8), candidate(LABS, 0, -1),
        "profile: --harness 'pi' --model 'openai-codex/gpt-5.6-sol'",
    ]),
    ('exact-exhausted', 6, [HOME, LABS], [row('codex', 'codex-home', 97, 0.8), row('codex', 'openai-codex', 0, -1), row('codex', 'openai-codex-muller-labs', 0, -2), row('codex', 'default', 100, 0.95)], [
        'status: escalate', 'reason: no rankable eligible candidate', candidate(HOME, 0, -1), candidate(LABS, 0, -2),
    ]),
    ('neither-named', 6, [HOME, LABS], [row('codex', 'default', 97, 0.8)], [
        'status: clear', candidate(HOME, unranked=True), candidate(LABS, 97, 0.8),
        "profile: --harness 'pi' --model 'openai-codex-muller-labs/gpt-5.6-sol'",
    ]),
    ('schema5', 5, [HOME, LABS, NATIVE, PI_NATIVE, SIGNED, CLAUDE], [row('codex', None, 61, 0.65), row('claude', None, 42, 0.4)], [
        'status: escalate', 'reason: genuine spendPriority tie',
        *[candidate(p, 61, 0.65) for p in [HOME, LABS, NATIVE, PI_NATIVE, SIGNED]], candidate(CLAUDE, 42, 0.4),
    ]),
    ('other-lanes', 6, [HOME, LABS, NATIVE, PI_NATIVE, SIGNED, CLAUDE], [row('codex', 'codex-home', 97, 0.8), row('codex', 'openai-codex', 0, -1), row('codex', 'openai-codex-muller-labs', 11, 0.3), row('codex', 'default', 100, 0.95), row('claude', 'default', 42, 0.4)], [
        'status: escalate', 'reason: genuine spendPriority tie', candidate(HOME, 0, -1), candidate(SIGNED, 0, -1),
        candidate(LABS, 11, 0.3), candidate(NATIVE, 97, 0.8), candidate(PI_NATIVE, 97, 0.8), candidate(CLAUDE, 42, 0.4),
    ]),
]

summary = []
for name, schema, profiles, rows, expected in cases:
    home = SCRATCH / name
    for directory in ['config', 'bin', 'tmp', 'user']:
        (home / directory).mkdir(parents=True, exist_ok=False)
    snapshot = {'generatedAt': '2026-09-22T00:00:00Z', 'schemaVersion': schema, 'providers': rows}
    rules = {'rules': [{'when': 'The task fixes a software bug with an identified root cause.', 'use': profiles}]}
    brief = '# Task\nFix a software bug in the pager. The identified root cause is an off-by-one condition that emits the final page twice. Change the condition and verify that every page is emitted exactly once.\n'
    (home / 'config/crew-dispatch.json').write_text(json.dumps(rules, indent=2) + '\n')
    (home / 'quota.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    (home / 'brief.md').write_text(brief)
    stub = home / 'bin/quota-axi'
    stub.write_text('#!/usr/bin/env bash\nset -eu\n[ "$#" -eq 1 ] && [ "$1" = --json ] || exit 64\nprintf "%s\\n" "$*" >> "$FM_HOME/quota.calls"\ncat "$FM_HOME/quota.json"\n')
    stub.chmod(0o700)
    env = {'PATH': str(home / 'bin') + ':' + os.environ['PATH'], 'HOME': str(home / 'user'), 'FM_HOME': str(home), 'TMPDIR': str(home / 'tmp'), 'TYPESAFE_API_KEY': os.environ['TYPESAFE_API_KEY'], 'LANG': 'en_US.UTF-8'}
    argv = ['bash', 'bin/fm-dispatch-resolve.sh', str(home / 'brief.md'), '--project', 'quota-lane-verification']
    visible_env = {k: v for k, v in env.items() if k != 'TYPESAFE_API_KEY'}
    command = 'env ' + ' '.join(shlex.quote(k + '=' + v) for k, v in visible_env.items()) + ' ' + shlex.join(argv)
    result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=20)
    calls = (home / 'quota.calls').read_text() if (home / 'quota.calls').exists() else ''
    missing = [item for item in expected if item not in result.stdout]
    passed = result.returncode == 0 and not result.stderr and calls == '--json\n' and not missing
    transcript = '# Real resolver and real typesafe.ai request; only quota-axi is a controlled snapshot source.\n# TYPESAFE_API_KEY inherited from the runtime, never recorded.\n$ ' + command + '\n\nstdout:\n' + result.stdout + '\nstderr:\n' + result.stderr + f'\nexit_code={result.returncode}\nquota-axi invocations:\n{calls}\nassertions={len(expected)}\nresult={"pass" if passed else "fail"}\n'
    if missing:
        transcript += 'missing expected output:\n' + '\n'.join(missing) + '\n'
    (EVIDENCE / f'{name}.log').write_text(transcript)
    (EVIDENCE / f'{name}-inputs.json').write_text(json.dumps({'brief': brief, 'rules': rules, 'quota': snapshot, 'expected': expected}, indent=2) + '\n')
    summary.append({'name': name, 'exit_code': result.returncode, 'assertions': len(expected), 'pass': passed, 'missing': missing})
    print(f'{name}: exit_code={result.returncode}, assertions={len(expected)}, result={"pass" if passed else "fail"}', flush=True)
    print(result.stdout, end='', flush=True)
    if result.stderr:
        print(result.stderr, flush=True)

(EVIDENCE / 'scenario-results.json').write_text(json.dumps(summary, indent=2) + '\n')
raise SystemExit(0 if all(item['pass'] for item in summary) else 1)
