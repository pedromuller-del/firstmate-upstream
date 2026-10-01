import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
assert (ROOT / "bin/fm-dispatch-resolve.sh").is_file()
assert os.environ.get("TYPESAFE_API_KEY"), "The existing API key must be injected into the environment"

def row(account, remaining, priority, provider="codex"):
    return {"provider": provider, "accountKey": account,
            "quotaSemantics": {"status": "known", "effectiveAvailability": [
                {"scope": "all_models", "status": "known", "effectivePercentRemaining": remaining,
                 "runway": {"status": "exhausted_now" if remaining == 0 else "through_reset"},
                 "selection": {"spendPriority": priority}}]}}

def profile(model, harness="pi", **fields):
    return dict(harness=harness, model=model, provider="codex", **fields)

HOME = profile("openai-codex/gpt-5.6-sol")
WORK = profile("openai-codex-work/gpt-5.6-luna")
NATIVE = profile("gpt-5.6-sol", "codex")
PI_NATIVE = profile("codex-native/gpt-6-astra", effort="ultra")
SIGNED = profile("openai-codex/gpt-5.6-sol", "pi-signed")

def candidate(p, detail):
    return "  candidate: " + p["harness"] + ":" + p["model"] + "  provider=codex  " + detail

healthy = "scope=all_models  remaining=97%  spendPriority=0.8  runway=through_reset  -> eligible"
exhausted = "scope=all_models  remaining=0%  spendPriority=-  runway=exhausted_now  -> not eligible: runway exhausted_now at all_models"
unranked = "-> eligible, unranked: provider codex has no quota row for account openai-codex: disclosed uncertainty"
home_rows = [row("openai-codex-work", 0, -1), row("default", 53, 9), row("codex-home", 97, 0.8), row("codex-home", 8, 100, "claude")]
both_rows = home_rows + [row("openai-codex", 0, -1)]
default_rows = [row("unrelated-account", 3, 8), row("default", 97, 0.8), row("codex-home", 8, 100, "claude")]
schema5_row = row("unused", 97, 0.8)
del schema5_row["accountKey"]

cases = [
    ("home-fallback", 6, home_rows, [HOME, WORK], "clear", [candidate(HOME, healthy), candidate(WORK, exhausted), "  profile: --harness 'pi' --model 'openai-codex/gpt-5.6-sol'"]),
    ("home-fallback-pi-signed", 6, home_rows, [SIGNED, WORK], "clear", [candidate(SIGNED, healthy), candidate(WORK, exhausted), "  profile: --harness 'pi-signed' --model 'openai-codex/gpt-5.6-sol'"]),
    ("native-codex", 6, home_rows, [NATIVE, WORK], "clear", [candidate(NATIVE, healthy), candidate(WORK, exhausted), "  profile: --harness 'codex' --model 'gpt-5.6-sol'"]),
    ("pi-native", 6, home_rows, [PI_NATIVE, WORK], "clear", [candidate(PI_NATIVE, healthy), candidate(WORK, exhausted), "  profile: --harness 'pi' --model 'codex-native/gpt-6-astra' --effort 'ultra'"]),
    ("exact-row-exhausted", 6, both_rows, [HOME, WORK], "escalate", [candidate(HOME, exhausted), candidate(WORK, exhausted), "  reason: no rankable eligible candidate"]),
    ("exact-row-exhausted-reversed", 6, list(reversed(both_rows)), [HOME, WORK], "escalate", [candidate(HOME, exhausted), candidate(WORK, exhausted), "  reason: no rankable eligible candidate"]),
    ("neither-named-row", 6, default_rows, [HOME, WORK], "clear", [candidate(HOME, unranked), candidate(WORK, healthy), "  profile: --harness 'pi' --model 'openai-codex-work/gpt-5.6-luna'", "  note: 1 eligible candidate(s) unranked (codex)"]),
    ("schema5-single-provider-row", 5, [schema5_row], [HOME, WORK, NATIVE, PI_NATIVE], "escalate", [candidate(p, healthy) for p in [HOME, WORK, NATIVE, PI_NATIVE]] + ["  reason: genuine spendPriority tie"]),
]

