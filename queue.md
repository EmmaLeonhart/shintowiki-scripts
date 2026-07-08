# shintowiki-scripts — Work Queue

Conventions live in `CLAUDE.md` (delete items when done — history in `DEVLOG.md`; terse items;
numbers = priority; bulk LLM-grunge lives in `remote_queue.json`, not here).

---

## 1. Category-orchestrator throughput (conditional, low priority)

- [ ] A full ns14 category cycle still takes ~many fires at ~1000 pages/145min. ONLY if the
  Japanese-category translation drain (cloud RAG → `category_moves.csv` → monthly `move_categories`)
  proves too slow: skip history_offload/fandom_mirror on the ~3k enwiki-junk cats, or shard ns14. No
  premature optimization. (Cleanup-loop reliability itself is DONE — run 28802688487 green end-to-end.)

## SPARQL-heavy audits

These need a full SPARQL scan. `query.wikidata.org` is 429-outaged (2026-07-06+), but the SPLIT
endpoint **`query-main.wikidata.org/sparql` works** — use it (it serves everything except scholarly
articles). Heavy, so the 22:00 cron owns them; the hourly loop can also run them via query-main now.

- [ ] **Typo review — routed to cloud RAG 2026-07-06.** 161 kana-vs-label candidates are work-files in
  `label_typo_review/` (builder: `shinto_miraheze/build_label_typo_review_queue.py`), emitted by
  `remote_queue.py`; the cloud worker fills ANSWER (LABEL_TYPO/KANA_ISSUE/PREFIX_OK/OTHER).
  Collector BUILT (`shinto_miraheze/collect_label_typo_answers.py`, 5 tests; LABEL_TYPO →
  `label_typo_fixes.txt` in ATOMIC_FILES) — run it once answers land. Comma cleanup draining (189).
  2026-07-07 late-morning check: 159 pending, no new cloud answers yet.

## 11. Bunrei residual (harvest EXHAUSTED 2026-07-06 — 6 sources, ~10,550 cited edges)

Online 総本社 sources are tapped (jinja-kikou 9,971 / animism 128 / toranomaki 40 / ikkojin 129 /
shinwa-otaku 205 / nicovideo 77; xrea = jinja-kikou dupe; 護国神社 excluded — officially not bunrei).

- [ ] (low) The one unharvested online source: onkamui Rakuten blog (~50 networks with NAMED branch
  enumerations, hierarchical prose — would catch branches whose names don't match their network
  suffix). Heavy parse; do only if the suffix-method coverage proves insufficient.
- [ ] (low) Paper-only: 神社本庁『全国神社祭祀祭礼総合調査』(1995), 岡田荘司『事典 神社の歴史と祭り』—
  authoritative 系統 counts; needs Emma or a library, not scrapeable.

## Session state (2026-07-07 late morning): contained verification session, hard stop 13:00

Today runs on Emma's five one-shot time-gated crons (11:00/11:30 full pace; 12:00/12:30 wrap-up
gradient; 13:00 finished) — they replace the usual 3-cron work-loop for today and die with the
session. Remaining queue items wait on external systems (cloud RAG answers, cloud category drain,
conditional triggers, paper sources); the not-for-today conditionals are written up on
[[Open questions]] for Emma.

## From [[Open questions]] answers 2026-07-07 (wiki-queue items go at the END, per Emma's rule on that page)

- [ ] Act on decisions from `_site/bunrei-research.html` (alternative authoritative bunrei
  sources — jawiki 勧請 prose harvest, NDL digitized pre-war registries, prefectural jinjachō) once
  Emma picks a direction.
- [ ] **description_adds.txt: land the uniqueness-checked generation** (running; verify temple
  lines say temple, commit adds + `description_collision_groups.json`).
- [ ] **Retrofit the uniqueness rule into `generate_description_fixes.py`** (the desc-then-label
  pairs predate the rule; same internal+external check, colliders join the collision groups).
- [ ] **Description enrichment pipeline — cloud stages** (`docs/description_enrichment_pipeline.md`,
  Emma 2026-07-07): collision groups get informative descriptions from Wikidata item context via
  the remote-queue work-file pattern. Staged: EN-first (when ja absent) → ja from EN → EN from
  unique ja → zh(Mandarin) from ja → zh variants from Mandarin → ko from EN → rest from EN.
  Slow by design; each stage a separate, significantly-separated operation.

## From [[Open questions]] wiki-queue 2026-07-08

- [ ] **Deity-name description test (English).** First line of defense against duplicate
  descriptions: work P825 (dedicated to) deity names into the description so the property is
  load-bearing ("Shinto shrine dedicated to Hachiman in …"). Emma unsure it helps (same-named
  shrines often share the deity) — TEST it on English collision data and measure how many
  collision groups it fully disambiguates; if it works it's a cheap alternative to the cloud
  pipeline for those groups. Corollary: the deity must have a label in the language before this
  form is used there.
- [ ] **Kokugakuin ranking anomalies — agentic review.** Comprehensive pass over the anomalies
  our catchers flag in Kokugakuin university shrine rankings; agentic RAG/reasoning per anomaly →
  either normalize the content or declare it intentionally-that-way.
- [ ] **Ronsha P1352 ranking judgments → cloud RAG** (from WD-cleanup triage 2026-07-08): the 35
  all-unranked ronsha dedup candidates need per-candidate likelihood rankings (P1352 qualifiers on
  P460) — judgment work, not automatable; route via the label_typo_review work-file pattern.
- [ ] **Kokugakuin P13677 matcher** (from WD-cleanup triage): 94 Shikinaisha lack the Museum entry
  ID; propose IDs by name/province match against the Kokugakuin dataset (RAG for ambiguous). This
  also unblocks the engishiki-reference generator for the ID-less unsourced rankings.
- [ ] **jawiki infobox comprehensive review** for Buddhist temples + Shinto shrines + KOFUN:
  what else is importable to Wikidata (existing properties or creative repurposing, like the
  reisai P837 import) that's underrepresented.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
