# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here. **Nothing here is "parked" or "out of scope" — every item gets done; ordering is
just priority.** Keep items TERSE (Emma 2026-07-06) — a checkbox + one or two lines; no essays, no
"LAST TASK"-style labels (there's always more). Numbers are priority order, not fixed identity.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Get the cleanup-loop reliably working (top priority — enables everything else)

TWO root causes found + fixed:
1. **Category timeout** (`1fa6c414`): ns14 ballooned to 28,176 pages × heavy per-page ops → blew the
   160-min step timeout. Added a wall-clock self-stop (`MAX_RUN_SECONDS=145min`). VALIDATED — the
   07-06 run's category-orchestrator step ran GREEN in 6m11s.
2. **Site-build push race** (`generate-pages.yml`): the "Commit updated _site to repo" step did a
   single `git push` with no retry; a sibling job pushed first → `! [rejected] main -> main` → the
   step exit-1'd and reddened the WHOLE cleanup-loop (the actual 07-06 failure). Fixed: fetch-rebase
   -retry loop (5 attempts) + non-fatal exit (mirrors `commit_state.sh`; _site is cosmetic — Pages
   deploys from the uploaded artifact, not the repo commit).

- [ ] VALIDATED 2026-07-06: run 28802688487 (fix `7b0f0379`) — `generate-pages/build` ✓ green + every
  orchestrator ✓; only `direct-daily-edits` (5h WD editor) still finishing. Confirm that final step
  lands green, then delete this item.
- [ ] THROUGHPUT (separate, lower priority): a full category cycle still takes ~many fires at
  ~1000 pages/145min. Only if draining item 2 proves too slow: skip history_offload/fandom_mirror on
  the ~3k enwiki-junk cats or shard ns14. No premature optimization.

## 2. Drain the category-deprecation back-pressure (depends on #1)

Once the loop runs: the **18 Japanese-named duplicate categories** tagged this session into
`[[Category:Japanese language category names]]` get translated (cloud) + merged by
`move_categories`; the interlang consolidation (`{{wikidata link}}` merge) and the new
`merged_qids_in_ill` op sweep the wiki.

- [ ] Confirm the 18 tagged dups actually move/merge once the loop is healthy; spot-check a few.

## 4. cdo (Min Dong) transliterator — maintenance only

Built + wired (gated `cdoify` in `generate_chinese_quickstatements.py`, registered, emits `cdo.txt`;
`cdo_readings.json` 1502 entries, 1502/2192 corpus-char coverage). No open task — the only ongoing
work is coverage growth:

- [ ] (low, recurring) Rerun `python fetch_cdo_readings.py --corpus --apply` after the zh corpus
  grows, to pick up new shrine-name chars. 690 chars currently have no Wiktionary `md=` reading
  (genuine gaps); gated cdo simply withholds labels containing them. Not a blocker.

## 6. POLICY: deleted-QID ills → best EXISTING Wikidata item, never recreate

Emma 2026-07-06: recreation is a losing game — a recreated item (Q140447362 "Tropical decor",
南国趣味) got re-deleted, breaking its relink. **Do not recreate.** For any `{{ill|…|qid=DELETED_QID}}`
(or an ill whose QID is later deleted), search Wikidata for the BEST EXISTING item and set `qid=` to
it (or de-ill if there's no reasonable match). Best-effort; imperfect beats a dead link.

- Tropical decor (the ONLY current case, on Jungle bath) → RAG'd to **Q368949 "exoticism"** and
  relinked. Done.
- [ ] If deleted-QID ills accumulate again (the `deleted_qids_in_ill` op re-flags dead QIDs on its
  sweep), resolve each RAG→existing-item, not by recreation. Only worth a `remote_queue` RAG source
  (mirror the category_translation one) if the volume returns; a handful get done by hand.
  Retire `recreate-deleted-wikidata/generate_recreate_quickstatements.py` (superseded by this policy).

## 7. Full audit of Emma's items → suggest properties / edits / changes (awaiting her list/image)

Emma 2026-07-06 (end-of-queue = not-immediate, NOT parked): she will provide a set of items (via an
image / a full list). The task: look over ALL of them individually and give suggestions — Wikidata
properties to add, edits, or other changes per item. A genuine per-item review, not a skim.

- [ ] When Emma provides the items: review each one and return concrete suggestions (properties/
  edits/changes). Ask her for the list/image if not yet given.


## 8. Audit pipeline-added aliases + clean up the damage

Root cause fixed (`b11f8b54`: label-only, no aliases — the pipeline had reused other same-named items'
labels as aliases, dragging in typos like `Zebshō` + comma-disambiguators). Damage is already live on
Wikidata:

- [ ] Audit aliases the pipeline ADDED (old `Aen` vs live aliases); QS to REMOVE junk (~72
  comma-disambiguators). BLOCKED-ON-EXTERNAL: needs a WDQS scan (429-outaged 2026-07-06).
- [ ] Trace SOURCE typos (`Zebshō` etc. = bad labels on other items); correct on Wikidata. WDQS-blocked.
- [x] Japanese-phonology validator BUILT: `modern-quickstatements/romaji_phonology.py`
  (`is_valid_romaji_mora` / `is_valid_label`; rejects `Zeb`-style coda garbage; 10 tests). Reusable to
  gate cloud-session labels + flag existing bad ones (the flag-at-scale sweep is the WDQS-blocked item
  above).


## 9. Audit Japanese shrine names repeated ≥10× (Emma)

- [ ] SPARQL: Shinto shrines (P31 Q845945) with ja labels; group, find names used ≥10×; audit those
  clusters (disambiguation / data-quality). BLOCKED-ON-EXTERNAL: WDQS 429-outaged 2026-07-06 — retry
  when it recovers.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
