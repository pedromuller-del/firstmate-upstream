# Scenario 1+3: real Claude crewmate paused on its own background job, real fm-watch.sh, lab tmux
## crewmate task prompt
You are a crewmate worker. Follow these status rules from your brief exactly:

3. Use gh-axi for GitHub operations and chrome-devtools-axi for browser operations.
4. Report status by appending one line:
   `echo "{state} [at=<epoch>]: {one short line}" >> '/tmp/fm-lab.A885cz/state/bgjob.status' && { [ ! -e '/tmp/fm-lab.A885cz/config/fleet-ledger' ] || '/home/agent/.no-mistakes/worktrees/754684345a7c/01M4Y8MGPZH9PQNM0CN728V16J/bin/fm-fleet-ledger.sh' appended '/tmp/fm-lab.A885cz/config' '/tmp/fm-lab.A885cz/state/bgjob.status' >/dev/null 2>&1 || true; }`
   States: working, needs-decision, blocked, paused, done, failed.
   Substitute `<epoch>` with the current Unix time in seconds - run `date +%s` and write the number it printed; a stamp that is not plain digits records no time at all.
   Each append wakes firstmate, so report sparingly: only phase changes a supervisor
   would act on (setup done, bug reproduced, fix implemented, validation passed) and the
   needs-decision/blocked/paused/done/failed states. No step-by-step FYI progress lines;
   firstmate reads your pane for that.
   Whenever you mention a PR anywhere - a status line, your terminal, a summary - write its full
   https:// URL exactly as the forge printed it, never a bare number such as "PR 108"; firstmate
   copies that URL from your line rather than assembling one.
   A mid-task `working:` line (including setup complete) is nonterminal: do not end the
   turn after it; continue the same stage until a defined `done:` gate under Definition of done.
   Use `paused: {why}` - distinct from `blocked:` - when deliberately waiting for work or an external condition expected to clear on its own, including your own validation round.
   Before ending your turn with your own background shell or monitor still running, or before waiting on your own pipeline run or a long foreground command, append `paused [at=<epoch>]: {job and completion condition}` to the status file.
   Name what you are waiting for and what will let you resume; do not repeat the declaration on every poll.
   Do not declare active implementation or reasoning as a wait.
   Firstmate may still raise one first-sight alert; the declared wait then uses the existing long recheck cadence instead of repeated possible-wedge alarms.
   When you know when the wait clears, include `until <YYYY-MM-DDTHH:MMZ>` (UTC) for a recheck at that time; for your own background job or command with a timeout, that time is its start plus its timeout, rounded up to the minute.
   Follow the resolution rule below when the wait clears, then resume the task.
   Use `blocked:` when you are stuck and need help.

Task (scenario 1): start the nightly build as YOUR OWN background shell job with a 120-second timeout, detached so it keeps running after your turn ends. Run exactly this in one Bash call, together with `date +%s` so you know the start time:
  nohup timeout 120 sh -c 'sleep 75; echo build finished; exit 1' > /tmp/fm-lab.A885cz/job/build.out 2>&1 &
Do NOT use your harness's own background-task feature; use the shell command above.
Then follow the status rules for waiting on your own background job, and end your turn.
Do not check on the job, do not poll, do not sleep, do not do anything else after the status line.

## crewmate pane after its turn
 ▐▛███▛█   Claude Code v2.1.300
▝▜██████▀  Opus 5.5 (1M context) with medium effort · Claude Max
 ▝▝   ▝▝   /tmp/fm-lab.A885cz/projects/demo
❯ /clear
❯ Read /tmp/fm-lab.A885cz/data/bgjob/task1.md and do exactly what it says.
  Ran 4 shell commands
● I started the nightly build as a detached nohup shell job at epoch 1792017919, with a 120-second timeout. As the task required, I did not check on it after starting it.
  I appended a paused line to /tmp/fm-lab.A885cz/state/bgjob.status. It says I'm waiting for the job to exit, recheck until 2026-10-14T22:48Z. The job's output goes to
  /tmp/fm-lab.A885cz/job/build.out.
  Next: after 22:48Z, read build.out. The job's own command ends with exit 1, so expect build finished and a non-zero exit, which means a failed report.
✻ Brewed for 15s · done 12:45 AM
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
❯ check build.out and report the result
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  claude  Opus 5.5 (1M context) · medium  ctx 40k/1M  quota 5h 2% 7d 11%   master
  ⏵⏵ bypass permissions on (shift+tab to cycle) · ← for agents

