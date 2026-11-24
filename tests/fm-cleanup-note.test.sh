#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(realpath "$0")")")
python3 - "$root/bin/fm-cleanup-note.py" <<'PY'
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    current, baseline = Path(d)/'current', Path(d)/'last'
    old = b'- exact\n- changing: old\n- 1 orphan slots (3M)\n'
    new = b'- exact\n- changing: new\n- exact\n- 1 orphan slots (3M)\n'
    current.write_bytes(new)

    def note(day):
        return subprocess.check_output([sys.executable, sys.argv[1], current, baseline, day, '4'])

    full = note('2026-11-20')
    assert new in full and b'Full current list:' not in full
    baseline.write_bytes(old)
    delta = note('2026-11-20')
    assert b'2 rows shown; 2 unchanged rows' in delta, delta
    assert b'- changing: new\n- exact\n' in delta and b'- changing: old' not in delta, delta
    assert b'Orphan summary (unchanged): 1 orphan slots (3M)' in delta, delta
    path = Path(next(s for s in delta.decode().splitlines() if s.startswith('Full current list: ')).split(': ', 1)[1])
    assert path.read_bytes() == new
    assert baseline.read_bytes() == old and note('2026-11-20') == delta
    baseline.write_bytes(new)
    current.write_bytes(b'- exact\n')
    assert b'0 rows shown; 1 unchanged rows' in note('2026-11-21')
    assert path.read_bytes() == new
print('cleanup note: archive, retry, exact multiplicity and orphan summary passed')
PY
