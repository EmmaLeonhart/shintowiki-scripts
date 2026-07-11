# shintowiki-scripts — Work Queue

Conventions live in `CLAUDE.md` (delete items when done — history in `DEVLOG.md`; terse items;
numbers = priority; bulk LLM-grunge lives in `remote_queue.json`, not here).

---

## 1. Category-orchestrator throughput (conditional, low priority)

- [ ] A full ns14 category cycle still takes ~many fires at ~1000 pages/145min. ONLY if the
  Japanese-category translation drain (cloud RAG → `category_moves.csv` → monthly `move_categories`)
  proves too slow: skip history_offload/fandom_mirror on the ~3k enwiki-junk cats, or shard ns14. No
  premature optimization. (Cleanup-loop reliability itself is DONE — run 28802688487 green end-to-end.)

## 2. Sequential-misc: populate the file (MECHANISM SHIPPED, empty no-op)

The sequential-misc mechanism Emma approved ("We're doing it") is built + tested in
`direct_daily_edits.py`: one line/day, strict top-to-bottom order, woven at a random
position, cursor advances only when a line reaches its end state (success, or an
already-gone removal) and HOLDS on any error — so a paired successor never runs before
its predecessor lands. `sequential_misc.txt` ships EMPTY (comments only); 14 tests +
80 existing pass. Next, deliberately (confirm the add-placement question with Emma):

- [ ] **Populate the ordered pairs** into `sequential_misc.txt`, each written first-to-
  land above its dependent. Real candidates (genuine add↔remove pairs): **Takano** — the
  merged P6375 add then its two partial removes (Emma pasted the 3 lines in order);
  **Awa entry-3** — add 天神社(Q137041912)@3 then delete the wrong 下立松原(Q11361262)@3;
  **province corrections** — Himure off Etchū, Shibi off Izumi (add-first/remove-later).
  Open design question for Emma: put the ADD in BOTH the atomic file and sequential
  (idempotent, but double-managed), or MOVE it into sequential only? The whole ordered
  unit must live in sequential for the guarantee to hold.
- [ ] NOT sequential: the 2,236 list-membership removals are **pure removals** (no
  re-add) → register script 2 to the atomic drip. The 22 duplicate `part of` are
  value-match-ambiguous → report only (Emma). Province exclusions are **add-only** (Emma
  was emphatic: nothing is ever removed from a province).

## SPARQL-heavy audits

These need a full SPARQL scan. `query.wikidata.org` is 429-outaged (2026-07-06+), but the SPLIT
endpoint **`query-main.wikidata.org/sparql` works** — use it (it serves everything except scholarly
articles). Heavy, so the 22:00 cron owns them; the hourly loop can also run them via query-main now.

- [ ] **Typo review — routed to cloud RAG 2026-07-06.** 161 kana-vs-label candidates are work-files in
  `label_typo_review/` (builder: `shinto_miraheze/build_label_typo_review_queue.py`), emitted by
  `remote_queue.py`; the cloud worker fills ANSWER (LABEL_TYPO/KANA_ISSUE/PREFIX_OK/OTHER).
  Collector BUILT (`shinto_miraheze/collect_label_typo_answers.py`, 5 tests; LABEL_TYPO →
  `label_typo_fixes.txt` in ATOMIC_FILES) — run it once answers land.
  2026-07-10 check: 157 pending, all `ANSWER` still empty — no cloud answers landed yet.
- **Comma-alias cleanup (189) — UNREGISTERED 2026-07-10, aliases left in place per Emma.** The
  file was registered ONLY with the fallback editor, which refuses alias removals outright
  (`"Term removal not supported"`), so all 189 lines silently failed and re-sampled every day
  while burning budget. `remove_junk_aliases.txt` deleted, registration removed. The junk aliases
  stay on Wikidata. (The earlier "draining" note was false — it never drained a single line.)

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

