#!/usr/bin/env bash
set -eu

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
fm_git_identity fmtest fmtest@example.invalid

test_drift_reports_all_missing_and_lists_aged_subjects() {
  local repo out
  repo=$(fm_test_tmproot fm-code-drift)
  git -C "$repo" init -q
  git -C "$repo" commit -qm base --allow-empty
  git -C "$repo" branch behind
  GIT_COMMITTER_DATE=2001-01-01T00:00:00Z git -C "$repo" commit -qm 'Older fix' --allow-empty
  git -C "$repo" commit -qm 'Fresh fix' --allow-empty
  out=$(cd "$repo" && bash "$ROOT/bin/fm-code-drift.sh" behind HEAD) \
    || fail "code drift exited $?"
  [ "$out" = $'missing-in behind: 2\nOlder fix\nmissing-in HEAD: 0' ] \
    || fail "unexpected code drift report: $out"
  if (cd "$repo" && bash "$ROOT/bin/fm-code-drift.sh" no-such-ref) >/dev/null 2>&1; then
    fail "code drift accepted an unknown ref"
  fi
  pass "code drift counts all missing commits and names only old subjects"
}

fm_test_run test_drift_reports_all_missing_and_lists_aged_subjects
