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

## 3. Category-name translation — residual tail

`[[Category:Japanese language category names]]` (~1186 subcats). Resolved so far: dated-maintenance
transform, phase-1 Wikidata-category-anchored (which already covers ~all `の神社` shrine cats — they
carry category QIDs → authoritative enwiki category sitelink), and phase-4 place gazetteer
(`の建築物`/`の歴史`/`の神社`/`の寺院`, jawiki→enwiki place + P31 gate). ~425 residual remain in
`docs/category_translation_residual.md`. Remaining productive patterns need EITHER a verified enwiki
category convention (only then a suffix is added) OR human translation — never machine-guessed:

- [ ] Work the residual tail: `の重要文化財` (Important Cultural Properties), `の旧県社`
  (shrine-rank-by-place), `<place>郡` bare districts, and `<sect>の寺院` sect-temples (P31 gate
  correctly sends these to residual — they're temples OF a Buddhist school, not IN a place; needs a
  separate sect→English-name path if wanted). Add a suffix only when the enwiki convention is
  verified; otherwise leave for human translation. Low urgency — phases 1/4 already drain the bulk.

## 4. EN/FR/ID label-gap regularization

- [ ] Some shrines have labels in one/two of en/fr/id but not all three (old technical failures).
  NEEDS-DECISION (Emma): is this still a distinct same-source cross-fill, or is it subsumed by the
  BFS/multilang drip (which now generates fr+id fills into the drip, confounding a live-Wikidata
  gap query)? Confirm scope, then build the fill where the others exist.

## 5. cdo (Min Dong) transliterator (do last)

cdo = the romanization (Bàng-uâ-cê) of the hanzi the zh label already produces. Approach found +
started: Wiktionary `|md=` param (神→sìng); no pip lib (`pyfoochow` absent). Partial data in
`shinto-label-generator/cdo_readings.json` (37 hanzi).

- [ ] Finish the hanzi→Min-Dong table (fetch `md=` for the full kanji set the zh generator emits),
  wire `cdoify()` reading the zh output. Zero cdo labels observed, so last — but it gets done.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
