#!/usr/bin/env bash
# Exercise remote hc control with real metadata and a private fake CLI.
set -eu
# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
TMP=$(fm_test_tmproot fm-remote-hc)
CODE="$TMP/code"
CHILD="$TMP/child"
mkdir -p "$CODE" "$CHILD/bin" "$CHILD/state/parent-route" "$CHILD/config" "$TMP/account"
cp -R "$ROOT/bin" "$CODE/bin"
touch "$CHILD/AGENTS.md"
printf 'mate\n' > "$CHILD/.fm-secondmate-home"
export HC_TEST_LOG="$TMP/calls" HC_TEST_STATE="$TMP/state"
printf 'alive\n' > "$HC_TEST_STATE"
cat > "$TMP/hc" <<'SH'
#!/usr/bin/env bash
set -eu
printf '%s|%s|%s\n' "${HC_SESSION:-}" "${HC_SOCKET:-}" "$*" >> "$HC_TEST_LOG"
case "$1" in
  --version) echo 'hc 0.1.14' ;;
  get)
    case "$(cat "$HC_TEST_STATE")" in missing) exit 3 ;; unreadable) exit 1 ;; esac
    tag=$HC_TEST_HOME_TAG st=live
    [ "$(cat "$HC_TEST_STATE")" != foreign ] || tag=foreign
    [ "$(cat "$HC_TEST_STATE")" != finished ] || st=finished
    jq -n --arg home "$tag" --arg st "$st" '{state:$st,labels:{"firstmate.task":"fm-mate","firstmate.home":$home},foreground:{name:"codex",argv0:"codex",args:"codex",pid:99999999},status:{state:"idle"}}'
    ;;
  read) echo 'fixture capture' ;;
  send|keys) echo '{}' ;;
  rm) printf 'missing\n' > "$HC_TEST_STATE"; echo '{}' ;;
  *) exit 88 ;;
esac
SH
chmod +x "$TMP/hc"
export FM_ROOT="$CODE" FM_HOME="$CHILD"
# shellcheck source=bin/fm-backend-hometag-lib.sh
. "$ROOT/bin/fm-backend-hometag-lib.sh"
export HC_TEST_HOME_TAG
HC_TEST_HOME_TAG=$(FM_HOME="$CODE" fm_backend_hometag)
write_meta() {
  fm_write_meta "$CHILD/state/parent-route/mate.meta" "backend=hc" "window=${1:-fm-remote}:t7" \
    "worktree=$CHILD" "project=$CODE" 'endpoint_task_id=mate' "hc_session=${1:-fm-remote}" 'hc_terminal=t7' 'harness=codex' 'kind=secondmate'
}
run_control() {
  env HOME="$TMP/account" FM_HOME="$CHILD" FM_ROOT_OVERRIDE="$CODE" FM_HC_BIN="${HC_TEST_BIN:-$TMP/hc}" \
    HC_SESSION=foreign HC_SOCKET=/foreign FM_HC_SOCKET=/foreign \
    "$CODE/bin/fm-remote-secondmate-control.sh" "$@"
}
for configured in hc herdr; do
  printf '%s\n' "$configured" > "$CHILD/config/backend"
  if run_control validate-backend mate rex > "$TMP/rex-conflict" 2>&1; then
    fail "direct Rex validation accepted config/backend=$configured"
  fi
  assert_grep 'refusing runtime change' "$TMP/rex-conflict" 'direct conflict must name the selection'

done
printf 'hc\n' > "$CHILD/config/backend"
if FM_BACKEND=rex run_control validate-backend mate rex > "$TMP/rex-conflict" 2>&1; then
  fail 'matching environment must not hide conflicting child configuration'
fi
assert_grep 'backend selects hc' "$TMP/rex-conflict" 'configuration must be checked independently'
printf 'rex\n' > "$CHILD/config/backend"
for selected in hc herdr; do
  if FM_BACKEND=$selected run_control validate-backend mate rex > "$TMP/rex-conflict" 2>&1; then
    fail 'direct Rex validation accepted managed environment'
  fi
  assert_grep 'FM_BACKEND' "$TMP/rex-conflict" 'environment conflict must name its source'
