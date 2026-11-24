#!/usr/bin/env bash
# Non-T3 inbox steering retains the recorded metadata's activity verdict,
# including partial records that still identify a terminal but lack a target.
set -eu

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TMP_ROOT=$(fm_test_tmproot fm-watch-inbox-meta)
mkdir -p "$TMP_ROOT/state" "$TMP_ROOT/config"

FM_HOME="$TMP_ROOT" FM_STATE_OVERRIDE="$TMP_ROOT/state" \
  FM_BUSY_REGEX=BUSYTOKEN bash -eu -c '
  . "$1/bin/fm-watch.sh"
  meta="$STATE/worker.meta"
  printf "terminal=lab:fm-worker\nharness=grok\nkind=ship\n" > "$meta"

  verdict=$(fm_busy_classify_meta "$meta" worker "$STATE" "BUSYTOKEN active")
  [ "$verdict" = "unknown no-target" ]
  # The terminal and rendered busy token alone would classify busy.
  fm_busy_is_busy tmux lab:fm-worker grok worker "$STATE" "BUSYTOKEN active"
  if inbox_steer_busy lab:fm-worker tmux worker "BUSYTOKEN active"; then
    echo "missing metadata target incorrectly deferred non-T3 steering" >&2
    exit 1
  fi

  printf "window=lab:fm-worker\n" >> "$meta"
  inbox_steer_busy lab:fm-worker tmux worker "BUSYTOKEN active"
  if inbox_steer_busy lab:fm-worker tmux worker "quiet output"; then
    echo "idle non-T3 metadata incorrectly deferred steering" >&2
    exit 1
  fi
' _ "$ROOT"

pass "non-T3 inbox guard preserves no-target uncertainty and recorded busy/idle verdicts"

REMOTE="$TMP_ROOT/remote"
mkdir -p "$REMOTE/state/parent-route/mate.inbox/handled" "$REMOTE/bin" "$TMP_ROOT/data" "$TMP_ROOT/fakebin"
printf 'mate\n' > "$REMOTE/.fm-secondmate-home"
printf '# fixture\n' > "$REMOTE/AGENTS.md"
printf 'window=remote:mate\nkind=secondmate\nremote_host=lab\n' > "$TMP_ROOT/state/mate.meta"
printf -- '- mate - fixture (host: lab; root: /remote/root; home: %s; scope: fixture; projects: sample; added 2026-08-26)\n' "$REMOTE" > "$TMP_ROOT/data/secondmates.md"
printf 'schema=fm-task-inbox.v1\nat=2026-01-01T00:00:00Z\n--\nhello\n' > "$REMOTE/state/parent-route/mate.inbox/001.msg"
printf 'schema=fm-task-inbox.v1\nat=2026-01-01T00:00:00Z\n--\nanother\n' > "$REMOTE/state/parent-route/mate.inbox/002.msg"
cat > "$TMP_ROOT/fakebin/ssh" <<'SH'
#!/usr/bin/env bash
[ "${FM_TEST_REMOTE_DOWN:-0}" != 1 ] || exit 255
[ "${FM_TEST_REMOTE_DELAY:-0}" -le 0 ] 2>/dev/null || sleep "$FM_TEST_REMOTE_DELAY"
[ -z "${FM_TEST_REMOTE_GARBAGE:-}" ] || { printf "%s\n" "$FM_TEST_REMOTE_GARBAGE"; exit 0; }
while [ "$#" -gt 0 ]; do
  case "$1" in -o) shift 2 ;; --) shift; break ;; *) exit 90 ;; esac
