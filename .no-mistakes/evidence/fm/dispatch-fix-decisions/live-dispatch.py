import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

root = Path.cwd()
evidence = Path(__file__).parent / 'round2'
evidence.mkdir(exist_ok=True)
lab = root / '.dispatch-live-lab'
for part in ['home/config', 'tmp', 'pi-empty', 'xdg-config', 'xdg-cache', 'bin']:
    (lab / part).mkdir(parents=True, exist_ok=True)
env = {key: value for key, value in os.environ.items()
       if key in ['PATH', 'TYPESAFE_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'USER', 'LOGNAME']}
env.update(HOME=str(lab / 'home'), FM_HOME=str(lab / 'home'),
           TMPDIR=str(lab / 'tmp'), LC_ALL='C', LANG='C',
           XDG_CONFIG_HOME=str(lab / 'xdg-config'), XDG_CACHE_HOME=str(lab / 'xdg-cache'),
           PI_CODING_AGENT_DIR=str(lab / 'pi-empty'),
           FM_DISPATCH_PROVIDER='typesafe', FM_DISPATCH_MODEL='jev-latest')

def write_input(path, value):
    old = path.read_text() if path.exists() else None
    body = value if isinstance(value, str) else json.dumps(value, indent=2) + '\n'
    if old == body:
        return
    patch = '*** Begin Patch\n'
    if old is None:
        patch += f'*** Add File: {path}\n' + ''.join('+' + line + '\n' for line in body.splitlines())
    else:
        patch += f'*** Update File: {path}\n@@\n'
        patch += ''.join('-' + line + '\n' for line in old.splitlines())
        patch += ''.join('+' + line + '\n' for line in body.splitlines())
    patch += '*** End Patch\n'
    subprocess.run(['apply_patch', patch], check=True, stdout=subprocess.DEVNULL)

profiles = [
    {'harness': 'claude', 'model': 'opus', 'effort': 'xhigh'},
    {'harness': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'high'},
    {'harness': 'cursor', 'model': 'cursor-grok-4.6-medium'},
    {'harness': 'claude', 'model': 'sonnet', 'effort': 'low'},
    {'harness': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'xhigh'},
]
conditions = [
    'Work the brief itself calls unusually difficult or high-risk, such as a security-sensitive redesign or a migration where a mistake is costly; routine builds, ports, and installers do not qualify.',
    'Routine feature work, a port, or an installer build inside an existing codebase.',
    'A bug fix whose root cause the brief states.',
    'A trivial mechanical edit such as a rename, typo, version bump, or wording fix.',
    'A read-only investigation, diagnosis, or audit whose deliverable is a written report, not a code change.',
]
base = {'shared_quota': True,
        'rules': [{'when': c, 'use': p} for c, p in zip(conditions, profiles)],
        'default': {'harness': 'codex', 'model': 'gpt-5.6-sol', 'effort': 'low'}}
base['rules'][0]['approval'] = 'captain'
records = []

def run(name, rules, brief, expected, extra=None):
    write_input(lab / 'home/config/crew-dispatch.json', rules)
    write_input(lab / 'brief.md', '## Captain\'s intent\n' + brief + '\n')
    command = ['bash', 'bin/fm-dispatch-resolve.sh', str(lab / 'brief.md'), '--project', 'dispatch-validation']
    start = time.monotonic()
    result = subprocess.run(command, env=env | (extra or {}), text=True, capture_output=True, timeout=65)
    elapsed = round(time.monotonic() - start, 3)
    text = result.stdout + result.stderr
    passed = expected(result.returncode, text)
    record = {'name': name, 'command': command, 'exit_code': result.returncode,
              'elapsed_seconds': elapsed, 'passed': passed, 'output': text,
              'rules': rules, 'brief': brief,
              'remaining_temporary_files': [p.name for p in (lab / 'tmp').iterdir()]}
    records.append(record)
    (evidence / f'live-{name}.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'{name}: exit={result.returncode} expected={passed}\n{text}', flush=True)
    return record

bug = 'Fix the pagination bug: the last page repeats an item because orders_query.go uses <= instead of <. Change that comparison only.'
run('clear-profile', base, bug, lambda c,t: c == 0 and 'status: clear' in t and "--harness 'cursor'" in t)
run('captain-approval', base, 'Redesign the authentication system. This is unusually difficult and security-sensitive; a mistake exposes all accounts.', lambda c,t: c == 0 and 'status: escalate' in t and 'explicit approval' in t and 'profile:' not in t)
run('low-confidence', base, 'Split a large service file into smaller modules without changing its behavior. Some boundaries are unclear; identify them while moving the code.', lambda c,t: c == 0 and 'status: clear' in t and 'low confidence:' in t)
floor_rules = copy.deepcopy(base)
for rule in floor_rules['rules']:
    rule['min_confidence'] = 1
run('declared-floor', floor_rules, 'Split a large service file into smaller modules without changing behavior. Infer boundaries during the work.', lambda c,t: c == 0 and 'status: ambiguous' in t and 'below its floor' in t and 'profile:' not in t)
expiry = copy.deepcopy(base)
expiry['rules'][2]['until'] = '2000-01-01T00:00:00Z'
run('expired-rule', expiry, bug, lambda c,t: c == 0 and 'status: clear' in t and "--harness 'cursor'" not in t and 'rule_5=' not in t)
future = copy.deepcopy(base)
future['rules'][2]['until'] = '2400-02-29T23:59:59Z'
run('future-leap-day', future, bug, lambda c,t: c == 0 and 'status: clear' in t and "--harness 'cursor'" in t)
expired = copy.deepcopy(base)
for rule in expired['rules']:
    rule['until'] = '2000-01-01T00:00:00Z'
run('all-expired', expired, bug, lambda c,t: c == 0 and 'no rules to match' in t and 'profile:' not in t)
for index, until in enumerate(['soon', 42, '2999-13-40T25:61:61Z', '2999-02-29T00:00:00Z', '2000-13-01T00:00:00Z', '2999-01-01T24:00:00Z', '2999-01-01T00:00:60Z']):
    invalid = copy.deepcopy(base)
    invalid['rules'][0]['until'] = until
    run(f'invalid-until-{index}', invalid, bug, lambda c,t: c == 2 and 'malformed rules file' in t and 'profile:' not in t)
ties = copy.deepcopy(base)
ties['rules'] = [{'when': 'The task changes software code.', 'use': p} for p in profiles[:2]]
run('tie-attempt', ties, 'Change software code.', lambda c,t: c == 0 and 'top-probability tie' in t and 'profile:' not in t)
for provider, model in [('openrouter', 'typesafe/jev-1.13'), ('openai', 'gpt-6-luna')]:
    run(f'{provider}-availability', base, bug, lambda c,t: c == 0 and 'status: clear' in t,
        {'FM_DISPATCH_PROVIDER': provider, 'FM_DISPATCH_MODEL': model})
(evidence / 'live-results.json').write_text(json.dumps(records, indent=2) + '\n')
