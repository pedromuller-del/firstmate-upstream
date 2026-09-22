from pathlib import Path
import copy
import json
import os
import subprocess

root = Path.cwd()
evidence = Path(__file__).parent
lab = root / ".quota-lane-validation"
(lab / "home/config").mkdir(parents=True, exist_ok=True)
(lab / "tmp").mkdir(exist_ok=True)
(lab / "brief.md").write_text("Fix the known pager off-by-one condition from <= to < and verify the page count.\n")
fakebin = lab / "fixture-bin"
fakebin.mkdir(exist_ok=True)
(fakebin / "curl").write_text("""#!/usr/bin/env bash
while [ "$#" -gt 0 ]; do
  case "$1" in -o) output=$2; shift 2 ;; *) shift ;; esac
done
cat >/dev/null
cat >"$output" <<'JSON'
{"model":"fixture-rule-matcher","answers":{"rule":{"choice":"rule_1","confidence":1,"probabilities":{"rule_1":1,"default":0}}}}
JSON
printf 200
""")
(fakebin / "quota-axi").write_text('#!/bin/sh\ncat "${QUOTA_AXI_FIXTURE:?}"\n')
for p in fakebin.iterdir():
    p.chmod(0o755)

def row(provider, key, remaining, priority):
    result = {"provider": provider, "quotaSemantics": {"status": "known", "effectiveAvailability": [{"scope": "all_models", "status": "known", "effectivePercentRemaining": remaining, "runway": {"status": "exhausted_now" if remaining == 0 else "through_reset"}, "selection": {"spendPriority": priority}}]}}
    if key is not None:
        result["accountKey"] = key
    return result

candidates = [
    {"harness": "pi", "model": "openai-codex/gpt-5.6-sol", "provider": "codex"},
    {"harness": "pi", "model": "openai-codex-muller-labs/gpt-5.6-luna", "provider": "codex"},
    {"harness": "pi", "model": "codex-native/gpt-6-astra", "provider": "codex", "effort": "ultra"},
    {"harness": "codex", "model": "gpt-5.6-sol"},
    {"harness": "cursor", "model": "cursor-grok-4.6-medium"},
]
rules = {"rules": [{"when": "Implement a concrete software bug fix with a known root cause.", "use": candidates}]}
(lab / "home/config/crew-dispatch.json").write_text(json.dumps(rules))
base = {"generatedAt": "2030-01-01T00:00:00Z", "schemaVersion": 6, "providers": [row("codex", "codex-home", 97, 0.8), row("codex", "openai-codex-muller-labs", 0, -1), row("cursor", "default", 22, 0.3)]}
both = copy.deepcopy(base)
both["providers"].append(row("codex", "openai-codex", 0, -1))
reversed_rows = copy.deepcopy(both)
reversed_rows["providers"].reverse()
default_only = {"schemaVersion": 6, "providers": [row("codex", "default", 97, 0.8), row("cursor", "default", 22, 0.3)]}
no_codex = {"schemaVersion": 6, "providers": [row("cursor", "default", 22, 0.3)]}
schema5 = {"schemaVersion": 5, "providers": [row("codex", None, 97, 0.8), row("cursor", None, 22, 0.3)]}
cases = [("exact-row-exhausted", both), ("exact-row-reversed", reversed_rows), ("neither-named-row-default-present", default_only), ("no-codex-row", no_codex), ("schema-5", schema5)]
env = os.environ.copy()
for name in ["FM_CONFIG_OVERRIDE", "FM_ROOT_OVERRIDE"]:
    env.pop(name, None)
env.update(LC_ALL="C", TMPDIR=str(lab / "tmp"), FM_HOME=str(lab / "home"), TYPESAFE_API_KEY="fixture-only-key", PATH=str(fakebin) + os.pathsep + env["PATH"])
outputs = {}
for name, snapshot in cases:
    snapshot_path = evidence / (name + "-input.json")
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n")
    env["QUOTA_AXI_FIXTURE"] = str(snapshot_path)
    result = subprocess.run(["bash", "bin/fm-dispatch-resolve.sh", str(lab / "brief.md")], env=env, capture_output=True, text=True, timeout=30)
    (evidence / (name + ".txt")).write_text("Fixture-driven executable check; NOT live. Real fm-dispatch-resolve.sh with simulated quota-axi and Typesafe.ai responses.\n$ bash bin/fm-dispatch-resolve.sh <brief>\n" + result.stdout + result.stderr + "\nexit_code: " + str(result.returncode) + "\n")
    assert result.returncode == 0, (name, result.stderr)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("candidate:")]
    home, labs, native, codex, cursor = lines
    if name.startswith("exact-row"):
        assert "remaining=0%" in home and "not eligible: runway exhausted_now" in home, home
        assert "remaining=0%" in labs and "not eligible" in labs, labs
        assert all("remaining=97%" in line and "-> eligible" in line for line in [native, codex]), lines
        assert "reason: genuine spendPriority tie" in result.stdout, result.stdout
    elif name == "neither-named-row-default-present":
        assert "eligible, unranked: provider codex has no quota row for account openai-codex" in home, home
        assert all("remaining=97%" in line and "-> eligible" in line for line in [labs, native, codex]), lines
    elif name == "no-codex-row":
        assert all("eligible, unranked:" in line for line in [home, labs, native, codex]), lines
        assert "profile: --harness 'cursor'" in result.stdout, result.stdout
    else:
        assert all("remaining=97%" in line and "-> eligible" in line for line in [home, labs, native, codex]), lines
        assert "reason: genuine spendPriority tie" in result.stdout, result.stdout
    assert "remaining=22%" in cursor and "spendPriority=0.3" in cursor, cursor
    outputs[name] = lines
    print("PASS", name, "exit=0")
assert outputs["exact-row-exhausted"] == outputs["exact-row-reversed"]
print("5 fixture-driven executable cases passed; row reversal preserved every candidate's output.")
