#!/usr/bin/env bash
# Drives bin/fm-wake-drain.sh in a disposable lab home through the issue-7286 filter shapes.
# usage: drive-ack-rows.sh <repo-root-with-bin>
set -u
REPO=$1
LAB=$(mktemp -d "${TMPDIR:-/tmp}/fm-lab.XXXXXX")
"$REPO/bin/fm-lab-home.sh" create "$LAB" >/dev/null
export FM_HOME="$LAB"
unset FM_STATE_OVERRIDE FM_ROOT_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE
queue() { bash -c '. "$1/bin/fm-wake-lib.sh"; fm_wake_append "$2" "$3" "$4"' _ "$REPO" "$@"; }
seed() {
  for i in 1 2 3 4 5; do queue stale "window-$i" "stale: window-$i"; done
  queue check due-recheck "check: due recheck for worker alpha"
  queue signal alpha "signal: $LAB/state/alpha.status"
}
run() {  # <label> <filter>
  seed
  echo "### $1   (\$ bin/fm-wake-drain.sh 2>&1 $2)"
  out=$(cd "$REPO" && eval "bin/fm-wake-drain.sh 2>&1 $2")
  printf '%s\n' "$out"
  ack=$(printf '%s\n' "$out" | sed -n 's/^WAKE_ACK_REQUIRED:.* run bin\/fm-wake-drain.sh //p' | tail -1)
  case "$out" in *due-recheck*) echo ">> due-recheck VISIBLE in filtered output" ;; *) echo ">> due-recheck HIDDEN by filter" ;; esac
  # shellcheck disable=SC2086
  (cd "$REPO" && bin/fm-wake-drain.sh $ack >/dev/null 2>&1); echo ">> ack '$ack' rc=$? queue-left=$(wc -l < "$LAB/state/.wake-queue" 2>/dev/null || echo 0)"
  echo
}
run "rg -v digit-led rows" "| rg -v '^\\d'"
run "first WAKE_ACK line only" "| rg WAKE_ACK | head -1"
run "tail -2" "| tail -2"
echo "### stdout discarded (\$ bin/fm-wake-drain.sh >/dev/null)"; seed
out=$(cd "$REPO" && bin/fm-wake-drain.sh 2>&1 >/dev/null | rg WAKE_ACK); printf '%s\n' "$out"
ack=$(printf '%s\n' "$out" | sed -n 's/^WAKE_ACK_REQUIRED:.* run bin\/fm-wake-drain.sh //p')
(cd "$REPO" && bin/fm-wake-drain.sh $ack >/dev/null 2>&1); echo ">> ack rc=$?"
echo
echo "### adversarial key: spaces, shell metachars, 80-char key"
queue signal 'evil key; echo $HOME `x` "q" [a] (b)' "signal: odd"
queue stale "$(printf 'k%.0s' $(seq 80))" "stale: long"
out=$(cd "$REPO" && bin/fm-wake-drain.sh 2>&1 >/dev/null | rg WAKE_ACK)
printf '%s\n' "$out"
ack=$(printf '%s\n' "$out" | sed -n 's/^WAKE_ACK_REQUIRED:.* run bin\/fm-wake-drain.sh //p')
(cd "$REPO" && bin/fm-wake-drain.sh $ack >/dev/null 2>&1); echo ">> ack '$ack' rc=$? queue-left=$(wc -l < "$LAB/state/.wake-queue" 2>/dev/null || echo 0)"
echo
echo "### empty queue: no rows summary"
(cd "$REPO" && bin/fm-wake-drain.sh 2>&1 | rg WAKE_ACK) || echo ">> no WAKE_ACK_REQUIRED line printed"
rm -r "$LAB"
