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

## 11. Bunrei residual (harvest EXHAUSTED — 7 sources incl. onkamui parser 2026-07-07, ~10,650 cited edges)

Online 総本社 sources are tapped (jinja-kikou 9,971 / animism 128 / toranomaki 40 / ikkojin 129 /
shinwa-otaku 205 / nicovideo 77; xrea = jinja-kikou dupe; 護国神社 excluded — officially not bunrei).

- [ ] (low) Paper-only: 神社本庁『全国神社祭祀祭礼総合調査』(1995), 岡田荘司『事典 神社の歴史と祭り』—
  authoritative 系統 counts; needs Emma or a library, not scrapeable.

## From [[Open questions]] answers 2026-07-07 (wiki-queue items go at the END, per Emma's rule on that page)

- [ ] Act on decisions from `_site/bunrei-research.html` (alternative authoritative bunrei
  sources — jawiki 勧請 prose harvest, NDL digitized pre-war registries, prefectural jinjachō) once
  Emma picks a direction.
- [ ] **Description enrichment pipeline — cloud stages** (`docs/description_enrichment_pipeline.md`,
  Emma 2026-07-07): collision groups get informative descriptions from Wikidata item context via
  the remote-queue work-file pattern. Staged: EN-first (when ja absent) → ja from EN → EN from
  unique ja → zh(Mandarin) from ja → zh variants from Mandarin → ko from EN → rest from EN.
  Slow by design; each stage a separate, significantly-separated operation.

## From [[Open questions]] wiki-queue 2026-07-08

- [ ] **Kokugakuin ranking anomalies — execute the scoped routing**
  (`docs/kokugakuin_anomaly_review_scope_2026-07.md`, scoped 2026-07-08): 7 sequence anomalies
  (RENUMBER→browser batch / INTENTIONAL→log) + ~85 multiple-P13677 rows (P958 answers→drip-safe
  qualifier-adds); clone the ronsha_ranking_review pattern.
- [ ] **Kokugakuin P13677 matcher — FEASIBLE, mechanics probed 2026-07-08**: the database's
  detail pages carry the entry's shrine name in the static <title> ("［ID:181165］ 麻績神社"), so
  an id→name index is harvestable. Known P13677 ids: 5,197 entries sparsely spread over
  29,949..183,385 — do NOT enumerate the whole range; harvest titles for ids NEAR the known
  engishiki blocks (or via the site's search), then match the 94 no-ID shikinaisha by name (+
  province from the parent ronsha), RAG for ambiguous. Polite throttle (~1s); unblocks the
  engishiki-reference generator for the ID-less unsourced rankings.
- [ ] **jawiki infobox imports — Emma's modeling calls only** (all mechanical builds SHIPPED
  2026-07-08: saijin 2,362 / honzon 760 / souken 4,118 / kofun 1,036 / P3225 2; 社格-ref
  structurally empty). Waiting on Emma: 伝-dates via P1480 "presumably" (8,837 skipped fields),
  神体 / 山号 / 寺格 / 被葬者 / 鎮守神 mappings, shinto-wiki-as-source for the ~106 unsourced
  modern ranks.

## From [[Open questions]] wiki-queue 2026-07-08 (afternoon)

- [ ] **Commons-category English labels** (Emma; cf. Q115566088): shrines/temples with a
  Wikimedia Commons category (P373/sitelink) but no English label — derive a standardized
  English label from the Commons category name. Size it, build the generator (non-destructive,
  uniqueness-checked like everything now).
- [ ] **Speculative report: extend Commons-label derivation to other religious buildings** —
  Mosques, Churches, Hindu Temples, non-Japanese Buddhist Temples, Synagogues, Gurdwaras.
  Report only, keep speculative; no edits.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
