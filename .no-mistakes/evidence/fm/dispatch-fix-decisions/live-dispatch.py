import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path('/Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH')
EVIDENCE = Path(__file__).parent
LAB = Path(tempfile.mkdtemp(prefix='.dispatch-check-', dir=ROOT))
REAL = {name: shutil.which(name) for name in ['curl', 'pi', 'quota-axi', 'mktemp']}
RESULTS = []
PROFILE = {'harness': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'low'}
BASE = {
    'shared_quota': True,
    'rules': [
        {'when': 'Unusually difficult or high-risk security redesign or costly migration. Routine builds, ports, and installers do not qualify.', 'use': {'harness': 'claude', 'model': 'opus'}, 'approval': 'captain'},
        {'when': 'Routine feature work, a port, or an installer build inside an existing codebase.', 'use': PROFILE},
        {'when': 'A bug fix whose root cause the brief states.', 'use': {'harness': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'medium'}},
        {'when': 'A trivial mechanical edit such as a rename, typo, version bump, or wording fix.', 'use': {'harness': 'claude', 'model': 'sonnet'}},
        {'when': 'A read-only investigation, diagnosis, or audit whose deliverable is a written report, not a code change.', 'use': {'harness': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'}},
    ],
    'default': PROFILE,
}

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def scenario(name, rules, brief, extra=None):
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        return {'stdout': ''}
    case = LAB / name
    for part in ['config', 'tmp', 'codex', 'pi', 'xdg', 'cache', 'bin']:
        (case / part).mkdir(parents=True, exist_ok=True)
    write(case / 'config/crew-dispatch.json', json.dumps(rules))
    write(case / 'brief.md', "## Captain's intent\n" + brief + '\n\n## Firstmate spec\nKeep the change limited to the stated task.\n')
    wrapper = '''#!{python}
import json, os, pathlib, subprocess, sys, time
tool=pathlib.Path(sys.argv[0]).name
real=json.loads(os.environ['LIVE_REAL'])[tool]
args=sys.argv[1:]
event={{'tool':tool,'args':args,'root':os.environ.get('PI_CODING_AGENT_DIR'),'start':time.time()}}
if tool=='curl':
    body=sys.stdin.buffer.read()
    event['request']=json.loads(body)
    previous=pathlib.Path(os.environ['LIVE_EVENTS'])
    temps=[json.loads(line)['path'] for line in previous.read_text().splitlines() if json.loads(line)['tool']=='mktemp'] if previous.exists() else []
    event['temp_permissions']=[{{'path':p,'mode':oct(pathlib.Path(p).stat().st_mode & 0o777)}} for p in temps if pathlib.Path(p).is_file()]
    try: os.fstat(3); fds=(3,)
    except OSError: fds=()
    run=subprocess.run([real]+args,input=body,pass_fds=fds)
    if '-o' in args:
        response=pathlib.Path(args[args.index('-o')+1]).read_text()
        try: event['response']=json.loads(response)
        except ValueError: event['response']=response
elif tool=='mktemp':
    run=subprocess.run([real]+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    event['path']=run.stdout.decode().strip()
    if event['path'] and pathlib.Path(event['path']).exists(): event['mode']=oct(pathlib.Path(event['path']).stat().st_mode & 0o777)
    sys.stdout.buffer.write(run.stdout); sys.stderr.buffer.write(run.stderr)
elif tool=='quota-axi':
    run=subprocess.run([real]+args+['--provider','codex','--profile-only','--no-credential-refresh'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    event['stdout']=run.stdout.decode(errors='replace')
    event['stderr']=run.stderr.decode(errors='replace')
    sys.stdout.buffer.write(run.stdout); sys.stderr.buffer.write(run.stderr)
else:
    run=subprocess.run([real]+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    event['stdout']=run.stdout.decode(errors='replace')
    event['stderr']=run.stderr.decode(errors='replace')
    sys.stdout.buffer.write(run.stdout); sys.stderr.buffer.write(run.stderr)
event.update(exit_code=run.returncode,end=time.time())
with open(os.environ['LIVE_EVENTS'],'a') as f: f.write(json.dumps(event)+'\\n')
sys.exit(run.returncode)
'''.format(python=sys.executable)
    for name_ in REAL:
        if REAL[name_]:
            write(case / 'bin' / name_, wrapper)
            (case / 'bin' / name_).chmod(0o700)
    env = {key: value for key, value in os.environ.items() if key in ['PATH', 'HOME', 'USER', 'LOGNAME', 'TYPESAFE_API_KEY', 'NO_MISTAKES_GATE']}
    env.update(FM_HOME=str(case), TMPDIR=str(case / 'tmp'), PI_CODING_AGENT_DIR=str(case / 'pi'), CODEX_HOME=str(case / 'codex'), XDG_CONFIG_HOME=str(case / 'xdg'), XDG_CACHE_HOME=str(case / 'cache'), LC_ALL='C', LIVE_REAL=json.dumps(REAL), LIVE_EVENTS=str(case / 'events.jsonl'), PATH=str(case / 'bin') + ':' + os.environ['PATH'])
    if extra:
        extra(case, env)
    before = time.monotonic()
    run = subprocess.run(['bash', str(ROOT / 'bin/fm-dispatch-resolve.sh'), str(case / 'brief.md'), '--project', 'synthetic-dispatch-check'], env=env, text=True, capture_output=True, timeout=55)
    events = [json.loads(line) for line in (case / 'events.jsonl').read_text().splitlines()] if (case / 'events.jsonl').exists() else []
    result = {'name': name, 'exit_code': run.returncode, 'elapsed_seconds': round(time.monotonic()-before, 3), 'stdout': run.stdout, 'stderr': run.stderr, 'rules': rules, 'brief': brief, 'events': events, 'remaining_temps': [p.name for p in (case / 'tmp').iterdir()]}
    result['remaining_recorded_temps'] = [e['path'] for e in events if e['tool'] == 'mktemp' and Path(e['path']).exists()]
    write(EVIDENCE / (name + '.json'), json.dumps(result, indent=2))
    RESULTS.append(result)
    print(name + ': exit=' + str(run.returncode) + '\n' + run.stdout + run.stderr, flush=True)
    return result

try:
    scenario('live-clear', BASE, 'Fix the pagination bug. Root cause: the offset uses <= instead of < in orders_query.go. Change that comparison.')
    scenario('live-private-snapshots', BASE, 'Fix the pagination bug. Root cause: the offset uses <= instead of < in orders_query.go. Change that comparison.')
    for index, brief in enumerate([
        'Split a large module into smaller files. Preserve behavior. Some boundaries are unclear; investigate them as needed.',
        'Create a weekly on-call schedule for the team. There is no code change.',
        'Improve the wording and structure of a long onboarding document. Decide whether a small wording edit or restructuring is best.',
        'The orders list is slow. Identify the cause and make the smallest fix if the cause is obvious; otherwise write a diagnosis.',
        'Change a retry policy to handle intermittent failures. The exact cause is not known.',
    ]):
        result = scenario('live-borderline-' + str(index + 1), BASE, brief)
        if 'low confidence:' in result['stdout']:
            break
    scenario('live-captain-approval', BASE, 'Perform a high-risk security redesign of authorization and a costly production data migration. The brief explicitly calls this unusually difficult.')
    low_approval = copy.deepcopy(BASE)
    low_approval['rules'][4]['approval'] = 'captain'
    scenario('live-low-captain-approval', low_approval, 'The orders list is slow. Identify the cause and make the smallest fix if the cause is obvious; otherwise write a diagnosis.')
    floor_rules = copy.deepcopy(BASE)
    for rule in floor_rules['rules']:
        rule['min_confidence'] = 1
    scenario('live-declared-floor', floor_rules, 'Split a large module into smaller files. Preserve behavior. Some boundaries are unclear; investigate them as needed.')
    scenario('live-low-declared-floor', floor_rules, 'The orders list is slow. Identify the cause and make the smallest fix if the cause is obvious; otherwise write a diagnosis.')
    tie_rules = {'shared_quota': True, 'rules': [
        {'when': 'A mechanical typo fix in documentation.', 'use': PROFILE},
        {'when': 'A mechanical typo fix in documentation.', 'use': {'harness': 'claude', 'model': 'sonnet'}},
    ], 'default': PROFILE}
    scenario('live-equal-rules', tie_rules, 'Fix the spelling of documentation in README. Both matching rules have exactly the same condition.')
    expiry = {'shared_quota': True, 'rules': [
        {'when': 'Fix a pagination bug whose root cause is a wrong comparison.', 'until': '2000-01-01T00:00:00Z', 'use': {'harness': 'claude', 'model': 'sonnet'}},
        {'when': 'Fix a pagination bug whose root cause is a wrong comparison.', 'until': '2096-02-29T00:00:00Z', 'use': PROFILE},
    ], 'default': PROFILE}
    scenario('live-expired-rule', expiry, 'Fix the pagination bug. Root cause: a wrong comparison uses <= instead of <.')
    expiry['rules'][1]['until'] = '2000-01-01T00:00:00Z'
    scenario('live-all-expired', expiry, 'Fix the pagination bug caused by a wrong comparison.')
    for index, value in enumerate(['2999-13-40T25:61:61Z', '2027-02-29T12:00:00Z', '2096-02-29T00:00:00+00:00', 42, '2001-02-30T00:00:00Z']):
        expiry['rules'][1]['until'] = value
        scenario('live-invalid-until-' + str(index+1), expiry, 'Fix the pagination bug caused by a wrong comparison.')
    pi_rules = {'rules': [
        {'when': 'A bug fix with a stated root cause.', 'use': {'harness': 'pi', 'model': 'anthropic/claude-sonnet-4-5', 'provider': 'claude'}},
        {'when': 'A documentation typo.', 'use': {'harness': 'pi', 'model': 'anthropic/claude-opus-4-5', 'provider': 'claude'}},
        {'when': 'A retired rule.', 'until': '2000-01-01T00:00:00Z', 'use': {'harness': 'pi', 'model': 'expired-provider/unused', 'provider': 'codex'}},
    ], 'default': [{'harness': 'pi', 'model': 'openai-codex/gpt-6.1-sol', 'provider': 'codex'}]}
    def pin(case, env):
        write(case / 'config/pi-account', str(case / 'pi') + '\nanthropic openai-codex\n')
        (case / 'ambient-pi').mkdir()
        env['PI_CODING_AGENT_DIR'] = str(case / 'ambient-pi')
    scenario('live-pi-refresh-failure', pi_rules, 'Fix the pagination bug. Root cause: the comparison uses <= instead of <.', pin)
    def invalid_pin(case, env):
        write(case / 'config/pi-account', str(case / 'missing-root') + '\nanthropic openai-codex\n')
    scenario('live-invalid-account-pin', pi_rules, 'Fix the pagination bug. Root cause: the comparison uses <= instead of <.', invalid_pin)
    for provider, key in [('openrouter', 'OPENROUTER_API_KEY'), ('openai', 'OPENAI_API_KEY')]:
        def provider_env(case, env, provider=provider):
            env['FM_DISPATCH_PROVIDER'] = provider
            env['FM_DISPATCH_MODEL'] = 'typesafe/jev-1.13' if provider == 'openrouter' else 'gpt-6-luna'
        scenario('live-' + provider + '-availability', BASE, 'Fix the pagination bug caused by a wrong comparison.', provider_env)
finally:
    write(EVIDENCE / ('live-summary.json' if len(sys.argv) == 1 else 'live-followup-summary.json'), json.dumps([{'name': r['name'], 'exit_code': r['exit_code'], 'elapsed_seconds': r['elapsed_seconds']} for r in RESULTS], indent=2))
    shutil.rmtree(LAB)
    print('Disposable dispatch lab removed.', flush=True)
