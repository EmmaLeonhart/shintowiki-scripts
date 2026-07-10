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

## LAST — hard-residual street addresses, via the Kokugakuin website links (Emma 2026-07-09)

**Ontology, corrected by Emma:** *"you're getting ronsha ontology wrong — a ronsha is specifically
always only one address."* A Shikinai Ronsha item is ONE candidate shrine, so it has exactly ONE
address. Several addresses on one Ronsha is simply an error, never a legitimate list of candidates'
addresses. (My earlier write-up claimed the entry item had absorbed its candidates' addresses. That
was wrong and is not a model to reason from.)

**Method, per Emma:** read the Kokugakuin website links on each item to figure out which address is
right. Not a mechanical rule.

State as of 2026-07-09 (`generate_uncited_address_removals.py` now emits 0 lines — the
cited-vs-uncited signal is exhausted). Of 46 Ronsha items still holding more than one Japanese
`P6375` (Emma removed one prefix case by hand):

* **~44 carry no reference at all** on any address. 3 were coarser-prefix duplicates of each other
  (Emma removed one); the rest name genuinely different places.
* **`Q11547364` Hibita Shrine** — a real source conflict: the shrine's own site (hibita.jp) gives
  `神奈川県伊勢原市三ノ宮1472`; *Kanagawa Prefecture Shrine Records* (Q137052933) p. 352 gives `…1468`.
* **`Q3530344` Toga Shrine** — both addresses carry only `P143` (imported from jawiki), which is not
  a source. They are its 里宮 and 奥宮.

- [ ] Per item, open the Kokugakuin entry page (`P13677` → `https://jmapps.ne.jp/kokugakuin/det.html?data_id=$1`)
  and read the address off it. Report before editing; do not guess a rule and drip it.

## LAST IN THE QUEUE — province exclusion

> ### !!! STOP GATE !!!
> **Run an `AskUserQuestion` with Emma BEFORE attempting any part of this task.**
> Emma 2026-07-09: *"the entire point of asking these questions is it's supposed to stop everything
> so that you don't do anything destructive."* She asked for this gate twice. An agent walked past
> it once already, drifted here from an unrelated queue item, and started building a removal batch.
> **This task ADDS statements. It removes nothing, ever.**

**Emma's statement of the task, verbatim (2026-07-09):**

> *"I'm not trying to get you to remove anything. I'm trying to get you to add links to the Beppyō
> Shrines and Kokushi Genzaisha, and Shikigeisha that are located within the province. … the idea
> here is essentially that the excluded thing lists the shrines that would be in that list because
> they're a Beppyō shrine or whatever, except they didn't exist back then or whatever. … it involves
> shape files of the provinces and all these things. You need a state file of the province, and then
> you need to cross-reference the coordinates of all members of these classes with the state file in
> order to find which ones are within the future jurisdiction of the province."*

> *"This is such a hard task that I don't realistically feel we could do it today, just to be clear."*
> *"I put it at the end of the queue"* — and it stays there.

### The data model — VERIFIED on Yamashiro (Q11467693) and Yamato (Q11433427), 2026-07-09

Everything already exists. Nothing here needs inventing.

```
LIST item (e.g. Q11467693 "List of Shikinaisha in Yamashiro Province")
  P361  part of              -> Q11064932  Engishiki Jinmyōchō     <-- THIS is how you find the lists
  P1001 applies to jurisdiction -> Q749276 Yamashiro Province      <-- the province link
  P3113 does not have part   -> <excluded shrine>                  <-- THE STATEMENT TO ADD
          P3831 object of statement has role -> Q10898274 Beppyō Shrine
                                             or Q118469772 shikigesha (式外社)
```

* **`P3113` sits on the LIST, not on the shrine.** (Two earlier write-ups had this backwards.)
* **`P3831`** carries the *reason* the shrine is excluded — its class.
* **`P1001`** gives the province. **All 69 lists already have it.** (An earlier note claimed "neither
  list links to its province" — that was wrong; only P131/P276/P17 had been checked.)

### Current state (queried 2026-07-09)

| | |
|---|---|
| Engishiki Jinmyōchō lists (`?l wdt:P361 wd:Q11064932`) | **69** |
| …carrying `P1001` (province) | **69 (all)** |
| …carrying at least one `P3113` | **50** |
| Total `P3113` statements on those lists | **287** |
| …of which carry the `P3831` role qualifier | **only 22** (15 Beppyō, 7 shikigesha) |

### The candidate pool to classify (non-Shikinaisha, with `P625` coordinates)

| Class | QID | How it is typed | Count |
|---|---|---|---|
| Beppyō Shrine | `Q10898274` | **`P13723`** (a *ranking*), NOT `P31` | **236** |
| Kokushi genzaisha | `Q118304363` | `P31` | **62** |
| Shikigesha (式外社) | `Q118469772` | `P31` | **9** |

Note the trap: `P31 = Q10898274` has **zero** instances. Beppyō is a shrine *ranking* (`P13723`).

### THE HARD PART — and it is genuinely hard

"Within the province's jurisdiction" is a **point-in-polygon test** against **historical province
(令制国 / kuni) boundaries**, which do not correspond to modern prefectures.

* **All 69 provinces have `P625` — a single centroid POINT.**
* **ZERO of them have `P3896` (geoshape).** There is no polygon on Wikidata to test against.

So the work is, in order:

1. Obtain historical province boundary polygons (shapefile / GeoJSON). See
   [`docs/province_shapefiles.md`](docs/province_shapefiles.md).
2. Map each polygon to its Wikidata province QID (the 69 `P1001` targets).
3. For each of the ~307 candidate shrines, point-in-polygon its `P625` into a province.
4. Emit **ADD-only** QuickStatements: `<list>|P3113|<shrine>|P3831|<class QID>`.
5. Separately consider backfilling `P3831` onto the **265 unqualified** existing `P3113` statements.

### Rules

- [ ] **ADD ONLY.** No `-` lines. Ever. Emma has said "don't remove anything" three times.
- [ ] Run the `AskUserQuestion` STOP GATE first.
- [ ] Do not start this because other items look blocked. It is last on purpose.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick, job 55ae0bbe — Emma
  replaced the earlier 3-cron setup when she extended the session 2026-07-08).
- [ ] Run the status-report action once more independently as an end-of-session summary.
