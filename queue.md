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

- [ ] **(d) P361 part-of migration — batch BUILT, needs Emma's word before it runs.**
  `modern-quickstatements/generate_p361_shikinaisha_list_fix.py` →
  `modern-quickstatements/_site/p361_shikinaisha_list_fix.txt`. Browser batch only (remove+add is
  not drip-safe); deliberately not in `ATOMIC_FILES`. **841 removals, 36 adds.** The list's true
  membership is reconstructed from the neighbour witnesses (a clean statement at ordinal N asserts
  N-1 = its P155, N+1 = its P156) — unanimous on every list. THE DECISION: on this reading a pure
  P460 candidate keeps **no** P361 at all (691 of 726 item/list pairs), because list membership
  belongs to the entry item. The other reading of "add in a new one derived from the list item" —
  every candidate keeps ONE statement mirroring its entry — gives **301 adds** instead of 36.
  20× swing, destructive either way. Also unresolved: QuickStatements' `-` on several identical
  values is undocumented (removes one, or all?); the batch emits one `-` per existing statement so
  it is correct under either, at the cost of some "not found" lines if `-` already removes all.
- [ ] (e) Street-address citation convention (Emma): for Shikinaisha lists, cite the jawiki
  Shikinaisha-list article. No immediate citation otherwise; official names mostly already cited.
- [ ] (f) 3 items skipped by the P361 generator on a contested ordinal (Q135288221 in Q11642130;
  Q335618 and Q705035 in Q3200280) — two clean statements disagree about who occupies a position.
  Per-item review.

## From [[Open questions]] wiki-queue 2026-07-09 (second batch)

- [ ] **Two autogenerated pages concatenated — need a human merge.** Surfaced by
  `finish_japanese_content_merge.py`, whose lead merge refused them (two stub leads):
  `Mifune Shrine (Taki)` is the same article twice; `Oyama Otsu Shrine` is Oyama Otsu Shrine and
  Ozu Shrine in one page.
- [ ] **151 pages have no imported lead** in the `'''Name''' (kana) is …` form — they open straight
  into `{{Shinto shrine}}` or a maintenance template, so their autogenerated stub lead was left in
  place (blanking it with nothing to merge into would destroy the lead). Whether those want a
  hand-written lead is Emma's call.
- [ ] **Reisai days beyond jawiki** — per
  <https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Shinto#Day_of_Reisai>, many reisai dates
  are well documented in databases. Agentic RAG to find sources. NB the `Day of Reisai` property
  proposal was **declined** (2025-12-07, no support), so the model stays P837 + P3831=Q11385469 per
  `docs/wikidata_shrine_festival_model.md` — do not resurrect a bespoke property.

## LAST IN THE QUEUE — province exclusion (Emma 2026-07-09: postponed; "may very well be the most complicated task in the entirety of the queue by far")

- [ ] **The "excluded" property goes on the SHRINES, not on the lists.** Emma: *"Shikinaisha lists
  should not exclude it. They should not exclude the Beppyo shrines. Rather, Beppyo shrines that are
  not Shikinaisha but are within the province's jurisdiction should have the excluded property on
  them."* Reason for Beppyo: "it didn't exist yet".
- [ ] **"Within the province's jurisdiction" = a geographic coordinate query.** Emma: *"a geographic
  coordinates-based querying system, which I'm pretty sure can exist using STL files, but it's hard.
  I think it's prohibitively hard, to the point of putting it at the end of the queue."*
  Point-in-polygon of `P625` against historical province boundaries.
- [ ] Which Wikidata property expresses "excluded from this list" is **still unanswered** - do not
  guess. Nothing in the data uses one: zero shrines carry `P1011`; the lists' `P361` statements carry
  only `P155`/`P156`/`P1545`. Candidates: deprecated-rank `P361` + `P2241` (shrine-side, Wikidata's
  canonical "this claim is false"); `P1011` excluding; `P3113` does not have part (both list-side,
  contradicting "on them").

**Investigated 2026-07-09 (Yamashiro Q11467693 / Yamato Q11433427) - facts for whoever picks this up:**
* Beppyo is **not** a `P31` class - it is a shrine *ranking*: `P13723 = Q10898274`. 350 items;
  **240 not Shikinaisha**, 236 of those with coordinates. (`P31 = Q10898274` has zero instances.)
* Kokushi genzaisha **is** a `P31` class (`Q118304363`): 159 items, 157 not Shikinaisha.
* The lists already contain non-Shikinaisha members. Yamashiro: 146 members, only 88 Shikinaisha
  (plus 56 Ronsha, a kokushi genzaisha, a Buddhist temple). Yamato: 300 members, 212 Shikinaisha.
  42 non-Shikinaisha Beppyo shrines already carry `P361` into a Shikinaisha list.
* **Neither list links to its province.** Their only statement is `P361 -> Q11064932` (Engishiki
  Jinmyocho) - no `P131`, no `P276`. So "within the province's jurisdiction" is unrepresentable
  today. The ~60 `<province>の式内社一覧` items could be linked to their province from their own
  Japanese label with no coordinates at all, which would unblock the rest.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick, job 55ae0bbe — Emma
  replaced the earlier 3-cron setup when she extended the session 2026-07-08).
- [ ] Run the status-report action once more independently as an end-of-session summary.
