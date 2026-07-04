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

## Wikidata direct path at 300/day — verify + cleanup

Emma decisions 2026-07-04: QS permanently dead (no manual batch ever);
direct_daily_edits.py is the only editor, MAX_EDITS=300 at 30-90s.
1. VERIFY after 2-3 daily cycles: reports/ show ~300-line runs; sampled
   temple QIDs gain en labels.
2. Cleanup: retire submit_daily_batch's QS attempt (burns a failed API call
   per file per day).

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
3. **Property labels (Emma, NEW).** Enumerate every Wikidata property (P-id) used across
   the crawled corpus items' statements; for each, count which covered languages lack a
   label. IMPORTANT: property labels are TRANSLATION (e.g. "shrine ranking" → de), not
   name transliteration — the translit generators do NOT apply. Bounded first step:
   emit a report of distinct properties + missing-language counts. Then scope a
   translation approach; do NOT guess-transliterate property names.
4. **Texts/concepts labelling (the thorny target the BFS exists for).** Engishiki text,
   kanazukai, Ritsuryō funding types, Shinto-as-religion, etc. need real
   translation/judgment, NOT systematic transliteration. Write a scoping plan before
   building; likely routes through the remote (translation) routine, not a translit script.
5. **Broaden kami source.** `Q524158` gave 352; also sweep Shinto-deity subclasses /
   Japanese-deity classes for fuller coverage, re-run `generate_kami_quickstatements.py`.
6. **Wire new label files into `docs/index.html`** browse site (kami_labels,
   shrine_rank_labels, province_labels, shikinaisha_lists).

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.
