# Todo

Long-horizon backlog — genuine, not-yet-done tasks ONLY. Active session work is in [queue.md](queue.md); finished work + history in [DEVLOG.md](DEVLOG.md); how the pipelines/orchestrators work lives in [CLAUDE.md](CLAUDE.md) and `docs/` (e.g. `docs/remote_queue_pipeline.md`). Reference/narrative and completed/dropped items do NOT belong here.

## Scheduled reminders

- [ ] **July 2026 — audit terminating cleanup scripts.** Confirm these are inert (state covers every eligible page → no edits), then remove from `wiki-cleanup.yml` + delete: `reimport_from_enwiki.py`, `migrate_talk_pages.py`, `normalize_category_pages.py` (Sun), `remove_legacy_cat_templates.py` (monthly). Overlaps with the legacy-script audit below.
- [ ] **2027-05-23 — proposed-label drip-feed flips 20/day → ALL.** Automatic in `modern-quickstatements/select_label_proposals.py` (`RAMP_DATE`). Reminder only; if community feedback says the ~965k proposals need rework, fix the generators (or push `RAMP_DATE`) before the flip.

## Repo / script tasks

- [ ] **Audit which pre-orchestrator legacy scripts still run.** Most should stay — they run frequently or are wiki-state-driven (no `.state` file, by design). Catalogue each script wired into the workflows: still producing edits? trigger? wiki-state-driven (keep) vs genuinely inert (retire). Not a delete-spree — a confirmation pass.


## Wiki content tasks (manual / human review)

- [ ] **ILLs without `WD=` / "Unknown" targets.** Fill missing `WD=` via `fix_ill_destinations.py`; check each context, don't blind-overwrite. Includes the Shikinaisha pages whose ILLs point at "Unknown".
- [ ] **Duplicate QID disambiguation pages** (~621 `Q{QID}` pages → 2+ categories). `resolve_double_category_qids.py` auto-handles same-target cases (in the cleanup loop); genuinely-different-target ones need human review. Also `[[Category:duplicated qid category redirects]]`.
- [ ] **Translate category names in `[[Category:Japanese language category names]]`** → canonical English titles; review the post-audit leftovers there for any remaining automated cleanup.
- [ ] **Categories with interwikis but no `{{wikidata link}}`.** Re-run the wikidata-link resolution on these (older passes added interwikis without the template).
- [ ] **Multiple `{{wikidata link}}` on one page.** Per-case review — usually a Wikidata disambiguation issue.
- [ ] **`[[Category:Pages with duplicated content]]` + remaining `need_translation/` pages.** Mostly handled by the cloud-queue worker (`docs/remote_queue_pipeline.md`); manual review only for the hard cases — canonical-title choice / history merge, and the 9 large kokuzō articles. NEVER strip `[[Category:Need translation]]` without verifying the body is actually English (the sync deletes the file when the category goes).



## Wikidata (social / high-care — respect the freeze to 2026-06-06; QuickStatements pipeline only)

- [ ] **Recreate deleted Wikidata items.** A batch of ILL-target items were deleted by another editor. Build `generate_recreate_quickstatements.py`: walk `[[Category:Pages with deleted QID in ill template]]`, render `CREATE` + `P11250|"shinto:..."` blocks for human review via the existing QS pipeline. Define a minimum claim set that won't get re-deleted (the original failure). Lower-risk than a direct-API recreator; human-gates notability.