done
shift 2
home=$(perl -MMIME::Base64=decode_base64 -e 'print decode_base64($ARGV[0])' "$3")
args=()
while IFS= read -r -d '' arg; do args+=("$arg"); done < <(perl -MMIME::Base64=decode_base64 -e 'print decode_base64($ARGV[0])' "$4")
exec env FM_HOME="$home" FM_ROOT_OVERRIDE="$FM_TEST_ROOT" "$FM_TEST_ROOT/bin/${args[0]}" "${args[@]:1}"
SH
chmod +x "$TMP_ROOT/fakebin/ssh"
FM_HOME="$TMP_ROOT" FM_ROOT_OVERRIDE="$ROOT" FM_STATE_OVERRIDE="$TMP_ROOT/state" \
  FM_SSH_BIN="$TMP_ROOT/fakebin/ssh" FM_TEST_ROOT="$ROOT" FM_TASK_INBOX_GRACE_SECS=0 \
  bash -eu -c '
  . "$1/bin/fm-watch.sh"
  wake() { :; }
  for i in 1 2 3 4 5; do inbox_steer_check remote:mate mate; done
  [ -f "$FM_WAKE_QUEUE" ] && [ "$(wc -l < "$FM_WAKE_QUEUE" | tr -d " ")" = 1 ] || { echo "expected one remote inbox wake" >&2; exit 1; }
  grep -Eq "mate.*2.*(age|old)" "$FM_WAKE_QUEUE" || { echo "wake must name mate, count and age" >&2; exit 1; }
  mv "$2/state/parent-route/mate.inbox/001.msg" "$2/state/parent-route/mate.inbox/002.msg" "$2/state/parent-route/mate.inbox/handled/"
  printf "schema=fm-task-inbox.v1\ndelivery=fire-and-forget\n--\nnotice\n" > "$2/state/parent-route/mate.inbox/003.msg"
  for i in 1 2 3 4 5; do inbox_steer_check remote:mate mate; done
  [ "$(wc -l < "$FM_WAKE_QUEUE" | tr -d " ")" = 1 ] || { echo "acknowledged or fire-and-forget record produced wake" >&2; exit 1; }
  rm "$2/state/parent-route/mate.inbox/003.msg"
  printf "schema=fm-task-inbox.v1\n--\nwhile down\n" > "$2/state/parent-route/mate.inbox/003.msg"
  FM_TEST_REMOTE_DOWN=1 inbox_steer_check remote:mate mate
  FM_TEST_REMOTE_GARBAGE="garbled probe" inbox_steer_check remote:mate mate
  # Pending-shaped but malformed (extra field), aged past grace and the ring limit.
  for i in 1 2 3 4 5; do FM_TEST_REMOTE_GARBAGE="pending 003.msg 1 99 extra" inbox_steer_check remote:mate mate; done
  [ "$(wc -l < "$FM_WAKE_QUEUE" | tr -d " ")" = 1 ] || { echo "unreachable or garbled remote probe produced a wake" >&2; exit 1; }
  for i in 1 2 3 4 5; do inbox_steer_check remote:mate mate; done
  [ "$(wc -l < "$FM_WAKE_QUEUE" | tr -d " ")" = 2 ] || { echo "stuck record after an unknown probe did not wake once" >&2; exit 1; }
  grep -Eq "mate has 1 unhandled.*003.msg" "$FM_WAKE_QUEUE" || { echo "second wake must name the stuck record" >&2; exit 1; }
  mv "$2/state/parent-route/mate.inbox/003.msg" "$2/state/parent-route/mate.inbox/handled/"
' _ "$ROOT" "$REMOTE"
pass "remote inbox alerts once for unhandled records and stays quiet on unknown probes"

FM_HOME="$TMP_ROOT" FM_ROOT_OVERRIDE="$ROOT" FM_STATE_OVERRIDE="$TMP_ROOT/state" \
  bash -eu -c '
  . "$1/bin/fm-watch.sh"
  wake() { :; }
  rm -f "$FM_WAKE_QUEUE"
  printf "window=lab:pi\nharness=pi\nkind=ship\n" > "$STATE/pi.meta"
  "$1/bin/fm-busy-event.sh" arm "$STATE" pi >/dev/null
  fixture=" Allow project MCP server “postgres”?
 Project config: /tmp/project/.pi/mcp.json
 Endpoint: uvx postgres-mcp
 This server can run local commands or make network requests with your user permissions.
 → Don'"'"'t allow
   Allow
 ↑↓ navigate  enter select  escape/ctrl+c cancel"
  launch_mcp_prompt_check lab:pi pi "$fixture"
  launch_mcp_prompt_check lab:pi pi "$fixture"
  [ "$(wc -l < "$FM_WAKE_QUEUE" | tr -d " ")" = 1 ] || { echo "expected one prompt-specific wake" >&2; exit 1; }
  grep -Eqi "MCP.*(consent|approval)" "$FM_WAKE_QUEUE" || { echo "wake must identify MCP consent" >&2; exit 1; }
' _ "$ROOT"
pass "Pi MCP launch consent produces one prompt-specific wake"

# shellcheck source=tests/watch-triage-helpers.sh
. "$(dirname "${BASH_SOURCE[0]}")/watch-triage-helpers.sh"
case_dir=$(make_case remote-inbox-loop)
mkdir -p "$case_dir/data" "$case_dir/config"
printf 'window=remote:mate\nkind=secondmate\nremote_host=lab\n' > "$case_dir/state/mate.meta"
printf -- '- mate - fixture (host: lab; root: /remote/root; home: %s; scope: fixture; projects: sample; added 2026-08-26)\n' "$REMOTE" > "$case_dir/data/secondmates.md"
printf 'schema=fm-task-inbox.v1\nat=2026-01-01T00:00:00Z\n--\nnew instruction\n' > "$REMOTE/state/parent-route/mate.inbox/004.msg"
watch_bg "$case_dir/state" "$case_dir/fakebin" "$case_dir/out" env \
  FM_HOME="$case_dir" FM_ROOT_OVERRIDE="$ROOT" FM_SSH_BIN="$TMP_ROOT/fakebin/ssh" \
  FM_TEST_ROOT="$ROOT" FM_TASK_INBOX_GRACE_SECS=0 FM_TASK_INBOX_RING_MAX=0 \
  FM_WATCH_HANDLING_SUCCESSOR=1
