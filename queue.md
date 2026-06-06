# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Session 2026-06-05 — barrel through the wiki-content backlog (Emma remote-control)

Working order follows `docs/wiki_content_scripting_plans_2026-05.md` (3 & 4 first, then 2, then 1, then 5 — gated). Every wiki-writing script is wired into CI (no local write creds); the dev session tests dry-run / read-only and commits + pushes so the next CI fire exercises it.

### A. Item 4 — `report_multiple_wikidata_links.py` (SMALL, render-once standalone)
Consume `[[Category:Pages with multiple wikidata links]]`; for each page extract the QIDs from each `{{wikidata link|Q…}}`, fetch each item's label/description from Wikidata, write a side-by-side review page (`[[Multiple wikidata links]]`) so a human can pick the correct one. Read-only on content. Wire into category-orchestrator follow-up or a CI step. Test dry-run.

### B. Item 3 — `report_double_qid_tail.py` (SMALL, render-once standalone)
Consume `[[Category:Double category qids]]` (≈7 pages). For each dab page list the competing category targets, whether each exists, its QID (from the category's `{{wikidata link}}`), and member count. Write to a wiki review page (`[[Double category QID tail]]`). Read-only on content. Wire into CI. Test dry-run.

### C. Item 2 — `fix_ill_destinations.py` (MEDIUM, category-driven filler)
Consume `[[Category:Pages with unresolved QID in ill template]]`. For each `{{ill}}` lacking a valid `qid=Q\d+` (skip `qid=DELETED_QID`): (1) enwiki pageprops `wikibase_item` on the English target → fill; (2) Mode-B sitelink resolution for non-en pairs, single unique QID → fill, 2+ distinct → leave; (3) literal "Unknown" → leave. Fill ONLY writes a qid into a call that had none — never overwrites. Bounded by `--max-edits`, stateless, `--apply`/`--run-tag`. Wire into CI. Test dry-run.

### D. Item 1 — `generate_category_translation_moves.py` phase (a) (LARGE → start deterministic chunk)
Enumerate `[[Category:Japanese language category names]]` subcats. Phase (a): deterministic dated-maintenance transform (`YYYY年M月` → `Month YYYY`; collapse long malformed timestamp forms onto the month form) + a small hand-maintained template-prefix lookup. Emit `category_moves.csv` rows `(source,dest,reason)` for the confident deterministic cases ONLY; everything else → residual report, never guessed. (Phases b/c/d — Wikidata-label resolver, place gazetteer, human queue — are follow-on todo items.) The existing `move_categories.py` already consumes the CSV (monthly CI step). Test by inspecting the generated CSV.

### E. Item 5 — recreate deleted Wikidata items — POST OPEN QUESTION (gated on Emma + freeze)
Do NOT build/run the generator. Per the plan it needs Emma's explicit notability go-ahead + a defensible minimum claim set, and Wikidata freeze runs to 2026-06-06. Post a precise open question to `git_synced/Open questions.wiki` (minimum claim set proposal + the 144-item scope) for Emma to approve; commit + push so it syncs to the wiki.

### F. queue item 2 (carried) — comprehensive program audit
Write `docs/program_audit_2026-06.md`: every workflow, orchestrator+ops, legacy CI script, sync script, the QS pipeline, the remote-queue loop — what runs, trigger, state file, what's failing/stuck/orphaned, in-flight wiki migrations + next observable step, verdict per item (keep/fix/retire). Link from `todo.md`.

### G. queue item 1 (carried) — deferred-verification sweep (read-only checks)
Walk `docs/deferred_verification.md` Open items; run each read-only check now (action=parse / category counts / sync edit-summary inspection). Move confirmed ones to Verified with date+observation; fix anything broken. Don't bring back `.state` files.

### H. Prune resolved meta blocks
The weekly-OQ-sweep block: live `[[Open questions]]` has no new actionable items (checked at session start) — prune that block. The monthly-verify-sweep block is the same work as G — fold into G and prune.

### Y. (pinned tail) Ensure the three autonomous-loop crons are running
Start them if this session never did; restart if a planning burst killed them.

### Z. (pinned tail) Run the status-report action once more — end-of-session summary
