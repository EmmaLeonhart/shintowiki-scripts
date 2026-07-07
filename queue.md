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

## 1. Category-orchestrator throughput (conditional, low priority)

- [ ] A full ns14 category cycle still takes ~many fires at ~1000 pages/145min. ONLY if #2's drain
  proves too slow: skip history_offload/fandom_mirror on the ~3k enwiki-junk cats, or shard ns14. No
  premature optimization. (Cleanup-loop reliability itself is DONE — run 28802688487 green end-to-end.)

## 2. Drain the category-deprecation back-pressure

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

## WDQS-gated audits — ONLY the 10pm cron works these

These need a full `query.wikidata.org` SPARQL scan; WDQS has been 429-outaged (2026-07-06+). **The
regular work-loop SKIPS this whole section** — do NOT attempt these on the hourly loop. A dedicated
**22:00 local cron** tries them once a night; if WDQS is still down it no-ops and retries tomorrow.

- [ ] **Alias audit + cleanup.** Cross-ref the old `Aen` lines the pipeline submitted vs live
  Wikidata aliases; generate QS to REMOVE the junk (~72 comma-disambiguators like `…, Hino, Tokyo`).
  Trace the SOURCE typos (`Zebshō` etc. are bad labels on OTHER items) and correct them. (Root cause
  already fixed `b11f8b54`; phonology validator already built — `modern-quickstatements/romaji_phonology.py`.)
- [ ] **Repeated-name shrine audit.** Shinto shrines (P31 Q845945) with a ja label used ≥10×; audit
  those clusters for disambiguation / data-quality.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
