# Quota routing validation

Target: `2e9d865a2c34511b99c621cc11e1995771e6a1bf`. Base: `f5735dc28a83186ef95715c8683333245762a8c6`.

Five real-service resolver calls passed. All three requested alternate snapshot cases passed executable-interface tests; schema 5 also passed against real quota data. The exact-plus-home and neither-named-row layouts were not available from the live account configuration and are not claimed as live.

## Commands and results

- `bash tests/fm-dispatch-resolve.test.sh`, with `TYPESAFE_API_KEY` removed, `LC_ALL=C`, `LANG=C`, and `TMPDIR` inside the isolated worktree directory: 24 passing groups, exit 0.
- `bash tests/fm-quota-choose.test.sh`, under the same environment: 55 passing groups, exit 0.
- Replayed the target dispatcher test in an isolated copy of tracked `bin/`, its three test dependencies, and `docs/examples/crew-dispatch.json`. Only the quota library changed between runs. With `git show f5735dc28a83186ef95715c8683333245762a8c6:bin/fm-quota-axi-lib.sh`: 17 passing groups followed by the expected home-fallback failure, exit 1. With the target library: 24 passing groups, exit 0. Additional logging saved the actual resolver stdout without changing its assertions.
- `quota-axi --help`, `quota-axi --version`, and `quota-axi auth --provider codex --json` established the installed version, read-only options, and available runtime credential source. Version: 0.1.48.
- `quota-axi --provider codex --no-credential-refresh --json`: real schema-6 home and sibling data, exit 0.
- `quota-axi --provider codex --profile-only --no-credential-refresh --json`, selecting the existing Codex credential store through its documented environment variable: real schema-5 data, exit 0. No credential file was copied or edited.
- `bash bin/fm-dispatch-resolve.sh <isolated brief.md> --project quota-routing-validation`: five calls with isolated `FM_HOME`, configuration, and temporary files. A pass-through executable forwarded the real quota-axi output unchanged while adding `--no-credential-refresh`; the schema-5 call additionally used `--provider codex --profile-only`. All calls used the real TypeSafe API and exited 0. Captured output values were compared with the matching live quota inputs.

## Observed behavior

- Pi home fallback: 96% remaining, positive spendPriority, eligible and selected against the exhausted sibling.
- Pi `codex-native/` and the `codex` harness: both read the home row. The sibling remained exhausted. Cursor retained its separate 22% row and higher spendPriority, winning the three mixed-provider runs.
- Schema 5: Pi home, Pi sibling, Pi native, and native Codex all received the same measured row and escalated on a genuine tie.
- Fixture with an exhausted exact `openai-codex` row beside a healthy home row: the exact row vetoed the candidate; the resolver did not borrow home quota.
- Fixture with neither named row but a healthy `default` row: Pi home remained eligible and unranked; the sibling retained its default fallback.

## Setup corrections and limits

The initial dispatcher test inherited the process API key and therefore did not exercise its absent-key case. The initial helper test inherited unsupported `C.UTF-8`, contaminating stderr. Both issues were corrected by isolating the environment, then both complete targeted suites passed. The first isolated regression replay omitted the documented config example; adding that tracked input fixed the replay setup.

Live verification of the two remaining schema-6 layouts requires an isolated authorized quota source that actually emits those account combinations. The current source emits `codex-home` and `openai-codex-muller-labs`, not an exact `openai-codex` row or a default-only Codex layout. Production account configuration was not changed to manufacture these cases. Their successful fixture transcripts are explicitly labeled non-live.

No Herdr session or fleet pane was needed. No linters, formatters, full repository suite, push, PR, or CI phase was run. All transient test files were removed from the worktree; evidence remains in this directory.
