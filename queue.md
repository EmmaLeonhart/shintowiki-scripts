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

## 3. Category-name translation — phase (c) place-name gazetteer

THE real category backlog: `[[Category:Japanese language category names]]` (~1189 subcats).
Phases a+b shipped (dated-maintenance transform + Wikidata-anchored resolver). Remaining:

- [ ] **Phase (c):** a JP→EN place-name gazetteer for the residual content cats with no
  Wikidata-category anchor — the productive patterns `<place>の神社` → `Shinto shrines in <place>`,
  `<place>市`/`<place>県`. Bootstrap the gazetteer from Wikidata place labels (authoritative, not
  guessing). Residual list auto-maintained at `docs/category_translation_residual.md`.

## 4. Un-sync the 144 resolved deleted-QID-ill pages

All 144 pages' `{{ill|…|qid=DELETED_QID}}` are now resolved (created/relinked/de-illed) and the
instruction comment is removed, but they still carry `[[Category:Git synced pages]]`, so
`git_synced/` is still 144 pages larger than normal.

- [ ] Remove `[[Category:Git synced pages]]` from each resolved page so the next
  `sync_git_synced_pages` run pushes the final content to the wiki and drops the local copy.
  Verify the sync pushes-then-drops (doesn't drop before propagating the relinked content).

## 5. EN/FR/ID label-gap regularization

- [ ] Some shrines have labels in one/two of en/fr/id but not all three (old technical failures).
  NEEDS-DECISION (Emma): is this still a distinct same-source cross-fill, or is it subsumed by the
  BFS/multilang drip (which now generates fr+id fills into the drip, confounding a live-Wikidata
  gap query)? Confirm scope, then build the fill where the others exist.

## 6. cdo (Min Dong) transliterator (do last)

cdo = the romanization (Bàng-uâ-cê) of the hanzi the zh label already produces. Approach found +
started: Wiktionary `|md=` param (神→sìng); no pip lib (`pyfoochow` absent). Partial data in
`shinto-label-generator/cdo_readings.json` (37 hanzi).

- [ ] Finish the hanzi→Min-Dong table (fetch `md=` for the full kanji set the zh generator emits),
  wire `cdoify()` reading the zh output. Zero cdo labels observed, so last — but it gets done.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
