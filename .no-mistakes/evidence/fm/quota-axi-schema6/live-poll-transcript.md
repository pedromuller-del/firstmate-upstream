# Live quota poll results
Bounded foreground calls use the real poll child and installed quota-axi 0.1.47. A wrapper only appends --no-credential-refresh; schema-5 cases also select Cursor on the producer. No snapshot stubs are used and no watch was armed. Account labels are redacted to neutral examples.
An initial driver expected both accounts to remain at 3%. Live usage reduced one to 2%; the product correctly returned low. Assertions below use the returned values.

## schema6-aggregate
Producer provider filter: none
```console
$ bash bin/fm-procevent-quota.sh poll --threshold 4 --interval 0.1 --timeout 20
quota: quota
status: low
detail: {"provider":"aggregate","summary":[{"provider":"claude","accountKey":"default","best":null},{"provider":"codex","accountKey":"openai-codex","best":{"scope":"all_models","status":"known","effectivePercentRemaining":3,"boundedBy":["weekly"],"limitingWindowIds":["weekly"],"pace":{"status":"ahead","aheadWindowIds":["weekly"],"worstReservePercentPoints":-34.0035,"worstReserveWindowId":"weekly"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":11784,"projectedExhaustedAt":"2026-09-19T09:43:37.411Z","limitingWindowId":"weekly","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":-1.4587}}},{"provider":"codex","accountKey":"openai-codex-work","best":{"scope":"all_models","status":"known","effectivePercentRemaining":2,"boundedBy":["weekly"],"limitingWindowIds":["weekly"],"pace":{"status":"ahead","aheadWindowIds":["weekly"],"worstReservePercentPoints":-81.9372,"worstReserveWindowId":"weekly"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":1983,"projectedExhaustedAt":"2026-09-19T07:00:16.427Z","limitingWindowId":"weekly","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":-6.0773}}},{"provider":"cursor","accountKey":"default","best":{"scope":"all_models","status":"known","effectivePercentRemaining":24,"boundedBy":["included_usage","auto_usage","api_usage"],"limitingWindowIds":["auto_usage"],"pace":{"status":"mixed","aheadWindowIds":["included_usage","auto_usage"],"worstReservePercentPoints":-13.6177,"worstReserveWindowId":"auto_usage"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":510615,"projectedExhaustedAt":"2026-09-25T04:17:29.235Z","limitingWindowId":"auto_usage","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":0.3998}}},{"provider":"copilot","accountKey":"default","best":null},{"provider":"grok","accountKey":"default","best":{"scope":"all_products","status":"known","effectivePercentRemaining":91,"boundedBy":["credits"],"limitingWindowIds":["credits"],"pace":{"status":"ahead","aheadWindowIds":["credits"],"worstReservePercentPoints":-3.6363,"worstReserveWindowId":"credits"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":328003,"projectedExhaustedAt":"2026-09-23T01:33:56.433Z","limitingWindowId":"credits","projectionConfidence":"early"},"selection":{"status":"known","spendPriority":-0.7163}}},{"provider":"kimi","accountKey":"default","best":null},{"provider":"zai","accountKey":"default","best":null},{"provider":"agy","accountKey":"default","best":null},{"provider":"alibaba","accountKey":"default","best":null},{"provider":"opencode-go","accountKey":"default","best":null},{"provider":"commandcode","accountKey":"default","best":null}]}
condition_polls: 1
exit_code: 0
```

```console
$ bash bin/fm-procevent-quota.sh classify /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-aggregate-poll.txt
low
exit_code: 0
```
```console
$ bash bin/fm-procevent-quota.sh terminal /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-aggregate-poll.txt
exit_code: 0
```

## schema6-codex
Producer provider filter: none
```console
$ bash bin/fm-procevent-quota.sh poll --threshold 4 --interval 0.1 --timeout 20 --provider codex
quota: quota-codex
status: low
detail: {"provider":"codex","summary":[{"provider":"codex","accountKey":"openai-codex","best":{"scope":"all_models","status":"known","effectivePercentRemaining":3,"boundedBy":["weekly"],"limitingWindowIds":["weekly"],"pace":{"status":"ahead","aheadWindowIds":["weekly"],"worstReservePercentPoints":-34.0032,"worstReserveWindowId":"weekly"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":11784,"projectedExhaustedAt":"2026-09-19T09:43:39.249Z","limitingWindowId":"weekly","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":-1.4587}}},{"provider":"codex","accountKey":"openai-codex-work","best":{"scope":"all_models","status":"known","effectivePercentRemaining":2,"boundedBy":["weekly"],"limitingWindowIds":["weekly"],"pace":{"status":"ahead","aheadWindowIds":["weekly"],"worstReservePercentPoints":-81.9369,"worstReserveWindowId":"weekly"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":1983,"projectedExhaustedAt":"2026-09-19T07:00:18.246Z","limitingWindowId":"weekly","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":-6.0771}}}]}
condition_polls: 1
exit_code: 0
```

