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

## 6. Resolve the current deleted-QID ills (RAG → best existing item, never recreate)

Policy (Emma 2026-07-06): a deleted-QID ill gets its `qid=` set to the BEST EXISTING Wikidata item
(research, not recreate). `deleted_qids_in_ill` op now SELF-HEALS the stale category (fixed
2026-07-07 + tests) — so Bath Additive + Iyo Shrine (tagged but no deleted QID) auto-clear next sweep.
The 3 real cases are researched and ready:

- [ ] Apply via CI (wiki creds): **Ogawa Shrine** + **Nawino Shrine** ill `Q702140` (Ōnamuchi-no-Mikoto,
  DELETED) → **Q276944** (Ōkuninushi); **Takeo Shimokorihiko Shrine** ill Taira-clan (`Q568647` DELETED)
  → **Q1079102** (Taira clan). Wire a date-gated one-off into `wiki-cleanup.yml` (don't hand to Emma).
  Retire `recreate-deleted-wikidata/generate_recreate_quickstatements.py` (superseded).

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
