import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
REAL = {name: shutil.which(name) for name in ("curl", "pi", "quota-axi", "bash", "mktemp")}
LAB = Path(tempfile.mkdtemp(prefix=".dispatch-live-", dir=ROOT))
RESULTS = []
ONLY = os.environ.get("DISPATCH_LIVE_ONLY")
RESULT_NAME = "live-results-extra.json" if ONLY else "live-results.json"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2))


def profile(model="sonnet"):
    return {"harness": "claude", "model": model, "effort": "high"}


def run_case(name, rules, brief, expected, extra_env=None):
    if ONLY and name not in ONLY.split(","):
        return {"stdout": ""}
    case = LAB / name
    home = case / "home"
    for directory in (home / "config", case / "tmp", case / "pi", case / "xdg", case / "cache", case / "trace"):
        directory.mkdir(parents=True, exist_ok=True)
    write(home / "config/crew-dispatch.json", rules)
    write(case / "brief.md", "# Task\n\n## Captain's intent\n" + brief + "\n")
    env = {k: os.environ[k] for k in ("PATH", "TYPESAFE_API_KEY", "USER", "LOGNAME") if k in os.environ}
    env.update(HOME=str(home), FM_HOME=str(home), TMPDIR=str(case / "tmp"), XDG_CONFIG_HOME=str(case / "xdg"), XDG_CACHE_HOME=str(case / "cache"), PI_CODING_AGENT_DIR=str(case / "pi"), PI_OFFLINE="1", PI_TELEMETRY="0", LC_ALL="C", QUOTA_AXI_SNAPSHOT=str(LAB / "quota-seed.json"), TRACE_DIR=str(case / "trace"))
    env["PATH"] = str(LAB / "trace-bin") + os.pathsep + env["PATH"]
    if extra_env:
        env.update(extra_env(case))
    start = time.monotonic()
    process = subprocess.Popen([REAL["bash"], "bin/fm-dispatch-resolve.sh", str(case / "brief.md"), "--project", "dispatch-validation"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while process.poll() is None:
        time.sleep(0.01)
    stdout, stderr = process.communicate()
    elapsed = round(time.monotonic() - start, 3)
    events = (case / "trace/events").read_text() if (case / "trace/events").exists() else ""
    temporaries = (case / "trace/tempfiles").read_text().splitlines()
    modes = [int(line.split("\t", 1)[0], 8) for line in temporaries]
    remaining = [line for line in temporaries if Path(line.split("\t", 1)[1]).exists()]
    output = f"$ bash bin/fm-dispatch-resolve.sh <isolated-brief> --project dispatch-validation\nexit: {process.returncode}\nelapsed_seconds: {elapsed}\nstdout:\n{stdout}\nstderr:\n{stderr}\nreal subprocesses:\n{events}\nresolver_temporary_file_modes_at_allocation: {[oct(m) for m in modes]}\nresolver_temporary_files_after_exit: {len(remaining)}\n"
    checks = {"exit": process.returncode == expected.get("exit", 0), "output": all(text in stdout + stderr for text in expected.get("contains", [])), "no_profile": not expected.get("no_profile") or "  profile:" not in stdout, "private_temporaries": bool(modes) and all(m & 0o077 == 0 for m in modes), "cleanup": not remaining}
    if expected.get("no_subprocesses"):
        checks["no_subprocesses"] = not events
    if "elapsed_between" in expected:
        low, high = expected["elapsed_between"]
        checks["bounded_wait"] = low <= elapsed <= high
    (EVIDENCE / f"{name}.txt").write_text(output)
    for path in (case / "trace").iterdir():
        if path.name != "events":
            shutil.copyfile(path, EVIDENCE / f"{name}-{path.name}")
    record = {"name": name, "exit": process.returncode, "seconds": elapsed, "checks": checks, "pass": all(checks.values()), "stdout": stdout, "events": events}
    RESULTS.append(record)
    print(json.dumps(record), flush=True)
    (EVIDENCE / RESULT_NAME).write_text(json.dumps(RESULTS, indent=2) + "\n")
    return record


try:
    now = dt.datetime.now(dt.timezone.utc)
    iso = lambda value: value.isoformat(timespec="seconds").replace("+00:00", "Z")
    seed = {"schemaVersion": 3, "providers": [{"provider": "claude", "label": "Claude", "source": "oauth", "windows": [{"id": "five_hour", "label": "session", "kind": "session", "percentUsed": 20, "percentRemaining": 80, "startsAt": iso(now - dt.timedelta(hours=2)), "resetsAt": iso(now + dt.timedelta(hours=3)), "windowSeconds": 18000}], "state": {"status": "fresh", "stale": False, "refreshedAt": iso(now), "sourcesTried": ["disposable-test-data"]}}]}
    write(LAB / "quota-seed.json", seed)
    write(EVIDENCE / ("quota-seed-extra.json" if ONLY else "quota-seed.json"), seed)
    wrapper = '''#!/usr/bin/env bash
set -u
name=${0##*/}
if [ "$name" = mktemp ]; then
  path=$(REAL_MKTEMP "$@") || exit $?
  printf '%s\\t%s\\n' "$(stat -f '%Lp' "$path")" "$path" >> "$TRACE_DIR/tempfiles"
  printf '%s\\n' "$path"
  exit 0
fi
printf '%s start %s\\n' "$name" "$*" >> "$TRACE_DIR/events"
case "$name" in
  curl)
    output=''
    args=("$@")
    while [ "$#" -gt 0 ]; do
      case "$1" in -o) output=$2; shift 2 ;; *) shift ;; esac
    done
    cat > "$TRACE_DIR/request.json"
    REAL_CURL "${args[@]}" < "$TRACE_DIR/request.json"
    code=$?
    [ ! -f "$output" ] || cp "$output" "$TRACE_DIR/response.json"
    ;;
  pi)
    printf 'pi root %s\\n' "${PI_CODING_AGENT_DIR-unset}" >> "$TRACE_DIR/events"
    REAL_PI "$@" > "$TRACE_DIR/pi-output.txt" 2>&1
    code=$?
    cat "$TRACE_DIR/pi-output.txt"
    ;;
  quota-axi)
    REAL_QUOTA "$@" > "$TRACE_DIR/quota.json"
    code=$?
    cat "$TRACE_DIR/quota.json"
    ;;
esac
printf '%s exit %s\\n' "$name" "$code" >> "$TRACE_DIR/events"
exit "$code"
'''
    for token, command in (("REAL_CURL", "curl"), ("REAL_PI", "pi"), ("REAL_QUOTA", "quota-axi"), ("REAL_MKTEMP", "mktemp")):
        wrapper = wrapper.replace(token, shlex.quote(REAL[command]))
    for name in ("curl", "pi", "quota-axi", "mktemp"):
        write(LAB / "trace-bin" / name, wrapper)
        (LAB / "trace-bin" / name).chmod(0o700)
    normal = {"rules": [{"when": "A simple bug fix with a stated root cause.", "use": profile()}], "default": profile("opus")}
    bug = "Fix an off-by-one in pager.sh. The root cause is <= instead of < on line 40. Change that operator."
    run_case("clear", normal, bug, {"contains": ["status: clear", "profile: --harness 'claude' --model 'sonnet' --effort 'high'"]})
    expired = copy.deepcopy(normal)
    expired["rules"].insert(0, {"when": normal["rules"][0]["when"], "use": profile("expired-model"), "until": "2000-01-01T00:00:00Z"})
    expired["rules"][1]["until"] = "2999-01-01T00:00:00Z"
    run_case("expired-and-future", expired, bug, {"contains": ["status: clear", "--model 'sonnet'"]})
    all_expired = copy.deepcopy(normal)
    all_expired["rules"][0]["until"] = "2000-01-01T00:00:00Z"
    run_case("all-expired", all_expired, bug, {"contains": ["no rules to match"], "no_profile": True, "no_subprocesses": True})
    for index, until in enumerate(("2999-13-40T25:61:61Z", "2025-02-29T00:00:00Z", "2024-02-30T00:00:00Z", "2028-02-29T24:00:00Z", "2028-02-29T00:00:60Z", "2028-02-29T00:00:00+00:00")):
        malformed = copy.deepcopy(normal)
        malformed["rules"][0]["until"] = until
        run_case(f"invalid-until-{index + 1}", malformed, bug, {"exit": 2, "contains": ["malformed rules file", "until"], "no_profile": True, "no_subprocesses": True})
    leap = copy.deepcopy(normal)
    leap["rules"][0]["until"] = "2028-02-29T00:00:00Z"
    run_case("valid-leap-day", leap, bug, {"contains": ["status: clear"]})
    approval = copy.deepcopy(normal)
    approval["rules"][0]["approval"] = "captain"
    run_case("captain-approval", approval, bug, {"contains": ["status: escalate", "explicit approval"], "no_profile": True})
    uncertain = {"rules": [{"when": "Implementation where the worker must design parts of the solution itself within an existing codebase.", "use": profile()}, {"when": "Read-only investigations or audits without code changes.", "use": profile("opus")}], "default": profile("haiku")}
    ambiguous_briefs = ["Split a large file into smaller files without changing behavior.", "Investigate a slow function and apply a small fix if the root cause is obvious.", "Consider whether to split the module; make a small change if useful.", "Fix documentation and inspect the parser, with implementation optional.", "Review the retry policy and adjust it only if necessary."]
    for index, brief in enumerate(ambiguous_briefs):
        result = run_case(f"low-confidence-{index + 1}", uncertain, brief, {"contains": ["status: clear"]})
        if "low confidence:" in result["stdout"]:
            break
    low_approval = copy.deepcopy(uncertain)
    low_approval["rules"][1]["approval"] = "captain"
    run_case("low-confidence-approval", low_approval, ambiguous_briefs[4], {"contains": ["status: escalate", "explicit approval"], "no_profile": True})
    for count in (2, 3):
        equal_rules = {"rules": [{"when": normal["rules"][0]["when"], "use": profile(f"model-{index}")} for index in range(count)], "default": profile()}
        run_case(f"tie-attempt-{count}", equal_rules, bug, {})
    declared = copy.deepcopy(uncertain)
    for rule in declared["rules"]:
        rule["min_confidence"] = 1
    run_case("declared-floor", declared, ambiguous_briefs[1], {"contains": ["status: ambiguous", "below its floor"], "no_profile": True})
    pi_rules = copy.deepcopy(normal)
    pi_rules["rules"].append({"when": "Generate an image.", "use": [{"harness": "pi", "model": "openai-codex/gpt-5.6-sol", "provider": "codex"}, {"harness": "pi", "model": "openai-codex/gpt-5.6-luna", "provider": "codex"}]})
    pi_rules["default"] = [{"harness": "pi", "model": "anthropic/claude-sonnet-4-6", "provider": "claude"}]
    def pin(case):
        write(case / "home/config/pi-account", str(case / "pi") + "\nanthropic openai-codex\n")
        return {}
    run_case("pi-failure-nonfatal", pi_rules, bug, {"contains": ["status: clear"]}, pin)
    def refused_pin(case):
        write(case / "home/config/pi-account", str(case / "missing-account") + "\nanthropic openai-codex\n")
        return {}
    run_case("pi-refused-pin", pi_rules, bug, {"contains": ["status: clear"]}, refused_pin)
    timed_rules = copy.deepcopy(normal)
    timed_rules["default"] = {"harness": "pi", "model": "anthropic/claude-sonnet-4-6", "provider": "claude"}
    def hung_store(case):
        write(case / "home/config/pi-account", str(case / "pi") + "\nanthropic\n")
        os.mkfifo(case / "pi/auth.json", 0o600)
        return {}
    run_case("pi-timeout", timed_rules, bug, {"contains": ["status: clear"], "elapsed_between": [10, 15]}, hung_store)
finally:
    shutil.rmtree(LAB)
    print("Disposable live-test home removed.", flush=True)
