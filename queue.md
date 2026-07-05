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

**Active — QuickStatements provenance comments** (promoted from todo.md 2026-07-05).
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

ROLLOUT REMAINING — the 3 CI-run generators (these DO apply on CI once wired; thread a
per-label `source`, fix any 3-tuple sample loop): **korean** (hanja vs koreanize source),
**chinese** (ja kanji), **multilang** (the id/en source label it extracts). indonesian
already emits `# Source:` comments. One generator per tick. Each wired file ~doubles in
line count on regen (a comment per label) — the intended "annotate output lines".
(Sanskrit-engine polish DONE: Greek double-nasal νντ→ντ; Arabic/Perso-Arabic/Hebrew
word-initial vowel carriers — Indra → ar إندرا / fa ایندرا / he אינדרא.)

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
