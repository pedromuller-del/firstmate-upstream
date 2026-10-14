# Scenario 2: real Claude crewmate paused on its own background job WITHOUT until, real fm-watch.sh, lab tmux
## crewmate task (job has no timeout)
Task (scenario 2): start the nightly build as YOUR OWN background shell job, detached so it keeps running after your turn ends. It has no timeout and you do not know how long it takes. Run exactly this in one Bash call, together with `date +%s`:
  nohup sh -c 'sleep 60; echo build finished; exit 1' > /tmp/fm-lab.A885cz/job/build2.out 2>&1 &
Do NOT use your harness's own background-task feature; use the shell command above.
Then follow the status rules for waiting on your own background job, and end your turn.
Do not check on the job, do not poll, do not sleep, do not do anything else after the status line.
## crewmate pane
 ▐▛███▛█   Claude Code v2.1.300
▝▜██████▀  Opus 5.5 (1M context) with medium effort · Claude Max
 ▝▝   ▝▝   /tmp/fm-lab.A885cz/projects/demo
❯ Read /tmp/fm-lab.A885cz/data/bgjob2/task2.md and do exactly what it says.
  Read 1 file, ran 2 shell commands
● 🟡 I started the nightly build as a detached nohup job at epoch 1792018206 and appended a paused line to bgjob2.status. The line has no until time because the job has no timeout. The build is still
  running, and I did not check on it.
  One mismatch in the brief: the status line goes to bgjob2.status, but the ledger command points at bgjob.status. I ran both exactly as written.
  Next: wait for the build to finish and write to /tmp/fm-lab.A885cz/job/build2.out. It ends with exit 1, so expect it to report a failure.
✻ Cogitated for 15s · done 12:50 AM
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
❯ zz
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  claude  Opus 5.5 (1M context) · medium  ctx 40k/1M  quota 5h 2% 7d 11%   master
  ⏵⏵ bypass permissions on (shift+tab to cycle)
## status file
paused [at=1792018206]: waiting on own nohup nightly build job (no timeout, unknown duration); resumes when /tmp/fm-lab.A885cz/job/build2.out shows the job exited
## job output (job ended ~22:51:06Z)
build finished
## watcher stdout (rounds 4-7)
##### scenario 2
=== watcher round 4 start 2026-10-14T22:50:31Z
check: rearm-resurface
=== watcher round 4 exit=0 2026-10-14T22:50:32Z
=== watcher round 5 start 2026-10-14T22:50:45Z
signal: /tmp/fm-lab.A885cz/state/bgjob2.status
=== watcher round 5 exit=0 2026-10-14T22:50:48Z
=== watcher round 6 start 2026-10-14T22:51:19Z
stale: crew:bgjob2
=== watcher round 6 exit=0 2026-10-14T22:51:31Z
=== watcher round 7 start 2026-10-14T22:51:57Z
Round 6 queued the one first-sight alert: 1792018291 6 stale crew:bgjob2 'stale: crew:bgjob2' (acked).
Round 7: pane hash changed at ~22:52:22Z by typing 'zz' into the idle input box (job already ended).
## triage trail for bgjob2
[2026-10-15T00:51:58+0200] absorbed stale (paused, awaiting external, age 108s): crew:bgjob2
[2026-10-15T00:52:04+0200] absorbed stale (paused, awaiting external, age 114s): crew:bgjob2
[2026-10-15T00:52:10+0200] absorbed stale (paused, awaiting external, age 120s): crew:bgjob2
[2026-10-15T00:52:16+0200] absorbed stale (paused, awaiting external, age 126s): crew:bgjob2
[2026-10-15T00:52:33+0200] absorbed non-terminal stale (declared wait or open captain call already re-surfaced this window): crew:bgjob2
[2026-10-15T00:52:38+0200] absorbed stale (paused, awaiting external, age 148s): crew:bgjob2
[2026-10-15T00:52:44+0200] absorbed stale (paused, awaiting external, age 154s): crew:bgjob2
[2026-10-15T00:52:50+0200] absorbed stale (paused, awaiting external, age 160s): crew:bgjob2
[2026-10-15T00:52:56+0200] absorbed stale (paused, awaiting external, age 166s): crew:bgjob2
[2026-10-15T00:53:02+0200] absorbed stale (paused, awaiting external, age 172s): crew:bgjob2
## wake queue after round 7: rows=0
## throttle marker (no :due)
declared:r1:313633007374726f6e673a33383a34393033303531353a323032362d31302d31352030303a34393a34302e393739383731343233202b3032303000726567756c61722066696c653a38316234002d007265616461626c65007265616461626c65
