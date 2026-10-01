import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
RESULTS = []


def row(provider, account, remaining, spend):
    return {"provider": provider, "accountKey": account, "quotaSemantics": {
        "status": "known", "effectiveAvailability": [{"scope": "all_models",
        "status": "known", "effectivePercentRemaining": remaining,
        "runway": {"status": "exhausted_now" if remaining == 0 else "through_reset"},
        "selection": {"spendPriority": spend}}]}}


def snapshot(layout):
    rows = [row("codex", "codex-home", 97, .8),
            row("codex", "openai-codex-work", 0, -1.4),
            row("codex", "default", 0, -.5),
            row("cursor", "default", 24, .39)]
    if layout in ("both", "both-reversed"):
        rows.append(row("codex", "openai-codex", 0, -2))
    if layout == "both-reversed":
        rows.reverse()
    if layout == "default-only":
        rows = [row("codex", "default", 91, .7), rows[-1]]
    if layout == "schema5":
        rows = [rows[0], rows[-1]]
        for item in rows:
            del item["accountKey"]
    return {"generatedAt": "2026-10-01T12:00:00Z", "schemaVersion": 5 if layout == "schema5" else 6, "providers": rows}


def toon(data):
    keyed = data["schemaVersion"] == 6
    fields = "provider," + ("accountKey," if keyed else "")
    fields += "scope,effectivePercentRemaining,spendPriority,runway,confidence,limitedBy,resetsAt"
    lines = ["bin: quota-axi", 'generatedAt: "2026-10-01T12:00:00Z"', f'quota[{len(data["providers"])}]{{{fields}}}:']
    for provider in data["providers"]:
        bound = provider["quotaSemantics"]["effectiveAvailability"][0]
        values = [provider["provider"]] + ([provider["accountKey"]] if keyed else [])
        values += ["all_models", str(bound["effectivePercentRemaining"]), str(bound["selection"]["spendPriority"]), bound["runway"]["status"], "established", "weekly", '"2026-10-07T12:00:00Z"']
        lines.append("  " + ",".join(values))
    return "\n".join(lines + ["exhaustion[0]:", "attention[0]:", ""])


