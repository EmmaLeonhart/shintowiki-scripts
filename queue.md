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

Goal: generalize labels for Shinto texts/concepts/deities/ranks/provinces across all
covered languages. Everything lives in `shinto-label-generator/`. Shrines + Buddhist
temples + Shikinaisha lists are ALREADY covered (algorithmic names) and are excluded
from new labelling (but NOT pruned from the BFS graph). Shipped so far (see DEVLOG
2026-07-04): Shikinaisha-list generator; kami / shrine-rank / province generators
(`translit_common.py` shared helper); BFS crawler + per-layer analysis.

1. **BFS crawl → depth 5 (resumable).** `shinto-label-generator/bfs/crawl_shinto_bfs.py`,
   forward-links-only, resumes from `bfs/state.json`; `--max-nodes N` bounds a run.
   Growth 54→183→4932; level 3 (~5000+) was mid-crawl. A background run may be active
   THIS session — do NOT start a second crawl while one is writing state.json (two
   writers corrupt it). When stopped, resume with e.g. `--max-nodes 2000 --max-depth 5`;
   commit updated `state.json` + new `levels/level_NN.tsv`. Deeper levels drift into
   non-Shinto geography (LAYER_ANALYSIS.md) → NEEDS-DECISION from Emma on the cutoff
   (likely depth 3-4); surface level sizes, don't silently push to 5.
2. **Re-run layer analysis as levels land.** `python bfs/analyze_layers.py` after each
   new `level_NN.tsv`; refresh `bfs/LAYER_ANALYSIS.md`.
3. **Property labels (Emma, NEW) — first step DONE, needs a relevance filter + Emma.**
   `bfs/property_label_report.py` → `property_label_report.md`: 806 distinct properties
   on the Shinto-core items (levels 0-1) — counting MAIN values, QUALIFIERS, and
   references (qualifiers matter: Shinto properties are heavily qualified; +90 props vs
   direct-only), ALL with gaps in ≥1 covered lang. FINDING: much of the 806 is irrelevant
   external-ID properties (e.g. "Video Game History Foundation Library subject ID"); the
   genuinely actionable Shinto/structural targets
   are a small set — e.g. **P14005 Japanese court rank** (missing 57/60), P13723, P527,
   P31, P361. NEXT: (a) filter to Shinto-relevant properties (drop external-ID datatype
   props); (b) property labels are TRANSLATION not transliteration → Emma-scoped decision
   on how to fill them (do NOT guess-transliterate). Extending the sweep to layer 2 is a
   network follow-up (blocked while the crawl holds the Wikidata budget).
4. **Texts/concepts — RECONCILED with the roadmap (`docs/mass-label-expansion-plan.md` §5).**
   Emma's roadmap says missing labels use SYSTEMATIC transliteration ("systematic
   guesswork"), NOT bespoke translation — so no translation pipeline is wanted. The main
   text (Engishiki Jinmyōchō) is already labelled via the shikinaisha generator; the
   remaining Shinto terms (kanazukai, Ritsuryō funding types) are tiny sets that can fold
   into a general bare-term transliteration pass if desired. Off-domain
   encyclopedia/database/language items are skipped. No further action unless Emma wants
   the small term sweep.
5. **Humans DONE; court ranks PARTIAL (CJK only — need lexical translation).** Japanese
   people (`generate_human_quickstatements.py`, 27 romaji-named figures →1050 labels,
   `looks_romaji`-guarded) shipped. Court ranks (P14005, 16 values): CJK+ko shipped and
   correct (they share the kanji 正一位 etc.), BUT the en labels are LEXICAL
   ("Junior/Senior Nth Rank") → the ~50 non-CJK langs need lexical TRANSLATION, not
   transliteration (compose from translated Junior/Senior + ordinal + Rank). NOT done.
6. **Buddhist deities — SHELVED, needs an ANALYSIS task (Emma).** The bare-name engine
   transliterates the JAPANESE reading, but Buddhist deity names are Sanskrit-derived
   with established forms per language (Indra≠"indora", Avalokiteśvara≠Kannon-reading).
   Generator gated behind `--buddhist` (off); bad output removed. NEXT: comprehensive
   analysis of how each Buddhist deity's name is rendered across the covered languages;
   only ones whose English name IS Japanese-derived can use the engine. Systematic
   *translation*, not transliteration.
7. **Misc list must use subclass-of (P279), not only instance-of (P31).** BUG:
   `list_miscellaneous.py`/`categorize_miscellaneous.py` dropped items that are classes
   (only P279, no P31) via the `if types[q]` guard — Shinto concept-classes got thrown
   out. Fix: include P279 in the type signal + easy-root exclusion; rebuild
   `miscellaneous.tsv` + `miscellaneous_categorized.md`.
8. **Drift items are wanted too (Emma) — need a TRANSLATION pipeline.** The "drift"
   (encyclopedia articles, concepts, etc.) is NOT to be discarded — build a proper
   lexical-TRANSLATION pipeline so they get labels too (this is the recurring theme:
   descriptive things translate, only proper names transliterate). `bilateral relation`
   (76) = "X–Japan relations" articles, pure drift from the Japan node — Emma skeptical;
   lowest priority / probably skip.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
