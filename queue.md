# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here. **Nothing here is "parked" or "out of scope" — every item gets done; ordering is
just priority.**

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Get the cleanup-loop reliably working (Emma priority)

The cleanup-loop is still unreliable: the category-orchestrator step intermittently hits its
160-min timeout (07-04 failed on it; the `63926a81` mwclient-retry-cap helped so 07-05 passed,
but runs take 8h+ and the 07-06 run ran 3h+). The category orchestrator "has never completed a
full cycle" (CLAUDE.md), so the category deprecation / translation / interlang-consolidation
back-pressure never fully drains.

- [ ] Make the cleanup-loop green-complete every fire. Diagnose the category-orchestrator
  slowness (allpages(ns=14) walk vs the 150-min internal budget / 160-min step timeout — why it
  overshoots), and fix: the internal time-budget should stop it and commit state well before the
  step timeout so it resumes next run (it is cursor-resumable), and/or split the namespace across
  jobs. Verify a real run green-completes, not just local.

## 2. cdo (Min Dong) transliterator (lowest priority — do last)

cdo = the **romanization (Bàng-uâ-cê) of the hanzi the zh label already produces**
(`generate_chinese_quickstatements.py`: kana→man'yōgana + OpenCC). Pipeline: zh-hanzi →
per-character Min Dong reading → Bàng-uâ-cê string. **Approach found + started 2026-07-06:**
Wiktionary exposes the reading in the zh-pron `|md=` param (神→sìng, 社→siâ); no pip library
exists (`pyfoochow` absent, opencc is script-only). Partial data fetched into
`shinto-label-generator/cdo_readings.json` (37 of the man'yōgana + common-shrine hanzi).

- [ ] Finish the hanzi→Min-Dong table (shrine names carry arbitrary kanji, so fetch `md=` for the
  full kanji set the zh generator emits over the shrine query), then wire a `cdoify()` that reads
  the zh output and joins the BUC readings. Zero cdo labels observed on JP shrines/temples, so
  this is last — but it gets done.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
