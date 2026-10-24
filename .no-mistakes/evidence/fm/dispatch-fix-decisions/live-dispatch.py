import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

root = pathlib.Path.cwd()
lab = root / ".dispatch-validation"
evidence = pathlib.Path(__file__).parent
env = {k: v for k, v in os.environ.items() if not k.startswith("FM_")}
env.update({
    "LC_ALL": "C", "LANG": "C", "FM_HOME": str(lab / "home"),
    "PI_CODING_AGENT_DIR": str(lab / "pi-empty"),
    "QUOTA_AXI_SNAPSHOT": str(lab / "quota.json"),
    "XDG_CONFIG_HOME": str(lab / "xdg-config"),
    "XDG_CACHE_HOME": str(lab / "xdg-cache"),
    "DISPATCH_LIVE_CALLS": str(evidence / "live-calls.log"),
    "DISPATCH_REAL_PI": shutil.which("pi"),
    "DISPATCH_REAL_QUOTA": shutil.which("quota-axi"),
    "DISPATCH_REAL_CURL": shutil.which("curl"),
    "PATH": str(lab / "bin") + ":" + os.environ["PATH"],
    "TMPDIR": str(lab / "tmp"),
})
for directory in ("pi-empty", "pi-pinned", "tmp", "xdg-config", "xdg-cache"):
    (lab / directory).mkdir(exist_ok=True)
for name in ("pi", "quota-axi", "curl"):
    (lab / "bin" / name).chmod(0o700)
observed_modes = set()
stop = threading.Event()
def observe_files():
    while not stop.is_set():
        for path in (lab / "tmp").iterdir():
            try:
                if path.is_file() and path.stat().st_size:
                    observed_modes.add(path.stat().st_mode & 0o777)
            except FileNotFoundError:
                pass
        stop.wait(0.001)
observer = threading.Thread(target=observe_files)
observer.start()
results = []
profiles = []
try:
    cases = [(f"repeat-{i}", None, "brief.md", "clear", 0) for i in range(1, 6)]
    cases += [
        ("expiry", "expiry", "brief.md", "clear", 0),
        ("all-expired", "all-expired", "brief.md", "escalate", 0),
        ("bad-date", "bad-date", "brief.md", None, 2),
        ("bad-leap", "bad-leap", "brief.md", None, 2),
        ("valid-leap", "valid-leap", "brief.md", "clear", 0),
        ("approval", "approval", "brief.md", "escalate", 0),
        ("tie", "tie", "brief.md", None, 0),
        ("declared-floor", "declared-floor", "brief.md", "ambiguous", 0),
        ("low-confidence-approval", "low-confidence-approval", "brief.md", "escalate", 0),
        ("refresh", "refresh", "brief.md", "clear", 0),
        ("refresh-default", "refresh-default", "brief.md", "clear", 0),
        ("ambiguous", "ambiguous", "ambiguous.md", None, 0),
    ]
    cases += [(f"tie-{n}", f"tie-{n}", "brief.md", None, 0) for n in (3, 5, 8, 12, 20)]
    cases += [(f"balanced-{n}", "balanced", "balanced.md", None, 0) for n in range(1, 6)]
    cases.append(("timeout", "refresh-default", "brief.md", "clear", 0))
    cases += [(name, name, "brief.md", "clear", 0) for name in ("pin-refused", "signed-missing")]
    if len(sys.argv) > 1:
        cases = [case for case in cases if case[0] in sys.argv[1:]]
    for name, config, brief, status, expected_exit in cases:
        case_env = dict(env)
        case_env["DISPATCH_LIVE_CALLS"] = str(evidence / f"live-{name}-calls.log")
        case_env["DISPATCH_LIVE_REQUESTS"] = str(evidence / f"live-{name}-requests.jsonl")
        if config:
            case_env["FM_CONFIG_OVERRIDE"] = str(lab / "configs" / config)
        if name == "timeout":
            case_env["DISPATCH_PI_DELAY"] = "30"
        command = [str(root / "bin/fm-dispatch-resolve.sh"), str(lab / brief), "--project", "dispatch-live-lab"]
        started = time.monotonic()
        result = subprocess.run(command, env=case_env, text=True, capture_output=True, timeout=60)
        elapsed = time.monotonic() - started
        transcript = f"case={name}\n$ bin/fm-dispatch-resolve.sh .dispatch-validation/{brief} --project dispatch-live-lab\nFM_CONFIG_OVERRIDE={config or 'home/config'}\n{result.stdout}{result.stderr}exit={result.returncode} elapsed={time.monotonic() - started:.2f}s\n"
        (evidence / f"live-{name}.log").write_text(transcript)
        okay = result.returncode == expected_exit and (status is None or f"status: {status}" in result.stdout)
        if name == "timeout":
            okay = okay and 10 <= elapsed < 15
        if expected_exit == 2:
            okay = okay and "malformed rules file:" in result.stderr and not result.stdout
        if name.startswith("repeat-"):
            profiles.extend(line for line in result.stdout.splitlines() if line.startswith("  profile:"))
        results.append({"name": name, "checked_expectation": status or f"exit {expected_exit} only", "passed": okay, "exit": result.returncode})
        print(transcript, flush=True)
        assert not any(path.is_file() for path in (lab / "tmp").iterdir()), f"temporary files retained after {name}"
finally:
    stop.set()
    observer.join()
deterministic = len(profiles) == 5 and len(set(profiles)) == 1
summary = {"results": results, "deterministic": deterministic, "profiles": profiles, "observed_nonempty_file_modes": sorted(f"{mode:03o}" for mode in observed_modes), "temporary_files_remaining": sum(path.is_file() for path in (lab / "tmp").iterdir())}
(evidence / ("live-edge-results.json" if len(sys.argv) > 1 else "live-results.json")).write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
assert not profiles or deterministic
assert all(result["passed"] for result in results)
assert not any(mode & 0o077 for mode in observed_modes)
