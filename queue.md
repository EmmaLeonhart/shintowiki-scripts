# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Standardization — deferred tails (need new transliterators; not CI-gated)

- **th** (33/135 labels): needs a real Thai transliterator (pre-posed vowel
  signs); build only as its own deliberate task.
- **pa/km/lo/dz/new/mad/shn** (≤16 labels each): no script converter, 0-2
  observed labels — revisit only if a converter arrives or Sonnet does them.
- **cdo**: zero observed labels, mixed-script wiki — parked with evidence.

---

## Multilingual label generalization (BFS-driven)

Goal: name every important Shinto entity in all ~60 covered languages. All the
transliteration categories (kami / Buddhist deities+Sanskrit engine / provinces /
people / texts / Shikinaisha lists / court-ranks-CJK / misc-terms) are SHIPPED and
wired into the 11-step `!regenerateQuickStatements.bat` — see DEVLOG 2026-07-04.

DELIVERY to Wikidata (verified 2026-07-04): `modern-quickstatements/select_label_proposals.py`
globs `shinto-label-generator/quickstatements/*.txt` — ALL category files included,
not just `<lang>.txt` — into `label_proposals_drip.txt`, drip-fed **20/day** by the
daily submission (routed to direct-daily-edits since the QS path is retired). The
drip opens FULLY on `RAMP_DATE` = 2027-05-23 (a deliberate ~1-year community-review
window). So the labels reach Wikidata; the tail just drains slowly until the ramp.

Remaining:

1. **Translation tier (cron-driven, ongoing).** Daily 15:00 run
   (`generate_concept_translations.py`) hand-translates descriptive Shinto concepts
   into confident languages, non-destructive + state-tracked. Batch 1 done (5
   concepts → 44 labels). Left: more concepts, Shinto-property names (P13723 etc.;
   relevance filter in `bfs/property_label_report.md`), the concept-classes, and the
   90-item text residue (`bfs/text_labels_residue.md`). World-religion drift =
   already labelled, skip.
2. **Kami tok classifier — NEEDS-DECISION (Emma).** Buddhist-deity tok now carries
   `jan sewi` (person + sacred). The 352 kami tok labels (in `kami_labels.txt`) carry
   NO classifier ("Enma", not "jan sewi Enma"). Deities should take one — but `jan
   sewi` = *person*-deity, and many kami are mountains/rivers/objects/concepts, which
   would want a different head noun (`ma sewi` land, `ijo sewi` thing, …). Decision:
   one classifier for all kami, or per-kami by P31 type? Don't blanket-apply until
   decided (would mis-classify the non-person kami).
3. **Polish (low priority):** Sanskrit engine niceties — Arabic initial-vowel
   carrier, Greek d→ντ inside clusters. (tok for Sanskrit deities DONE — `jan sewi`
   classifier + n-coda-aware cluster-breaking; court-rank non-CJK translation DONE.)

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
