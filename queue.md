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
## From [[Open questions]] wiki-queue 2026-07-09 (second batch)

- [ ] **Reisai: WAIT FOR THE GATE, then reassess** (Emma 2026-07-10, after seeing the numbers).
  Evidence: `docs/reisai_prefectural_feasibility_2026-07.md`. The jawiki harvest is done —
  `reisai.txt` holds **3,239 pending `P837` lines**, which will take live coverage from 197 to
  ~3,400. Only **2 of 47** prefectures (Mie, Kumamoto) are on the shared `jinja-net.jp` platform;
  Tokyo/Kanagawa/Fukuoka's own domains do not resolve. Mie is the best case and yields ~22%
  parseable 例祭 dates over ~280 address-bearing items ≈ **60 statements**, needing a bespoke
  scraper plus a name+address matcher (141 of Mie's 593 shrine labels are shared, so a name alone
  cannot identify a shrine). Build nothing until the 3,239 have landed and the real gap is
  measurable. The parser (`modern-quickstatements/jinjacho_reisai.py`, 22 tests) is already built.
  NB the `Day of Reisai` property proposal was **declined** (2025-12-07); the model stays
  `P837` + `P3831`=`Q11385469` per `docs/wikidata_shrine_festival_model.md`.

## LAST — hard-residual street addresses: cross-product run; the glitch is NOT the general case

`modern-quickstatements/resolve_ronsha_addresses.py` (REPORT ONLY) now matches **every address
against every coordinate** on the Kokugakuin entry, as Emma asked. Report:
`docs/ronsha_address_resolution_2026-07.md`.

**Emma's hypothesis was that the entry's coordinates come from an adjacent, non-candidate shrine,
so nothing would match. The data says otherwise.** Municipality matching found **zero** no-match
items. Geocoding each address (国土地理院 address search) and measuring to the nearest coordinate:
median **0.65 km**, minimum **5 m**, and 27 of 65 addresses within 500 m. Only **2 items**
(`Q107410067`, `Q43594855`) have every address more than 2 km from every coordinate.

Of 33 items with exactly one Kokugakuin id: **10 resolved · 22 several · 1 error · 0 no-match.**