done
for configured in rex tmux; do
  printf '%s\n' "$configured" > "$CHILD/config/backend"
  FM_BACKEND=$configured run_control validate-backend mate rex
done
assert_absent "$CHILD/state/fleet-backend" 'legacy Rex validation must not create a managed pin'
assert_absent "$HC_TEST_LOG" 'Rex validation must not contact hc'
pass 'direct Rex selection refuses conflicting child configuration'

printf 'rex\n' > "$CHILD/config/backend"
if run_control validate-backend mate hc > "$TMP/preflight" 2>&1; then fail 'pre-inheritance conflict must refuse'; fi
assert_absent "$CHILD/state/fleet-backend" 'refused validation must not pin child'
assert_absent "$HC_TEST_LOG" 'validation must never contact hc'
rm "$CHILD/config/backend"
run_control validate-backend mate hc
assert_grep 'hc' "$CHILD/state/fleet-backend" 'preflight must bind child runtime'
assert_absent "$HC_TEST_LOG" 'binding must not contact hc'
if run_control validate-backend mate herdr >/dev/null 2>&1; then fail 'child binding must refuse migration'; fi
pass 'pre-inheritance validation binds the child without contacting a runtime'

[ -z "$(run_control validate-backend mate hc)" ] || fail 'an existing child pin must not be reported as new'
run_control release-backend mate hc
assert_absent "$CHILD/state/fleet-backend" 'release must remove the pin of an aborted creation'
[ "$(run_control validate-backend mate hc)" = fleet_pin=new ] || fail 'a new child pin must be reported to the creating parent'
write_meta
if run_control release-backend mate hc > "$TMP/release" 2>&1; then fail 'release must refuse while an endpoint record exists'; fi
assert_grep 'keeping its fleet runtime' "$TMP/release" 'refused release must say why'
assert_grep 'hc' "$CHILD/state/fleet-backend" 'refused release removed the pin'
rm "$CHILD/state/parent-route/mate.meta"
pass 'validate-backend reports a new child pin, and release-backend removes it only before any endpoint record'

write_meta
OUT=$(run_control route mate)
assert_contains "$OUT" 'hc_session=fm-remote' 'route must publish recorded hc session'
assert_contains "$OUT" 'hc_terminal=t7' 'route must publish recorded hc terminal'
[ "$(run_control state mate)" = alive ] || fail 'hc endpoint must be classified alive'
assert_contains "$(run_control capture mate)" 'fixture capture' 'capture must use recorded endpoint'
[ "$(run_control observe mate)" = idle ] || fail 'observation must use recorded hc terminal'
assert_no_grep '/foreign' "$HC_TEST_LOG" 'ambient socket must never redirect remote control'
assert_grep 'fm-remote|' "$HC_TEST_LOG" 'control must use dedicated remote session'
pass 'hc route, state and capture use the recorded dedicated session'

run_control send mate 'harmless durable steer' fire-and-forget
[ -n "$(find "$CHILD/state/parent-route/mate.inbox" -type f -print)" ] || fail 'send must persist inbox record'
assert_grep '|send ' "$HC_TEST_LOG" 'send must ring the hc endpoint'
pass 'hc send persists the existing steering inbox'

printf 'foreign\n' > "$HC_TEST_STATE"
[ "$(run_control state mate)" = unverified ] || fail 'foreign labels must not authorize endpoint reuse'
printf 'unreadable\n' > "$HC_TEST_STATE"
[ "$(run_control state mate)" = unreadable ] || fail 'unreadable core must not become missing'
if run_control launch mate codex - - hc > "$TMP/refused" 2>&1; then fail 'unreadable endpoint must refuse duplicate launch'; fi
assert_grep 'refusing duplicate launch' "$TMP/refused" 'launch must preserve uncertain endpoint'
write_meta default
[ "$(run_control state mate 2>/dev/null)" = unverified ] || fail 'wrong session must be unverified'
if run_control capture mate >/dev/null 2>&1; then fail 'wrong session capture must refuse'; fi
pass 'unreadable and foreign-session endpoints refuse unsafe recovery'

