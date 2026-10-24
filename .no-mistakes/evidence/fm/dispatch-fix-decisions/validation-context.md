# Dispatch validation context

Target: `ca23c0ac25d8da0a9ebed1a540570175ae53a28b`.
Base: `d22640f478e3392313e27b04fb41de12bd25d2e7`.

The live checks executed the worktree's `bin/fm-dispatch-resolve.sh`, the real TypeSafe Decisions API, installed Pi 1.4.0, and installed quota-axi 0.1.55. The API answered as `jev-1.14.0`.

The resolver used disposable `FM_HOME` directories. Pi used empty, disposable account roots. quota-axi consumed a synthetic cache-format snapshot through its documented `QUOTA_AXI_SNAPSHOT` interface. This proves resolver integration and the `--json --max-age 2m` invocation, not fresh vendor reads or the upstream cache implementation. No operator quota, configuration, or credentials were copied. The API key remained in memory and was passed through the resolver's normal descriptor-based interface.

Transparent CLI observers retained API request/response JSON, quota JSON, resolver output, and invocation order. They delegated to the real executables. A `jq` observer measured the filter output file's mode before its first write. A `mktemp` observer recorded generated paths so cleanup could be checked after exit.

The timeout experiment suspended a real Pi subprocess with SIGSTOP. The resolver continued after 10.865 seconds and emitted a clear profile. Both observed Pi process IDs were absent afterward. The first shell-based suspension attempt did not stall Pi and is retained in the trace; it is not the timeout proof. The second Python-based suspension produced the measured timeout.

`check-live-evidence.py` asserts the generated public outputs. `live-summary.txt` contains its verified results. These assertions inspect execution evidence, not implementation source.

## Setup corrections

The initial resolver and quota-selection suites inherited unavailable `C.UTF-8`. Locale warnings broke stderr assertions. They passed after setting `LC_ALL=C` and `LANG=C`.

The first secondmate-harness and secondmate-liveness runs placed temporary homes under the worktree. `fm-spawn.sh:3475` correctly refused those nested homes. Changing Bash alone did not resolve the refusal. The final rerun uses the toolchain's normal temporary directory, as allowed for incidental test fixtures. No guard was disabled and no product code changed.

## Previously accepted limits

Exact probability ties and unoffered response choices remain covered by the deterministic resolver suite. A live attempt using identical option text returned probabilities 0.62 and 0.37, not an exact tie. The real decision endpoint has no caller-controlled response injection interface. No replacement API response was counted as live.

Successful renewal of an expired Pi login remains untested. Empty isolated roots exercised real authentication failures, and the timeout experiment exercised a stalled real process. A successful renewal needs a dedicated authenticated Pi test account and authorization to refresh it; production credential mutation and credential copying were forbidden.

The primary's interpretation of the clear-profile instruction remains the previously accepted live limitation. No primary or worker was launched in this phase. The recorded test-round-1 decision accepted this scope, so it was not reopened or treated as a new finding.

OpenRouter response guards and pi-signed executable selection were exercised by deterministic behavioral tests, not by authenticated live vendor sessions. There was no OpenRouter key in the run environment and no pi-signed executable on PATH.

This phase did not run linters, static analysis, the complete repository suite, PR publication, CI, or merges. CLI transcripts are the applicable product evidence; the change has no rendered UI.

## Final targeted results

Every command below exited 0. Counts are the suites' reported `ok` checks, not a count of internal assertions. All ran with `LC_ALL=C` and `LANG=C`.

| Command | Passed | Failed |
| --- | ---: | ---: |
| `bash tests/fm-dispatch-resolve.test.sh` | 36 | 0 |
| `bash tests/fm-quota-choose.test.sh` | 58 | 0 |
| `bash tests/fm-bootstrap.test.sh` | 30 | 0 |
| `bash tests/fm-procevent-quota.test.sh` | 33 | 0 |
| `bash tests/fm-startup-memory-budget.test.sh` | 4 | 0 |
| `bash tests/fm-secondmate-sync.test.sh` | 33 | 0 |
| `bash tests/fm-secondmate-harness.test.sh` | 56 | 0 |
| `bash tests/fm-secondmate-liveness.test.sh` | 22 | 0 |
| `bash tests/fm-shared-captain-inheritance.test.sh` | 13 | 0 |
| Total | 285 | 0 |

The final two corrected runs used the original toolchain `TMPDIR`, without the diagnostic Bash override. The seven other suites used a worktree-local temporary directory. Suites ran serially.

Live commands were `python3 .dispatch-phase/run-live.py`, followed by focused invocations with `low_overlap floor_overlap approval_overlap tie_attempt`, `approval_low`, `expired invalid_date`, and `pi_override pi_bad_pin`. `DISPATCH_PAUSE_PI=1 python3 .dispatch-phase/run-live.py pi_pin` drove the stalled-Pi case. Each driver invoked `bin/fm-dispatch-resolve.sh <brief> --project disposable-dispatch-validation` with the isolated settings described above.

`python3 check-live-evidence.py` verified eight behavior groups, with zero failures and exit 0. The actual installed quota-axi passed `fm_quota_axi_compatible` with installed version 0.1.55 and required minimum 0.1.54, exit 0. The bootstrap suite covers rejection below that minimum.

All disposable validation files were removed. `git status --short` returned no entries and `git diff --exit-code` exited 0. No source or tracked test file changed during this phase.
