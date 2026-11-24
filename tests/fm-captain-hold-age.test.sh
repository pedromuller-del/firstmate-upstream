#!/usr/bin/env bash
set -u

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

test_age_reports_open_holds() {
  local home output stamp
  home=$(fm_test_tmproot fm-captain-hold-age) || { fail "fixture setup failed"; return; }
  mkdir -p "$home/data"
  fm_test_tasks_toml "$home/.tasks.toml"
  cat > "$home/data/backlog.md" <<'EOF'
## In flight

## Queued

- [ ] two-days - Two days (repo: example) (hold: choose) (hold-kind: captain)
  Captain hold set: 2026-11-21T12:00:00Z

- [ ] eight-days - Eight days (repo: example) (hold: choose) (hold-kind: captain) (hold-until: 2026-11-30)
  Captain hold set: 2026-11-15T12:00:00Z

- [ ] fifteen-days - Fifteen days (repo: example) (hold: choose) (hold-kind: captain)
  Captain hold set: 2026-11-08T12:00:00Z

## Done

- [x] closed - Closed (repo: example) (hold: choose) (hold-kind: captain)
  Captain hold set: 2026-11-01T12:00:00Z
EOF
  stamp=$(cksum < "$home/data/backlog.md")
  output=$(FM_HOME="$home" FM_CAPTAIN_HOLD_NOW=2026-11-23T12:00:00Z bash "$ROOT/bin/fm-captain-hold.sh" age) || {
    fail "age exited $?"
    return
  }
  [ "$(printf '%s\n' "$output" | sed '$d' | LC_ALL=C sort)" = "$(printf '%s\t%s\t%s\t%s\n' \
    eight-days 2026-11-15T12:00:00Z 8 2026-11-30 \
    fifteen-days 2026-11-08T12:00:00Z 15 - \
    two-days 2026-11-21T12:00:00Z 2 -)" ] || { fail "unexpected age rows: $output"; return; }
  [ "${output##*$'\n'}" = 'open=3 older7=2 older14=1' ] || { fail "unexpected age totals: $output"; return; }
  [ "$(cksum < "$home/data/backlog.md")" = "$stamp" ] || { fail "age changed the backlog"; return; }
  pass "age lists open captain holds, dates and totals without changing the backlog"
}

command -v tasks-axi >/dev/null 2>&1 || { echo "skip: tasks-axi not found"; exit 0; }
fm_test_run test_age_reports_open_holds
