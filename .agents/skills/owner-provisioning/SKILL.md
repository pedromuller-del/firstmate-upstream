---
name: owner-provisioning
description: Load before creating, relaunching, or retiring an owner task in a secondmate home.
user-invocable: false
metadata:
  internal: true
---

# Owner provisioning

An owner is an ordinary long-running task in a secondmate home, not a new process class.
Create one for a project or a large delivery when sustained ownership is needed.
Route the request to the secondmate whose scope fits, and have that secondmate provision and supervise the owner in its own home.
Do not create a duplicate owner for the same responsibility.

## Create

1. Define the owner's project or delivery, responsibility, boundaries, escalation rules, and the marked return channel to its parent in its charter.
2. Use `bin/fm-brief.sh` to scaffold an ordinary task brief in the secondmate home, following the task lifecycle and the script's current help.
   Include the charter, the actual parent channel and its marked reply contract, and the ledger instructions below in the brief.
3. Give the owner `data/<owner>/ledger.md` in that home, with one row per item, plus `data/<owner>/review-log.md` and `data/<owner>/ledger-archive.md`.
   Include the guardrails and stow instructions below in the brief's Firstmate spec.
4. Resolve the task's delivery and dispatch settings under the ordinary task lifecycle, then launch it with `bin/fm-spawn.sh` in that home.
   Use `bin/fm-send.sh` for later instructions and the existing parent-channel contract for marked replies.

## Owner guardrails

1. Each ledger row cites a source a fresh reader can open (path, URL or sha) and carries `checked=<UTC>`.
   Check: `rg -c` of rows without a path, URL or sha is 0.
2. Recheck volatile facts (PR head, CI, reviews, worker state, quota) at their source before acting or reporting.
   The report line names the command and its time.
3. At relaunch and before each owner ask, a fresh reader (a different seat, or a fresh read of the sources by you) checks 3 random rows against their sources.
   Log the result in `review-log.md`.
   Fix any stale row before the ask goes out.
4. The row is the truth; the time log is history.
   The spot-check also compares each row with the newest log line for that item.
5. The ledger stays at most 120 lines.
   Archive closed items; no closed row stays longer than 1 day.
   Relaunch fresh when turns grow large.

## Owner stow at each relaunch

At each relaunch, before new work: move closed rows and stale facts from `ledger.md` to `ledger-archive.md` in the same data folder, with the date and the reason.
Never delete a row.
Then run the rule 3 spot-check.

No schedule and no cron: these steps run only at relaunch and before owner asks.

## Relaunch and retire

Use the ordinary task recovery and control contracts to relaunch an existing owner, preserving its brief, ledger, archive, and review log.
The relaunched owner performs the stow and spot-check above before new work.
On retirement, archive the ledger with its history in the owner's data folder; never delete it.
Follow the ordinary task cleanup and unresolved-decision safeguards.
