#!/usr/bin/env bash
# fm-remote-entrypoint.sh installs as a PATH symlink under ~/.local/bin
# (docs/remote-secondmates.md). SCRIPT_DIR must resolve to the real bin/
# directory so it can source its sibling fm-remote-job-lib.sh, not to the
# symlink's own directory.
set -u

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TMP_ROOT=$(fm_test_tmproot fm-remote-entrypoint)
REAL_BIN="$TMP_ROOT/real-root/bin"
LOCAL_BIN="$TMP_ROOT/local-bin"
mkdir -p "$REAL_BIN" "$LOCAL_BIN"
cp "$ROOT/bin/fm-remote-entrypoint.sh" "$ROOT/bin/fm-remote-job-lib.sh" "$REAL_BIN/"
chmod +x "$REAL_BIN/fm-remote-entrypoint.sh"
ln -s "$REAL_BIN/fm-remote-entrypoint.sh" "$LOCAL_BIN/fm-remote-entrypoint.sh"

run_entrypoint() { # <path> <stdout-file> <stderr-file>
  local path=$1 out=$2 err=$3 code
  "$path" >"$out" 2>"$err"
  code=$?
  printf '%s' "$code"
}

test_symlink_invocation_resolves_sibling_lib() {
  local out err code
  out="$TMP_ROOT/symlink.stdout"
  err="$TMP_ROOT/symlink.stderr"
  code=$(run_entrypoint "$LOCAL_BIN/fm-remote-entrypoint.sh" "$out" "$err")

  # A wrong SCRIPT_DIR fails while sourcing the sibling lib, before argv is
  # even checked, with a "No such file or directory" source error and exit 1.
  # Reaching the die() for missing protocol args proves the sibling lib
  # sourced from the real bin/, not from the symlink's own directory.
  assert_no_grep 'No such file or directory' "$err" \
    "invoking fm-remote-entrypoint.sh through a symlink failed to source its sibling lib"
  expect_code 64 "$code" "symlink invocation exit code"
  assert_grep 'remote entrypoint expects protocol, root, home, and argv' "$err" \
    "symlink invocation did not reach argument validation past sibling-lib sourcing"
  pass "fm-remote-entrypoint.sh invoked via a PATH symlink resolves SCRIPT_DIR to the real bin/ directory"
}

test_direct_invocation_still_works() {
  # Control: the same real script invoked directly (no symlink) must behave
  # identically, so the symlink coverage above is proven by contrast.
  local out err code
  out="$TMP_ROOT/direct.stdout"
  err="$TMP_ROOT/direct.stderr"
  code=$(run_entrypoint "$REAL_BIN/fm-remote-entrypoint.sh" "$out" "$err")

  expect_code 64 "$code" "direct invocation exit code"
  assert_grep 'remote entrypoint expects protocol, root, home, and argv' "$err" \
    "direct invocation did not reach argument validation"
  pass "fm-remote-entrypoint.sh invoked directly still resolves SCRIPT_DIR correctly"
}

test_doctor_hc_environment() {
  local root="$TMP_ROOT/doctor-root" home="$TMP_ROOT/doctor-home" account args output runtime mode expected
  mkdir -p "$root/bin" "$home" "$TMP_ROOT/runtime"
  : > "$root/AGENTS.md"
  cat > "$root/bin/fm-remote-doctor.sh" <<'SH'
#!/usr/bin/env bash
HC_SOCKET=${FM_HC_SOCKET:-} HC_SESSION=fm-remote exec "$FM_ROOT_OVERRIDE/bin/hc" "$@"
SH
  cat > "$root/bin/hc" <<'SH'
#!/usr/bin/env bash
printf '%s|%s|%s\n' "$HC_SESSION" "$HC_SOCKET" "$*"
SH
  chmod +x "$root/bin/fm-remote-doctor.sh" "$root/bin/hc"
  git -C "$root" init -q
  git -C "$root" add AGENTS.md bin
  account=$(unset HOME; cd ~ && pwd -P)
  for mode in check --fix; do
    if [ "$mode" = check ]; then
      args=$(printf 'fm-remote-doctor.sh\0' | base64 | tr -d '\n')
      expected=''
    else
      args=$(printf 'fm-remote-doctor.sh\0--fix\0' | base64 | tr -d '\n')
      expected=--fix
    fi
    for runtime in "$TMP_ROOT/runtime" ''; do
      output=$(XDG_RUNTIME_DIR="$runtime" "$REAL_BIN/fm-remote-entrypoint.sh" 1 \
        "$(printf '%s' "$root" | base64 | tr -d '\n')" \
        "$(printf '%s' "$home" | base64 | tr -d '\n')" "$args" </dev/null) || fail 'doctor bootstrap failed'
      [ "$output" = "fm-remote|$account/.local/state/herdr-core/fm-remote/fm-remote.sock|$expected" ] \
        || fail "doctor bootstrap selected the wrong socket: $output"
    done
  done
  pass 'doctor bootstrap passes the account hc socket regardless of XDG'
}

test_symlink_invocation_resolves_sibling_lib
test_direct_invocation_still_works
test_doctor_hc_environment
