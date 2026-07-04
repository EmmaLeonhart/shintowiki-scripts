# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Verify the category-prefix fix (gate: tonight's ~06:00 UTC cleanup-loop run — first to carry f88f3a9c)

After the run + daily-edits cycle: [[QuickStatements/Category label fixes]]
populates, the drip applies prefixed labels, no bare category labels re-emitted.
Ship details: DEVLOG 2026-07-04.

## Category-orchestrator wedge discriminator (gate: tonight's ~06:00 UTC run — first instrumented one in-pipeline)

Month-long daily 160-min zero-output wedge. Standalone dispatch with current
code SUCCEEDED in 6m24s (2026-07-04), so it does not reproduce outside the
pipeline. Tonight discriminates: wedges again → the faulthandler dump in the
job log names the line, fix it; succeeds → the mwclient retry-cap fix was the
cure, delete this item. Full forensic trail: DEVLOG 2026-07-04.

## 同上 pipeline residuals

1. **Generalize beyond 出雲国** (gate: doujou drip convergence): re-run the
   SPARQL in resolve_doujou_addresses.py; if other provinces carry 同上,
   extend the resolver's article list.
2. **Verify the FULL province-list sweep completes across runs.** The 07-04
   dispatch died at the old 170-min timeout at province ~62/68 with its
   runner-local progress lost; fixed 69a0745c (progress committed cross-run,
   cleared on completion; 355-min window; concurrency group). The 18:37 UTC
   schedule did NOT fire on day one (new schedules can lag registration) —
   if it also skips tomorrow, dispatch manually. Verify: a sweep run goes
   green, the tail provinces (alphabetically last ~6) get regenerated, and
   2-3 non-Awa pages carry the Address column.

## Standardization — deferred tails only (rungs 1-3 shipped+verified, DEVLOG 2026-07-04; ALL_LANGS now 48)

- **th** (33/135 labels): needs a real Thai transliterator (pre-posed vowel
  signs); build only as its own deliberate task.
- **pa/km/lo/dz/new/mad/shn** (≤16 labels each): no script converter, 0-2
  observed labels — revisit only if a converter arrives or Sonnet does them.
- **cdo**: zero observed labels, mixed-script wiki — parked with evidence.

## Wikidata direct path at 300/day — verify after 2-3 daily cycles

reports/ show the qs_retired daily reports + ~300-line direct runs; sampled
temple QIDs gain en labels (temple files only entered the direct list
2026-07-04 — they were orphaned in the QS-only list before). Details:
DEVLOG 2026-07-04.

---

## Multilingual label generalization (BFS-driven)

Goal: name every important Shinto entity in all ~60 covered languages. All the
transliteration categories (kami / Buddhist deities+Sanskrit engine / provinces /
people / texts / Shikinaisha lists / court-ranks-CJK / misc-terms) are SHIPPED and
wired into the 11-step `!regenerateQuickStatements.bat` — see DEVLOG 2026-07-04.
Remaining:

1. **Court ranks — non-CJK lexical translation.** "Junior/Senior Nth Rank" → each
   language; the rendering of 正/従 varies, so translate carefully, don't invent.
2. **Translation tier (cron-driven, ongoing).** Daily 15:00 run
   (`generate_concept_translations.py`) hand-translates descriptive Shinto concepts
   into confident languages, non-destructive + state-tracked. Batch 1 done (5
   concepts → 44 labels). Left: more concepts, Shinto-property names (P13723 etc.;
   relevance filter in `bfs/property_label_report.md`), the concept-classes, and the
   90-item text residue (`bfs/text_labels_residue.md`). World-religion drift =
   already labelled, skip.
3. **Polish:** tok for Sanskrit deities (needs a syllabifier); Sanskrit engine
   niceties (Arabic initial-vowel carrier, Greek d→ντ in clusters).

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