pid=$!
wait_for_exit "$pid" 200 || { reap "$pid"; fail "watcher did not surface the remote inbox"; }
grep -Eq 'remote secondmate mate has 1 unhandled' "$case_dir/state/.wake-queue" \
  || fail "watcher did not enqueue the remote inbox wake"
pass "watcher loop surfaces a remote mate's unhandled inbox"

case_dir=$(make_case remote-inbox-delayed-beacon)
mkdir -p "$case_dir/data" "$case_dir/config"
printf 'window=remote:mate\nkind=secondmate\nremote_host=lab\n' > "$case_dir/state/mate.meta"
printf -- '- mate - fixture (host: lab; root: /remote/root; home: %s; scope: fixture; projects: sample; added 2026-08-26)\n' "$REMOTE" > "$case_dir/data/secondmates.md"
watch_bg "$case_dir/state" "$case_dir/fakebin" "$case_dir/out" env \
  FM_HOME="$case_dir" FM_ROOT_OVERRIDE="$ROOT" FM_SSH_BIN="$TMP_ROOT/fakebin/ssh" \
  FM_TEST_ROOT="$ROOT" FM_TEST_REMOTE_DELAY=6 FM_TASK_INBOX_GRACE_SECS=0 FM_TASK_INBOX_RING_MAX=0 \
  FM_WATCH_HANDLING_SUCCESSOR=1
pid=$!
if ! wait_poll_cycle "$case_dir/state" "$pid" 40; then
  reap "$pid" || true
  fail "watcher beacon stalled behind delayed remote inbox probe"
fi
wait_for_exit "$pid" 200 || { reap "$pid" || true; fail "watcher did not surface the delayed remote inbox"; }
grep -Eq 'remote secondmate mate has 1 unhandled' "$case_dir/state/.wake-queue" \
  || fail "watcher did not enqueue the delayed remote inbox wake"
pass "watcher beacon keeps advancing while a remote inbox probe is delayed, then surfaces it"

case_dir=$(make_case remote-inbox-unreachable)
mkdir -p "$case_dir/data" "$case_dir/config"
printf 'window=remote:mate\nkind=secondmate\nremote_host=lab\n' > "$case_dir/state/mate.meta"
printf -- '- mate - fixture (host: lab; root: /remote/root; home: %s; scope: fixture; projects: sample; added 2026-08-26)\n' "$REMOTE" > "$case_dir/data/secondmates.md"
watch_bg "$case_dir/state" "$case_dir/fakebin" "$case_dir/out" env \
  FM_HOME="$case_dir" FM_ROOT_OVERRIDE="$ROOT" FM_SSH_BIN="$TMP_ROOT/fakebin/ssh" \
  FM_TEST_ROOT="$ROOT" FM_TEST_REMOTE_DOWN=1 FM_TASK_INBOX_GRACE_SECS=0 FM_TASK_INBOX_RING_MAX=0
pid=$!
if ! wait_poll_cycle "$case_dir/state" "$pid" || ! wait_poll_cycle "$case_dir/state" "$pid"; then
  reap "$pid"
  fail "watcher exited against an unreachable remote mate: $(cat "$case_dir/out")"
fi
# The watcher's TERM exit status is nonzero; this file runs under set -e.
reap "$pid" || true
[ ! -s "$case_dir/state/.wake-queue" ] || fail "unreachable remote mate queued a wake: $(cat "$case_dir/state/.wake-queue")"
pass "watcher loop stays quiet and running against an unreachable remote mate"

case_dir=$(make_case pi-mcp-loop)
mkdir -p "$case_dir/config"
printf 'window=lab:fm-pi\nharness=pi\nkind=ship\n' > "$case_dir/state/pi.meta"
"$ROOT/bin/fm-busy-event.sh" arm "$case_dir/state" pi >/dev/null
cat > "$case_dir/capture" <<'EOF'
 Allow project MCP server “postgres”?
 Project config: /tmp/project/.pi/mcp.json
 Endpoint: uvx postgres-mcp
 This server can run local commands or make network requests with your user permissions.
 → Don't allow
   Allow
 ↑↓ navigate  enter select  escape/ctrl+c cancel
EOF
watch_bg "$case_dir/state" "$case_dir/fakebin" "$case_dir/out" env \
  FM_HOME="$case_dir" FM_ROOT_OVERRIDE="$ROOT" FM_FAKE_TMUX_WINDOW=lab:fm-pi \
  FM_FAKE_TMUX_CAPTURE="$case_dir/capture" FM_WATCH_HANDLING_SUCCESSOR=1
pid=$!
wait_for_exit "$pid" 200 || { reap "$pid"; fail "watcher did not surface the Pi MCP prompt"; }
grep -Eqi 'MCP.*consent' "$case_dir/state/.wake-queue" || fail "watcher did not enqueue the MCP consent wake"
pass "watcher loop surfaces the Pi MCP consent prompt"
