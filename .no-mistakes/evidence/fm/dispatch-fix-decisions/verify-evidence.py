import json
from pathlib import Path
import re

evidence = Path(__file__).parent
records = json.loads((evidence / "live-results.json").read_text()) + json.loads((evidence / "live-results-extra.json").read_text())
by_name = {record["name"]: record for record in records}
assert all(record["pass"] for record in records)
assert len(json.loads((evidence / "expired-and-future-request.json").read_text())["questions"]["rule"]["criteria"]) == 2
for number in range(1, 7):
    record = by_name[f"invalid-until-{number}"]
    assert record["exit"] == 2 and not record["events"]
low = json.loads((evidence / "low-confidence-5-response.json").read_text())["answers"]["rule"]
assert low["confidence"] < 0.6
assert low["choice"] == max(low["probabilities"], key=low["probabilities"].get)
assert "status: clear" in by_name["low-confidence-5"]["stdout"]
assert "low confidence:" in by_name["low-confidence-5"]["stdout"]
assert json.loads((evidence / "low-confidence-approval-response.json").read_text())["answers"]["rule"]["confidence"] < 0.6
assert "status: escalate" in by_name["low-confidence-approval"]["stdout"]
pi_events = by_name["pi-failure-nonfatal"]["events"]
assert pi_events.count("pi start auth check --provider anthropic") == 1
assert pi_events.count("pi start auth check --provider openai-codex") == 1
assert pi_events.count("pi exit 1") == 2
assert pi_events.rindex("pi exit 1") < pi_events.index("quota-axi start --json --max-age 2m")
assert "pi start" not in by_name["pi-refused-pin"]["events"]
assert 10 <= by_name["pi-timeout"]["seconds"] <= 15
assert "pi start auth check --provider anthropic" in by_name["pi-timeout"]["events"]
assert "quota-axi exit 0" in by_name["pi-timeout"]["events"]
assert all(record["events"].count("quota-axi start --json --max-age 2m") <= 1 for record in records)
offline = json.loads((evidence / "response-boundaries-results.json").read_text())
assert len(offline) == 6 and all(record["pass"] for record in offline)
for provider in ("typesafe", "openrouter"):
    assert "Regression reproduced: True" in (evidence / f"offline-{provider}-effective-rule.txt").read_text()

selected = ["clear", "expired-and-future", "all-expired", "invalid-until-1", "invalid-until-2", "invalid-until-3", "invalid-until-4", "invalid-until-5", "invalid-until-6", "valid-leap-day", "low-confidence-5", "low-confidence-approval", "declared-floor", "pi-failure-nonfatal", "pi-refused-pin", "pi-timeout", "tie-attempt-2", "tie-attempt-3"]
text = "Real dispatch CLI evidence\n\nThe decision API calls used the existing TYPESAFE_API_KEY without copying it.\nThe installed quota-axi 0.1.55 consumed newly generated synthetic quota windows through its documented QUOTA_AXI_SNAPSHOT input. These runs do not prove vendor cache reuse or expired-token renewal.\nThe installed Pi CLI used disposable empty account roots. Logging wrappers delegated to the real executables and did not replace their responses.\nEvery disposable home was removed. No primary or worker was launched.\n\n"
for name in selected:
    text += f"===== {name} =====\n" + (evidence / f"{name}.txt").read_text() + "\n"
(evidence / "dispatch-live-evidence.txt").write_text(text)
text = "Offline response boundary checks\n\nThese cases inject typed responses and quota data. They are not live model checks.\nThe effective-rule regression runs the same inputs against 59b5165a^ and the target checkout.\n\n"
for provider in ("typesafe", "openrouter"):
    for name in ("effective-rule", "probability-tie", "unoffered-choice"):
        text += (evidence / f"offline-{provider}-{name}.txt").read_text() + "\n"
(evidence / "response-boundary-evidence.txt").write_text(text)
print(f"Verified {len(records)} real CLI invocations and 6 offline boundary cases; no failed final checks.")
