# Quota lane validation

The target selects Pi's built-in home Codex lane using real quota and the real Typesafe API. The base reports that same lane as eligible but unranked. No source changes were needed.

- Target resolver checks: 22 passing groups, exit 0.
- Adjacent quota chooser checks: 55 passing groups, exit 0.
- Added regression against base: 17 groups passed, then the home-lane assertion failed, exit 1, as expected.
- Adversarial fixture checks: 7 cases passed, exit 0. These are not live.
- Live CLI runs: target home selection, target lane isolation, and base comparison each exited 0; their public outputs were checked against the quota rows read during each run.

## Live evidence

All live resolver calls used an isolated FM_HOME and config under the run worktree. Curl reached the real Typesafe endpoint. A forwarding wrapper called the installed quota-axi with `--no-credential-refresh`, returned its output unchanged, and retained only quota fields for evidence. No fixture supplied live quota. No production credential files were copied or modified. No Herdr lifecycle or fleet panes were involved.

| Provider | Account | Remaining | Spend priority | Runway |
| --- | --- | --- | --- | --- |
| claude | default | 92% | 0.373 | through_reset |
| codex | codex-home | 97% | 0.8228 | through_reset |
| codex | openai-codex-muller-labs | 0% | -1.5572 | exhausted_now |
| cursor | default | 22% | 0.993 | projected_exhaustion |

- [Home selection](live-home-dispatch.txt): `pi:openai-codex/gpt-5.6-sol` selected; Muller Labs rejected at 0%.
- [Lane isolation](live-lanes-dispatch.txt): Pi home, Pi native, native Codex, and pi-signed home all matched codex-home; Cursor and Claude matched their independent rows; an unconfigured Pi account stayed unranked.
- [Base comparison](live-base-dispatch.txt): built-in Pi and pi-signed lanes remained unranked before the change.
- [Quota consumed by home selection](live-home-quota.json) and [quota consumed by lane isolation](live-lanes-quota.json).

## Focused commands

```sh
env -u TYPESAFE_API_KEY LC_ALL=C TMPDIR="$PWD/.quota-lane-validation/tmp" bash tests/fm-dispatch-resolve.test.sh
env -u TYPESAFE_API_KEY LC_ALL=C TMPDIR="$PWD/.quota-lane-validation/tmp" bash tests/fm-quota-choose.test.sh
git archive 6f0f139962eadaea29487cafead418a0eb2ec6e4 bin tests | tar -x -C .quota-lane-validation/base
git archive 6f0f139962eadaea29487cafead418a0eb2ec6e4 docs/examples/crew-dispatch.json | tar -x -C .quota-lane-validation/base
cp tests/fm-dispatch-resolve.test.sh .quota-lane-validation/base/tests/fm-dispatch-resolve.test.sh
env -u TYPESAFE_API_KEY LC_ALL=C TMPDIR="$PWD/.quota-lane-validation/tmp" bash .quota-lane-validation/base/tests/fm-dispatch-resolve.test.sh
python3 /Users/pedromuller/.no-mistakes/evidence/01M34TK4VA89AXEHF5K3G9JPEV/adversarial-check.py
```

The live entry point was `bin/fm-dispatch-resolve.sh .quota-lane-validation/brief.md --project quota-lane-validation`, with FM_HOME and FM_CONFIG_OVERRIDE pointing to `.quota-lane-validation/home`, TMPDIR pointing to `.quota-lane-validation/tmp`, and PATH prefixed with `.quota-lane-validation/forwardbin`. REAL_QUOTA_AXI came from `command -v quota-axi`; QUOTA_EVIDENCE named the corresponding JSON evidence file. The base comparison used `.quota-lane-validation/base/bin/fm-dispatch-resolve.sh` with the same configuration. The existing environment API key was used without printing or persisting it.

The first resolver-test attempt inherited TYPESAFE_API_KEY and failed its absent-key setup check. Clearing that variable fixed the setup. The first archived-base run omitted the documented config fixture; adding that unchanged base fixture allowed the intended regression assertion to fail. Neither setup issue required product changes.

## Limits

The real host has schema 6 with codex-home and Muller Labs, and no exact openai-codex row. Exact-row precedence, absence of both named home rows, exhausted-home reversal, row permutation, and schema 5 were exercised with controlled dependency fixtures, not live account state. [Adversarial outputs and inputs](adversarial-dispatch.txt) show those results. Live versions require an isolated quota-axi credential environment with the relevant account rows or a schema-5 producer; permission to alter production credentials was not requested or used.

The recorded decision to retain the existing default fallback was respected. No linters, formatters, complete repository suite, push, PR, or pipeline commands were run. This is a CLI-only change, so text transcripts are the end-user evidence.
