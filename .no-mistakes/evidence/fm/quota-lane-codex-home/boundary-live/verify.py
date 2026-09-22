from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import tempfile

root = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M354G9F3ZYS8PYSQSKWC9PAS')
evidence = Path(__file__).parent
assert Path.cwd() == root
assert os.environ.get('TYPESAFE_API_KEY'), 'Live Typesafe API key is required'
lab = Path(tempfile.mkdtemp(prefix='.quota-boundary-live-', dir=root))
profiles = [
    {'harness': 'pi', 'model': 'openai-codex/gpt-5.6-sol', 'provider': 'codex'},
    {'harness': 'pi', 'model': 'openai-codex-muller-labs/gpt-5.6-luna', 'provider': 'codex'},
    {'harness': 'pi', 'model': 'codex-native/gpt-6-astra', 'provider': 'codex', 'effort': 'ultra'},
    {'harness': 'codex', 'model': 'gpt-5.6-sol'},
    {'harness': 'cursor', 'model': 'cursor-grok-4.6-medium'},
]
rules = {'rules': [{'when': 'Implement a concrete software bug fix with a known root cause.', 'use': profiles}]}
brief = 'Fix the known pager off-by-one condition from <= to < and verify the page count.\n'
(evidence / 'crew-dispatch.json').write_text(json.dumps(rules, indent=2) + '\n')
(evidence / 'brief.md').write_text(brief)
results = []
try:
    for name in ['exact-row-exhausted', 'neither-named-row-default-present', 'schema-5']:
        home = lab / name
        for directory in ['config', 'stub-bin', 'tmp']:
            (home / directory).mkdir(parents=True)
        (home / 'config/crew-dispatch.json').write_text(json.dumps(rules))
        (home / 'brief.md').write_text(brief)
        snapshot = (evidence.parent / (name + '-input.json')).read_text()
        (home / 'quota.json').write_text(snapshot)
        (evidence / (name + '-input.json')).write_text(snapshot)
        stub = home / 'stub-bin/quota-axi'
        stub.write_text('''#!/usr/bin/env bash
set -eu
[ "$#" -eq 1 ] && [ "$1" = --json ] || exit 2
[ -z "${TYPESAFE_API_KEY+x}" ] && [ -z "${TYPESAFE_API_KEY_PRIVATE+x}" ] || exit 3
printf '%s\\n' "$*" >> "$FM_HOME/quota-axi.calls"
cat "$FM_HOME/quota.json"
''')
        stub.chmod(0o755)
        (evidence / 'quota-axi-stub.sh').write_text(stub.read_text())
        env = os.environ.copy()
        removed = ['FM_ROOT_OVERRIDE', 'FM_CONFIG_OVERRIDE', 'FM_STATE_OVERRIDE', 'FM_TIMING_LOG']
        for key in removed:
            env.pop(key, None)
        overrides = {'FM_HOME': str(home), 'TMPDIR': str(home / 'tmp'), 'LC_ALL': 'C', 'PATH': str(home / 'stub-bin') + os.pathsep + env['PATH']}
        env.update(overrides)
        assert Path(shutil.which('quota-axi', path=env['PATH'])) == stub
        assert not (home / 'stub-bin/curl').exists()
        cmd = ['bash', 'bin/fm-dispatch-resolve.sh', str(home / 'brief.md'), '--project', 'quota-lane-validation']
        displayed = ['env'] + [v for key in removed for v in ['-u', key]] + [key + '=' + value for key, value in overrides.items()] + cmd
        run = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=30)
        calls = (home / 'quota-axi.calls').read_text() if (home / 'quota-axi.calls').exists() else ''
        transcript = 'Real resolver and live Typesafe.ai; isolated fixture quota-axi.\nTYPESAFE_API_KEY inherited from runtime, never recorded.\n$ ' + shlex.join(displayed) + '\nstdout:\n' + run.stdout + '\nstderr:\n' + run.stderr + '\nexit_code: ' + str(run.returncode) + '\nquota-axi calls:\n' + calls
        (evidence / (name + '.txt')).write_text(transcript)
        print(transcript, flush=True)
        assert run.returncode == 0, (name, run.returncode)
        assert run.stderr == '', (name, run.stderr)
        assert calls == '--json\n', (name, calls)
        lines = [line.strip() for line in run.stdout.splitlines() if line.strip().startswith('candidate:')]
        assert len(lines) == len(profiles), (name, lines)
        pi_home, labs, native, codex, cursor = lines
        if name == 'exact-row-exhausted':
            assert 'remaining=0%' in pi_home and '-> not eligible: runway exhausted_now' in pi_home, pi_home
            assert 'remaining=0%' in labs and '-> not eligible:' in labs, labs
            assert all('remaining=97%' in line and 'spendPriority=0.8' in line and line.endswith('-> eligible') for line in [native, codex]), lines
            assert 'reason: genuine spendPriority tie' in run.stdout, run.stdout
        elif name == 'neither-named-row-default-present':
            assert '-> eligible, unranked: provider codex has no quota row for account openai-codex' in pi_home, pi_home
            assert all('remaining=97%' in line and 'spendPriority=0.8' in line and line.endswith('-> eligible') for line in [labs, native, codex]), lines
        else:
            assert all('remaining=97%' in line and 'spendPriority=0.8' in line and line.endswith('-> eligible') for line in [pi_home, labs, native, codex]), lines
            assert 'reason: genuine spendPriority tie' in run.stdout, run.stdout
        assert 'remaining=22%' in cursor and 'spendPriority=0.3' in cursor and cursor.endswith('-> eligible'), cursor
        results.append({'scenario': name, 'result': 'pass', 'live_typesafe': True, 'fixture_quota': True, 'exit_code': run.returncode, 'transcript': str(evidence / (name + '.txt'))})
        print('PASS ' + name + ' exit=0', flush=True)
finally:
    shutil.rmtree(lab)
    (evidence / 'results.json').write_text(json.dumps({'tested_head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), 'passed': len(results), 'expected': 3, 'scenarios': results, 'scratch_removed': not lab.exists()}, indent=2) + '\n')
print('3/3 boundary scenarios passed; exit=0; scratch homes removed.')
