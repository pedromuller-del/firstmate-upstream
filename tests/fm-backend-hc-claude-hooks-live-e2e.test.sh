#!/usr/bin/env bash
# tests/fm-backend-hc-claude-hooks-live-e2e.test.sh - default-on proof that a
# real Claude started by the hc live guard never runs the hooks of the
# Firstmate home it starts in.
#
# tests/fm-backend-hc-liveness-live-e2e.test.sh starts Claude in its own repo
# root, which can be a live primary home whose SessionStart hook would run a
# session start for that home. The scratch home here is one the hook treats as
# a primary root: this tree's tracked files, a secondmate-home marker
# (bin/fm-primary-scope-lib.sh force-includes it, the same gate a primary git
# checkout passes), and a seeded state/. Its state/ must keep the same digest -
# no lock, no wake drain, no status write - through two runs:
# - hc_test_start_claude, the guard's launch, held through the hook window,
#   because the guard reads and stops its Claude within seconds, before a hook
#   would write;
# - the scratch home's copy of the guard itself, with a recording `claude`
#   first on PATH, which must show that every Claude it started had
#   --safe-mode.
# Claude keys workspace trust to a git checkout's top level, so a git primary
# root here would need a new trust entry in the operator's Claude account; this
# folder is trusted the same way the control is, with no account write.
#
# A control project whose own SessionStart hook writes a marker first proves
# that a plain Claude in the same parent folder runs project hooks, so the
# proof cannot pass only because this machine never loads them there. Every
# Claude starts with no prompt, so this consumes no model tokens.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tests/lib.sh
. "$ROOT/tests/lib.sh"

HC_BIN=${FM_HC_BIN:-}
[ -n "$HC_BIN" ] || HC_BIN=$(command -v herdr-core 2>/dev/null || true)
[ -n "$HC_BIN" ] || HC_BIN=$(command -v hc 2>/dev/null || true)
HC_TOOL=hc
if [ -n "$HC_BIN" ] && [ -x "$HC_BIN" ]; then
  export FM_HC_BIN=$HC_BIN
  PATH="$(dirname "$HC_BIN"):$PATH"
  HC_TOOL=$(basename "$HC_BIN")
fi
fm_live_gate default-on FM_HC_CLAUDE_HOOKS "$HC_TOOL" claude jq git python3

# shellcheck source=tests/hc-test-safety.sh
. "$ROOT/tests/hc-test-safety.sh"

TMP_ROOT=$(fm_test_tmproot fm-hc-claude-hooks)
HC_TEST_SES=''
cleanup_lab() {
  local rc=$?
  trap - EXIT
  [ -z "$HC_TEST_SES" ] || hc_test_safe_teardown "$ROOT" "$HC_TEST_SES" || rc=1
  fm_test_cleanup
  exit "$rc"
}
trap cleanup_lab EXIT

state_digest() {  # <dir>
  python3 - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
for d, dirs, files in os.walk(root):
    dirs.sort()
    print("dir", os.path.relpath(d, root))
    for name in sorted(files):
        path = os.path.join(d, name)
        st = os.lstat(path)
        body = "-"
        if os.path.isfile(path) and not os.path.islink(path):
            with open(path, "rb") as f:
                body = hashlib.sha256(f.read()).hexdigest()
        print("file", os.path.relpath(path, root), st.st_size, st.st_mtime_ns, body)
PY
}

# Scratch folders: a control project whose SessionStart hook writes a marker,
# and a primary-scope home.
CONTROL=$TMP_ROOT/control
mkdir -p "$CONTROL/.claude"
cat > "$CONTROL/.claude/settings.json" <<'JSON'
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "touch \"$CLAUDE_PROJECT_DIR/hook-ran\""}]}]}}
JSON
HOME_ROOT=$TMP_ROOT/home
mkdir -p "$HOME_ROOT"
(cd "$ROOT" && git ls-files -z) | (cd "$ROOT" && tar --null -T - -cf -) | (cd "$HOME_ROOT" && tar -xf -) \
  || fail "could not copy the tracked tree into the scratch home"
printf 'hc-claude-hooks\n' > "$HOME_ROOT/.fm-secondmate-home"
mkdir -p "$HOME_ROOT/state"
printf 'working [at=1]: seeded\n' > "$HOME_ROOT/state/seeded.status"

unset FM_HOME FM_ROOT_OVERRIDE FM_STATE_OVERRIDE
HC_TEST_SES=$("$ROOT/bin/fm-hc-lab.sh" name claudehooks)
"$ROOT/bin/fm-hc-lab.sh" provision "$HC_TEST_SES" || fail "hc lab could not provision with ${HC_BIN:-no binary}"
hc_test_refuse_if_unsafe "$HC_TEST_SES" || fail "provisioned session '$HC_TEST_SES' does not satisfy the lab safety contract"
HC_LAB_DIR=$(hc_test_lab_dir)/$HC_TEST_SES
export HC_SESSION=$HC_TEST_SES FM_HC_SOCKET
FM_HC_SOCKET=$("$ROOT/bin/fm-hc-lab.sh" socket "$HC_TEST_SES")
export XDG_STATE_HOME="$HC_LAB_DIR/env/xdg-state" XDG_CONFIG_HOME="$HC_LAB_DIR/env/xdg-config" \
  XDG_DATA_HOME="$HC_LAB_DIR/env/xdg-data"
