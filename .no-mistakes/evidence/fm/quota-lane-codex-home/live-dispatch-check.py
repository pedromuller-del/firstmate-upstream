import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
quota_bin = shutil.which("quota-axi")
assert quota_bin
assert os.environ.get("TYPESAFE_API_KEY"), "TYPESAFE_API_KEY missing"

def profile(harness, model, provider="codex"):
    return dict(harness=harness, model=model, provider=provider)

home = profile("pi", "openai-codex/gpt-5.6-sol")
sibling = profile("pi", "openai-codex-muller-labs/gpt-5.6-luna")
cases = [
    ("home-fallback", [home, sibling], "pi", "openai-codex/gpt-5.6-sol"),
    ("native-codex", [profile("codex", "gpt-5.6-sol"), sibling], "codex", "gpt-5.6-sol"),
    ("pi-native", [profile("pi", "codex-native/gpt-6-astra"), sibling], "pi", "codex-native/gpt-6-astra"),
    ("pi-signed-home", [profile("pi-signed", "openai-codex/gpt-5.6-sol"), sibling], "pi-signed", "openai-codex/gpt-5.6-sol"),
    ("non-codex", [home, sibling, profile("cursor", "cursor-grok-4.6-medium", "cursor")], "cursor", "cursor-grok-4.6-medium"),
]
with tempfile.TemporaryDirectory(prefix=".quota-live-", dir=ROOT) as directory:
    lab = Path(directory)
    config = lab / "config"
    wrappers = lab / "wrappers"
    config.mkdir()
    wrappers.mkdir()
    wrapper = wrappers / "quota-axi"
    wrapper.write_text('#!/bin/bash\nset -o pipefail\n"$LIVE_QUOTA_BIN" "$@" --provider codex,cursor --no-credential-refresh | tee "$LIVE_QUOTA_SNAPSHOT"\n')
    wrapper.chmod(0o755)
    brief = lab / "brief.md"
    brief.write_text("# Codex quota routing validation\n\nFix a documented shell-script off-by-one bug whose root cause is already proven. This is a small coding bug fix.\n")
    env = dict(os.environ, LC_ALL="C", LANG="C", FM_HOME=str(lab), FM_CONFIG_OVERRIDE=str(config), LIVE_QUOTA_BIN=quota_bin, PATH=str(wrappers) + os.pathsep + os.environ["PATH"])
    env.pop("FM_ROOT_OVERRIDE", None)
    outcomes = []
    for label, candidates, chosen_harness, chosen_model in cases:
        (config / "crew-dispatch.json").write_text(json.dumps({"rules": [{"when": "Any coding task, including a small shell-script bug fix with an already-proven root cause.", "use": candidates}]}))
        snapshot = EVIDENCE / ("live-" + label + "-quota.json")
        env["LIVE_QUOTA_SNAPSHOT"] = str(snapshot)
        command = ["bash", "bin/fm-dispatch-resolve.sh", str(brief), "--project", "quota-validation"]
        result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=120)
        transcript = "command: FM_HOME=<isolated worktree directory> bash bin/fm-dispatch-resolve.sh <brief> --project quota-validation\nquota command: quota-axi --json --provider codex,cursor --no-credential-refresh (fresh real output forwarded unchanged)\n\n" + result.stdout + result.stderr + f"\nexit_code={result.returncode}\n"
        (EVIDENCE / ("live-" + label + ".log")).write_text(transcript)
        errors = []
        if result.returncode != 0:
            errors.append("nonzero exit")
        if "  status: clear" not in result.stdout:
            errors.append("not clear")
        expected = f"  profile: --harness '{chosen_harness}' --model '{chosen_model}'"
        if expected not in result.stdout:
            errors.append("unexpected selection")
        if snapshot.exists():
            quota = json.loads(snapshot.read_text())
            rows = {(r["provider"], r["accountKey"]): r for r in quota["providers"]}
            for candidate in candidates:
                key = "openai-codex-muller-labs" if candidate["model"].startswith("openai-codex-muller-labs/") else "codex-home"
                if candidate["provider"] == "cursor":
                    key = "default"
                row = rows[(candidate["provider"], key)]["quotaSemantics"]["effectiveAvailability"]
                bound = next(r for r in row if r["scope"] == "all_models")
                prefix = f'  candidate: {candidate["harness"]}:{candidate["model"]}  '
                lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
                if len(lines) != 1 or f'remaining={bound["effectivePercentRemaining"]}%' not in lines[0]:
                    errors.append("quota mismatch for " + candidate["model"])
                elif key == "openai-codex-muller-labs":
                    if "not eligible: runway exhausted_now" not in lines[0]:
                        errors.append("exhausted sibling was not blocked")
                elif "unranked" in lines[0] or f'spendPriority={bound["selection"]["spendPriority"]}' not in lines[0]:
                    errors.append("candidate was not ranked with its real spendPriority")
        else:
            errors.append("no real quota read")
        outcomes.append(dict(name=label, result="fail" if errors else "pass", errors=errors, exit_code=result.returncode))
        print(transcript, flush=True)
        print(json.dumps(outcomes[-1]), flush=True)
    (EVIDENCE / "live-results.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    raise SystemExit(any(r["errors"] for r in outcomes))
