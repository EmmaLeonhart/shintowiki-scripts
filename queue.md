# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Session 2026-06-05 — barrel through the wiki-content backlog (Emma remote-control)

Working order follows `docs/wiki_content_scripting_plans_2026-05.md` (3 & 4 first, then 2, then 1, then 5 — gated). Every wiki-writing script is wired into CI (no local write creds); the dev session tests dry-run / read-only and commits + pushes so the next CI fire exercises it.

### E. Item 5 — recreate deleted Wikidata items — POST OPEN QUESTION (gated on Emma + freeze)
Do NOT build/run the generator. Per the plan it needs Emma's explicit notability go-ahead + a defensible minimum claim set, and Wikidata freeze runs to 2026-06-06. Post a precise open question to `git_synced/Open questions.wiki` (minimum claim set proposal + the 144-item scope) for Emma to approve; commit + push so it syncs to the wiki.

### F. queue item 2 (carried) — comprehensive program audit
Write `docs/program_audit_2026-06.md`: every workflow, orchestrator+ops, legacy CI script, sync script, the QS pipeline, the remote-queue loop — what runs, trigger, state file, what's failing/stuck/orphaned, in-flight wiki migrations + next observable step, verdict per item (keep/fix/retire). Link from `todo.md`.

### Y. (pinned tail) Ensure the three autonomous-loop crons are running
Start them if this session never did; restart if a planning burst killed them.

### Z. (pinned tail) Run the status-report action once more — end-of-session summary
