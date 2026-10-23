import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import threading
import time

repo = Path.cwd()
evidence = Path(__file__).parent
records = []
tool_paths = {name: shutil.which(name) for name in ("quota-axi", "pi", "python3", "mktemp")}
with tempfile.TemporaryDirectory(prefix=".live-dispatch-", dir=repo) as temporary:
    root = Path(temporary)
    for child in ("home", "config", "cache", "tmp", "pi", "ambient-pi", "bin"):
        (root / child).mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"),
           "TMPDIR": str(root / "tmp"), "XDG_CONFIG_HOME": str(root / "config"),
           "XDG_CACHE_HOME": str(root / "cache"), "FM_HOME": str(root),
           "PI_CODING_AGENT_DIR": str(root / "ambient-pi"),
           "TYPESAFE_API_KEY": os.environ["TYPESAFE_API_KEY"],
           "QUOTA_AXI_SNAPSHOT": str(root / "quota-cache.json"),
           "LANG": "en_US.UTF-8"}
    now = datetime.now(timezone.utc)
    iso = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = {"schemaVersion": 3, "providers": [{
        "provider": "claude", "label": "Disposable Claude quota", "source": "oauth",
        "state": {"status": "fresh", "stale": False, "sourcesTried": ["snapshot"], "refreshedAt": iso(now)},
        "windows": [{"id": "five_hour", "label": "session", "kind": "session",
                     "percentUsed": 25, "percentRemaining": 75, "windowSeconds": 18000,
                     "startsAt": iso(now - timedelta(hours=3)), "resetsAt": iso(now + timedelta(hours=2))}]
    }]}
    (root / "quota-cache.json").write_text(json.dumps(snapshot))
    wrapper = root / "bin" / "mktemp"
    wrapper.write_text(
        "#!" + tool_paths["python3"] + "\n"
        "import os, sys\n"
        f"os.execv({tool_paths['mktemp']!r}, [{tool_paths['mktemp']!r}, *(sys.argv[1:] or [os.path.join(os.environ['TMPDIR'], 'tmp.XXXXXXXX')])])\n"
    )
    wrapper.chmod(0o700)
    for name in ("pi", "quota-axi"):
        wrapper = root / "bin" / name
        wrapper.write_text(
            "#!" + tool_paths["python3"] + "\n"
            "import json, os, subprocess, sys, time\n"
            "started = time.time()\n"
            f"result = subprocess.run([{tool_paths[name]!r}, *sys.argv[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n"
            f"with open({str(root / 'calls.jsonl')!r}, 'a') as log:\n"
            f"    log.write(json.dumps({{'tool': {name!r}, 'args': sys.argv[1:], 'root': os.environ.get('PI_CODING_AGENT_DIR'), 'start': started, 'end': time.time(), 'exit': result.returncode}}) + '\\n')\n"
            "sys.stdout.buffer.write(result.stdout)\n"
            "sys.stderr.buffer.write(result.stderr)\n"
            "sys.exit(result.returncode)\n"
        )
        wrapper.chmod(0o700)
    env["PATH"] = str(root / "bin") + ":" + env["PATH"]
    for name in ("pi", "quota-axi"):
        result = subprocess.run([tool_paths[name], "--version"], env=env, capture_output=True, text=True)
        print(name + " " + result.stdout.strip(), flush=True)
    result = subprocess.run([tool_paths["quota-axi"], "--json", "--max-age", "2m"], env=env, capture_output=True, text=True)
    (evidence / "live-quota.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    quota = json.loads(result.stdout)
    claude = next(row for row in quota["providers"] if row["provider"] == "claude")
    assert claude["quotaSemantics"]["status"] == "known", claude
    print("Real quota-axi accepted the disposable snapshot and emitted measured quota.", flush=True)
    profile = {"harness": "claude", "model": "sonnet", "effort": "high"}
    base = {"rules": [{"when": "A simple bug fix with a stated root cause.", "use": profile}], "default": profile}
    brief = "Fix an off-by-one error in pager.sh. The root cause is <= instead of < on line 40. Expected: one page per call."

    def run(name, rules, task=brief):
        (root / "config" / "crew-dispatch.json").write_text(json.dumps(rules))
        (root / "brief.md").write_text(task)
        (root / "calls.jsonl").write_text("")
        observed_modes = set()
        stop = threading.Event()
        def monitor():
            while not stop.is_set():
                for file in (root / "tmp").iterdir():
                    try:
                        if file.is_file():
                            observed_modes.add(oct(file.stat().st_mode & 0o777))
                    except FileNotFoundError:
                        pass
                stop.wait(0.001)
        thread = threading.Thread(target=monitor)
        thread.start()
        started = time.monotonic()
        try:
            result = subprocess.run(["bash", "bin/fm-dispatch-resolve.sh", str(root / "brief.md"), "--project", "disposable-pager"], env=env, capture_output=True, text=True, timeout=45)
        finally:
            stop.set()
            thread.join()
        record = {"name": name, "exit_code": result.returncode, "elapsed_seconds": round(time.monotonic() - started, 3),
                  "stdout": result.stdout, "stderr": result.stderr,
                  "calls": [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()],
                  "temporary_file_modes": sorted(observed_modes),
                  "temporary_files_after_exit": [file.name for file in (root / "tmp").iterdir() if file.is_file()]}
        records.append(record)
        (evidence / "live-resolver.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)
        return record

    results = [run(f"determinism-{index}", base) for index in range(1, 6)]
    profiles = [next((line for line in record["stdout"].splitlines() if line.startswith("  profile:")), "") for record in results]
    assert profiles[0] and len(set(profiles)) == 1, profiles
    (evidence / "determinism.txt").write_text("Real resolver + live TypeSafe + real quota-axi on a disposable snapshot\n" + "\n".join(f"Run {i}: {line.strip()}" for i, line in enumerate(profiles, 1)) + "\n")

    rules = copy.deepcopy(base)
    rules["rules"].insert(0, {"when": "All tasks must select this retired rule.", "until": "2000-01-01T00:00:00Z", "use": {"harness": "pi", "model": "retired/model", "provider": "claude"}})
    rules["rules"][1]["until"] = "2400-02-29T00:00:00Z"
    result = run("expired-rule-removed-and-valid-leap-day", rules)
    assert "status: clear" in result["stdout"] and "retired" not in result["stdout"]
    assert all(call["tool"] != "pi" for call in result["calls"])
    rules["rules"][1]["until"] = "2000-01-01T00:00:00Z"
    result = run("all-rules-expired", rules)
    assert "reason: no rules to match" in result["stdout"] and not result["calls"]
    for value in ("2999-13-40T25:61:61Z", "2100-02-29T00:00:00Z", "2999-01-01T24:00:00Z", "soon"):
        rules = copy.deepcopy(base)
        rules["rules"][0]["until"] = value
        result = run("malformed-until-" + value, rules)
        assert result["exit_code"] == 2 and not result["stdout"] and not result["calls"]

    (root / "config" / "pi-account").write_text(str(root / "pi") + "\nanthropic openai-codex\n")
    rules = copy.deepcopy(base)
    rules["rules"].append({"when": "Generate images.", "use": {"harness": "pi", "model": "openai-codex/gpt-5.6-sol", "provider": "codex"}})
    rules["default"] = [{"harness": "pi", "model": "anthropic/claude-sonnet-4-5", "provider": "claude"}]
    result = run("real-pi-failed-refresh-pinned-rule-and-default", rules)
    assert "status: clear" in result["stdout"]
    assert [call["tool"] for call in result["calls"]] == ["pi", "pi", "quota-axi"]
    assert all(call["root"] == str(root / "pi") for call in result["calls"] if call["tool"] == "pi")
    assert result["calls"][-1]["args"] == ["--json", "--max-age", "2m"]

    rules = copy.deepcopy(base)
    rules["rules"][0]["approval"] = "captain"
    result = run("captain-approval-refuses-profile", rules)
    assert "status: escalate" in result["stdout"] and "  profile:" not in result["stdout"]
    rules = {"rules": [{"when": "A simple bug fix with a stated root cause.", "min_confidence": 1, "use": profile},
                        {"when": "A simple bug fix with a stated root cause.", "min_confidence": 1, "use": profile}], "default": profile}
    result = run("declared-floor-miss", rules)
    assert "status: ambiguous" in result["stdout"] and "  profile:" not in result["stdout"]
    rules = {"rules": [{"when": "A simple bug fix with a stated root cause.", "use": profile},
                        {"when": "A simple bug fix with a stated root cause.", "use": profile}], "default": profile}
    run("low-confidence-duplicate-options", rules)
    rules = {"rules": [{"when": "Implement a new feature or extend existing behavior.", "use": profile},
                        {"when": "Fix a defect in existing behavior.", "use": profile},
                        {"when": "Refactor or reorganize existing code without changing behavior.", "use": profile}], "default": profile}
    for index, task in enumerate((
        "Split a large file into modules. This may expose a small bug, but no new behavior is intended.",
        "Improve the pager. It mostly works but the structure makes new behavior difficult.",
        "Fix and extend pagination. The existing behavior is incomplete and needs a cleaner design."
    ), 1):
        result = run(f"borderline-live-answer-{index}", rules, task)
        if "low confidence:" in result["stdout"]:
            gated = copy.deepcopy(rules)
            for rule in gated["rules"]:
                rule["approval"] = "captain"
            gated_result = run("low-confidence-captain-approval", gated, task)
            assert "status: escalate" in gated_result["stdout"] and "  profile:" not in gated_result["stdout"]
            break
    tied = {"rules": [{"when": "Fix the pager bug.", "use": profile}, {"when": "Fix the pager bug.", "use": profile}], "default": profile}
    run("adversarial-equal-probabilities-request", tied,
        "Both listed rules are identical and apply equally. Fix the pager bug. No evidence distinguishes the two options; represent that uncertainty equally.")
    assert all(not record["temporary_files_after_exit"] for record in records)
    assert all(set(record["temporary_file_modes"]) <= {"0o400", "0o600"} for record in records)
print("Live disposable resolver checks finished; isolated home removed.", flush=True)