git -C "$CHILD" init -q
write_meta
cp "$CHILD/state/parent-route/mate.meta" "$TMP/prior.meta"
printf 'missing\n' > "$HC_TEST_STATE"
if run_control relaunch mate codex - - > "$TMP/missing-relaunch" 2>&1; then
  fail 'real secondmate relaunch must not replace a missing terminal'
fi
assert_grep 'recovery is owned by the secondmate respawn path' "$TMP/missing-relaunch" 'missing secondmate must use its recovery owner'
cmp -s "$TMP/prior.meta" "$CHILD/state/parent-route/mate.meta" || fail 'refused relaunch changed the endpoint record'
printf 'alive\n' > "$HC_TEST_STATE"
pass 'real relaunch refuses a missing secondmate terminal without rebinding'

# The host-local spawn and relaunch are separate owners. Pin their boundary
# environment without starting a harness or any real terminal.
cat > "$CODE/bin/fm-spawn.sh" <<'SH'
#!/usr/bin/env bash
set -eu
[ "$HC_SESSION" = fm-remote ] && [ -z "${FM_HC_SOCKET:-}${HC_SOCKET:-}" ]
cat > "$FM_STATE_OVERRIDE/mate.meta" <<META
worktree=$FM_HOME
project=$FM_ROOT_OVERRIDE
backend=hc
window=fm-remote:t8
endpoint_task_id=mate
hc_session=fm-remote
hc_terminal=t8
harness=codex
kind=secondmate
META
SH
cat > "$CODE/bin/fm-control.sh" <<'SH'
#!/usr/bin/env bash
set -eu
[ "$HC_SESSION" = fm-remote ] && [ -z "${FM_HC_SOCKET:-}${HC_SOCKET:-}" ]
[ -f "$FM_STATE_OVERRIDE/mate.meta" ]
SH
chmod +x "$CODE/bin/fm-spawn.sh" "$CODE/bin/fm-control.sh"
write_meta
printf 'herdr\n' > "$CHILD/state/fleet-backend"
if run_control launch mate codex - - hc > "$TMP/conflict" 2>&1; then fail 'conflicting home runtime must refuse'; fi
assert_grep 'refusing endpoint runtime' "$TMP/conflict" 'conflict must name selected fleet runtime'
printf 'hc\n' > "$CHILD/state/fleet-backend"
rm "$CHILD/state/parent-route/mate.meta"
assert_contains "$(run_control launch mate codex - - hc)" 'hc_terminal=t8' 'launch must return published endpoint'
write_meta
assert_contains "$(run_control relaunch mate codex - -)" 'hc_terminal=t7' 'relaunch must preserve the terminal endpoint'
printf 'missing\n' > "$HC_TEST_STATE"
assert_contains "$(run_control launch mate codex - - hc)" 'hc_terminal=t8' 'missing endpoint must return replacement identity'
if HC_TEST_BIN=/nonexistent run_control launch mate codex - - hc > "$TMP/no-hc" 2>&1; then fail 'missing hc must refuse launch'; fi
assert_grep 'selected remote backend hc is unavailable' "$TMP/no-hc" 'missing selected hc must not fall back'
write_meta
printf 'finished\n' > "$HC_TEST_STATE"
[ "$(run_control state mate)" = dead ] || fail 'a finished hc terminal must read dead, not missing'
assert_contains "$(run_control launch mate codex - - hc)" 'hc_terminal=t8' 'finished endpoint must return replacement identity'
assert_grep 'rm --json t7' "$HC_TEST_LOG" 'launch must remove the finished terminal before replacing it'
pass 'launch and relaunch pin hc routing and return current endpoint identity'

