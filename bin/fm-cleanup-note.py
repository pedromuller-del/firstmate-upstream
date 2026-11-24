#!/usr/bin/env python3
"""Format a Mac cleanup note: fm-cleanup-note.py REPORT LAST_FILED YYYY-MM-DD COUNT."""
import argparse
from collections import Counter
from datetime import date
from hashlib import sha256
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('last_filed', type=Path)
    parser.add_argument('day', type=date.fromisoformat)
    parser.add_argument('count', type=int)
    args = parser.parse_args()
    data = args.report.read_bytes()
    rows = data.splitlines(keepends=True)
    try:
        remaining = Counter(args.last_filed.read_bytes().splitlines(keepends=True))
    except OSError:
        remaining = Counter()

    changed, orphan_summary = [], []
    grouped = 0
    for row in rows:
        if row.startswith(b'- ') and remaining[row]:
            grouped += 1
            remaining[row] -= 1
            if b' orphan slots (' in row:
                orphan_summary.append(b'Orphan summary (unchanged): ' + row[2:])
        else:
            changed.append(row)

    full_path = args.report.parent / 'note-lists' / f'{args.day}-{sha256(data).hexdigest()}.txt'
    if grouped:
        try:
            full_path.parent.mkdir(mode=0o700, exist_ok=True)
            if not full_path.exists():
                with tempfile.NamedTemporaryFile(dir=full_path.parent, delete=False) as out:
                    staged = Path(out.name)
                    try:
                        out.write(data)
                        out.close()
                        staged.replace(full_path)
                    finally:
                        staged.unlink(missing_ok=True)
        except OSError:
            grouped, changed = 0, rows

    print(f'Fleet cleanup sweep (mac, {args.day}): {args.count} item(s) look abandoned but are not certain, so the sweep deleted none of them. Decide each; the sweep lists them again every day until they change.')
    if grouped:
        print(f'{len(changed)} rows shown; {grouped} unchanged rows grouped below.')
    sys.stdout.flush()
    sys.stdout.buffer.writelines(changed)
    if grouped:
        sys.stdout.buffer.writelines(orphan_summary)
        print(f'Full current list: {full_path}')
    print(f'Slot table: {args.report.parent / "last-table.tsv"}')


if __name__ == '__main__':
    main()