def run_case(name, harness="pi", pin="ordinary", ambient="alternate", layout="home", expected="ranked", location="use", non_pi=False):
    records = []
    with tempfile.TemporaryDirectory(prefix=".quota-live-", dir=ROOT) as tmp:
        scratch = Path(tmp)
        home, fmhome, fakebin = scratch/"user", scratch/"fm", scratch/"bin"
        ordinary, alternate = home/".pi/agent", scratch/"alternate-account"
        for path in (ordinary, alternate, fmhome/"config", fakebin, scratch/"tmp"):
            path.mkdir(parents=True, exist_ok=True)
        alias = scratch/"home account alias"
        alias.symlink_to(ordinary, target_is_directory=True)
        pinpath = fmhome/"config/pi-account"
        pins = {"ordinary": "ordinary\nopenai-codex openai-codex-work codex-native\n",
                "multiple": "ordinary\nanthropic openai-codex openai-codex-work\n",
                "absolute": str(ordinary)+"\nopenai-codex\n",
                "alias": str(alias)+"\nopenai-codex\n",
                "alternate": str(alternate)+"\nopenai-codex\n",
                "other-provider": "ordinary\nanthropic\n",
                "similar-provider": "ordinary\nanthropic openai-codex-work\n",
                "malformed": "ordinary\n",
                "missing-root": str(scratch/"absent")+"\nopenai-codex\n"}
        if pin in pins:
            pinpath.write_text(pins[pin])
        elif pin == "directory":
            pinpath.mkdir()
        data = snapshot(layout)
        quota = scratch/"quota.json"
        quota.write_text(json.dumps(data))
        stub = fakebin/"quota-axi"
        stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$QUOTA_CALL_LOG"\n[ "$#" -eq 1 ] && [ "$1" = --json ] || exit 2\ncat "$QUOTA_FIXTURE"\n')
        stub.chmod(0o755)
        brief = scratch/"brief.md"
        brief.write_text("# Quota routing validation\n\n## Captain's intent\nFix a documented off-by-one in the pager. The root cause is a <= comparison.\n\n## Firstmate spec\nChange that comparison so each request returns exactly one page.\n")
        profiles = [{"harness": harness, "model": "openai-codex/gpt-5.6-sol", "provider": "codex"},
                    {"harness": harness, "model": "openai-codex-work/gpt-5.6-luna", "provider": "codex"},
                    {"harness": "cursor", "model": "default"}]
        if layout == "schema5":
            profiles += [{"harness": "codex", "model": "gpt-5.6-sol"},
                         {"harness": harness, "model": "codex-native/gpt-6-astra", "provider": "codex"}]
        if non_pi:
            profiles = [profiles[-1]]
        if expected == "error":
            profiles = [profiles[-1], profiles[0]]
        rule = {"when": "Any software bug fix, including a pager off-by-one with a known root cause.", "use": profiles}
        config = {"rules": [rule], "default": profiles}
        if location == "default":
            rule["use"] = {"harness": "cursor", "model": "default"}
        (fmhome/"config/crew-dispatch.json").write_text(json.dumps(config))
        env = {"PATH": str(fakebin)+os.pathsep+os.environ["PATH"], "HOME": str(home),
               "FM_HOME": str(fmhome), "TMPDIR": str(scratch/"tmp"), "LANG": "en_US.UTF-8",
               "TYPESAFE_API_KEY": os.environ["TYPESAFE_API_KEY"], "QUOTA_FIXTURE": str(quota),
               "QUOTA_CALL_LOG": str(scratch/"quota.calls")}
        if ambient != "unset":
            env["PI_CODING_AGENT_DIR"] = str(ordinary if ambient == "home" else alternate)

        def execute(command, test):
            p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=25)
            errors = test(p)
            record = {"command": shlex.join(command), "exit_code": p.returncode,
                      "stdout": p.stdout, "stderr": p.stderr, "assertion_errors": errors}
            records.append(record)
            return p

        def check_dispatch(p):
            errors = []
            def check(value, message):
                if not value:
                    errors.append(message)
            check(p.returncode == (2 if expected == "error" else 0), "unexpected resolver exit code")
            if expected == "error":
                check(not p.stdout, "invalid pin must not select another candidate")
                check("error: config/pi-account" in p.stderr, "configuration error must name the pin")
                check(not (scratch/"quota.calls").exists(), "invalid pin must stop before quota collection")
                return errors
            check(not p.stderr, "unexpected resolver stderr")
            check((scratch/"quota.calls").read_text() == "--json\n" if (scratch/"quota.calls").exists() else False, "one quota snapshot must be consumed")
            if non_pi:
                check("profile: --harness 'cursor'" in p.stdout, "non-Pi dispatch must ignore an unrelated invalid pin")
                return errors
            line = next((x for x in p.stdout.splitlines() if f"candidate: {harness}:openai-codex/gpt-5.6-sol " in x), "")
            if expected == "ranked":
                check("remaining=97%  spendPriority=0.8" in line and line.endswith("-> eligible"), "pinned home candidate must use codex-home")
                check(f"profile: --harness '{harness}' --model 'openai-codex/gpt-5.6-sol'" in p.stdout, "home candidate must be selected")
                check("openai-codex-work/gpt-5.6-luna  provider=codex  scope=all_models  remaining=0%" in p.stdout, "sibling must retain its exhausted row")
            elif expected == "exhausted":
                check("remaining=0%" in line and "not eligible: runway exhausted_now" in line, "exhausted exact row must veto the candidate")
                check("profile: --harness 'cursor'" in p.stdout, "healthy home must not override exact-row veto")
            elif expected == "unranked":
                check("eligible, unranked:" in line and "disclosed uncertainty" in line, "unproven account must stay eligible and unranked")
                wanted = "openai-codex-work/gpt-5.6-luna'" if layout == "default-only" else "--harness 'cursor'"
                check("profile:" in p.stdout and wanted in p.stdout.split("profile:")[-1], "known eligible candidate must win")
            elif expected == "schema5":
                candidates = [x for x in p.stdout.splitlines() if "candidate:" in x and "provider=codex" in x]
                check(len(candidates) == 4 and all("remaining=97%  spendPriority=0.8" in x for x in candidates), "all Codex lanes must consume the single schema-5 provider row")
                check("reason: genuine spendPriority tie" in p.stdout and "profile:" not in p.stdout, "schema-5 tied candidates must not be arbitrarily selected")
            return errors

        execute(["bash", "bin/fm-dispatch-resolve.sh", str(brief), "--project", "quota-routing-validation"], check_dispatch)
        helper_data = copy.deepcopy(data)
        for provider in helper_data["providers"]:
            if provider["provider"] == "codex":
                provider["provider"] = "pi"
        for kind in ("json", "toon"):
            helper = scratch/("helper."+kind)
            helper.write_text(json.dumps(helper_data) if kind == "json" else toon(helper_data))
            candidate = f"{harness}:openai-codex/gpt-5.6-sol"
            command = ["bash", "bin/fm-quota-choose.sh", "--snapshot", str(helper)]
            if non_pi:
                command += ["--candidate", "cursor:default"]
            elif expected == "error":
                command += ["--candidate", "cursor:default", "--candidate", candidate]
            else:
                command += ["--candidate", candidate]
            def check_helper(p):
                if expected == "error":
                    return [] if p.returncode == 2 and not p.stdout and "error: config/pi-account" in p.stderr else ["helper must report invalid pin before selecting an earlier candidate"]
                selected = expected in ("ranked", "schema5") or non_pi
                wanted = "cursor default" if non_pi else f"{harness} openai-codex/gpt-5.6-sol" if selected else "none"
                return [] if p.returncode == (0 if selected else 1) and p.stdout.strip() == wanted and not p.stderr else ["unexpected helper selection or exit"]
            execute(command, check_helper)
        record = {"name": name, "harness": harness, "pin": pin, "ambient": ambient, "layout": layout,
                  "expected": expected, "location": location, "quota_fixture": data,
                  "rules": config, "environment": {k:v for k,v in env.items() if k != "TYPESAFE_API_KEY"},
                  "credential_source": "inherited TYPESAFE_API_KEY, never written to evidence",
                  "transport": "real curl and live api.typesafe.ai; quota-axi is the authorized snapshot stub",
                  "helper_provider_contract": "helper fixtures use its documented primary Pi provider mapping",
                  "checks": records, "result": "fail" if any(x["assertion_errors"] for x in records) else "pass"}
    record["scratch_removed"] = not Path(tmp).exists()
    RESULTS.append(record)
    (EVIDENCE/"live-quota-results.json").write_text(json.dumps(RESULTS, indent=2)+"\n")
    text = [f"Case: {name}", f"Result: {record['result']}", "Real resolver/service; authorized quota snapshot stub; no account login used.",
            f"Pin: {pin}; ambient: {ambient}; layout: {layout}; harness: {harness}"]
    for item in records:
        text += ["$ "+item["command"], item["stdout"], item["stderr"], f"exit_code: {item['exit_code']}", "assertion_errors: "+json.dumps(item["assertion_errors"])]
    text += [f"scratch_removed: {record['scratch_removed']}"]
    (EVIDENCE/(name+".log")).write_text("\n".join(text)+"\n")
    print(name+": "+record["result"], flush=True)


