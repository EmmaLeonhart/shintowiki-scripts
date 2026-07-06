# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here. **Nothing here is "parked" or "out of scope" — every item gets done; ordering is
just priority.**

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Get the cleanup-loop reliably working (top priority — enables everything else)

DIAGNOSED + FIX SHIPPED (`1fa6c414`): the RED-timeout cause was ns14 ballooning to 28,176 pages
(mostly enwiki-import date/maintenance cats) × heavy per-page ops → 1000 pages cost 2h40m → blew
the 160-min category step timeout, killed red. Added a wall-clock self-stop
(`MAX_RUN_SECONDS=145min`) to `common.run_orchestrator` so every orchestrator stops clean/green
and resumes from the cursor. Remaining:

- [ ] Confirm on a live fire that the category (and module) orchestrator now green-completes —
  either exhausts or hits the 145-min cap and exits 0 with committed state. Next scheduled
  cleanup-loop fire validates (the 07-06 in-progress run is on pre-fix code). If it still reds,
  investigate the next-slowest step.
- [ ] THROUGHPUT (separate from reliability, lower priority): a full category cycle still takes
  ~many fires at ~1000 pages/145min. If draining the category back-pressure (item 2) is too slow,
  consider not running history_offload/fandom_mirror on the ~3k obvious enwiki-junk cats, or
  sharding ns14. Do NOT touch unless item 2 proves too slow — no premature optimization.

## 2. Drain the category-deprecation back-pressure (depends on #1)

Once the loop runs: the **18 Japanese-named duplicate categories** tagged this session into
`[[Category:Japanese language category names]]` get translated (cloud) + merged by
`move_categories`; the interlang consolidation (`{{wikidata link}}` merge) and the new
`merged_qids_in_ill` op sweep the wiki.

- [ ] Confirm the 18 tagged dups actually move/merge once the loop is healthy; spot-check a few.

## 3. Category-name translation — residual tail (machine-resolvable patterns EXHAUSTED)

`[[Category:Japanese language category names]]` (~1186 subcats). Resolved: dated-maintenance
transform, phase-1 Wikidata-category-anchored (covers ~all QID'd cats incl. `の神社` shrines via
authoritative enwiki category sitelink), and phase-4 place gazetteer (`の建築物`/`の歴史`/`の神社`/
`の寺院`/`の重要文化財`, jawiki→enwiki place + P31 gate). All productive patterns with a VERIFIED
enwiki category convention are now handled. The residual is genuinely human-translation / bespoke
territory (documented negatives, never machine-guessed):

- `の旧県社` shrine-rank-by-place — enwiki has no "Former prefectural shrines"/"Kensha" category.
- bare `<place>郡` districts — 6/9 have no enwiki article (abolished districts); the 3 that resolve
  (Ibo/Inashiki/Funai District) have NO matching enwiki *category*, and their P31 (district Q1122846)
  isn't a place-gate class. No category convention → residual.
- `の画像提供依頼` (image-request maintenance) + `<sect>の寺院` sect-temples — each need a bespoke
  path (maintenance-cat convention / sect→English name), not a place suffix.

- [ ] (low, human/bespoke only) Anything here advances only via human translation or a purpose-built
  resolver — do NOT add a place suffix for these (no verified enwiki category convention). Residual
  auto-refreshes at `docs/category_translation_residual.md` on each CI generator run.

## 4. EN/FR/ID label-gap regularization

- [ ] Some shrines have labels in one/two of en/fr/id but not all three (old technical failures).
  NEEDS-DECISION (Emma): is this still a distinct same-source cross-fill, or is it subsumed by the
  BFS/multilang drip (which now generates fr+id fills into the drip, confounding a live-Wikidata
  gap query)? Confirm scope, then build the fill where the others exist.

## 4b. Recreate the ~213 recoverable deleted-Immanuelle Wikidata items ([[Open questions]] Q1)

- [ ] NEEDS-DECISION (Emma): the fandom crossref recovered ~213 deleted items (203 QID-anchored)
  with per-language content (`recreate-deleted-wikidata/shinto_wiki_crossref.md`). The deleted-QID
  ILL-target subset was already created this session (Emma ran the QS) + relinked. Still open for the
  BROADER ~213: (a) recreate them all on Wikidata? (b) minimum viable claim set per type
  (person/shrine/facility/concept) to survive Wikidata deletion review? Nothing to Wikidata without
  Emma's go-ahead (CLAUDE.md WD rules). Analysis: `docs/deleted_immanuelle_items_analysis_2026-07-05.md`.
  If yes, express as QuickStatements only (feed the daily pipeline) — never a bespoke editor.

## 5. cdo (Min Dong) transliterator — maintenance only

Built + wired (gated `cdoify` in `generate_chinese_quickstatements.py`, registered, emits `cdo.txt`;
`cdo_readings.json` 1502 entries, 1502/2192 corpus-char coverage). No open task — the only ongoing
work is coverage growth:

- [ ] (low, recurring) Rerun `python fetch_cdo_readings.py --corpus --apply` after the zh corpus
  grows, to pick up new shrine-name chars. 690 chars currently have no Wiktionary `md=` reading
  (genuine gaps); gated cdo simply withholds labels containing them. Not a blocker.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
