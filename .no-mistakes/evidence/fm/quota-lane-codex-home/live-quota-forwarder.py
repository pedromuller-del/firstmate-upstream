#!/usr/bin/env python3
import json, os, subprocess, sys
result = subprocess.run([os.environ['REAL_QUOTA_AXI'], *sys.argv[1:], '--no-credential-refresh'], capture_output=True)
if result.returncode == 0:
    snapshot = json.loads(result.stdout)
    projection = {key: snapshot.get(key) for key in ('generatedAt', 'schemaVersion')}
    projection['providers'] = [{key: row.get(key) for key in ('provider', 'accountKey', 'quotaSemantics')} for row in snapshot['providers']]
    with open(os.environ['QUOTA_EVIDENCE'], 'w') as output:
        json.dump(projection, output, indent=2)
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