rm "$CHILD/state/fleet-backend"
printf 'tmux\n' > "$CHILD/config/backend"
write_meta
printf 'alive\n' > "$HC_TEST_STATE"
run_control launch mate codex - - hc >/dev/null
assert_absent "$CHILD/state/fleet-backend" 'legacy launch must not bind the child'
run_control relaunch mate codex - - >/dev/null
assert_absent "$CHILD/state/fleet-backend" 'legacy relaunch must not bind the child'
pass 'legacy launch and relaunch preserve an unbound home despite inherited tmux configuration'

# Exercise Rex routing with an inherited managed config, without a fleet pin.
printf 'herdr\n' > "$CHILD/config/backend"
rm "$CHILD/state/parent-route/mate.meta"
cat > "$CODE/bin/fm-spawn.sh" <<'SH'
#!/usr/bin/env bash
cat > "$FM_STATE_OVERRIDE/mate.meta" <<META
backend=rex
endpoint_task_id=mate
worktree=$FM_HOME
project=$FM_ROOT_OVERRIDE
window=00000001-0000-7000-8000-000000000002:00000002-0000-7000-8000-000000000003
rex_session_id=session:00000001-0000-7000-8000-000000000002
rex_window_id=window:00000003-0000-7000-8000-000000000004
rex_block_id=block:00000002-0000-7000-8000-000000000003
rex_server=unix:///fixture/rex.sock
harness=codex
kind=secondmate
META
SH
cat > "$CODE/bin/fm-control.sh" <<'SH'
#!/usr/bin/env bash
[ -f "$FM_STATE_OVERRIDE/mate.meta" ] || exit 1
printf 'relaunch reached\n'
SH
assert_contains "$(run_control launch mate codex - - rex)" 'backend=rex' 'legacy Rex launch must retain its selected endpoint'
assert_absent "$CHILD/state/fleet-backend" 'legacy Rex launch bound the child'
assert_contains "$(run_control relaunch mate codex - -)" 'relaunch reached' 'legacy Rex relaunch must reach its lifecycle owner'
assert_absent "$CHILD/state/fleet-backend" 'legacy Rex relaunch bound the child'
if run_control validate-backend mate rex > "$TMP/rex-conflict" 2>&1; then
  fail 'explicit validation accepted Rex against managed configuration'
fi
assert_grep 'refusing runtime change' "$TMP/rex-conflict" 'explicit validation must still reject managed conflict'
pass 'legacy Rex launch and relaunch ignore inherited Herdr selection while explicit validation refuses'

OUT=$(env HOME="$TMP/account" FM_HOME="$CHILD" FM_HC_BIN="$TMP/hc" FM_REMOTE_JOB_ACTIVE=1 \
  "$ROOT/bin/fm-remote-doctor.sh" --backend hc --worker-tool-probe 2>&1) || true
assert_contains "$OUT" "required hc=$TMP/hc" 'doctor must use adapter binary resolution'
OUT=$(env HOME="$TMP/account" FM_HOME="$CHILD" FM_HC_BIN="$TMP/hc" FM_REMOTE_JOB_ACTIVE=1 \
  XDG_RUNTIME_DIR="$TMP/runtime" "$ROOT/bin/fm-remote-doctor.sh" --backend hc 2>&1) || true
assert_contains "$OUT" 'check hc=ok:' 'doctor must validate hc version'
assert_contains "$OUT" 'check hc-server=fixable:' 'absent core must require explicit repair'
assert_no_grep 'server status' "$HC_TEST_LOG" 'read-only doctor must not autostart absent core'
pass 'doctor supports hc tools and does not autostart a missing core in check mode'

# A first remote creation that fails its host readiness check leaves the
# parent and the child unbound. The SSH boundary is faked; the child-side
# control script runs for real against a scratch child home.
PARENT2="$TMP/parent2"
CHILD2="$TMP/child2"
mkdir -p "$PARENT2/data" "$PARENT2/state" "$PARENT2/config" "$CHILD2/state" "$CHILD2/config" "$CHILD2/bin"
printf 'codex\n' > "$PARENT2/config/crew-harness"
printf 'rmate\n' > "$CHILD2/.fm-secondmate-home"
touch "$CHILD2/AGENTS.md"
printf -- '- rmate - remote hc mate (host: remote-hc; root: %s; home: %s; scope: remote hc; projects: ; added 2026-11-17)\n' \
  "$ROOT" "$CHILD2" > "$PARENT2/data/secondmates.md"
