#!/usr/bin/env python3
"""Drive the real quota producer, resolver, and worker CLI with isolated data."""
import copy
import datetime as dt
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import threading

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
BASE = "65a9a51f099e91c5e2d05c9ae9c3d5e493d51762"
records = []
requests = []


class RuleEndpoint(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == "/v1/systemone"
        assert set(body["questions"]["rule"]["criteria"]) == {"rule_1", "default"}
        requests.append(body)
        answer = {"model": "local-rule-fixture", "answers": {"rule": {
            "choice": "rule_1", "confidence": 1,
            "probabilities": {"rule_1": 1, "default": 0}}}}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(answer).encode())

    def log_message(self, *args):
        pass


def command(name, argv, env, expected_code, expected_text, stdin=None):
    run = subprocess.run(argv, env=env, input=stdin, text=True,
                         capture_output=True, timeout=30)
    passed = run.returncode == expected_code and expected_text in run.stdout + run.stderr
    records.append({"case": name, "command": argv, "exit_code": run.returncode,
                    "stdout": run.stdout, "stderr": run.stderr,
                    "expected_exit": expected_code, "expected_text": expected_text,
                    "result": "pass" if passed else "fail"})
    if not passed:
        raise AssertionError(json.dumps(records[-1], indent=2))
    return run.stdout


