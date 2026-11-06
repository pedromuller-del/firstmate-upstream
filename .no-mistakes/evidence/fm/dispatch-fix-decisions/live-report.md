# Dispatch live validation

Target: `88404c222c9cf4a2e8f49efa3b3b20b182296359`.

The real resolver called TypeSafe and the installed Pi and quota-axi CLIs. All inputs were synthetic. Forwarding observers recorded requests, responses, process exits, and file modes without replacing product behavior.

Quota was restricted to an empty Codex profile with `--profile-only --no-credential-refresh`. It returned missing-credentials exit 1. This proves that failed Pi checks reach the quota read; it does not prove a healthy reading, OAuth renewal, or cache reuse.

## Resolve a known bug to its exact profile without quota calls under shared quota

Result: pass, live.

Evidence: `live-clear.json`.

```text
exit=0
dispatch-resolve:
  status: clear
  model: jev-1.14.0   latency_ms: 519   tokens: 581/71
  rule: rule_3 (A bug fix whose root cause the brief states.)   confidence: 1.0
  probabilities: rule_1=0.0 rule_2=0.0 rule_3=1.0 rule_4=0.0 rule_5=0.0 default=0.0
  note: rule matched
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)
  profile: --harness 'codex' --model 'gpt-6.1-sol' --effort 'medium'

```

## Resolve a below-global-floor answer to its probability leader with a low-confidence note

Result: pass, live.

Evidence: `live-borderline-4.json`.

```text
exit=0
dispatch-resolve:
  status: clear
  model: jev-1.14.0   latency_ms: 517   tokens: 582/71
  rule: rule_5 (A read-only investigation, diagnosis, or audit whose deliver)   confidence: 0.29
  probabilities: rule_1=0.0 rule_2=0.12 rule_3=0.1 rule_4=0.0 rule_5=0.41 default=0.37
  note: rule matched (low confidence: answer confidence 0.29 below floor 0.6)
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)
  profile: --harness 'codex' --model 'gpt-6.1-sol' --effort 'high'

```

## Require captain approval even when the selected answer has low confidence

Result: pass, live.

Evidence: `live-captain-approval.json`.

```text
exit=0
dispatch-resolve:
  status: escalate
  model: jev-1.14.0   latency_ms: 469   tokens: 580/71
  rule: rule_1 (Unusually difficult or high-risk security redesign or costly)   confidence: 1.0
  probabilities: rule_1=1.0 rule_2=0.0 rule_3=0.0 rule_4=0.0 rule_5=0.0 default=0.0
  reason: rule requires the captain's explicit approval before dispatch
  candidate: claude:opus  provider=claude  -> eligible (quota ranking off: home declares a single shared quota)

```

Evidence: `live-low-captain-approval.json`.

```text
exit=0
dispatch-resolve:
  status: escalate
  model: jev-1.14.0   latency_ms: 544   tokens: 582/71
  rule: rule_5 (A read-only investigation, diagnosis, or audit whose deliver)   confidence: 0.28
  probabilities: rule_1=0.0 rule_2=0.12 rule_3=0.09 rule_4=0.0 rule_5=0.4 default=0.39
  reason: rule requires the captain's explicit approval before dispatch
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)

```

## Withhold a profile when its declared confidence floor has no qualifying alternative

Result: pass, live.

Evidence: `live-declared-floor.json`.

```text
exit=0
dispatch-resolve:
  status: ambiguous
  model: jev-1.14.0   latency_ms: 498   tokens: 578/71
  rule: rule_2 (Routine feature work, a port, or an installer build inside a)   confidence: 0.7
  probabilities: rule_1=0.0 rule_2=0.75 rule_3=0.0 rule_4=0.01 rule_5=0.0 default=0.24
  reason: rule_2 probability 0.75 below its floor 1; no other option clears its own floor
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)

```

Evidence: `live-low-declared-floor.json`.

```text
exit=0
dispatch-resolve:
  status: ambiguous
  model: jev-1.14.0   latency_ms: 457   tokens: 582/71
  rule: rule_5 (A read-only investigation, diagnosis, or audit whose deliver)   confidence: 0.32
  probabilities: rule_1=0.0 rule_2=0.13 rule_3=0.07 rule_4=0.0 rule_5=0.43 default=0.37
  reason: rule_5 probability 0.43 below its floor 1; no other option clears its own floor
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)

```

## Remove expired rules, retain a future leap-day rule, and stop when all rules expire

