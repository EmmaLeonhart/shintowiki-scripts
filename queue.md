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

## Multilingual label generalization (BFS-driven) — non-central-command session's active work

Goal: name every important Shinto entity across all ~60 covered languages so a
speaker of any of them can navigate the Engishiki and its world. Everything lives
in `shinto-label-generator/`, wired into `!regenerateQuickStatements.bat`.

**SHIPPED — transliteration (proper names), all wired into the 10-step batch:**
kami 18,651 · Buddhist deities 3,464 (JP engine for JP-named, separate Sanskrit
engine `sanskrit_translit.py` for Sanskrit-named — clusters preserved, all scripts
incl. ar/fa/he) · provinces 3,053 · Japanese people 1,050 · classical texts 2,611
(hub session's unified 287-scope labeller) · Shikinaisha lists 3,982 · court ranks
CJK/ko. Supporting: BFS crawl (stopped at level 3 = 45,949; deeper = geography
drift, resume only if wanted), misc categorization (P279 subclass bug FIXED),
property-coverage report.

**REMAINING:**
1. **Court ranks — non-CJK lexical translation.** en labels are lexical
   ("Junior/Senior Nth Rank"); the ~50 non-CJK langs need real translation
   (compose from Junior/Senior + ordinal + Rank), not transliteration.
2. **Descriptive concepts + properties + drift — the TRANSLATION tier.** Abstract
   Shinto concepts (State Shinto, religion types), the Wikidata properties
   themselves (P13723 etc. — report in `bfs/property_label_report.md`, relevance
   filter still todo), and the wanted "drift" (encyclopedia entries etc.) all need
   lexical translation. Route via the daily Claude translation routine
   (`remote_queue.json`), NOT blind generation. `bilateral relation` (76,
   "X–Japan relations") = pure drift, skip.
3. **Misc-terms transliterator — WRITTEN, blocked on API.**
   `generate_misc_terms_quickstatements.py` catches the Japanese-named terms in
   the misc bucket (-zukuri architecture styles, rituals like Reisai, sects like
   koshintō) via `looks_romaji`, excluding texts. Wikidata API is 429-blocking the
   session — run it when the limit clears, verify, then wire into the batch (step 11).
4. **Polish:** tok for Sanskrit deities (Toki Pona can't take clusters — needs a
   syllabifier); Sanskrit engine niceties (Arabic initial-vowel carrier, Greek
   d→ντ in clusters).
5. **Text residue: 90 unroutable** (no romaji/kana/kanji) in
   `bfs/text_labels_residue.md` — folds into the translation tier (item 2).

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
