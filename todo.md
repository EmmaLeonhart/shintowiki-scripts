# Todo

Long-horizon backlog — genuine, not-yet-done tasks ONLY. Active session work is in [queue.md](queue.md); finished work + history in [DEVLOG.md](DEVLOG.md); how the pipelines/orchestrators work lives in [CLAUDE.md](CLAUDE.md) and `docs/` (e.g. `docs/remote_queue_pipeline.md`). Reference/narrative and completed/dropped items do NOT belong here.

## Scheduled reminders

- [ ] **July 2026 — audit terminating cleanup scripts.** Confirm these are inert (state covers every eligible page → no edits), then remove from `wiki-cleanup.yml` + delete: `reimport_from_enwiki.py`, `migrate_talk_pages.py`, `normalize_category_pages.py` (Sun), `remove_legacy_cat_templates.py` (monthly). Overlaps with the legacy-script audit below.


## Repo / script tasks

- [ ] **Audit which pre-orchestrator legacy scripts still run.** Most should stay — they run frequently or are wiki-state-driven (no `.state` file, by design). Catalogue each script wired into the workflows: still producing edits? trigger? wiki-state-driven (keep) vs genuinely inert (retire). Not a delete-spree — a confirmation pass.


## Wiki content tasks (manual / human review)

> **Scripting plans for everything in this section:** [`docs/wiki_content_scripting_plans_2026-05.md`](docs/wiki_content_scripting_plans_2026-05.md) — per-item design (trigger, state model, multi-cycle pacing, effort). Recommended build order: duplicate-QID tail + multiple-wikidata-link reports (small) → `fix_ill_destinations.py` (medium) → Japanese category translation (large, phased) → recreate-deleted-WD (gated on Emma + freeze).

- [ ] **ILLs without `WD=` / "Unknown" targets.** Fill missing `WD=` via `fix_ill_destinations.py`; check each context, don't blind-overwrite. Includes the Shikinaisha pages whose ILLs point at "Unknown".
- [ ] **Duplicate QID disambiguation pages** — mostly DRAINED (verified 2026-05-30: `[[Category:Double category qids]]` = **7** members, `[[Category:Duplicated qid category redirects]]` = **0**; the ~621 historical figure is long gone). `resolve_double_category_qids.py` auto-handles same-target cases in the cleanup loop; the 7-page tail is the genuinely-different-target review remnant. Low priority — nearly done.
- [ ] **Translate category names in `[[Category:Japanese language category names]]`** → canonical English titles. **THE real remaining backlog (verified 2026-05-30: 1171 subcategories).** Mix of dated maintenance cats (`2020年2月` etc.) and content cats (`さいたま市の神社`). Needs a scripted translation pass — see the 8 PM plan cron.
- [ ] **Multiple `{{wikidata link}}` on one page.** Per-case review — usually a Wikidata disambiguation issue.
- [ ] **`[[Category:Pages with duplicated content]]` + remaining `need_translation/` pages.** Mostly handled by the cloud-queue worker (`docs/remote_queue_pipeline.md`); manual review only for the hard cases — canonical-title choice / history merge, and the 9 large kokuzō articles. NEVER strip `[[Category:Need translation]]` without verifying the body is actually English (the sync deletes the file when the category goes).



## Wikidata (social / high-care — respect the freeze to 2026-06-06; QuickStatements pipeline only)

- [ ] **Recreate deleted Wikidata items.** A batch of ILL-target items were deleted by another editor. Build `generate_recreate_quickstatements.py`: walk `[[Category:Pages with deleted QID in ill template]]`, render `CREATE` + `P11250|"shinto:..."` blocks for human review via the existing QS pipeline. Define a minimum claim set that won't get re-deleted (the original failure). Lower-risk than a direct-API recreator; human-gates notability.
