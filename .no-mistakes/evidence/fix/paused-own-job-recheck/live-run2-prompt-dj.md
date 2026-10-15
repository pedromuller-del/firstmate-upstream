You are a crewmate in a test. Follow these status rules from your brief exactly:

4. Report status by appending one line:
   `echo "{state} [at=<epoch>]: {one short line}" >> '/tmp/fm-lab.1FWOOG/state/dj.status' && { [ ! -e '/tmp/fm-lab.1FWOOG/config/fleet-ledger' ] || '/home/agent/.no-mistakes/worktrees/754684345a7c/01M4YJRGRKE8G9QH69178ZVFVG/bin/fm-fleet-ledger.sh' appended '/tmp/fm-lab.1FWOOG/config' '/tmp/fm-lab.1FWOOG/state/dj.status' >/dev/null 2>&1 || true; }`
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


Your task: start your own detached background shell job with a 120 s timeout by running this exact command with the ordinary Bash tool (do NOT use run_in_background):
    nohup timeout 120 sh -c 'sleep 60; echo nightly-build-done > job.out' >/dev/null 2>&1 &
Run date +%s immediately before starting it and treat that as the job start.
Then append the paused status line for this job, following the rules above.
Then end your turn immediately. Do not poll, sleep, or check the job. Do not write anything else.
