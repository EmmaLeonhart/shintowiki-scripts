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

Translation tier — investigated & closed for the local work-loop (2026-07-05):

- **Descriptive concepts: DONE.** `generate_concept_translations.py`'s hand-authored
  dict is fully drained (11/11 concepts, 57 labels, in the drip). It only translates
  what a human authors into the dict — no auto-discovery — so it is NOT "ongoing";
  it no-ops until someone adds entries. The confidently-Shinto concepts are exhausted.
- **Shinto property names: DONE.** The only two genuinely Shinto-specific descriptive
  properties — P13723 shrine ranking, P14005 court rank — are translated
  (`generate_property_translations.py`, in the drip). Every other entry in
  `bfs/property_label_report.md` is a GENERIC community-maintained Wikidata property
  (worshipped by, official religion, next-higher-rank, literal translation, …) —
  core infrastructure, out of this project's remit; do NOT mass-propose translations.
- **Concept-classes / 90-item text residue (`bfs/text_labels_residue.md`):** these are
  translation-not-transliteration of mostly non-Japanese / foreign-encyclopedia /
  infra titles — i.e. bulk LLM-grunge, which per the top-of-file policy belongs to the
  claude.ai remote routine (`remote_queue.json`), NOT the local work-loop. Not
  actionable here without guessing.

So the translation tier is COMPLETE: the transliteration matrix is shipped +
drip-delivered, and every confidently-actionable translation is done. What's left is
remote-routine drift and the 2027 delivery ramp.

**DONE — QuickStatements provenance comments** (2026-07-05; promoted from todo.md).
Annotate each generated label line with the source it derives from, as a `# <source>`
comment line (drip selector + submitter skip `#`, so it never reaches Wikidata; same
pattern generate_indonesian_proposals.py already uses). FOUNDATION SHIPPED: `write_qs`
now emits a provenance comment for 4-tuple `(qid, lang, label, source)` rows
(backward-compatible; tested). Sources: phonetic ← `romaji "…"`, CJK ← `ja kanji "…"`,
ko-hanja ← `ja kanji "…" (hanja)`, Sanskrit-named ← `Sanskrit "…"`.

**IMPORTANT — how comments actually reach the .txt (corrected 2026-07-05):** the
CATEGORY generators (kami, buddhist, human, misc_terms, shrine_rank, courtrank_buddhist,
province, text, shikinaisha, *_translations) are NOT run by CI — `label-generator-
regenerate.yml` only runs fetch_shrines_tokiponize / korean / chinese / indonesian /
multilang. So category-file comments apply only on Emma's local `!regenerateQuickStatements.bat`
rebuild (verified end-to-end 2026-07-05: a local `generate_misc_terms` run produced 960
well-formed `# <source>` lines, one per label, integrity tests green — then reverted so
category files stay a consistent set for the next full rebuild). The CI-run subset
(korean/chinese/multilang) DOES apply on CI once wired.

WIRED — ALL 8 CATEGORY generators done (2026-07-05): kami, human, misc_terms,
shrine_rank, courtrank_buddhist, buddhist, **province**, **text** (text's
`labels_for_item` now returns `(lang, label, source)` triples; its test helper +
a provenance assertion updated). These apply on Emma's next local
`!regenerateQuickStatements.bat`.

ROLLOUT COMPLETE — every transliteration generator now emits provenance. CI-run
(korean, indonesian, chinese, tokiponize already did; **multilang** wired 2026-07-05 →
applies next CI regen) + all 8 category generators (apply on the local `.bat` rebuild).
Not covered, by design: `shikinaisha_lists` (frame-built descriptive list-titles, not a
transliteration of one source label — could add a province/parent source later if wanted)
and the hand-authored `courtrank_/concept_/property_translations` (translations, no source
label → N/A). Each wired file ~doubles in line count on regen — the intended "annotate
output lines".
(Sanskrit-engine polish DONE: Greek double-nasal νντ→ντ; Arabic/Perso-Arabic/Hebrew
word-initial vowel carriers — Indra → ar إندرا / fa ایندرا / he אינדרא.)

---

## Backlog board barrel-through (2026-07-05 session)

Working the 8 `BACKLOG_ITEMS` (`site/generate_pages.py`). #1 and #2 done this session;
#3/#4/#6/#7 are shipped-automation whose residual is inherent human review / remote-
routine (not build tasks). The genuinely-buildable remainder is #5 (Japanese category
names, phased) and #8 (recreate deleted Wikidata items, below).

## Backlog #8 — recreate deleted Wikidata items (CONTINUATION for a future session)

Generator SHIPPED this session: `recreate-deleted-wikidata/generate_recreate_quickstatements.py`
(isolated dir; NOT auto-submitted; 7 unit tests; CI-wired). It walks
`[[Category:Pages with deleted QID in ill template]]` (144 pages → **304 distinct
deleted ill targets**) and writes info-rich `CREATE` blocks to
`recreate-deleted-wikidata/recreate_quickstatements.txt` + a human-review `review.md`.
Corrected the original design: the deleted QIDs are the ill **targets** (sub-topics),
NOT the pages (which already have their own items) — so NO `P11250|"shinto:…"`. Old
QIDs are carried as `#` provenance comments (36 recovered — 31 from `dd=`, +5 from the
QID-was-written-into-the-label-slot data-loss bug, now detected & recovered). Enrichment:
jawiki-article existence gates the sitelink (notability anchor); ja-already-linked-to-a-
live-item flags probable duplicates (2 found). Only **7/304** currently have a safe
jawiki sitelink → the rest need content before they'd survive re-deletion.

**Remaining (NOT this session — recreation itself is out of scope, per Emma):**
- [ ] Per-target research to give each item enough content to not be auto-deleted again
  (Wikidata churn is the risk). The count (304, only ~36 with recovered QIDs) is small
  enough to research individually. Enrich `CREATE` blocks with whatever authoritative
  data can be found (claims, better sitelinks, descriptions) beyond the current
  labels+provenance.
- [ ] Decide the minimum viable claim set per target-type (person / shrine / facility /
  concept) that survives Wikidata deletion review.
- [ ] Only after review: feed vetted blocks through the QuickStatements pipeline
  (human-gated; still respect the WD-editing rules in CLAUDE.md).

## Context dump + agentic RAG on deleted Immanuelle-created Wikidata items (next session)

- [ ] **Go over the context dump** committed this session in `context dump/` (a saved
  Claude Code page + assets, `911bbfb6`). Read it for the info/links it carries and fold
  anything actionable into the queue/plan.
- [ ] **Agentic RAG on the Wikidata items that Immanuelle created and that were then
  deleted.** Emma is dumping these (there are likely account restrictions preventing a
  live API pull, so the source is the dump, not a query). **Check the `context dump/` for
  the item info / links first**, then do agentic RAG over the things linked there to
  reconstruct enough content for recreation. **If that context is missing from the dump,
  say so explicitly** (don't fabricate) and flag it as blocked-on-Emma-providing-the-dump.
  Feeds directly into backlog #8 (deleted-QID recreation) above — the deleted
  Immanuelle-created items overlap the 304 deleted ill targets.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
