import os
import pathlib
import subprocess
import sys
import time

root = pathlib.Path.cwd()
evidence = pathlib.Path(__file__).parent
env = os.environ.copy()
env.update({"LC_ALL": "C", "LANG": "C", "LC_CTYPE": "C"})
for key in tuple(env):
    if key.startswith("FM_") or key in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY"):
        env.pop(key)
suites = sys.argv[1:] or [
    "fm-dispatch-resolve", "fm-quota-choose", "fm-bootstrap",
    "fm-procevent-quota", "fm-startup-memory-budget", "fm-secondmate-sync",
    "fm-secondmate-harness", "fm-secondmate-liveness", "fm-shared-captain-inheritance",
]
failures = 0
for suite in suites:
    started = time.monotonic()
    command = ["bash", f"tests/{suite}.test.sh"]
    result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (evidence / f"{suite}-locale-c.log").write_text(result.stdout)
    passed = sum(line.startswith("ok -") for line in result.stdout.splitlines())
    failed = sum(line.startswith("not ok -") for line in result.stdout.splitlines())
    print(f"{' '.join(command)}: {passed} passed groups, {failed} failed groups, exit {result.returncode}, {time.monotonic() - started:.1f}s", flush=True)
    if result.returncode:
        failures += 1
        print(result.stdout[-5000:], flush=True)
raise SystemExit(bool(failures))
