# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation
translation, fandom template fixup, shrine-disambig content strip)
lives in `remote_queue.json` and is worked by the remote-Claude cron
— not duplicated here.



## ▶ RESTART NOTICE — 2026-05-20

This session's predecessor crashed when the computer restarted around 16:00 local on 2026-05-20. Four parallel agentic sessions died at the same time; the local cron jobs they had scheduled (in-memory, not `durable: true`) died with them. Nothing on disk was lost — only chat context and in-memory schedules.

**Prior session transcript:** `crashed_session_2026-05-20.md` at this repo's root (extracted from saved HTML; corresponds to claude.ai session `015usYf1YoHo7qov4QwnVEuS`). Cross-repo context: `C:\Users\Immanuelle\Documents\Github\SESSION_RESTART_2026-05-20.md`.

**📋 The `chat archive` block(s) below this notice are LOAD-BEARING — read them, do not delete.** Emma manually pasted excerpts of the pre-crash session conversation directly into this `queue.md` to capture execution detail past where the auto-extract truncated. This is the *intended pattern* for recovering from session-crash context loss: paste the relevant chat into the queue so the next session has it inline rather than chasing auth-gated session URLs. The bullet summary in this notice is a navigation aid; the archive below is the substance. Leave the archive in place until the recovery is visibly complete (queue items reconciled, next steps executed); then it can be deleted alongside this notice.

**Where the session left off — the real finding:** The session was running the remote queue worker and noticed the first three `duplicated_content/` items it pulled (`Achi Shrine (Achi).wiki`, `Aekuni Shrine.wiki`, `Akao Shibutare Kōribe Shrine.wiki`) were all no-ops because the gating category had already been removed from the page body — i.e. these are sync-pending files waiting to be pushed-and-deleted, not real work items. The user then pushed back, suspecting a regression where the post-sync deletion was disabled. The session verified its own changes (no sync-logic edits this session) and ran `gh run list --workflow=wiki-cleanup.yml` → **zero results**. The actual driver, **`cleanup-loop.yml`** (runs every 6 hours), has been failing — the last 3 runs all failed at **step 18 (`delete_unused_redirects`)**, with the first failure today at **03:55 UTC, ~16 hours before this session started**. Because GHA stops at the first failed step, `sync_need_translation` (~step 398) and `sync_duplicated_content` (~step 424) never run, so the sync-pending files never get pushed-and-deleted, so the local queue is padded with already-done items. The transcript truncates mid-investigation of the step-18 failure.

**Resume by:** **(0) Clear the bloated queue first — see warning below.** (1) Find the root cause of `cleanup-loop.yml` step 18 (`delete_unused_redirects`) failing as of 03:55 UTC 2026-05-20 — `gh run view <id> --log` on the latest failed run; (2) fix it so syncs downstream can finally fire; (3) once syncs run, the remote queue self-drains. The `remote_queue.py` filter-gap idea (skip files missing the gating category) is a secondary optimization — the primary problem is the broken workflow.

**⚠ Clear the bloated queue before adding new work.** This `queue.md` accumulated content across many sessions — the user's own "Important background stuff to do" rant + the chat archive excerpt + this restart notice + the actual queue items add up to a wall. Walk every item against `git log --since="2026-05-19"` and **delete** anything already shipped, per CLAUDE.md §"Workflow Rules": queue is delete-only, no progress markers, no `[x]` checkboxes. The two-commits-ever pattern flagged in the chat archive below (`queue.md` only touched in 2 commits while 71 commits landed since) is the bloat problem in concrete terms — every session bypasses the queue rather than maintaining it. This is the FIRST step, before any new execution.

The user's own background note (the §"Important background stuff to do" section further below) was written during the crash; read it for the env-var / GitHub-Actions-only rule it codifies — this is consistent with the step-18 finding above (the fix lives in CI, not in a local script).

If a queued item calls for a cron job, re-create it locally and immediately per the new CLAUDE.md §"Cron requests" rule (pinned 2026-05-20). Prefer `durable: true` for any cron whose purpose is to survive across sessions.

Delete this notice and `crashed_session_2026-05-20.md` once the queue has visibly resumed.

chat archive

So has our editing and using claude remote stuff been consistent at going through that queue thing?


Ran 3 commands, read 2 files
No — the workflow rule is not being followed.

queue.md has been touched in 2 commits, ever (the 2026-05-18 sync that created it, and the 2026-05-19 remote_queue.json rebuild). 71 commits have landed since without ever touching it.
The current queue.md body has zero work items — only pinned notes. So either no planned work has happened in two days, or (much more likely) work has been happening without being staged through the queue first.
remote_queue.json is healthy on its own axis: 1,097 items, regenerated 2026-05-19, fed by the remote-Claude cron. That side of the pipeline (bulk grunge work → autonomous backlog) is working as designed.
The gap is the interactive-session discipline: "plan into queue.md FIRST, then execute" and "delete completed items in the same commit." Neither has been happening — items aren't being added before execution, and nothing has been deleted from it because nothing was added.

Want me to start enforcing it this session (write any plan into queue.md before doing it, delete in the same commit), or is the rule itself stale and worth revising in CLAUDE.md?

Okay so I'm going to guess in this case the todo.md is really not updated. The queue.md needs to have stuff set up to make it actually work based off of the rules. If they are not, then you'll need to copy them from cleanvib by running cleanvib to create a Gitignore repository in here and then grabbing all the documentation and merging it in with here. And you should be basically going through the todo.md and clearing all the stuff in the todo.md that's being done and then moving the stuff that we can do into the queue.md and then starting to barrel through it. But there are also remote repositories. Remote workflow things that Claude is doing and committing to main that will be gradually changing in Wiki. And I don't know the degree that those things are properly working. And I'd like you to give an analysis of them and see if they need to be changed or something because there's a Python file that specifically makes a file that indicates which thing that Claude should be editing what day. Also, I want you to do a cron create that is setup so that

