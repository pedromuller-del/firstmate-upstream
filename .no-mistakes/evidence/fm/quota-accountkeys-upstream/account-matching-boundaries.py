#!/usr/bin/env python3
"""Check remaining raw-input boundaries and the corrected regression oracle."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
BASE = "65a9a51f099e91c5e2d05c9ae9c3d5e493d51762"
TARGET = "29ff8e20ec4319f5478a88691a99926d6159b2e9"
previous = json.loads((EVIDENCE / "account-matching-live.json").read_text())
records = []


def run(name, argv, env, code, expected):
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=240)
    passed = result.returncode == code and expected in result.stdout + result.stderr
    records.append({"case": name, "command": argv, "exit_code": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr,
                    "expected_exit": code, "expected_text": expected,
                    "result": "pass" if passed else "fail"})
    assert passed, json.dumps(records[-1], indent=2)
    print(name + ': pass', flush=True)
    return result


try:
    with tempfile.TemporaryDirectory(prefix=".quota-boundaries-", dir=ROOT) as temporary:
        lab = Path(temporary)
        (lab / "tmp").mkdir()
        env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LANG": "C",
               "TMPDIR": str(lab / "tmp"), "FM_HOME": str(lab),
               "XDG_CONFIG_HOME": str(lab / "xdg-config"), "XDG_CACHE_HOME": str(lab / "xdg-cache")}
        original = json.loads(previous["records"][0]["stdout"])
        snapshot = lab / "quota.json"
        for name, aliases, expected in [
            ("empty-array-default-fallback", [], "codex default"),
            ("absent-array-default-fallback", None, "codex default"),
            ("duplicate-alias-same-row", ["codex-home", "codex-home"], "codex default"),
            ("whitespace-only-alias-accepted", ["codex-home", " "], "codex default")]:
            document = copy.deepcopy(original)
            codex = next(row for row in document["providers"] if row["provider"] == "codex")
            if aliases is None:
                codex.pop("accountKeys", None)
            else:
                codex["accountKeys"] = aliases
            if aliases in (None, []):
                codex["accountKey"] = "default"
            snapshot.write_text(json.dumps(document))
            run(name, [str(ROOT / "bin/fm-quota-choose.sh"), "--snapshot", str(snapshot), "codex:default"], env, 0, expected)

        document = copy.deepcopy(original)
        next(row for row in document["providers"] if row["provider"] == "claude")["accountKeys"] = [8]
        snapshot.write_text(json.dumps(document))
        run("malformed-unrelated-provider-rejects-entire-snapshot", [str(ROOT / "bin/fm-quota-choose.sh"),
            "--snapshot", str(snapshot), "codex:default"], env, 2, "invalid quota-axi provider data")

        document = copy.deepcopy(original)
        document["schemaVersion"] = 5
        for row in document["providers"]:
            row.pop("accountKey", None)
            row["accountKeys"] = 7
        snapshot.write_text(json.dumps(document))
        run("schema5-still-ignores-accountKeys", [str(ROOT / "bin/fm-quota-choose.sh"),
            "--snapshot", str(snapshot), "codex:default"], env, 0, "codex default")

        cache = copy.deepcopy(next(record["input_cache"] for record in previous["records"]
                     if record["case"] == "whitespace-alias-exact-match/producer"))
        cache_file = lab / "quota-cache.json"
        env["QUOTA_AXI_SNAPSHOT"] = str(cache_file)
        cache_file.write_text(json.dumps(cache))
        poll = [str(ROOT / "bin/fm-procevent-quota.sh"), "poll", "--provider", "codex",
                "--threshold", "90", "--interval", "1", "--timeout", "3"]
        run("quota-event-accepts-whitespace-alias", poll, env, 0, "status: low")
        cache["providers"][0]["reuse"]["accountKeys"] = [""]
        cache_file.write_text(json.dumps(cache))
        run("quota-event-rejects-malformed-alias", poll, env, 0, "status: error")

        base_dir = lab / "base-with-current-tests"
        base_dir.mkdir()
        for revision, paths in [(BASE, ["bin"]), (TARGET, ["tests", "docs/examples"])]:
            archive = subprocess.check_output(["git", "archive", revision, *paths])
            with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
                contents.extractall(base_dir, filter="data")
        result = run("current-resolver-test-rejects-original-matcher",
                     ["bash", str(base_dir / "tests/fm-dispatch-resolve.test.sh")], env, 1,
                     "a credential key covered only by accountKeys binds to its producer row")
        lines = (result.stdout + result.stderr).splitlines()
        print(f"Regression oracle: {sum(line.startswith('ok - ') for line in lines)} preceding checks passed; "
              f"{sum(line.startswith('not ok - ') for line in lines)} expected failure; exit={result.returncode}")
finally:
    (EVIDENCE / "account-matching-boundaries.json").write_text(json.dumps(records, indent=2) + "\n")
    transcript = []
    for record in records:
        transcript.extend(["CASE " + record["case"], "$ " + " ".join(record["command"]),
                           record["stdout"].rstrip(), record["stderr"].rstrip(),
                           f"exit={record['exit_code']} expected_exit={record['expected_exit']} result={record['result']}", ""])
    (EVIDENCE / "account-matching-boundaries.txt").write_text("\n".join(transcript))
