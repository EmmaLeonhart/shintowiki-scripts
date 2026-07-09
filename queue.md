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

## From [[Open questions]] answers 2026-07-07 (wiki-queue items go at the END, per Emma's rule on that page)

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

- [ ] **(d) P361 part-of migration — DO NOT RUN. Emma 2026-07-09: "don't remove anything."**
  `generate_p361_shikinaisha_list_fix.py` → `_site/p361_shikinaisha_list_fix.txt`. Never in
  `ATOMIC_FILES`, never executed; no Wikidata edit has ever been made from it.
  **Scope bug found + fixed 2026-07-09** while working item (f): the first version treated every
  `P361` target as a Shikinaisha list. Of 249 targets only **47** were; the other 202 were shrines
  and classes (Kamigamo Shrine, Shirayama Hime, Beppyō Shrine, Twenty-Two Shrines, the Ninety-Nine
  Ōji Shrines). Its removal lines would have deleted **425 real statements**, including subshrines'
  membership of their parent shrines. Now filtered to `?list wdt:P361 wd:Q11064932` (Emma's own
  method); the batch falls to 495 removals / 36 adds. Three tests pin the scope.
  **But looking at Yamashiro shows removal is wrong anyway:** all 17 items it would strip there hold
  exactly ONE `P361` into Yamashiro with ONE ordinal (Kitano Tenmangū #31, Ujigami #57). They were
  only ever "duplicates" because the detection counted `P361` statements pointing at *other* targets.
  The real within-list duplicate set has not been measured. Nothing to remove until it is, and Emma
  has said remove nothing.
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

## LAST IN THE QUEUE — province exclusion (Emma 2026-07-09: postponed; "may very well be the most complicated task in the entirety of the queue by far")

**The model already exists on the lists. Both of my earlier write-ups were wrong.**
Emma: *"I didn't ask you to remove anything at all. I asked you to add the EXCLUDED property to the
list. This is an additive thing based off of a property that is on the Yamato and Yamashiro lists."*
And: *"here's how you find the lists — they are linked as a part of the Engishiki Jinmyōchō."*

Looked at `Q11467693` (Yamashiro) and `Q11433427` (Yamato) properly. What is actually there:

* `P3113` **does not have part** → the excluded shrine. **On the LIST**, not on the shrine.
  (I wrote "the excluded property goes on the SHRINES, not on the lists". That was wrong.)
* qualified by `P3831` **object of statement has role** → the reason class:
  `Q10898274` Beppyō Shrine, or `Q118469772` shikigesha (式外社 — Emma's "whatever that other thing").
* `P1001` **applies to jurisdiction** → the province. Yamashiro→`Q749276`, Yamato→`Q907495`.
  **All 69 Engishiki lists already carry `P1001`.** (I wrote "neither list links to its province".
  Also wrong — I checked P131/P276/P17 and never P1001.)

State: 69 lists (`?l wdt:P361 wd:Q11064932`). **50 already carry `P3113`; 287 statements total, but
only 22 carry the `P3831` role qualifier** — 265 are unqualified.

- [ ] ADD-ONLY. For each list, add `P3113` → shrine, `P3831` → reason class, for shrines in that
  province's jurisdiction that are Beppyō (`P13723 = Q10898274`, 240 non-Shikinaisha) / kokushi
  genzaisha (`P31 = Q118304363`, 157 non-Shikinaisha) / shikigesha, and are NOT Shikinaisha.
  **Remove nothing.**
- [ ] Open question: backfill the `P3831` role onto the 265 unqualified existing `P3113` statements?
- [ ] The remaining hard part is only the jurisdiction test — which province a modern shrine sits in.
  Emma: a coordinate/point-in-polygon problem, *"prohibitively hard"*. The LIST side needs no
  geometry: `P1001` is already there.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick, job 55ae0bbe — Emma
  replaced the earlier 3-cron setup when she extended the session 2026-07-08).
- [ ] Run the status-report action once more independently as an end-of-session summary.
