from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

repo = Path.cwd()
evidence = Path(__file__).parent
with tempfile.TemporaryDirectory(prefix=".live-timeout-", dir=repo) as temporary:
    root = Path(temporary)
    for child in ("home", "config", "cache", "tmp", "pi", "bin"):
        (root / child).mkdir()
    quota = json.loads((evidence / "live-quota.json").read_text())
    snapshot = {"schemaVersion": 3, "providers": [p for p in quota["providers"] if p["provider"] == "claude"]}
    provider = snapshot["providers"][0]
    provider.update(label="Disposable Claude quota", source="oauth")
    provider["state"]["sourcesTried"] = ["snapshot"]
    window = provider["windows"][0]
    window.update(percentUsed=25, windowSeconds=18000,
                  startsAt=(datetime.fromisoformat(window["resetsAt"]) - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    (root / "quota.json").write_text(json.dumps(snapshot))
    profile = {"harness": "claude", "model": "sonnet", "effort": "high"}
    rules = {"rules": [{"when": "Fix a simple bug.", "use": profile}],
             "default": {"harness": "pi", "model": "anthropic/claude-sonnet-4-5", "provider": "claude"}}
    (root / "config" / "crew-dispatch.json").write_text(json.dumps(rules))
    (root / "config" / "pi-account").write_text(str(root / "pi") + "\nanthropic\n")
    (root / "brief.md").write_text("Fix the <= instead of < bug on line 40 of pager.sh.")
    real_pi = shutil.which("pi")
    wrapper = root / "bin" / "pi"
    wrapper.write_text(
        "#!" + shutil.which("python3") + "\n"
        "import os, signal, subprocess, sys\n"
        f"child = subprocess.Popen([{real_pi!r}, *sys.argv[1:]])\n"
        "os.kill(child.pid, signal.SIGSTOP)\n"
        f"with open({str(root / 'pid')!r}, 'w') as f: f.write(str(child.pid))\n"
        "sys.exit(child.wait())\n"
    )
    wrapper.chmod(0o700)
    env = {"PATH": str(root / "bin") + ":" + os.environ["PATH"],
           "HOME": str(root / "home"), "TMPDIR": str(root / "tmp"),
           "XDG_CONFIG_HOME": str(root / "config"), "XDG_CACHE_HOME": str(root / "cache"),
           "FM_HOME": str(root), "PI_CODING_AGENT_DIR": str(root / "pi"),
           "TYPESAFE_API_KEY": os.environ["TYPESAFE_API_KEY"],
           "QUOTA_AXI_SNAPSHOT": str(root / "quota.json")}
    started = time.monotonic()
    try:
        probe = subprocess.run(["quota-axi", "--json", "--max-age", "2m"], env=env, capture_output=True, text=True)
        assert probe.returncode == 0, probe.stderr
        started = time.monotonic()
        result = subprocess.run(["bash", "bin/fm-dispatch-resolve.sh", str(root / "brief.md")],
                                env=env, capture_output=True, text=True, timeout=20)
        elapsed = time.monotonic() - started
        pid = int((root / "pid").read_text())
        process = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
        record = {"command": "bash bin/fm-dispatch-resolve.sh <disposable-brief>",
                  "fault": "SIGSTOP sent only to this run's real Pi auth-check child after launch",
                  "exit_code": result.returncode, "elapsed_seconds": round(elapsed, 3),
                  "stdout": result.stdout, "stderr": result.stderr,
                  "pi_child_stat_after_return": process.stdout.strip() or "absent"}
        (evidence / "live-refresh-timeout.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record), flush=True)
        assert result.returncode == 0 and "status: clear" in result.stdout
        assert 10 <= elapsed < 18
        assert not process.stdout.strip() or process.stdout.strip().startswith("Z")
    finally:
        if (root / "pid").exists():
            try:
                os.kill(int((root / "pid").read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
