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

- [ ] **Kokugakuin ranking anomalies — PARKED per Emma 2026-07-08.** The multiple-P13677 set:
  Emma ruled ALL ~66 ambiguous; the name-match elimination algorithm was WRONG (item names don't
  reliably match entry titles — two-run overlaps mean both adjacent IDs can describe the same
  shrine; deciding which entry is right needs the Kokugakuin page itself, per item). No mechanical
  rule exists. Sequence-gap anomalies: same — history + Kokugakuin-page ordering per item (the
  Q135040778 investigation is the worked example: triplicate import, rank-2 merged into an empty
  husk Q135193070). Nothing here is batch-fixable — but the investigation is now TOOLED:
  browse-render the Kokugakuin entry page and read its 現社名など（１..N） ordering, which per
  Emma IS the ranking ground truth (method + Q135040778 worked example in
  `docs/kokugakuin_anomaly_review_scope_2026-07.md`). Emma-led, tool-assisted.
- [ ] **Kokugakuin P13677 matcher — BUILT + RAN 2026-07-08, finding needs Emma**:
  `modern-quickstatements/match_kokugakuin_ids.py` (strict exact-label match, district-blocked
  scan, 417-title index cached in `kokugakuin_title_index.json`). The no-ID set is down to 18
  (was 94). ZERO safe auto-adds: every name-matching entry id is ALREADY HELD, usually by several
  items (candidates carry their entry's id) — the 18 look like surplus/duplicate items from the
  two-run desync, i.e. merge decisions, not missing ids. Per-item review sheet:
  `kokugakuin_id_report.txt` (ENTRY-TAKEN rows list current holders). Emma's call: merge vs re-id.
- [ ] **jawiki infobox imports — Emma's modeling calls only** (all mechanical builds SHIPPED
  2026-07-08: saijin 2,362 / honzon 760 / souken 4,118 / kofun 1,036 / P3225 2; 社格-ref
  structurally empty). Waiting on Emma: 伝-dates via P1480 "presumably" (8,837 skipped fields),
  神体 / 山号 / 寺格 / 被葬者 / 鎮守神 mappings, shinto-wiki-as-source for the ~106 unsourced
  modern ranks.

## From [[Open questions]] wiki-queue 2026-07-09 — "Anomaly corrections" (Emma)

Target page: `shrine-ranking.html` § "Duplicate Properties on Shikinai Ronsha".
Live counts 2026-07-09 16:30 UTC: P361 **384**, P1448 **104**, P6375 **250**.

- [ ] **(a) shrine-ranking.html "not updating"** — DIAGNOSED: the page *is* rebuilt daily
  (origin `f96cd758`, "Last updated 2026-07-09 06:39 UTC"), the counts just barely move because
  nothing drains them. What made it *look* frozen: the Takagi Shrine (Q59282644) "example of all
  three issues" line is **hardcoded** in `generate_duplicates_section()` and Q59282644 now has 1×
  each. Fix: derive the example from the query (or drop it), and surface the build time next to
  each count so a stale render is obvious.
- [ ] **(b) P1448 official-name table** (104 items) — replace the bare `<li>QID (n statements)`
  list with a real table: ja label | each official name (+ its `P1264` period / `P1814` kana /
  its references) | every `P13677` Kokugakuin entry on the item as a clickable link
  (`https://jmapps.ne.jp/kokugakuin/det.html?data_id=$1`). Emma: "Every single one of them is
  probably going to be manually fixable for me if I just have that information."
- [ ] **(c) P6375 street-address table** (250 items) — show every address with **all** its
  citations rendered as footnotes / an expanding block. Emma's predictor: "if any one of them has
  a citation, that's a really good sign" — so sort/flag cited-vs-uncited. Needs the more
  sophisticated view *before* she can decide.
- [ ] **(d) P361 part-of migration** (384 items) — on the actual shrine item, remove **every**
  P361→Shikinaisha-list statement; add ONE derived from the list-entry item, taking `P1545`
  ordinal + `P155`/`P156` from the entry item's own (already-clean) statement. Two references:
  `P248=Q135159299` + `P13677=<entry id>` (the form every coordinate already uses), and the
  jawiki Shikinaisha-list article (`P4656=https://ja.wikipedia.org/wiki/<list>`).
  **Add-first / remove-later as two separate scripts** (CLAUDE.md). BLOCKER to resolve first:
  when a Ronsha item carries several `P13677` entry ids (e.g. Q11677110 holds 182062/182063/182065),
  which entry's ordinal becomes the single new statement? Build the report, then ask.
- [ ] (e) Street-address citation convention (Emma): for Shikinaisha lists, cite the jawiki
  Shikinaisha-list article. No immediate citation otherwise; official names mostly already cited.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick, job 55ae0bbe — Emma
  replaced the earlier 3-cron setup when she extended the session 2026-07-08).
- [ ] Run the status-report action once more independently as an end-of-session summary.
