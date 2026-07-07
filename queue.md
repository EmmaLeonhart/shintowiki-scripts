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

## SPARQL-heavy audits

These need a full SPARQL scan. `query.wikidata.org` is 429-outaged (2026-07-06+), but the SPLIT
endpoint **`query-main.wikidata.org/sparql` works** — use it (it serves everything except scholarly
articles). Heavy, so the 22:00 cron owns them; the hourly loop can also run them via query-main now.

- [ ] **Alias audit — trace SOURCE typos.** Comma-disambiguator cleanup DONE 2026-07-07: found 207
  comma-aliases on shrine/temple items via query-main, wrote 189 removals (`-Qxxx|Aen|"…"`) to
  `modern-quickstatements/remove_junk_aliases.txt` (kept 18 two-name aliases) — the daily pipeline
  drains them. REMAINING: trace the SOURCE typos (`Zebshō` etc. are bad LABELS on OTHER items, likely
  a cloud session) and correct them via QS; the phonology validator (`romaji_phonology.py`) can flag
  invalid-mora labels at scale via query-main.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