Your message got cut off mid-sentence on the cron part — I'll work the rest and ask about the cron at the end.

Let me start by reading the current state in parallel.


Read 4 files, ran 7 commands, searched code, used a tool
I have what I need to answer the substantive questions. Here's the analysis before I ask you the missing piece.

Remote workflow — assessment
The build side is healthy:

remote_queue.py runs daily via build-remote-queue.yml at 04:00 UTC. It has rebuilt successfully 7 days running (latest: today, 2026-05-20).
Current queue: 1,097 items across 4 categories:
fandom_unique/: 647 (template fixup for fandom mirror)
miraheze_unique/: 181 (shrine-disambig cleanup)
duplicated_content/: 135 (paragraph reorg)
need_translation/: 134 (JP → EN translation)
The consume side is dead:

Commits by author since 2026-05-01: 70 github-actions[bot], 2 Emma-Leonhart, ZERO from any "remote-Claude" worker.
Zero non-CI commits to duplicated_content/, need_translation/, or fandom_unique/ in three weeks.
Source-dir file counts are essentially the same as item counts, so nothing has drained.
The script that "indicates which thing Claude should be editing" is remote_queue.py — but it emits the full queue every day, not a per-day slice. The queue.md plan calls it "the remote-Claude cron," but I cannot find any agent, GitHub Action, or external worker that reads remote_queue.json and commits back. It appears the consumer was never wired up, or was decommissioned and the build side just kept rebuilding into the void.

todo.md / queue.md discipline
The rules in CLAUDE.md (plan into queue.md first, delete on completion, mirror into TaskCreate) are already documented — you don't need cleanvib to import them. They're just not being followed. queue.md has zero work items right now; todo.md has ~25 items, several already marked [x] (completion-tracking left in place rather than deleted, against the rule).

What I'd like to know before barreling through
Asked
Cron purpose
Your message cut off at "do a cron create that is setup so that" — what should the cron do?

Periodically work the queue myself

On the remote-Claude consumer that doesn't exist — what do you want?

Wire one up in this repo

The cleanvib step — still needed?

Still run it

---

## Important background stuff to do


Okay, so you are the same chat that was running through a bunch of other stuff here. You are the same chat, and I just set up a cron job to start going for the queue 1 hour after I wrote this.

Actually, write the queue in any meaningful way, so I am having to basically write all this for you. 

First thing is first, you do have context in this conversation to actually write through a thing to fill out. in ##stuff to do


So in the section directly below, that is your actual description of what you did. For some godforsaken reason, you decide to write a Python script. You decide to write a Python script to do this thing. The Python script is going to fail, and it's going to fail hard because the environmental variables are not there. I repeat, the environmental variables are not there. The environmental variables are not there, and I'm not going to put them there. You should not have done anything involving environmental variables. You should actually add that to the CLAUDE.md that you should never be doing anything dependent on environmental variables, because I'm not going to give them. All our actions rely on GitHub actions. 


What you're supposed to do is basically do whatever the fuck it is you are trying to do. You're specifically supposed to be editing the files, I think. Probably realistically, you just for some reason decide to write the script and run the script locally instead of as part of the GitHub Actions.

The point is, scripts are supposed to be edited so that this change is fixed on the GitHub Actions side based off of their Claude stuff, so you don't have to do anything. You don't really have to do anything with it. We don't do anything locally because, for cron jobs, we set up stuff locally because agentic stuff is better locally. We do nothing locally for actual wiki editing. All of it occurs through GitHub Actions. That is a very important rule that should have been clear to you. 


## Chat you said

Here is a chat thing

● Done. One-shot cron 03cafb84 fires at 16:29 local (~1 hour from now) and runs the unstick.

  What it'll do:
  1. shinto_miraheze/unstick_duplicated_content_conflicts.py — script I just wrote.
  2. For each of the 135 conflicted duplicated_content/*.wiki files: fetch live wiki text → build wiki + separator +
  local → ensure [[Category:Pages with duplicated content]] present → push merged to wiki → write merged locally →
  update sync state.
  3. Pages stay in the dedup queue (legitimately — they literally have both versions stitched).
  4. Sync's next run sees wiki == local, no conflict, queue drains normally as Claude dedups them.

  Needs WIKI_USERNAME + WIKI_PASSWORD env vars when the cron fires — the cron prompt has it abort with a clear message
  if they're missing rather than try anything destructive. Make sure your .env has them set, or set them in this shell
  before the cron fires.

  Two safety nets in the prompt: dry-run first, stop on first error, no bulk retry. Won't push the local commit — leaves
   that to you.



## Stuff to do

Use your existing context to fill this up with a series of instructions on exactly what it is that you should be doing step by step after you have unfrozen. 


You have the context to You have the context to put all this stuff together into a clear, actionable form and then barrel through it with a set of steps that you'll be putting down here, below this. You should have been putting this in here already, but you have all the information. 






## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.


## Wikidata: カミノヤシロ kana — secondary ask (bot request 2026-02-26)

Primary append job shipped (see DEVLOG 2026-05-23). Still open:

- [ ] DECIDE (needs Emma): the bot request's secondary ask — items `P31`=Q135038714
  whose kana is a standalone `P1814` *statement* (not a qualifier) need the kana
  *moved into* a P1448 ojp-hani qualifier AND カミノヤシロ appended. More invasive
  (statement restructuring); scope separately before building. Per the request,
  this is "best done before" the primary append for full coverage.
