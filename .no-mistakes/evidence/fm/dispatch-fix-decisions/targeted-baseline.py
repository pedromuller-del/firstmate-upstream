import json
import os
from pathlib import Path
import subprocess
import time

evidence = Path(__file__).parent
env = dict(os.environ, LC_ALL="C")
for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "FM_DISPATCH_PROVIDER", "FM_DISPATCH_MODEL"):
    env.pop(name, None)
results = []
for name in ("fm-quota-choose", "fm-procevent-quota", "fm-startup-memory-budget", "fm-secondmate-sync", "fm-secondmate-harness", "fm-secondmate-liveness", "fm-shared-captain-inheritance", "fm-bootstrap"):
    command = ["bash", f"tests/{name}.test.sh"]
    started = time.monotonic()
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    (evidence / f"{name}.log").write_text(output)
    record = {"command": command, "exit": result.returncode, "pass": sum(line.startswith("ok -") or line.startswith("ok ") for line in output.splitlines()), "fail": sum(line.startswith("not ok") for line in output.splitlines()), "seconds": round(time.monotonic() - started, 2)}
    results.append(record)
    print(json.dumps(record), flush=True)
    if result.returncode:
        print(output[-6000:], flush=True)
    (evidence / "baseline-results.json").write_text(json.dumps(results, indent=2) + "\n")
