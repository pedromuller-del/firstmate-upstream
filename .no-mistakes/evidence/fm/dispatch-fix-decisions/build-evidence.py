import json
import os
import pathlib

evidence = pathlib.Path(__file__).parent
lab = pathlib.Path.cwd() / ".dispatch-validation"
def read(name):
    return (evidence / name).read_text()

profiles = [next(line for line in read(f"live-repeat-{n}.log").splitlines() if line.startswith("  profile:")) for n in range(1, 6)]
assert len(set(profiles)) == 1
assert "low confidence:" in read("live-tie.log")
assert "low confidence:" in read("live-ambiguous.log")
assert "status: escalate" in read("live-low-confidence-approval.log")
assert "status: ambiguous" in read("live-declared-floor.log")

decoder = json.JSONDecoder()
raw = read("live-expiry-requests.jsonl").strip()
requests = []
while raw:
    request, end = decoder.raw_decode(raw)
    requests.append(request)
    raw = raw[end:].strip()
assert all(set(request["questions"]["rule"]["criteria"]) == {"default", "rule_1"} for request in requests)
assert not any((evidence / f"live-{name}-requests.jsonl").exists() for name in ("all-expired", "bad-date", "bad-leap"))
for name in ("refresh", "refresh-default"):
    calls = read(f"live-{name}-calls.log").splitlines()
    assert len(calls) == 3
    assert calls[0].endswith("argv=auth check --provider anthropic ")
    assert calls[1] == "pi exit=1"
    assert calls[2] == "quota argv=--json --max-age 2m "
assert "/pi-pinned argv=" in read("live-refresh-default-calls.log")
for name in ("pin-refused", "signed-missing", "expiry"):
    assert read(f"live-{name}-calls.log").splitlines() == ["quota argv=--json --max-age 2m "]
assert not any(path.is_file() for path in (lab / "tmp").iterdir())

intro = "Real resolver, real TypeSafe jev-1.14.0, and installed quota-axi 0.1.55.\nQuota came from a synthetic dataset through quota-axi's documented QUOTA_AXI_SNAPSHOT mode.\nThe 80% value is test data, not an operator account measurement.\nNo operator credentials were copied or refreshed.\n\n"
routing = intro + "Five repeated requests returned identical profile lines:\n" + "\n".join(profiles) + "\n\n"
for name in ("repeat-1", "repeat-2", "repeat-3", "repeat-4", "repeat-5", "tie", "ambiguous", "approval", "low-confidence-approval", "declared-floor"):
    routing += read(f"live-{name}.log") + "\n"
(evidence / "dispatch-routing.log").write_text(routing)
guards = intro
for name in ("expiry", "all-expired", "bad-date", "bad-leap", "valid-leap", "refresh", "refresh-default", "pin-refused", "signed-missing"):
    guards += read(f"live-{name}.log") + "\n"
    calls_path = evidence / f"live-{name}-calls.log"
    if calls_path.exists():
        guards += "Observed dependency calls:\n" + calls_path.read_text() + "\n"
guards += "Actual expiry request criteria:\n" + json.dumps(requests[-1]["questions"]["rule"]["criteria"], indent=2) + "\n"
guards += "All-expired and malformed configurations produced no HTTP request.\n"
guards += "Nonempty temporary files sampled with mode 600; no temporary regular files remained after resolver exits.\n"
guards += "\nFault-injection check: a wrapper delayed Pi for 30 seconds. This is supplemental, not proof of live OAuth renewal.\n" + read("live-timeout.log")
(evidence / "dispatch-guards.log").write_text(guards)
fixtures = {
    "quota": json.loads((lab / "quota.json").read_text()),
    "rules": {str(path.parent.relative_to(lab)): json.loads(path.read_text()) for path in lab.glob("**/crew-dispatch.json") if "package" not in path.parts},
    "briefs": {path.name: path.read_text() for path in lab.glob("*.md")},
}
(evidence / "disposable-fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
for key_name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY"):
    secret = os.environ.get(key_name)
    if secret:
        assert not any(secret.encode() in path.read_bytes() for path in evidence.iterdir() if path.is_file()), f"secret found: {key_name}"
print("Evidence assertions passed: identical profiles, low-confidence output, approval/floor guards, filtered HTTP criteria, Pi order and pin, no ambient fallback, cleanup, and no API-key values in evidence.")
