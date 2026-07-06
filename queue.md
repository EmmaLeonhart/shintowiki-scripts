# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Long-tail language transliterators (build task)

- [ ] **Thai (`th`)** transliterator — kana→Thai script with pre-posed vowel reordering
  (เ/แ/โ/ใ/ไ written before the consonant, pronounced after). 33/135 labels. BLOCKED on a
  *verified* converter: no Thai transliteration lib is installed (pythainlp/tltk/thai_romanization
  all absent) and hand-rolling kana→Thai orthography can't be verified here — shipping unverifiable
  labels to Wikidata is worse than not shipping. Needs a deliberate build with a Thai reference.
  `pa/km/lo/dz/new/mad/shn` (≤16 labels) + `cdo` have no converter either. `python
  shinto-label-generator/language_registry.py` lists uncovered languages by count.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
