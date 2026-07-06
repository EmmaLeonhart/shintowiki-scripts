# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

---

## 1. Long-tail language transliterators (residual)

- [ ]  (Min Dong) — mixed Chinese characters + Bàng-uâ-cê romanization, NOT a plain
  romaji→script transliteration, so the multilang engine does not fit it. Only remaining
  uncovered lang. (th/new/pa/mad/my/km/lo/dz/shn all SHIPPED 2026-07-06.)

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
