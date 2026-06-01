# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

## Monthly verification sweep (<!-- monthly-verify-sweep --> 2026-06-01)

Walk `docs/deferred_verification.md` and actually TEST each Open item (the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators). For each: run its check; if it works, move it to the doc's Verified section with the date + what you observed; if it's broken, fix it and note the fix. Then delete THIS block.

## Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-06-01)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

## 1. Review the deferred-verification log

Walk `docs/deferred_verification.md` and actually TEST each Open item — the batched verification we skip in the moment because wiki/CI changes are slow lagging indicators (8–24h to manifest). Highest priority right now: the **sync `.state`-file removal** (shipped 2026-05-30, all 5 sync scripts now stateless + timestamp-based) — watch the next sync cycles for spurious deletions / category-churn and fix the stateless orphan/winner logic if needed (do NOT bring the `.state` files back). For each item: run its check; if it works, move it to the doc's Verified section with the date + what you saw; if it's broken, fix it. (The `monthly-verification-sweep.yml` GH Action re-adds this task monthly.)

## 2. Comprehensive audit of the whole program

Produce a written, comprehensive audit of everything this repo does to the wiki(s) and Wikidata — a single document a human can read to understand the full machine. Cover:
- **What runs:** every workflow in `.github/workflows/`, every orchestrator + its ops, every legacy standalone script wired into CI, every sync script, the QuickStatements pipeline, the remote-queue/cloud-worker loop. For each: what it does, its trigger/schedule, and its current state file (if any).
- **What's failing or stuck:** anything erroring, not producing edits when it should, or whose state file has stopped advancing.
- **What's never been wired in / orphaned:** scripts in the tree that nothing invokes; half-finished pipelines; ops written but not registered.
- **The processes in flight on the wiki:** the multi-cycle migrations (double-category-qid drain, crud-category lifecycle, need_translation/duplicated_content sync, etc.) — where each one is in its lifecycle and what the next observable step is.
- **Verdict per item:** keep / fix / retire, with reasoning.
Write it to `docs/` (e.g. `docs/program_audit_2026-06.md`) and link it from `todo.md`. This is the "figure out what's actually left and what the machine is doing" pass.
