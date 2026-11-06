# Test phase record

Target commit: `88404c222c9cf4a2e8f49efa3b3b20b182296359`.

Nine live scenarios passed. Six previously accepted live limitations remain. No product failure was observed. No source or test file was changed. The outer executor retains delivery authority.

## Offline commands

All isolated commands unset `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, and `FM_DISPATCH_API_KEY`, and use `LC_ALL=C`.

| Command | Reported checks | Exit |
| --- | --- | --- |
| `bash tests/fm-dispatch-resolve.test.sh` | 78 passed, 0 failed | 0 |
| `bash tests/fm-procevent-quota.test.sh` | 33 passed, 0 failed | 0 |
| `bash tests/fm-startup-memory-budget.test.sh` | 4 passed, 0 failed | 0 |
| `bash tests/fm-secondmate-sync.test.sh` | 33 passed, 0 failed | 0 |
| `bash tests/fm-secondmate-liveness.test.sh` | 28 passed, 0 failed | 0 |
| `bash tests/fm-shared-captain-inheritance.test.sh` | 13 passed, 0 failed | 0 |
| `bash tests/fm-quota-choose.test.sh` | 58 passed, 0 failed | 0 |
| `bash tests/fm-secondmate-harness.test.sh` | 49 passed, 0 failed before the local 240-second cap | Interrupted |
| Seven remaining existing harness cases, selected by `complete-targeted-cases.py` | 7 passed, 0 failed | 0 |
| `bash tests/fm-bootstrap.test.sh` | 30 passed, 0 failed before the local 240-second cap | Interrupted |
| Existing `test_crew_dispatch_validation`, selected by `complete-targeted-cases.py` | 1 passed, 0 failed | 0 |
| `bash tests/fm-spawn-dispatch-profile.test.sh` | 40 passed, 0 failed before the local 240-second cap | Interrupted; optional broader suite incomplete |

The harness and bootstrap cases completed across the original run and fresh isolated fixture selections. Their original complete-suite commands did not exit successfully. The optional spawn run passed its explicit-profile and model/effort forwarding checks before interruption; its unrelated remaining cases were not run. These are targeted checks, not a replacement for remote CI.

The initial resolver run inherited the real TypeSafe key. Its absent-key case failed after 21 passing checks, with exit 1. The isolated rerun above corrected that setup and passed all 78 checks.

## Product evidence and cleanup

`live-dispatch.py` ran the real resolver against TypeSafe using synthetic inputs. Forwarding observers recorded the real Pi and quota-axi calls. Quota reads used an empty isolated Codex profile, so missing credentials returned exit 1; no healthy quota reuse or OAuth renewal was inferred.

`verify-live.py` checked the captured public output, protocol responses, process order, and temporary-file modes: nine live scenarios passed, zero failed. `live-report.md` contains the product output and the six limitations.

`primary-probe.py` started Claude on a private tmux socket with a 120-column by 40-row terminal. The first socket path exceeded the OS limit; a shorter evidence-local path worked. Claude reached the workspace-trust dialog. The probe did not change trust settings. It stopped the private server with exit 0 and removed the lab.

The installed tools reported Pi `1.5.0` and quota-axi `0.1.55`. `pi-signed` was absent from PATH. OpenRouter and OpenAI probes reported their keys absent. No host search or installation was performed.

The evidence directory was checked for the supplied API-key values; none were present. All disposable live labs were removed. The worktree remained clean.