## status file written by the crewmate
paused [at=1792017921]: own nohup nightly build job (timeout 120s), waiting for it to exit; output in /tmp/fm-lab.A885cz/job/build.out until 2026-10-14T22:48Z
job start epoch 1792017919 = 2026-10-14T22:45:19Z; start+120s = 2026-10-14T22:47:19Z; rounded up = 22:48Z
## job output
build finished

## watcher stdout across rounds (1: status signal, 2: absorb until due recheck, 3: after ack)
=== watcher round 1 start 2026-10-14T22:46:01Z
signal: /tmp/fm-lab.A885cz/state/bgjob.status
=== watcher round 1 exit=0 2026-10-14T22:46:05Z
=== watcher round 2 start 2026-10-14T22:46:29Z
stale: crew:bgjob (paused 155s, awaiting external - the declared clearing time has passed, rechecked on a long cadence not a wedge; confirm the wait cleared)
=== watcher round 2 exit=0 2026-10-14T22:48:00Z
=== watcher round 3 start 2026-10-14T22:48:32Z
/home/agent/.no-mistakes/worktrees/754684345a7c/01M4Y8MGPZH9PQNM0CN728V16J/bin/fm-wake-lib.sh: line 588: 3378804 Hangup                     sleep "$POLL"

## triage trail
[2026-10-15T00:46:41+0200] absorbed non-terminal stale (declared wait or open captain call already re-surfaced this window): crew:bgjob
[2026-10-15T00:46:46+0200] absorbed stale (paused until 74s from now, declared time not reached): crew:bgjob
[2026-10-15T00:46:52+0200] absorbed stale (paused until 68s from now, declared time not reached): crew:bgjob
[2026-10-15T00:46:58+0200] absorbed stale (paused until 62s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:03+0200] absorbed stale (paused until 57s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:09+0200] absorbed stale (paused until 51s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:15+0200] absorbed stale (paused until 45s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:21+0200] absorbed stale (paused until 39s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:26+0200] absorbed stale (paused until 34s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:32+0200] absorbed stale (paused until 28s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:38+0200] absorbed stale (paused until 22s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:43+0200] absorbed stale (paused until 17s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:49+0200] absorbed stale (paused until 11s from now, declared time not reached): crew:bgjob
[2026-10-15T00:47:55+0200] absorbed stale (paused until 5s from now, declared time not reached): crew:bgjob
[2026-10-15T00:48:33+0200] absorbed stale (paused, declared time reached, age 188s): crew:bgjob
[2026-10-15T00:48:39+0200] absorbed stale (paused, declared time reached, age 194s): crew:bgjob
[2026-10-15T00:48:44+0200] absorbed stale (paused, declared time reached, age 199s): crew:bgjob
[2026-10-15T00:48:50+0200] absorbed stale (paused, declared time reached, age 205s): crew:bgjob
[2026-10-15T00:48:56+0200] absorbed stale (paused, declared time reached, age 211s): crew:bgjob
[2026-10-15T00:49:01+0200] absorbed stale (paused, declared time reached, age 216s): crew:bgjob
[2026-10-15T00:49:07+0200] absorbed stale (paused, declared time reached, age 222s): crew:bgjob
[2026-10-15T00:49:13+0200] absorbed stale (paused, declared time reached, age 228s): crew:bgjob
[2026-10-15T00:49:18+0200] absorbed stale (paused, declared time reached, age 233s): crew:bgjob
[2026-10-15T00:49:24+0200] absorbed stale (paused, declared time reached, age 239s): crew:bgjob
[2026-10-15T00:49:30+0200] absorbed stale (paused, declared time reached, age 245s): crew:bgjob

## .paused-resurfaced-crew_bgjob
declared:r1:313539007374726f6e673a33383a34393032383932313a323032362d31302d31352030303a34343a32312e373632333536363236202b3032303000726567756c61722066696c653a38316234002d007265616461626c65007265616461626c65:due
## wake queue after round-3 (post-ack) - empty means no repeat
(rows: 0)

## wake queue captured at 22:48:23Z, before the ack (one stale row)
1792018080	3	stale	crew:bgjob	stale: crew:bgjob (paused 155s, awaiting external - the declared clearing time has passed, rechecked on a long cadence not a wedge; confirm the wait cleared)
