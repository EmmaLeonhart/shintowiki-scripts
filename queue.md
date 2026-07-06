# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Long-tail language transliterators — cdo (Min Dong)

Emma 2026-07-06: cdo = the **romanization (Bàng-uâ-cê) of the hanzi the zh label already
produces** (generate_chinese_quickstatements.py: kana→man'yōgana + OpenCC). So the pipeline is
zh-hanzi → per-character Min Dong reading → Bàng-uâ-cê string.

- [ ] Build the hanzi→Min Dong romanizer. NEEDS-INVESTIGATION (dataset): no pip library
  ( doesn't exist; opencc is script-only, not romanization). The man'yōgana set is
  just 65 distinct hanzi, but shrine/temple names carry **arbitrary kanji**, so a comprehensive
  hanzi→Min-Dong reading table is needed — source it from Wiktionary's Min Dong (cdo)
  pronunciations or a downloadable Min-Dong rime dataset, verify a sample, then wire a 
  that reads the zh output. Low priority (zero cdo labels observed on JP shrines/temples), but
  now has a concrete approach rather than being blocked.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
