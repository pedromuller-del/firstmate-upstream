#!/usr/bin/env bash
# Public lab CLI regressions. Oracle: roots must exclude untrusted writers,
# sessions must never be adopted, and incomplete inventories cannot verify.
# Command stubs inject filesystem failures, not expected inventory contents.
set -eu
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=tests/lib.sh
. "$ROOT/tests/lib.sh"
TMP_ROOT=$(fm_test_tmproot fm-hc-lab-tests)
LAB=${1:-$ROOT/bin/fm-hc-lab.sh}
export FM_HC_LAB_DIR="$TMP_ROOT/lab" FM_HC_LAB_SOCK_DIR="$TMP_ROOT/sockets"
export XDG_STATE_HOME="$TMP_ROOT/state" XDG_RUNTIME_DIR="$TMP_ROOT/runtime"
mkdir -p "$TMP_ROOT/fakebin" "$XDG_STATE_HOME/herdr-core"
printf 'real state\n' > "$XDG_STATE_HOME/herdr-core/state"
export REAL_FIND REAL_CAT
REAL_FIND=$(command -v find)
REAL_CAT=$(command -v cat)
cat > "$TMP_ROOT/fakebin/hc" <<'SH'
#!/usr/bin/env bash
[ -z "${FAKE_HC_ENV_LOG:-}" ] || env >> "$FAKE_HC_ENV_LOG"
printf '{"pid":123}\n'
SH
cat > "$TMP_ROOT/fakebin/find" <<'SH'
#!/usr/bin/env bash
[ "${FAIL_READ:-}" != find ] || exit 1
if [ "${FAIL_READ:-}" = metadata ]; then
  # Simulate a file disappearing between inventory and metadata collection.
  printf '%s/missing-file\n' "$1"
  exit 0
fi
exec "$REAL_FIND" "$@"
SH
cat > "$TMP_ROOT/fakebin/cat" <<'SH'
#!/usr/bin/env bash
case "${FAIL_READ:-}:$*" in
  roots:*/fleet-roots.txt|baseline:*/fleet-state.txt) exit 1 ;;
esac
exec "$REAL_CAT" "$@"
SH
# No real Core processes exist in these tests.
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP_ROOT/fakebin/ps"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP_ROOT/fakebin/sleep"
chmod +x "$TMP_ROOT/fakebin/"*
export FM_HC_BIN="$TMP_ROOT/fakebin/hc" PATH="$TMP_ROOT/fakebin:$PATH"

refuse() {
  local diagnostic=$1
  shift
  if "$@" > "$TMP_ROOT/out" 2> "$TMP_ROOT/err"; then
    fail "unexpected success: $*"
  fi
  grep -q "$diagnostic" "$TMP_ROOT/err" || fail "missing diagnostic: $diagnostic"
}

for root in "$FM_HC_LAB_DIR" "$FM_HC_LAB_SOCK_DIR"; do
  mkdir -m 777 "$root"
  chmod 777 "$root"
  for command in provision run stop teardown; do
    refuse 'unsafe root' bash "$LAB" "$command" fm-hclab-unsafe ls
  done
  [ ! -e "$FM_HC_LAB_DIR/fm-hclab-unsafe" ] || fail 'unsafe root accepted'
  rm -rf "$root"
  mkdir -m 700 "$TMP_ROOT/redirect"
  ln -s "$TMP_ROOT/redirect" "$root"
  refuse 'unsafe root' bash "$LAB" provision fm-hclab-redirected
  [ ! -e "$TMP_ROOT/redirect/fm-hclab-redirected" ] || fail 'symlink root accepted'
  rm "$root"
  rmdir "$TMP_ROOT/redirect"
done

bash "$LAB" provision fm-hclab-good
# The filesystem's permission bits are the owned output contract here.
python3 - "$FM_HC_LAB_DIR" "$FM_HC_LAB_SOCK_DIR" <<'PY'
import os, stat, sys
for path in sys.argv[1:]:
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o700, path
PY
printf 'do not overwrite\n' > "$FM_HC_LAB_DIR/fm-hclab-good/sentinel"
refuse 'refusing to adopt or overwrite' bash "$LAB" provision fm-hclab-good
[ "$(cat "$FM_HC_LAB_DIR/fm-hclab-good/sentinel")" = 'do not overwrite' ] || fail 'existing session overwritten'

for failure in find metadata roots baseline; do
  refuse 'refusing unverified teardown' env FAIL_READ=$failure bash "$LAB" teardown fm-hclab-good
  [ -d "$FM_HC_LAB_DIR/fm-hclab-good" ] || fail 'failed verification removed evidence'
done
refuse 'could not record the fleet-state tripwire' env FAIL_READ=find bash "$LAB" provision fm-hclab-incomplete
[ ! -e "$FM_HC_LAB_DIR/fm-hclab-incomplete" ] || fail 'incomplete provision retained'
bash "$LAB" teardown fm-hclab-good
[ ! -e "$FM_HC_LAB_DIR/fm-hclab-good" ] || fail 'successful teardown retained session'
printf 'ok - private roots, exclusive sessions, and fail-closed tripwire\n'