Result: pass, live.

Evidence: `live-expired-rule.json`.

```text
exit=0
dispatch-resolve:
  status: clear
  model: jev-1.14.0   latency_ms: 498   tokens: 439/35
  rule: rule_1 (Fix a pagination bug whose root cause is a wrong comparison.)   confidence: 1.0
  probabilities: rule_1=1.0 default=0.0
  note: rule matched
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)
  profile: --harness 'codex' --model 'gpt-6.1-sol' --effort 'low'

```

Evidence: `live-all-expired.json`.

```text
exit=0
dispatch-resolve:
  status: escalate
  reason: no rules to match

```

## Reject malformed and calendar-invalid expiry values before calling any service

Result: pass, live.

Evidence: `live-invalid-until-1.json`.

```text
exit=2

error: malformed rules file: /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH/.dispatch-check-7t_ezzno/live-invalid-until-1/config/crew-dispatch.json - until must be a valid ISO 8601 UTC instant (YYYY-MM-DDTHH:MM:SSZ)
```

Evidence: `live-invalid-until-2.json`.

```text
exit=2

error: malformed rules file: /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH/.dispatch-check-7t_ezzno/live-invalid-until-2/config/crew-dispatch.json - until must be a valid ISO 8601 UTC instant (YYYY-MM-DDTHH:MM:SSZ)
```

Evidence: `live-invalid-until-3.json`.

```text
exit=2

error: malformed rules file: /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH/.dispatch-check-7t_ezzno/live-invalid-until-3/config/crew-dispatch.json - until must be an ISO 8601 UTC instant (YYYY-MM-DDTHH:MM:SSZ) when present
```

Evidence: `live-invalid-until-4.json`.

```text
exit=2

error: malformed rules file: /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH/.dispatch-check-7t_ezzno/live-invalid-until-4/config/crew-dispatch.json - until must be an ISO 8601 UTC instant (YYYY-MM-DDTHH:MM:SSZ) when present
```

Evidence: `live-invalid-until-5.json`.

```text
exit=2

error: malformed rules file: /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M6RS0XKP6V2CRD7BTHY8Z0NH/.dispatch-check-7t_ezzno/live-invalid-until-5/config/crew-dispatch.json - until must be a valid ISO 8601 UTC instant (YYYY-MM-DDTHH:MM:SSZ)
```

## Create private rule snapshots and remove them after resolution

Result: pass, live.

Evidence: `live-private-snapshots.json`.

```text
exit=0
dispatch-resolve:
  status: clear
  model: jev-1.14.0   latency_ms: 587   tokens: 581/71
  rule: rule_3 (A bug fix whose root cause the brief states.)   confidence: 1.0
  probabilities: rule_1=0.0 rule_2=0.0 rule_3=1.0 rule_4=0.0 rule_5=0.0 default=0.0
  note: rule matched
  candidate: codex:gpt-6.1-sol  provider=codex  -> eligible (quota ranking off: home declares a single shared quota)
  profile: --harness 'codex' --model 'gpt-6.1-sol' --effort 'medium'

```

## Check each live Pi provider and the root default through the pinned account, then read quota despite auth failure

Result: pass, live.

Evidence: `live-pi-refresh-failure.json`.

```text
exit=0
dispatch-resolve:
  status: error
  reason: quota-axi --json failed
dispatch-resolve: error (quota-axi --json failed)
```

## Avoid ambient-account refresh when the configured Pi account root is invalid

Result: pass, live.

Evidence: `live-invalid-account-pin.json`.

```text
exit=0
dispatch-resolve:
  status: error
  reason: quota-axi --json failed
dispatch-resolve: error (quota-axi --json failed)
```

## Live limitations

The previously accepted six-scenario exception remains. A real provider did not emit an exact probability tie, an unoffered choice, or a non-leading raw choice. Those branches passed the offline resolver suite. Empty isolated Pi roots have no renewable OAuth identity. The installed quota-axi supports the reuse flag, but healthy reuse requires authorized credentials. Pi-signed is absent from PATH and the repository supplies no build or installer for that signed wrapper. OpenRouter and OpenAI keys are absent. The real Claude primary reached its workspace-trust dialog on a 120-column by 40-row terminal; approving it would modify the operator trust store outside the allowed boundary. The private tmux server was stopped and the lab removed.

No product GUI or layout changed. Evidence is the CLI output, captured API protocol, file permissions, and primary terminal transcript.