Reported, nothing to do (both tabulated in `docs/province_exclusion_residual_2026-07.md`): the
seven no-class exclusions are four different problems with no general criterion; the 河内 polygon
is wrong across southern Osaka (it swallows Sumiyoshi Taisha, *ichinomiya of Settsu*) and its 21
borderline assignments were emitted anyway on Emma's instruction.

## LAST — Kokugakuin P13677 matcher: Emma to explain, then decide

Moved to the tail 2026-07-09 at Emma's request: *"I do not understand what you are asking here …
put [it] at the end of the queue so that I can explain it later on … I don't even understand what
this actual thing even is."* Not parked — it gets done, once she has explained what she wants.

`modern-quickstatements/match_kokugakuin_ids.py` (strict exact-label match, district-blocked scan,
417-title index in `kokugakuin_title_index.json`) cut the no-ID set from 94 to 18. Zero safe
auto-adds: every name-matching entry id is already held, usually by several items. Review sheet:
`kokugakuin_id_report.txt`.

- [ ] Emma explains what this task is; then merge vs re-id gets decided.

## Engishiki list membership — the LIST is the source of truth (Emma 2026-07-10)

Emma: *"the actual wikidata items for the list of the shrines contain the entire list in them …
all of their lists are deduplicated. This happened due to earlier import issues and they were
fixed in the list items but not the shrines themselves."* The damage came from piped links in the
jawiki list, where a shrine that was part of another shrine got piped in.

**The algorithm.** An item the list NAMES as a part keeps exactly one clean "part of" statement —
ordinal and follows/followed-by derived from the list's own ordering, plus two references. An item
the list does NOT name loses its list link entirely.

* items named as parts (the entries) — **2,839**
* Shikinai Ronsha claiming membership — **2,277**; of those, actually named as a part — **126**
  (Emma: *"those 126 should be continued in the listing"*)
* Ronsha claiming membership but NOT named — **~2,151**, all junk

**Script 1 (adds) BUILT and registered:** `generate_list_membership_rebuild.py` →
`list_membership_rebuild.txt`, **5,643 lines**, ADD-only, diffed against live state so it shrinks
as it lands. 26 entries carry several Kokugakuin ids, so no database reference is claimed for them.

- [ ] **Script 2 BUILT** (`generate_list_membership_removals.py`, remove-only, 22 tests,
  **unregistered**): 2,236 lines over the 2,151 Ronsha no list names; 126 named parts untouched.
  Emma runs it by hand. Regenerating it against live state is idempotent. Its protection query
  counts an item as *named* whether or not the `has part` carries an ordinal — the 岩井温泉 hole.
- [ ] `report_ronsha_list_membership.py` and `docs/ronsha_list_membership_2026-07.md` hold the
  per-item detail.

**22 of the 126 named parts carry duplicate `part of` statements** (30 extra; `Q11631810` has 3).
QuickStatements cannot say "remove this statement, not its identical twin", so neither script can
clean them. Emma 2026-07-10: **report only, leave them.**

Three defects run down 2026-07-10 — `docs/engishiki_list_defects_2026-07.md`:

- [ ] **Awa `Q11450714` — one hand fix.** Delete `has part` → `Q11361262` with ordinal **3**.
  Entry 3 is 天神社; a piped link `[[下立松原神社#…|下立松原神社]]` was imported instead. The add of
  `Q137041912` 天神社 at ordinal 3 is queued in `miscellaneous_edits.txt`. QuickStatements cannot do
  the delete — two statements share the value `Q11361262`, so a value-matched removal could take the
  correct one at ordinal 5.

