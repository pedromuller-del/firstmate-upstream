import json
import os
from pathlib import Path
import shutil
import subprocess
import time

root = Path.cwd()
lab = root / '.dispatch-live-lab'
evidence = Path(__file__).parent / 'round2'
evidence.mkdir(exist_ok=True)
for name in ['pi', 'quota-axi']:
    (lab / 'bin' / name).chmod(0o700)
for name in ['pi-pinned', 'pi-ambient']:
    (lab / name).mkdir(exist_ok=True)

def write_input(path, value):
    old = path.read_text() if path.exists() else None
    body = value if isinstance(value, str) else json.dumps(value, indent=2) + '\n'
    patch = '*** Begin Patch\n'
    if old is None:
        patch += f'*** Add File: {path}\n'
    else:
        patch += f'*** Update File: {path}\n@@\n' + ''.join('-' + line + '\n' for line in old.splitlines())
    patch += ''.join('+' + line + '\n' for line in body.splitlines()) + '*** End Patch\n'
    subprocess.run(['apply_patch', patch], check=True, stdout=subprocess.DEVNULL)

env = {k: v for k,v in os.environ.items() if k in ['PATH', 'TYPESAFE_API_KEY', 'USER', 'LOGNAME']}
env.update(HOME=str(lab / 'home'), FM_HOME=str(lab / 'home'),
           TMPDIR=str(lab / 'tmp'), LC_ALL='C', LANG='C',
           XDG_CONFIG_HOME=str(lab / 'xdg-config'), XDG_CACHE_HOME=str(lab / 'xdg-cache'),
           PI_CODING_AGENT_DIR=str(lab / 'pi-ambient'),
           LAB_REAL_PI=shutil.which('pi'), LAB_REAL_QUOTA=shutil.which('quota-axi'),
           LAB_REAL_JQ=shutil.which('jq'), LAB_PRIVACY_TRACE=str(evidence / 'live-private-filter.jsonl'),
           LAB_TRACE=str(evidence / 'live-pi-trace.jsonl'),
           FM_DISPATCH_PROVIDER='typesafe', FM_DISPATCH_MODEL='jev-latest')
env['PATH'] = str(lab / 'bin') + ':' + env['PATH']
freeze = os.environ.get('LAB_FREEZE_PROVIDER')
if freeze:
    env['LAB_FREEZE_PROVIDER'] = freeze
    env['LAB_TRACE'] = str(evidence / 'live-pi-timeout-trace.jsonl')
write_input(lab / 'home/config/pi-account', str(lab / 'pi-pinned') + '\nopenai-codex anthropic\n')
rules = {'rules': [
    {'when': 'A software bug fix.', 'use': [
        {'harness': 'pi', 'model': 'openai-codex/gpt-5.6-sol', 'provider': 'codex'},
        {'harness': 'pi', 'model': 'openai-codex/gpt-5.6-terra', 'provider': 'codex'}]},
    {'when': 'A retired software rule.', 'until': '2000-01-01T00:00:00Z',
     'use': {'harness': 'pi', 'model': 'expired-provider/model', 'provider': 'codex'}}],
    'default': [{'harness': 'pi', 'model': 'anthropic/claude-sonnet-5', 'provider': 'claude'}]}
write_input(lab / 'home/config/crew-dispatch.json', rules)
write_input(lab / 'brief.md', 'Fix a software bug caused by an off-by-one comparison.\n')
command = ['bash', 'bin/fm-dispatch-resolve.sh', str(lab / 'brief.md')]
start = time.monotonic()
result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=65)
duration = round(time.monotonic()-start, 3)
print(result.stdout + result.stderr, flush=True)
trace = [json.loads(line) for line in Path(env['LAB_TRACE']).read_text().splitlines()] if Path(env['LAB_TRACE']).exists() else []
probe_env = env | {'PI_CODING_AGENT_DIR': str(lab / 'pi-pinned')}
probe = subprocess.run([env['LAB_REAL_PI'], 'auth', 'check', '--provider', 'openai-codex', '--json'],
                       env=probe_env, text=True, capture_output=True, timeout=15)
quota = subprocess.run([env['LAB_REAL_QUOTA'], '--json', '--max-age', '2m', '--provider', 'zai', '--no-credential-refresh'],
                       env=env, text=True, capture_output=True, timeout=30)
record = {'command': command, 'exit_code': result.returncode, 'elapsed_seconds': duration,
          'output': result.stdout + result.stderr, 'trace': trace,
          'probe_exit_code': probe.returncode, 'probe_output': probe.stdout + probe.stderr,
          'quota_exit_code': quota.returncode, 'quota_output': quota.stdout + quota.stderr,
          'isolation': 'Real Pi and quota-axi executables. Empty Pi account roots. quota-axi limited to the unconfigured zai provider, with credential refresh disabled. No fake responses.'}
(evidence / ('live-pi-timeout.json' if freeze else 'live-pi.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
