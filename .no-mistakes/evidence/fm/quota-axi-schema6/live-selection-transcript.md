# Live quota selection
Account labels are redacted to neutral examples. Commands used actual keys; quota values and results are unchanged.

## Base validator rejects real schema 6
```console
$ bash -c '. "$1"; fm_quota_json_valid < "$2"' _ /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/base-quota-lib.sh /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6.json
exit_code: 1
```


## Target validator accepts identical real schema 6
```console
$ bash -c '. bin/fm-quota-axi-lib.sh; fm_quota_json_valid < "$1"' _ /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6.json
exit_code: 0
```


## Native Codex does not borrow a Pi account: live-schema6.json
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6.json --candidate codex:gpt-6-astra
none
exit_code: 1
```


## Select default-account provider after unmeasured native Codex: live-schema6.json
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6.json --candidate codex:gpt-6-astra --candidate cursor:default
cursor default
exit_code: 0
```


## Native Codex does not borrow a Pi account: live-schema6-toon.txt
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6-toon.txt --candidate codex:gpt-6-astra
none
exit_code: 1
```


## Select default-account provider after unmeasured native Codex: live-schema6-toon.txt
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema6-toon.txt --candidate codex:gpt-6-astra --candidate cursor:default
cursor default
exit_code: 0
```


## Reverse current provider rows; selection stays unchanged
```console
$ bash bin/fm-quota-choose.sh --candidate codex:gpt-6-astra --candidate cursor:default
cursor default
exit_code: 0
```


## Collect unexpanded provider as schema 5
```console
$ quota-axi --no-credential-refresh --provider cursor --json
{
  "generatedAt": "2026-09-19T06:25:21.578Z",
  "schemaVersion": 5,
  "providers": [
    {
      "provider": "cursor",
      "plan": "Team",
      "windows": [
        {
          "id": "included_usage",
          "label": "included usage",
          "kind": "monthly",
          "resetsAt": "2026-09-30T13:18:05.000Z",
          "percentRemaining": 33,
          "pace": {
            "status": "ahead",
            "reservePercentPoints": -4.622,
            "burnMultiple": 1.0741
          }
        },
        {
          "id": "auto_usage",
          "label": "auto usage",
          "kind": "monthly",
          "resetsAt": "2026-09-30T13:18:05.000Z",
          "percentRemaining": 24,
          "pace": {
            "status": "ahead",
            "reservePercentPoints": -13.622,
            "burnMultiple": 1.2184
          }
        },
        {
          "id": "api_usage",
          "label": "API usage",
          "kind": "monthly",
          "resetsAt": "2026-09-30T13:18:05.000Z",
          "percentRemaining": 84,
          "pace": {
            "status": "behind",
            "reservePercentPoints": 46.378,
            "burnMultiple": 0.2565
          }
        },
        {
          "id": "grok_bot",
          "label": "Grok Bot",
          "kind": "weekly",
          "resetsAt": "2026-09-21T18:12:49.357Z",
          "percentRemaining": 100,
          "pace": {
            "status": "behind",
            "reservePercentPoints": 64.4101,
            "burnMultiple": 0
          }
        }
      ],
      "state": {
        "status": "fresh",
        "stale": false
      },
      "quotaSemantics": {
        "status": "known",
        "effectiveAvailability": [
          {
            "scope": "all_models",
            "status": "known",
            "effectivePercentRemaining": 24,
            "boundedBy": [
              "included_usage",
              "auto_usage",
              "api_usage"
            ],
            "limitingWindowIds": [
              "auto_usage"
            ],
            "pace": {
              "status": "mixed",
              "aheadWindowIds": [
                "included_usage",
                "auto_usage"
              ],
              "worstReservePercentPoints": -13.622,
              "worstReserveWindowId": "auto_usage"
            },
            "runway": {
              "status": "projected_exhaustion",
              "usableRunwaySeconds": 510580,
              "projectedExhaustedAt": "2026-09-25T04:15:01.550Z",
              "limitingWindowId": "auto_usage",
              "projectionConfidence": "established"
            },
            "selection": {
              "status": "known",
              "spendPriority": 0.3996
            }
          },
          {
            "scope": "grok_bot",
            "status": "known",
            "effectivePercentRemaining": 100,
            "boundedBy": [
              "grok_bot"
            ],
            "limitingWindowIds": [
              "grok_bot"
            ],
            "pace": {
              "status": "behind",
              "worstReservePercentPoints": 64.4101,
              "worstReserveWindowId": "grok_bot"
            },
            "runway": {
              "status": "through_reset",
              "projectionConfidence": "established"
            },
            "selection": {
              "status": "known",
              "spendPriority": 2.8098
            }
          }
        ]
      }
    }
  ]
}
exit_code: 0
```