**Izumo — report only (Emma 2026-07-10).** `Q135040786` is doing duty for TWO register entries:
意宇郡 entry 28 is 同社坐韓国伊大弖神社 (in 揖夜神社's grounds) and entry 39 is 同社坐韓国伊**太**弖神社
(in 佐久多神社's). Its label is the 大 spelling; its own statement describes 39. Ordinal 39 is an
empty hole and ordinal 29 carries a spurious extra statement. Emma: leave it.
*Consequence:* `contested_entries()` withholds `Q135040787` 筑陽神社 — a correct entry — from script 1
for as long as ordinal 29 stays contested. It gets no ordinal, neighbours or references.

**The 17 palace deities — report only (Emma 2026-07-10).** Kokugakuin indexes 神産日神 … 足島神
individually (ids 180542–180558, a contiguous run) and an item exists for each, but the Imperial
Palace list names only four grouped items (八神殿, 座摩神, 御門巫祭神 八座, 生島巫祭神 二座). Both
models say true things; nothing is wrong today. `docs/engishiki_list_structure_2026-07.md`.
- **`Q11474068` 岩井温泉 — DONE, and the previous tick's recommendation was WRONG.** The onsen's
  classes are correct: the Inaba list's entry 6 is 二上山, a *mountain*, carrying the same
  `Shikinaisha` + `Shinto shrine` classes. Where the register's shrine is identified with a natural
  feature, the feature carries the classes. The real defect was that the **list's** `has part` →
  onsen lost its `series ordinal` — the only such statement in all 69 lists. Queued as an ADD:
  `Q11420254|P527|Q11474068|P1545|"7"`.
- Resolved, nothing to do: of the 13 named entries lacking a Kokugakuin id, **4 are palace kami**
  (八神殿, 座摩神, and two 座-count entries) which the shrine database cannot index; the other 9
  are ordinary entries whose id was never matched, and script 1 already handles that.

**The 150 confirmed Shikinaisha not named as parts: INVESTIGATED, both decisions deferred**
(`docs/orphan_shikinaisha_2026-07.md`, `report_orphan_shikinaisha.py`). 84 are modern shrine items
duplicating a 927 entry item the list already names (47 by shared Kokugakuin id, 29 by exact ja
label, 8 by normalised label). 66 have no twin. Emma 2026-07-10 answered **report only, decide
later** to both — what to do about the 84 duplicate pairs, and whether the 66 are mis-tagged
shrines or entries the lists are missing. Nothing is edited. Two loose threads recorded there:
13 named entries lack a Kokugakuin id, and `Q11474068` 岩井温泉 is a **hot spring** carrying the
confirmed Shikinaisha class.

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
- [ ] `Q134736575` — **third orphaning, found 2026-07-10.** 見光寺 in 飯能市 (Saitama), created by
  `Higa4` 2025-06, was overwritten as 見光寺 in 横浜市保土ケ谷区: coordinates, address, postcode and
  corporate number removed, jawiki `見光寺` sitelink attached. SPARQL confirms **nothing on Wikidata
  holds the Hannō 見光寺 any more**. Our `en`/`id` labels survive and are not contradictory (both
  temples read Kenkō-ji), so the item asserts one identity — the wrong one. Same hold.
- [ ] `Q140476265` — they created 琵琶島神社 and blanked it two minutes later. Now 0 labels,
  0 claims, 0 sitelinks. Junk item; nothing of ours in it.

## LAST — re-examine ブルーノ・プラス's contributions (Emma 2026-07-10)

- [ ] Look over the editor's contributions again. `archive_destroyed_items.py` runs in CI and
  captures any newly-damaged item automatically, but Emma wants a periodic human-directed pass:
  re-read `docs/bruno_plus_analysis_2026-07.md`, re-run the archiver and
  `watch_conflicting_editor.py`, and report what changed — new identity changes, whether they have
  been blocked, and whether any venue now mentions them.

## Pinned tail (keep last, always)

- [ ] Ensure the work-loop cron is running (single recurring :13/:43 tick — Emma replaced the
  earlier 3-cron setup 2026-07-08; job ids are session-local and change each session, current
  session's is 20cd74bb). SYNC step fast-forwards the branch onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
