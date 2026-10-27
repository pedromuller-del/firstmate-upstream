import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path.cwd()
evidence = Path(__file__).parent
lab = Path(tempfile.mkdtemp(prefix=".dispatch-boundaries-", dir=root))


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content))


try:
    home = lab / "home"
    fakebin = lab / "fakebin"
    write(home / "config/crew-dispatch.json", {"rules": [{"when": "Implement a feature.", "use": {"harness": "claude", "model": "sonnet"}}, {"when": "Investigate without code changes.", "use": {"harness": "claude", "model": "opus"}}], "default": {"harness": "claude", "model": "haiku"}})
    write(lab / "brief.md", "# Task\nInvestigate and fix a bug.\n")
    write(fakebin / "curl", """#!/usr/bin/env bash
while [ "$#" -gt 0 ]; do
  case "$1" in -o) out=$2; shift 2 ;; *) shift ;; esac
done
cat >/dev/null
cp "$RESPONSE" "$out"
printf 200
""")
    write(fakebin / "quota-axi", """#!/usr/bin/env bash
printf 'quota-called\\n' >> "$CALLS"
cat "$QUOTA_FIXTURE"
""")
    for path in fakebin.iterdir():
        path.chmod(0o700)
    write(lab / "quota.json", {"schemaVersion": 5, "providers": [{"provider": "claude", "quotaSemantics": {"status": "known", "effectiveAvailability": [{"scope": "all_models", "status": "known", "effectivePercentRemaining": 80, "selection": {"spendPriority": 0.5}, "runway": {"status": "through_reset"}}]}}]})
    env = {"PATH": str(fakebin) + os.pathsep + os.environ["PATH"], "HOME": str(home), "FM_HOME": str(home), "LC_ALL": "C", "RESPONSE": str(lab / "response.json"), "QUOTA_FIXTURE": str(lab / "quota.json"), "CALLS": str(lab / "calls"), "TYPESAFE_API_KEY": "synthetic-test-key", "OPENROUTER_API_KEY": "synthetic-test-key"}
    before = lab / "before/bin"
    before.mkdir(parents=True)
    for path in (root / "bin").iterdir():
        if path.name != "fm-dispatch-resolve.sh":
            (before / path.name).symlink_to(path)
    prior = subprocess.check_output(["git", "show", "59b5165a^:bin/fm-dispatch-resolve.sh"], text=True)
    write(before / "fm-dispatch-resolve.sh", prior)
    cases = [("effective-rule", "rule_2", {"rule_1": 0.55, "rule_2": 0.42, "default": 0.03}), ("probability-tie", "rule_1", {"rule_1": 0.49, "rule_2": 0.49, "default": 0.02}), ("unoffered-choice", "rule_9", {"rule_1": 0.55, "rule_2": 0.42, "default": 0.03})]
    records = []
    for provider in ("typesafe", "openrouter"):
        for label, choice, probabilities in cases:
            write(lab / "response.json", {"model": "synthetic-response", "answers": {"rule": {"type": "choice", "choice": choice, "confidence": 0.41, "probabilities": probabilities}}})
            write(lab / "calls", "")
            current = subprocess.run(["bash", "bin/fm-dispatch-resolve.sh", str(lab / "brief.md")], env=dict(env, FM_DISPATCH_PROVIDER=provider, FM_DISPATCH_MODEL="jev-latest"), text=True, capture_output=True)
            expected = {"effective-rule": "fallback: rule_1 (Implement a feature.) probability 0.55 replaces rule_2", "probability-tie": "top-probability tie", "unoffered-choice": "response is not a rule Choice answer"}[label]
            passed = current.returncode == 0 and expected in current.stdout
            if label != "effective-rule":
                passed = passed and "  profile:" not in current.stdout
            if label == "unoffered-choice":
                passed = passed and not (lab / "calls").read_text()
            text = f"OFFLINE response injection; not a live model result.\nprovider: {provider}\nexit: {current.returncode}\n{current.stdout}{current.stderr}"
            if label == "effective-rule":
                previous = subprocess.run(["bash", str(before / "fm-dispatch-resolve.sh"), str(lab / "brief.md")], env=dict(env, FM_DISPATCH_PROVIDER=provider, FM_DISPATCH_MODEL="jev-latest"), text=True, capture_output=True)
                reproduced = previous.returncode == 0 and "status: clear" in previous.stdout and expected not in previous.stdout and "--model 'sonnet'" in previous.stdout
                passed = passed and reproduced
                text += f"\nBefore fix 59b5165a, same response and quota:\nexit: {previous.returncode}\n{previous.stdout}\nRegression reproduced: {reproduced}\n"
            (evidence / f"offline-{provider}-{label}.txt").write_text(text)
            record = {"provider": provider, "case": label, "exit": current.returncode, "pass": passed}
            records.append(record)
            print(json.dumps(record), flush=True)
    (evidence / "response-boundaries-results.json").write_text(json.dumps(records, indent=2) + "\n")
    assert all(record["pass"] for record in records)
finally:
    shutil.rmtree(lab)