# Every lab terminal gets the lab server's environment, so the operator's own
# terminal markers must not reach the hc call that starts the server: a harness
# hook in the lab would report to the operator's pane.
HERDR_ENV=1 HERDR_SOCKET_PATH=/operator/herdr.sock HERDR_PANE_ID=operator-pane \
  TMUX=/operator/tmux,1,0 TMUX_PANE=%1 FAKE_HC_ENV_LOG="$TMP_ROOT/hc-env" \
  bash "$LAB" provision fm-hclab-markers
grep -qx 'HC_SESSION=fm-hclab-markers' "$TMP_ROOT/hc-env" || fail 'provision made no hc call to check'
! grep -E '^(HERDR_[A-Z_]*|TMUX|TMUX_PANE)=' "$TMP_ROOT/hc-env" \
  || fail 'the lab server inherited the operator terminal markers'
bash "$LAB" teardown fm-hclab-markers
printf 'ok - the lab server never inherits the operator Herdr or tmux markers\n'

# A lab Claude can start in the root of a live Firstmate home, so the shared
# launch starts it with hooks off and refuses a Claude that cannot do that.
(
  # shellcheck source=tests/hc-test-safety.sh
  . "$ROOT/tests/hc-test-safety.sh"
  fm_backend_hc_cli() { printf '%s\n' "$@" > "$TMP_ROOT/claude-run"; printf '{"address":"lab-term"}\n'; }
  printf '#!/usr/bin/env bash\necho "Usage: claude [options] [prompt]"\n' > "$TMP_ROOT/fakebin/claude-old"
  printf '#!/usr/bin/env bash\necho "  --safe-mode   Start with all customizations disabled"\n' > "$TMP_ROOT/fakebin/claude-new"
  chmod +x "$TMP_ROOT/fakebin/claude-old" "$TMP_ROOT/fakebin/claude-new"
  HC_SESSION=fm-hclab-claude
  status=0
  hc_test_start_claude "$TMP_ROOT/fakebin/claude-old" "$TMP_ROOT" >/dev/null 2> "$TMP_ROOT/claude-refusal" || status=$?
  [ "$status" = 1 ] || fail "a Claude without --safe-mode was not refused (status $status)"
  grep -q 'does not document --safe-mode' "$TMP_ROOT/claude-refusal" || fail 'the refusal gave no reason'
  [ ! -e "$TMP_ROOT/claude-run" ] || fail 'a Claude without --safe-mode was started'
  address=$(hc_test_start_claude "$TMP_ROOT/fakebin/claude-new" "$TMP_ROOT" --label firstmate.task=t)
  [ "$address" = lab-term ] || fail "the launch printed '$address', not the terminal address"
  [ "$(tail -n 2 "$TMP_ROOT/claude-run" | tr '\n' ' ')" = "$TMP_ROOT/fakebin/claude-new --safe-mode " ] \
    || fail "the lab Claude did not start with --safe-mode: $(tr '\n' ' ' < "$TMP_ROOT/claude-run")"
)
printf 'ok - a lab Claude starts with hooks off, and one that cannot is refused\n'

# A real core rewrites terminals.json whenever one of its terminals changes its
# title or status text, so the tripwire compares that file's terminal set.
TERMS="$XDG_STATE_HOME/herdr-core/default/terminals.json"
mkdir -p "$(dirname "$TERMS")"
terms() { # <next_id> <id:title:msg>... - replaced atomically, as hc does
  local next=$1 entry id rest sep='' body=''
  shift
  for entry in "$@"; do
    id=${entry%%:*} rest=${entry#*:}
    body="$body$sep\"$id\":{\"address\":\"t$id\",\"title\":\"${rest%%:*}\",\"status\":null,\"msg\":\"${rest#*:}\"}"
    sep=,
  done
  printf '{"next_id":%s,"holder":null,"terminals":{%s}}\n' "$next" "$body" > "$TERMS.new"
  mv "$TERMS.new" "$TERMS"
}
terms 3 '1:main:idle' '2:shell:'
bash "$LAB" provision fm-hclab-text
terms 3 '1:main - reviewing PR 12:working on the review, step 4 of 9' '2:shell:'
bash "$LAB" teardown fm-hclab-text 2> "$TMP_ROOT/err" \
  || fail "a title or msg change on an existing real terminal tripped the tripwire: $(cat "$TMP_ROOT/err")"
printf 'ok - title or msg text changing on an existing real terminal passes the tripwire\n'
for change in added removed replaced recreated; do
  terms 3 '1:main:idle' '2:shell:'
  bash "$LAB" provision "fm-hclab-$change"
  case "$change" in
    added) terms 4 '1:main:idle' '2:shell:' '3:lab:' ;;
    removed) terms 3 '1:main:idle' ;;
    replaced) terms 3 '1:main:idle' '3:lab:' ;; # only the ids differ
    recreated) terms 4 '1:main:idle' '2:shell:' ;;
  esac
  refuse 'FLEET-STATE TRIPWIRE FAILED' bash "$LAB" teardown "fm-hclab-$change"
  terms 3 '1:main:idle' '2:shell:'
  bash "$LAB" teardown "fm-hclab-$change"
done
printf 'ok - a real terminal added, removed, replaced, or created and removed fails the tripwire\n'