## Select live schema-5 Cursor: live-schema5-cursor.json
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema5-cursor.json --candidate cursor:default
cursor default
exit_code: 0
```


## Collect unexpanded provider as schema 5
```console
$ quota-axi --no-credential-refresh --provider cursor
bin: ~/.nvm/versions/node/v24.15.0/bin/quota-axi
description: Report local agent-provider quota windows for routing-aware agents
generatedAt: "2026-09-19T06:25:22.430Z"
quota[2]{provider,scope,effectivePercentRemaining,spendPriority,runway,confidence,limitedBy,resetsAt}:
  cursor,all_models,24,0.3996,projected_exhaustion,established,auto_usage,"2026-09-30T13:18:05.000Z"
  cursor,grok_bot,100,2.8098,through_reset,established,grok_bot,"2026-09-21T18:12:49.357Z"
exhaustion[1]{provider,scope,usableRunwaySeconds,projectedExhaustedAt,limitingWindowId}:
  cursor,all_models,510580,"2026-09-25T04:15:02.671Z",auto_usage
attention[0]:
help[1]:
  Run `quota-axi --full` for windows, pace, reserve, and account evidence
exit_code: 0
```


## Select live schema-5 Cursor: live-schema5-cursor.toon
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema5-cursor.toon --candidate cursor:default
cursor default
exit_code: 0
```


## Preserve unknown-provider ineligibility: live-schema5.json
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema5.json --candidate claude:default
none
exit_code: 1
```


## Preserve unknown-provider ineligibility: live-schema5-toon.txt
```console
$ bash bin/fm-quota-choose.sh --snapshot /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/live-schema5-toon.txt --candidate claude:default
none
exit_code: 1
```

Input is the current snapshot with mutation: unsupported-schema

## Refuse unsupported-schema
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: unsupported quota-axi schema version: 7
exit_code: 2
```

Input is the current snapshot with mutation: missing-account-key

## Refuse missing-account-key
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: invalid quota-axi provider data
exit_code: 2
```

Input is the current snapshot with mutation: duplicate-provider-account

## Refuse duplicate-provider-account
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: invalid quota-axi provider data
exit_code: 2
```

Input is the current snapshot with mutation: whitespace-account-key

## Refuse whitespace-account-key
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: invalid quota-axi provider data
exit_code: 2
```

Input is the current snapshot with mutation: non-string-account-key

## Refuse non-string-account-key
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: invalid quota-axi provider data
exit_code: 2
```


## Refuse inconsistent account columns across TOON sections
```console
$ bash bin/fm-quota-choose.sh --candidate cursor:default
error: invalid quota-axi snapshot
exit_code: 2
```


## Resolver remains off without its API key
```console
$ bash bin/fm-dispatch-resolve.sh /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/brief.md --project quota-schema6-validation
dispatch-resolve: off (TYPESAFE_API_KEY absent from the environment and /Users/pedromuller/.no-mistakes/worktrees/9cdf64f8f989/01M2W51BK51263V20KM4CCCW0Z/.quota-test-phase/home/.env)
exit_code: 0
```
