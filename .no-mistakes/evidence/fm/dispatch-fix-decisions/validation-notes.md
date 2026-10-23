# Dispatch validation evidence

Target: `175a583f56777d1913c6f00bb583d71d91573d27`.

`live_resolver.py` executes the worktree's resolver, the live TypeSafe API, Pi 1.4.0, and quota-axi 0.1.55.
Quota data comes from quota-axi's documented `QUOTA_AXI_SNAPSHOT` input with a disposable synthetic cache record.
The quota CLI itself runs unchanged; it does not query real quota accounts in snapshot mode.
Temporary homes, account roots, configuration, and instrumentation stay inside the worktree and are removed after each run.
Instrumentation delegates to the real Pi and quota executables and records arguments, exit codes, ordering, and duration.
On macOS, a `mktemp` wrapper supplies an explicit worktree-local template so temporary rules can be observed without inspecting system temporary directories.

## Product evidence

- `determinism.txt`: five real resolver calls returned the same profile line.
- `live-resolver.json`: complete resolver output, actual CLI calls, expiry and malformed-date results, low-confidence resolution, approval and declared-floor refusals, and observed temporary-file permissions and cleanup.
- `live-quota.json`: real quota-axi output from the disposable snapshot.
- `live-refresh-timeout.json`: a real Pi auth-check process was suspended with SIGSTOP; the resolver stopped it and still resolved in 10.608 seconds.

The live low-confidence answer had confidence 0.43 and returned a clear profile with a low-confidence note.
The approval-gated equivalent had confidence 0.48 and returned no profile.
The declared-floor scenario returned `ambiguous` when its rule probability did not reach 1.
The live equal-probability attempt returned 0.48 and 0.44, so it did not exercise an exact tie.

## Setup corrections

The first live driver's cleanup assertion incorrectly included Node's compile-cache directory.
The corrected driver observes regular rule files and verifies their removal; all sampled file modes were 0600 or 0400.
The first timeout fixture used quota-axi's compact report as a cache record and was rejected.
The corrected cache includes the required label, source, source-attempt list, and window timing; a real quota-axi preflight validates it before the timeout scenario.

Two targeted suites initially refused their fixture workers because their temporary homes were inside the source root.
Diagnostic reruns identified the exact refusal: `secondmate home cannot be inside the firstmate repo`.
Their final reruns use a byte-identical export of tracked files with sibling fixture homes, all inside the worktree.
The liveness suite also requires a Git index because the remote-command interface refuses untracked executables.
Its exported fixture therefore receives an isolated Git index before execution, without changing the gate checkout or its Git metadata.
The temporary diagnostic edits were reverted.
`targeted-tests.json`, `targeted-tests-retest.json`, `targeted-tests-isolated.json`, and `targeted-tests-indexed.json` retain the separate command outcomes.

## Limits

Successful renewal of a real expired vendor token was not tested.
Both real Pi checks used an empty disposable account root and returned exit 1; their failures did not stop routing.
Production credentials were neither copied nor changed, and no login was performed.
`pi-signed` was absent from PATH; executable selection is covered by the behavioral suite, not a real signed CLI run.
The behavioral suite covers exact probability ties and unoffered answer IDs for both decision providers.
The live TypeSafe API did not emit those malformed or tied answers, and no OpenRouter key was available.
The instruction to pass a clear profile unchanged was reviewed as documentation; a full agent-driven spawn was not exercised.
No linters, full repository test run, PR operation, merge, or CI phase was executed.