for harness in ("pi", "pi-signed"):
    for pin in ("ordinary", "multiple", "absolute", "alias"):
        run_case(harness+"-home-"+pin, harness=harness, pin=pin)
    for layout in ("both", "both-reversed"):
        run_case(harness+"-exact-"+layout, harness=harness, layout=layout, expected="exhausted")
    run_case(harness+"-default-only", harness=harness, layout="default-only", expected="unranked")
    run_case(harness+"-schema5", harness=harness, layout="schema5", expected="schema5")
    for ambient in ("unset", "home", "alternate"):
        run_case(harness+"-unpinned-"+ambient, harness=harness, pin="absent", ambient=ambient, expected="unranked")
    run_case(harness+"-alternate-pin", harness=harness, pin="alternate", ambient="home", expected="unranked")
    for pin in ("other-provider", "similar-provider"):
        run_case(harness+"-"+pin, harness=harness, pin=pin, expected="unranked")
    for pin in ("malformed", "missing-root", "directory"):
        for location in ("use", "default"):
            run_case(harness+"-invalid-"+pin+"-"+location, harness=harness, pin=pin, expected="error", location=location)
run_case("non-pi-invalid-pin", pin="malformed", non_pi=True)
print(json.dumps({"passed": sum(x["result"] == "pass" for x in RESULTS), "failed": sum(x["result"] == "fail" for x in RESULTS), "commands": sum(len(x["checks"]) for x in RESULTS)}))
raise SystemExit(any(x["result"] == "fail" for x in RESULTS))