stub = """#!/usr/bin/env bash
set -eu
[ "$#" -eq 1 ] && [ "$1" = --json ] || exit 64
printf '%s\n' "$*" >> "$QUOTA_AXI_CALLS"
cat "$QUOTA_AXI_FIXTURE"
"""
brief = """# Task
## Captain's intent
Fix the off-by-one error in a pager. It emits one extra page because the loop uses <= instead of <. Change that comparison and verify that one requested page produces one page.
## Firstmate spec
This is a routine code bug fix with a stated root cause.
"""
results = []
for name, schema, rows, profiles, status, expected in cases:
    destination = EVIDENCE / name
    destination.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".quota-live-" + name + "-", dir=ROOT) as scratch:
        lab = Path(scratch)
        for folder in ["home/config", "fakebin", "tmp"]:
            (lab / folder).mkdir(parents=True)
        snapshot = {"schemaVersion": schema, "generatedAt": "2026-10-01T00:00:00Z", "providers": rows}
        rules = {"rules": [{"when": "A routine code bug fix with a stated root cause.", "use": profiles}]}
        (lab / "home/config/crew-dispatch.json").write_text(json.dumps(rules, indent=2) + "\n")
        (lab / "quota.json").write_text(json.dumps(snapshot, indent=2) + "\n")
        (lab / "brief.md").write_text(brief)
        (lab / "fakebin/quota-axi").write_text(stub)
        (lab / "fakebin/quota-axi").chmod(0o755)
        env = os.environ.copy()
        unset = ["FM_ROOT_OVERRIDE", "FM_STATE_OVERRIDE", "FM_DATA_OVERRIDE", "FM_CONFIG_OVERRIDE", "FM_PROJECTS_OVERRIDE", "FM_GATE_REFUSE_BYPASS", "FM_TEST_SEAM"]
        for key in unset:
            env.pop(key, None)
        overrides = dict(LC_ALL="C", LANG="C", FM_HOME=str(lab / "home"), PATH=str(lab / "fakebin") + os.pathsep + env["PATH"], TMPDIR=str(lab / "tmp"), QUOTA_AXI_FIXTURE=str(lab / "quota.json"), QUOTA_AXI_CALLS=str(lab / "quota-axi.calls"))
        env.update(overrides)
        command = [str(ROOT / "bin/fm-dispatch-resolve.sh"), str(lab / "brief.md"), "--project", "quota-validation"]
        printable = ["env"] + [item for key in unset for item in ["-u", key]] + [key + "=" + value for key, value in overrides.items()] + command
        (destination / "command.txt").write_text("# TYPESAFE_API_KEY is inherited; its value is never recorded.\n" + shlex.join(printable) + "\n")
        for source, target in [("home/config/crew-dispatch.json", "crew-dispatch.json"), ("quota.json", "quota.json"), ("brief.md", "brief.md"), ("fakebin/quota-axi", "quota-axi")]:
            shutil.copyfile(lab / source, destination / target)
        run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=25)
        (destination / "stdout.txt").write_text(run.stdout)
        (destination / "stderr.txt").write_text(run.stderr)
        (destination / "exit-code.txt").write_text(str(run.returncode) + "\n")
        calls = (lab / "quota-axi.calls").read_text() if (lab / "quota-axi.calls").exists() else ""
        (destination / "quota-axi.calls").write_text(calls)
        missing = [line for line in ["  status: " + status] + expected if line not in run.stdout.splitlines()]
        errors = (["unexpected exit code"] if run.returncode else []) + missing
        if run.stderr:
            errors.append("unexpected stderr")
        if calls != "--json\n":
            errors.append("expected exactly one fixture quota snapshot")
        if status != "clear" and any(line.startswith("  profile:") for line in run.stdout.splitlines()):
            errors.append("unexpected selected profile")
        result = dict(name=name, result="fail" if errors else "pass", live=True, exit_code=run.returncode, errors=errors, real_product="bin/fm-dispatch-resolve.sh", real_service="https://api.typesafe.ai/v1/systemone", fixture_dependency="quota-axi", evidence=str(destination))
    result["scratch_removed"] = not lab.exists()
    results.append(result)
    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(name + ": " + result["result"] + ", exit " + str(run.returncode), flush=True)
    print(run.stdout, flush=True)
(EVIDENCE / "quota-live-results.json").write_text(json.dumps(results, indent=2) + "\n")
raise SystemExit(any(r["result"] != "pass" or not r["scratch_removed"] for r in results))