Each account is below 4%: [3, 2]. Their sum is 5%, but status is low, proving the watch does not combine account quotas.

```console
$ bash bin/fm-procevent-quota.sh classify /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-codex-poll.txt
low
exit_code: 0
```
```console
$ bash bin/fm-procevent-quota.sh terminal /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-codex-poll.txt
exit_code: 0
```

## schema6-default-account
Producer provider filter: none
```console
$ bash bin/fm-procevent-quota.sh poll --threshold 100 --interval 0.1 --timeout 20 --provider cursor
quota: quota-cursor
status: low
detail: {"provider":"cursor","accountKey":"default","best":{"scope":"all_models","status":"known","effectivePercentRemaining":24,"boundedBy":["included_usage","auto_usage","api_usage"],"limitingWindowIds":["auto_usage"],"pace":{"status":"mixed","aheadWindowIds":["included_usage","auto_usage"],"worstReservePercentPoints":-13.6176,"worstReserveWindowId":"auto_usage"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":510616,"projectedExhaustedAt":"2026-09-25T04:17:33.667Z","limitingWindowId":"auto_usage","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":0.3998}}}
condition_polls: 1
exit_code: 0
```

```console
$ bash bin/fm-procevent-quota.sh classify /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-default-account-poll.txt
low
exit_code: 0
```
```console
$ bash bin/fm-procevent-quota.sh terminal /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema6-default-account-poll.txt
exit_code: 0
```

## schema5-aggregate
Producer provider filter: cursor
```console
$ bash bin/fm-procevent-quota.sh poll --threshold 100 --interval 0.1 --timeout 20
quota: quota
status: low
detail: {"provider":"aggregate","summary":[{"provider":"cursor","best":{"scope":"all_models","status":"known","effectivePercentRemaining":24,"boundedBy":["included_usage","auto_usage","api_usage"],"limitingWindowIds":["auto_usage"],"pace":{"status":"mixed","aheadWindowIds":["included_usage","auto_usage"],"worstReservePercentPoints":-13.6175,"worstReserveWindowId":"auto_usage"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":510617,"projectedExhaustedAt":"2026-09-25T04:17:35.676Z","limitingWindowId":"auto_usage","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":0.3998}}}]}
condition_polls: 1
exit_code: 0
```

```console
$ bash bin/fm-procevent-quota.sh classify /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema5-aggregate-poll.txt
low
exit_code: 0
```
```console
$ bash bin/fm-procevent-quota.sh terminal /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema5-aggregate-poll.txt
exit_code: 0
```

## schema5-cursor
Producer provider filter: cursor
```console
$ bash bin/fm-procevent-quota.sh poll --threshold 100 --interval 0.1 --timeout 20 --provider cursor
quota: quota-cursor
status: low
detail: {"provider":"cursor","best":{"scope":"all_models","status":"known","effectivePercentRemaining":24,"boundedBy":["included_usage","auto_usage","api_usage"],"limitingWindowIds":["auto_usage"],"pace":{"status":"mixed","aheadWindowIds":["included_usage","auto_usage"],"worstReservePercentPoints":-13.6175,"worstReserveWindowId":"auto_usage"},"runway":{"status":"projected_exhaustion","usableRunwaySeconds":510617,"projectedExhaustedAt":"2026-09-25T04:17:36.667Z","limitingWindowId":"auto_usage","projectionConfidence":"established"},"selection":{"status":"known","spendPriority":0.3998}}}
condition_polls: 1
exit_code: 0
```

```console
$ bash bin/fm-procevent-quota.sh classify /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema5-cursor-poll.txt
low
exit_code: 0
```
```console
$ bash bin/fm-procevent-quota.sh terminal /Users/pedromuller/.no-mistakes/evidence/01M2W51BK51263V20KM4CCCW0Z/schema5-cursor-poll.txt
exit_code: 0
```