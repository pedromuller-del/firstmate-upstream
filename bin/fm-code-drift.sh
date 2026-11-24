#!/usr/bin/env bash
# fm-code-drift.sh - count commits in HEAD missing from each supplied ref.
#
# Usage: fm-code-drift.sh <ref>...
# Run from the checkout to inspect. Prints the subjects of missing commits
# whose committer dates are more than 24 hours old. Does not fetch or write.
set -eu

usage() { sed -n '2,6s/^# \{0,1\}//p' "$0"; }
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  '') usage >&2; exit 2 ;;
esac

cutoff=$(( $(date +%s) - 86401 ))
for ref in "$@"; do
  base=$(git rev-parse --verify --quiet --end-of-options "${ref}^{commit}") || {
    printf 'fm-code-drift: cannot resolve commit ref %s\n' "$ref" >&2
    exit 2
  }
  count=$(git rev-list --count "$base..HEAD" --)
  printf 'missing-in %s: %s\n' "$ref" "$count"
  git log --no-show-signature --format=%s --before="@$cutoff" "$base..HEAD" --
done