cat > "$TMP/fake-ssh" <<'SH'
#!/usr/bin/env bash
while [ "$#" -gt 0 ]; do
  case "$1" in -o) shift 2 ;; --) shift; break ;; *) exit 90 ;; esac
done
[ "$1" = remote-hc ] && [ "$2" = fm-remote-entrypoint.sh ] || exit 91
shift 2
mapfile -d '' args < <(printf '%s' "$4" | base64 -d)
printf '%s\n' "${args[*]}" >> "$FAKE_SSH_LOG"
case "${args[0]}:${args[1]:-}" in
  fm-remote-doctor.sh:*)
    [ -n "${FAKE_HOST_READY:-}" ] && exit 0
    echo 'check hc-server=broken: fixture host is not ready'; exit 1 ;;
  fm-remote-secondmate-control.sh:launch) echo 'error: fixture launch failed after creating nothing provable' >&2; exit 1 ;;
  *) exec env FM_HOME="$FAKE_CHILD" FM_ROOT_OVERRIDE="$FAKE_ROOT" "$FAKE_ROOT/bin/${args[0]}" "${args[@]:1}" ;;
esac
SH
chmod +x "$TMP/fake-ssh"
: > "$TMP/ssh.log"
if env HOME="$TMP/account" FM_HOME="$PARENT2" FM_BACKEND=hc FM_SSH_BIN="$TMP/fake-ssh" \
  FAKE_SSH_LOG="$TMP/ssh.log" FAKE_CHILD="$CHILD2" FAKE_ROOT="$ROOT" \
  "$ROOT/bin/fm-spawn.sh" rmate --secondmate > "$TMP/remote-abort.out" 2>&1; then
  fail 'remote creation succeeded on a host that is not ready'
fi
assert_grep 'is not ready for a remote second mate' "$TMP/remote-abort.out" 'remote creation must stop at readiness'
grep -qx 'fm-remote-secondmate-control.sh validate-backend rmate hc' "$TMP/ssh.log" || fail 'creation must validate the child before readiness'
grep -qx 'fm-remote-secondmate-control.sh release-backend rmate hc' "$TMP/ssh.log" || fail 'abort must release the new child pin'
assert_no_grep 'control.sh launch ' "$TMP/ssh.log" 'an unready host must never receive a launch'
assert_absent "$PARENT2/state/fleet-backend" 'aborted remote creation left the parent bound'
assert_absent "$CHILD2/state/fleet-backend" 'aborted remote creation left the child bound'
pass 'a remote creation that fails readiness releases the new parent and child pins'

# Once the launch request leaves the parent, the endpoint may exist, so a
# failed launch keeps both pins for reconciliation.
rm -f "$CHILD2/state/fleet-backend"
: > "$TMP/ssh.log"
if env HOME="$TMP/account" FM_HOME="$PARENT2" FM_BACKEND=hc FM_SSH_BIN="$TMP/fake-ssh" \
  FAKE_SSH_LOG="$TMP/ssh.log" FAKE_CHILD="$CHILD2" FAKE_ROOT="$ROOT" FAKE_HOST_READY=1 \
  "$ROOT/bin/fm-spawn.sh" rmate --secondmate > "$TMP/remote-launch-failed.out" 2>&1; then
  fail 'remote creation succeeded although the launch failed'
fi
grep -q 'control.sh launch rmate' "$TMP/ssh.log" || fail "the fixture never reached the launch: $(cat "$TMP/remote-launch-failed.out")"
assert_no_grep 'release-backend' "$TMP/ssh.log" 'a failed launch released the child pin'
assert_grep 'hc' "$PARENT2/state/fleet-backend" 'a failed launch released the parent pin'
assert_grep 'hc' "$CHILD2/state/fleet-backend" 'a failed launch released the child pin'
pass 'a remote creation whose launch request failed keeps both pins for reconciliation'
