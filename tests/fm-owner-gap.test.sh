#!/usr/bin/env bash
set -u

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

test_owner_gap_checks_registered_projects_and_open_owners() {
  local home today output
  home=$(fm_test_tmproot fm-owner-gap) || fail "fixture setup failed"
  mkdir -p "$home/data"
  fm_test_tasks_toml "$home/.tasks.toml"
  today=$(date -u +%Y-%m-%d)
  cat > "$home/data/projects.md" <<'EOF'
# Projects
- A - Project A
- Project B [direct-PR] - Project B
- C - Project C
EOF
  cat > "$home/data/backlog.md" <<EOF
## In flight

## Queued
- [ ] a1 - One (repo: A) (since $today)
- [ ] a2 - Two (repo: A) (since $today)
- [ ] b1 - One (repo: Project B) (since $today)
- [ ] b2 - Two (repo: Project B) (since $today)
- [ ] b3 - Three (repo: Project B) (since $today)
- [ ] b-owner - Owner (repo: Project B) (since 2001-01-01)
  Has context with a comma and "quotes".
  Owner of: Project B
- [ ] c1 - One (repo: C) (since $today)
- [ ] c2 - Two (repo: C) (since $today)
- [ ] c3 - Old (repo: C) (since 2001-01-01)
- [ ] u1 - One (repo: Unregistered) (since $today)
- [ ] u2 - Two (repo: Unregistered) (since $today)
- [ ] u3 - Three (repo: Unregistered) (since $today)

## Done
- [x] a3 - Three (repo: A) (since $today)
- [x] a-owner - Retired owner (repo: A) (since 2001-01-01)
  Owner of: A
EOF
  output=$(FM_HOME="$home" bash "$ROOT/bin/fm-owner-gap.sh") || fail "owner gap exited $?"
  [ "$output" = 'owner-gap A' ] || fail "unexpected owner gap report: $output"
  pass "owner gap reports active registered projects lacking an open owner"
}

command -v tasks-axi >/dev/null 2>&1 || { echo "skip: tasks-axi not found"; exit 0; }
fm_test_run test_owner_gap_checks_registered_projects_and_open_owners