**What the 22 actually are:** in **16** of them the item's two addresses match *two different*
coordinates on the *same* entry — the item carries the addresses of two different candidate
shrines the entry lists. A Ronsha is one shrine with one address (Emma 2026-07-09), so these are
**conflations**, not coordinate glitches. The other 6 have both addresses in one municipality
(Hibita's 三ノ宮1472 vs 1468), which coordinates cannot separate.

- [ ] Emma: the 10 **resolved** rows are safe to act on — one address sits at a coordinate, the
  other does not. A script-2 (remove-only, SPARQL-gated) can drop the losers once she says so.
- [ ] The 16 **conflations** are the real residual: each needs deciding *which candidate this item
  is*, which the entry cannot answer. Emma's call.
- [ ] `Q107410067` and `Q43594855` are the only two that look like the glitch she described.

## LAST IN THE QUEUE — province exclusion (STOP GATE PASSED; batch BUILT + WIRED TO THE DRIP)

The gate was run. Emma answered seven `AskUserQuestion` blocks; the shapefile step is solved and
scripts 1 + 2 are built and tested (30 tests). What remains is Emma running the batch.

**Shipped:** `docs/province_shapefiles.md` (CODH 旧国・旧郡境界データセット, CC BY-NC, cached in
gitignored `.province_cache/`, geometry never committed and never uploaded);
`modern-quickstatements/province_geometry.py` (85 features → 68 classical provinces: the 1869
Mutsu/Dewa splits unioned back, Hokkaidō + Ryūkyū dropped, 對馬 aliased);
`generate_province_exclusions.py` (**ADD-only**, 382 QS lines: 113 new `P3113` exclusions +
258 `P3831` role backfills); `generate_province_exclusion_removals.py` (**script 2**, SPARQL-gated,
emits nothing until the matching add lands); `docs/province_exclusion_residual_2026-07.md`.

**Model, per Emma:** `LIST|P3113|shrine|P3831|<every class it holds>|P1013|<criterion>`, where the
criterion is `Q3877969` non-existence for Beppyō-only shrines and `Q110240047` omission for anything
shikigesha/kokushi-genzaisha (both of which *existed* in 927 by Wikidata's own definitions).

**Emma 2026-07-10: not a browser batch any more.** *"I was going to run the Shikinaisha lists right
now, but … wire them into the atomic statements thing so that they gradually get done over time …
This editor trumps making slight modelling improvements."* `province_exclusions.txt` (382 lines,
ADD-only, 0 removals, every line parses with two qualifiers) is registered in `ATOMIC_FILES` and
drips behind `conflict_gate` like everything else.

- [ ] **Script 2 stays UNREGISTERED and manual.** `generate_province_exclusion_removals.py` is
  add-first/remove-later: it emits nothing until SPARQL confirms the adds landed. Run it by hand
  once the drip has worked through the two corrections (Himure Hachimangū off Etchū, Shibi Shrine
  off Izumi) — never register a removal batch that depends on ordering.
- [ ] The seven no-class exclusions need **no general criterion** — they are four different
  problems (three are themselves `P31=Shikinaisha`; one is a multi-topic Wikimedia article; one is
  on the wrong province entirely). Per-item decisions are tabulated in the residual doc.
- [ ] The 河内 polygon is provably wrong across southern Osaka (it swallows Sumiyoshi Taisha, the
  *ichinomiya of Settsu*). 21 borderline assignments were emitted anyway on Emma's instruction and
  are listed in the residual doc so they can be found again.

## LAST — Kokugakuin P13677 matcher: Emma to explain, then decide

Moved to the tail 2026-07-09 at Emma's request: *"I do not understand what you are asking here …
put [it] at the end of the queue so that I can explain it later on … I don't even understand what
this actual thing even is."* Not parked — it gets done, once she has explained what she wants.

`modern-quickstatements/match_kokugakuin_ids.py` (strict exact-label match, district-blocked scan,
417-title index in `kokugakuin_title_index.json`) cut the no-ID set from 94 to 18. Zero safe
auto-adds: every name-matching entry id is already held, usually by several items. Review sheet:
`kokugakuin_id_report.txt`.

- [ ] Emma explains what this task is; then merge vs re-id gets decided.

## Shikinai Ronsha list-membership migration — Emma's wiki-queue item (d), restored

I deleted this item's real content and replaced it with a "duplicate links" framing that was not
what Emma asked for. Her original text, restored:

> **(d) part-of migration** — on the actual shrine item, remove **every** part-of→Shikinaisha-list
> statement; add ONE derived from the **list-entry item**, taking the ordinal + follows/followed-by
> from the entry item's own (already-clean) statement. Two references: "stated in" the Kokugakuin
> database + the entry id, and the jawiki Shikinaisha-list article. **Add-first / remove-later as
> two separate scripts.** BLOCKER to resolve first: when a Ronsha item carries several Kokugakuin
> entry ids (e.g. Q11677110 holds 182062/182063/182065), which entry's ordinal becomes the single
> new statement? Build the report, then ask.

Report BUILT: `docs/ronsha_list_membership_2026-07.md`
(`modern-quickstatements/report_ronsha_list_membership.py`, report-only).

Structure verified: `Futarasan Shrine` (the modern shrine) carries four part-of statements, two
into the Shimotsuke list — one with ordinal 4 and neighbours, one bare. `Futaarayama Shrine`, its
entry item, carries exactly one: ordinal 4, with follows/followed-by, and the Kokugakuin id. The
shrine reaches its entry item through "said to be the same as".

Of **2,277** Ronsha with a list membership:

| | |
|---|---:|
| unambiguous — one entry item, one clean statement | **1,950** |
| **ambiguous** — several entry items or several ordinals (the blocker) | **74** |
| no entry item reachable | **253** |

- [ ] **Emma: the blocker.** Which entry's ordinal wins for the 74? Listed in the report with each
  shrine's Kokugakuin ids and every candidate entry's ordinal.
- [ ] Then: script 1 ADDS the single derived statement for the 1,950; script 2 REMOVES the old ones
  only where SPARQL confirms the add landed. Two scripts, never one.
- [ ] The 253 with no reachable entry item need a different route.
- [ ] Items (a) shrine-ranking example, (b) official-name table, (c) address table and (e) address
  citation convention from the same wiki-queue bullet all SHIPPED 2026-07-09.

## LAST — repurposed-item damage, on hold (Emma 2026-07-10)

See `docs/bruno_plus_analysis_2026-07.md`. Emma: *document, don't touch*; *no contact*.
The Kikuna restoration is DONE as a queued batch (`miscellaneous_edits.txt`) — it targets our own
`Q134926804`, not the husk, so it cannot read as a reversion.

- [ ] `Q123044569` — Kamo Shrine (Odawara) was overwritten as 大美和神社. **No item holds Kamo
  Shrine any more.** It still carries Kamo's `de`/`id`/`fr` labels (two of them ours), so it
  asserts two identities at once. Emma: leave them, record only. A replacement item is on hold
  until we understand what is going on with this person.
- [ ] `Q134886554` — Chikadono Shrine (**Saitama**, 熊谷市下増田749) was overwritten as 近殿神社
  (**Kanagawa**, Yokosuka) on 2026-07-10 02:18 UTC. Its corporate number, postcode, address,
  coordinates and our `P1814` kana are gone from Wikidata entirely; no item holds that shrine.
  Still carries our `id`/`fr` Chikadono labels. Same hold.
- [ ] `Q140476265` — they created 琵琶島神社 and blanked it two minutes later. Now 0 labels,
  0 claims, 0 sitelinks. Junk item; nothing of ours in it.

## LAST — re-examine ブルーノ・プラス's contributions (Emma 2026-07-10)

- [ ] Look over the editor's contributions again. `archive_destroyed_items.py` runs in CI and
  captures any newly-damaged item automatically, but Emma wants a periodic human-directed pass:
  re-read `docs/bruno_plus_analysis_2026-07.md`, re-run the archiver and
  `watch_conflicting_editor.py`, and report what changed — new identity changes, whether they have
  been blocked, and whether any venue now mentions them.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick, job 892a7dc2 — Emma
  replaced the earlier 3-cron setup when she extended the session 2026-07-08).
- [ ] Run the status-report action once more independently as an end-of-session summary.