unset HC_TERMINAL_ID HC_TERMINAL_SOCKET HC_SCOPE HC_SOCKET
# shellcheck source=/dev/null
. "$ROOT/bin/fm-backend.sh"
fm_backend_source hc || fail "fm_backend_source hc failed"
CLAUDE_BIN=$(command -v claude)

# 1. A plain Claude in this parent folder runs its project's SessionStart hook.
address=$(fm_backend_hc_cli "$HC_SESSION" run --bg --json --no-parent --outlive-parent --no-notify \
  --cwd "$CONTROL" "$CLAUDE_BIN" | jq -r '.address // empty')
fm_backend_hc_address_valid "$address" || fail "the control Claude did not start in the hc lab"
for _ in $(seq 1 30); do
  [ -e "$CONTROL/hook-ran" ] && break
  sleep 1
done
fm_backend_kill hc "$HC_SESSION:$address" >/dev/null 2>&1 || true
if [ ! -e "$CONTROL/hook-ran" ]; then
  printf 'skip: live: a plain claude in %s ran no project hook (the folder is not trusted here), so this machine cannot prove the launch keeps them off\n' "$CONTROL"
  exit 0
fi
pass "control: a plain Claude in the scratch parent folder runs its project's SessionStart hook"

# 2. The guard's launch, held in the scratch home through the hook window
# (a plain Claude's hook writes there within 5 seconds and is done within 15),
# leaves its state/ alone.
before=$(state_digest "$HOME_ROOT/state")
address=$(hc_test_start_claude "$CLAUDE_BIN" "$HOME_ROOT") \
  || fail "CLAUDE HOOKS: the hooks-off lab launch did not start Claude in the scratch home"
fm_backend_hc_address_valid "$address" || fail "the guard's launch did not start Claude in the scratch home"
composer=
for _ in $(seq 1 30); do
  composer=$(fm_backend_hc_composer_state "$HC_SESSION:$address")
  [ "$composer" = empty ] && break
  sleep 1
done
[ "$composer" = empty ] || fail "Claude never reached an empty composer in the scratch home (it reads '$composer'), so the hook window was not exercised"
sleep 20
after=$(state_digest "$HOME_ROOT/state")
fm_backend_kill hc "$HC_SESSION:$address" >/dev/null 2>&1 || true
[ "$before" = "$after" ] || fail "LIVE HOME HOOKS: the guard's lab Claude changed the state/ of the Firstmate home it started in: $(diff <(printf '%s\n' "$before") <(printf '%s\n' "$after"))"
pass "a Claude started by the hc live guard's launch in a primary-scope home leaves that home's state/ unchanged"

# 3. The scratch home's copy of the guard starts every Claude with hooks off.
SHIM=$TMP_ROOT/shim
mkdir -p "$SHIM"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >> %q\nexec %q "$@"\n' \
  "$TMP_ROOT/claude-calls" "$CLAUDE_BIN" > "$SHIM/claude"
chmod +x "$SHIM/claude"
# The guard puts its hc binary's folder first on PATH, so hc is linked here too.
ln -s "$HC_BIN" "$SHIM/$HC_TOOL"
out=$(PATH="$SHIM:$PATH" FM_HC_BIN="$SHIM/$HC_TOOL" FM_HC_LIVENESS_DRIFT=1 \
  bash "$HOME_ROOT/tests/fm-backend-hc-liveness-live-e2e.test.sh" 2>&1)
status=$?
after=$(state_digest "$HOME_ROOT/state")
launches=0
while IFS= read -r args; do
  case "$args" in --help | --version) continue ;; esac
  case " $args " in
    *' --safe-mode '*) launches=$((launches + 1)) ;;
    *) fail "LIVE HOME HOOKS: the guard started Claude without --safe-mode (arguments: '$args')" ;;
  esac
done < "$TMP_ROOT/claude-calls"
assert_contains "$out" "ok - hc composer: idle claude" "the guard did not start and read a Claude from the scratch home (rc $status)"
[ "$status" -eq 0 ] || fail "the guard failed from the scratch home (rc $status): $out"
[ "$launches" -ge 2 ] || fail "the guard started $launches Claude terminals with --safe-mode, not its liveness and composer pair"
[ "$before" = "$after" ] || fail "LIVE HOME HOOKS: the guard changed the state/ of the Firstmate home it ran from: $(diff <(printf '%s\n' "$before") <(printf '%s\n' "$after"))"
pass "the hc live guard, run from a primary-scope home, starts every Claude with --safe-mode and leaves that home's state/ unchanged"
echo FM_TEST_COMPLETE