def cached_row(provider, key, remaining, aliases=None):
    now = dt.datetime.now(dt.timezone.utc)
    row = {"provider": provider, "label": provider, "source": "oauth",
           "state": {"status": "fresh", "sourcesTried": ["snapshot"],
                     "refreshedAt": now.isoformat()},
           "windows": [{"id": "five_hour", "label": "session", "kind": "session",
                        "windowSeconds": 18000, "percentUsed": 100 - remaining,
                        "percentRemaining": remaining,
                        "startsAt": (now - dt.timedelta(hours=2)).isoformat(),
                        "resetsAt": (now + dt.timedelta(hours=3)).isoformat()}]}
    if key is not None:
        row["accountKey"] = key
    if aliases is not None:
        row["reuse"] = {"context": "a" * 64, "inputs": [], "inputsDigest": "b" * 64,
                        "readingAt": now.isoformat(), "lanes": 1, "lane": 0,
                        "accountKeys": aliases}
    return row


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    with tempfile.TemporaryDirectory(prefix=".account-live-", dir=ROOT) as temporary:
        lab = Path(temporary)
        (lab / "config").mkdir()
        (lab / "tmp").mkdir()
        brief = lab / "brief.md"
        brief.write_text("# Task\nValidate account matching with the only configured rule.\n")
        cache = lab / "quota-cache.json"
        snapshot_file = lab / "quota.json"
        env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LANG": "C",
               "TMPDIR": str(lab / "tmp"), "FM_HOME": str(lab),
               "XDG_CONFIG_HOME": str(lab / "xdg-config"),
               "XDG_CACHE_HOME": str(lab / "xdg-cache"),
               "QUOTA_AXI_SNAPSHOT": str(cache), "FM_DISPATCH_PROVIDER": "systemone",
               "FM_DISPATCH_MODEL": "local-rule-fixture"}
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RuleEndpoint)
        env["FM_DISPATCH_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            folded = cached_row("codex", "credential-primary", 80,
                                ["credential-alias", "codex-home"])
            other_provider = cached_row("claude", "other", 0, ["codex-home", "credential-alias"])
            fallback = cached_row("codex", "default", 0)
            positive_fallback = cached_row("codex", "default", 91)
            exact = cached_row("codex", "codex-home", 0)
            ambiguous = cached_row("codex", "other-credential", 60, ["codex-home", "credential-alias"])
            cases = [
                ("unique-alias-without-default", [folded, other_provider], "remaining=80%", 0, "codex default"),
                ("unique-alias-reversed", [other_provider, folded], "remaining=80%", 0, "codex default"),
                ("unique-alias-before-exhausted-default", [fallback, folded], "remaining=80%", 0, "codex default"),
                ("exact-wins-over-two-aliases-and-default", [folded, ambiguous, positive_fallback, exact], "remaining=0%", 1, "none"),
                ("exact-wins-reversed", [exact, positive_fallback, ambiguous, folded], "remaining=0%", 1, "none"),
                ("ambiguous-alias-with-default", [folded, ambiguous, positive_fallback], "eligible, unranked: provider codex has no quota row for account codex-home", 1, "none"),
                ("ambiguous-alias-reversed", [positive_fallback, ambiguous, folded], "eligible, unranked: provider codex has no quota row for account codex-home", 1, "none"),
                ("ambiguous-alias-without-default", [folded, ambiguous], "eligible, unranked: provider codex has no quota row for account codex-home", 1, "none"),
                ("absent-alias-default-fallback", [cached_row("codex", "other", 0), positive_fallback], "remaining=91%", 0, "codex default"),
                ("empty-alias-default-fallback", [cached_row("codex", "other", 0, []), positive_fallback], "remaining=91%", 0, "codex default"),
                ("missing-row-remains-unranked", [cached_row("codex", "other", 80)], "eligible, unranked: provider codex has no quota row for account codex-home", 1, "none"),
                ("whitespace-alias-exact-match", [cached_row("codex", "codex-home", 80, ["codex-home", "work account"])], "remaining=80%", 0, "codex default"),
                ("duplicate-alias-in-one-row", [cached_row("codex", "primary", 80, ["codex-home", "codex-home"])], "remaining=80%", 0, "codex default"),
                ("schema5-provider-match", [cached_row("codex", None, 80)], "remaining=80%", 0, "codex default"),
            ]
            unique_snapshot = None
            for name, rows, expected, helper_code, helper_text in cases:
                dump(cache, {"schemaVersion": 3, "providers": rows})
                snapshot = command(name + "/producer", ["quota-axi", "--json"], env, 0, '"providers"')
                snapshot_file.write_text(snapshot)
                parsed = json.loads(snapshot)
                records[-1]["input_cache"] = {"schemaVersion": 3, "providers": rows}
                assert parsed["schemaVersion"] == (5 if name.startswith("schema5") else 6)
                if name == "unique-alias-without-default":
                    unique_snapshot = snapshot
                    assert any(r["provider"] == "codex" and
                               {"credential-alias", "codex-home"}.issubset(r.get("accountKeys", []))
                               for r in parsed["providers"])
                dump(lab / "config/crew-dispatch.json", {"rules": [{"when": "Validate account matching.",
                     "use": [{"harness": "codex", "model": "default"}]}]})
                resolved = command(name + "/resolver", [str(ROOT / "bin/fm-dispatch-resolve.sh"), str(brief)], env, 0, expected)
                if "unranked" in expected:
                    assert "status: escalate" in resolved and "profile:" not in resolved
                elif helper_code == 0:
                    assert "status: clear" in resolved and "profile:" in resolved
                command(name + "/worker", [str(ROOT / "bin/fm-quota-choose.sh"), "--snapshot", str(snapshot_file),
                                            "--candidate", "codex:default"], env, helper_code, helper_text)
                if name == "unique-alias-without-default":
                    dump(lab / "config/crew-dispatch.json", {"rules": [{"when": "Validate account matching.",
                         "use": [{"harness": "pi", "model": "credential-alias/gpt-6-astra", "provider": "codex"}]}]})
                    command("pi-lane-alias/resolver", [str(ROOT / "bin/fm-dispatch-resolve.sh"), str(brief)], env, 0, "remaining=80%")
                    command("stdin-snapshot/worker", [str(ROOT / "bin/fm-quota-choose.sh"), "codex:default"], env, 0, "codex default", snapshot)

            valid = json.loads(unique_snapshot)
            for malformed in (None, "codex-home", 1, False, {}, [""], ["codex-home", 7], [None], [[]]):
                document = copy.deepcopy(valid)
                next(r for r in document["providers"] if r["provider"] == "codex")["accountKeys"] = malformed
                dump(snapshot_file, document)
                command("malformed-accountKeys=" + json.dumps(malformed),
                        [str(ROOT / "bin/fm-quota-choose.sh"), "--snapshot", str(snapshot_file), "codex:default"],
                        env, 2, "invalid quota-axi provider data")

            document = copy.deepcopy(valid)
            row = next(r for r in document["providers"] if r["provider"] == "codex")
            row["accountKey"] = "work account"
            dump(snapshot_file, document)
            command("accountKey-whitespace-still-invalid", [str(ROOT / "bin/fm-quota-choose.sh"),
                    "--snapshot", str(snapshot_file), "codex:default"], env, 2, "invalid quota-axi provider data")

            dump(cache, {"schemaVersion": 3, "providers": [cached_row("codex", "codex-home", 80, [""])]})
            command("malformed-empty-alias/resolver", [str(ROOT / "bin/fm-dispatch-resolve.sh"), str(brief)],
                    env, 0, "quota-axi --json returned an invalid snapshot")

            base_dir = lab / "base"
            base_dir.mkdir()
            archive = subprocess.check_output(["git", "archive", BASE, "bin"])
            with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
                contents.extractall(base_dir, filter="data")
            snapshot_file.write_text(unique_snapshot)
            command("regression-before-fix", [str(base_dir / "bin/fm-quota-choose.sh"),
                    "--snapshot", str(snapshot_file), "codex:default"], env, 1, "none")
            command("regression-after-fix", [str(ROOT / "bin/fm-quota-choose.sh"),
                    "--snapshot", str(snapshot_file), "codex:default"], env, 0, "codex default")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


try:
    main()
finally:
    dump(EVIDENCE / "account-matching-live.json", {"records": records, "classifier_requests": requests,
         "isolation": "Real Firstmate CLIs, real curl, real installed quota-axi in documented QUOTA_AXI_SNAPSHOT mode. Local HTTP fixture selects the sole dispatch rule; it does not perform account matching. No credentials or vendor APIs used. Temporary data and server removed."})
    transcript = []
    for record in records:
        if record["case"].endswith("/producer"):
            continue
        transcript.extend(["CASE " + record["case"], "$ " + " ".join(record["command"]),
                           record["stdout"].rstrip(), record["stderr"].rstrip(),
                           f"exit={record['exit_code']} result={record['result']}", ""])
    (EVIDENCE / "account-matching-transcript.txt").write_text("\n".join(transcript))
print(f"{len(records)} commands passed; {len(requests)} real HTTP resolver requests; temporary data and endpoint removed")
