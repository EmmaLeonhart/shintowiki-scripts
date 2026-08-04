# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

## 🚦 Wiki-editing gate — WORK-LOOP READS THIS FIRST
<!-- WIKI_GATE: WAIT -->
**Status: ⏸ WAITING** (weekly edit-test failed, 2026-07-26 10:56 UTC) — wiki editing is locked.
The Sunday `weekly-wiki-edit-test.yml` job re-tests a real edit and flips this to **`WIKI_GATE: GO`** when it lands.

> ⛔ **FULL BLACKOUT until 2026-08-09** (Emma 2026-07-27). Not just "no writes": **no requests to
> shinto.miraheze.org of any kind, reads included.** The 403 has been up since 2026-07-11 and never
> lifted; Emma's read is that our continuing to read through the challenge is what kept us looking
> persistent, so it was never relaxed. Every Miraheze-touching workflow is now gated on
> `wiki_editing_lockout.state`, and `weekly_wiki_edit_test.py` holds its probe until `blackout_until`
> passes — so the first test after the blackout, Sunday 2026-08-09, lands on ~13 days of true silence.

**THE QUEUE IS SPLIT IN TWO (Emma 2026-07-27).** Read this before picking work:

- **§A — NOT gated on shintowiki.** Wikidata, external DBs, repo/CI work. **Runnable right now,
  today, regardless of the 403.** The work-loop starts here, every tick, always.
- **§B — GATED on shintowiki access.** Nothing in §B can start until the marker says **GO**.
  Do not fire §B decisions, do not "prepare" §B work, do not touch the wiki to check something.

**Work-loop, every tick:** SYNC (pull remote) first, then read the marker.
- Marker **WAIT** → work §A only. §B does not exist for you.
- Marker **GO** → §A still comes first; then §B unlocks and the decisions fire one at a time.

**Item tags.** ❓ ASK = needs Emma's decision, the exact AskUserQuestion is written under the item;
fire it, don't skip it. ▶ DO = just execute. 🤖 AUTO = runs itself. ⏸ PARKED = waiting on a named
external thing.

---

# ═══════ §A — NOT GATED ON SHINTOWIKI · RUN THESE NOW ═══════

## A00. ▶ The 11 unresolved lineage cases are ANSWERED on the shintowiki 分霊 page

Emma 2026-08-04: **the 11 are solved on the shintowiki page on bunrei.** Read that page and apply
its answers — do not re-derive them, and do not guess a target for any of them.

⛔ **Gated on the blackout, which is the only reason this is not done yet.** No requests to
shinto.miraheze.org of any kind until **2026-08-09** (see the gate at the top). First thing after
it lifts: pull the 分霊 page, then fix the 11.

The 11 (from `lineage/manual_fixes.tsv`; Google Sheet "11 judgement calls"):
- **5 targets the article names but that would not resolve** — 佐嘉神社←松原神社 (dab),
  忌部神社←五所神社 (dab), 瀧原宮←磯宮 (no article), 坐摩神社←宮中（神祇官西院）の坐摩神,
  劔神社←伊部郷座ヶ岳の素盞嗚尊神霊.
- **6 with no origin in the article** — 小俣神社 (since resolved: ←豊受大神宮), 度津神社, 月讀宮,
  石園座多久虫玉神社, 風宮, 風日祈宮. The other five are staged as `P612 = Q24238356` (unknown,
  cited to the jawiki article) per Emma 2026-08-04 — **if the 分霊 page gives a real answer it
  supersedes that**, via `python lineage/build_p612_quickstatements.py --supersede`.

Everything else is done: 419 statements staged in `modern-quickstatements/beppyo_p612.txt`, and the
21 shrines with no Wikidata item are Emma's by hand (Google Doc "21 Ise shrines that need a
Wikidata item"). Method: `docs/lineage_full_read_method.md`.

## A0. 🖥️ name-in-kana → label pipeline — BUILT 2026-08-03; bucket (b) DONE, bucket (a) draining

**Status.** Builder `shinto_miraheze/build_name_in_kana_queue.py` + collector
`collect_name_in_kana.py`, on the same work-file/ANSWER-marker pattern as the other cloud queues;
`name_in_kana.txt` registered in `direct_daily_edits.ATOMIC_FILES`; the queue is registered in
`remote_queue.py` so the routine fills answers unattended.
- ✅ **Bucket (b) is FINISHED** — all 54 done locally: 50 P1814 lines + 43 en labels (via
  `kana_english.label_for`). 4 produced no statement: 3 legitimately mixed-script readings and 1
  two-shrine disambiguation page.
- ⏳ **Bucket (a): 2,582 targets; 197 done locally 2026-08-04**, 34 work-files left in this tranche.
- ⚠️ **The builders re-queued finished work, and both are fixed.** Skipping only on work-file
  existence is wrong: the collector DELETES the file when it answers, and the SPARQL/category target
  set cannot see the staged line either, because the freeze holds delivery until 2026-08-10. So a
  rebuild re-created 12 name-in-kana files (and, earlier, 14 Beppyo ones) for work already done —
  answering them would have written a second identical statement each. Both builders now consult the
  staged `.txt` + `_resolved.log` via `already_handled()`. **Until the freeze lifts, local staging is
  the only record of what has been done; do not trust the target query to know.**
  **The cloud routine is one path, not the only one** — these can be extracted locally in batches
  exactly like bucket (b), and waiting on the routine is not a blocker. It addresses only a handful
  of items per run across all 2,252 queue entries, so local batches are the faster road. Rebuild more
  work-files with `--limit N` once the current 177 are drained.
- ✅ **The Engishiki collision does not exist** (checked in the cleanup's own code, not assumed):
  `generate_kana_qualifier_add.py` guards both branches with `is_katakana()`, `_remove.py` emits
  value-matched removals, and this builder only queues items that already have no top-level P1814.
  The 601 are queued normally; `--hold-engishiki` restores the old blanket hold.
- ⛔ **4 ブルーノ・プラス husks are hard-excluded** (`REPURPOSED` in the builder): Q123044569,
  Q134886554, Q134736575, Q140476265. They reach the target set legitimately — the repurposing
  stripped their P1814 — and writing to one would be editing the husk. A5 says document, don't touch.
- ❗ **Known gate limitation, not yet decided:** the hiragana-only gate also rejects *legitimately*
  mixed-script readings. Now **7 known**: ハワイいしづちじんじゃ, ハワイだいじんぐう, スワトウじんじゃ,
  ペリリューじんじゃ (Peleliu), サムハラじんじゃ, アラハバキかみ, and counting — the colonial-era and
  overseas shrines make this a recurring class, not a handful of oddities. These are logged as KATAKANA and produce nothing. Emma's call whether to
  allow katakana that is a loanword/place-name rather than an ancient reading.

**Original brief follows.**

**What it is.** Give shrines a correct *modern hiragana* P1814 (name in kana), extracted by Opus from the
jawiki lead, as a new stage of the **label** pipeline. Name-in-kana is in almost every jawiki article but
is NOT reliably regex-extractable (furigana / bold-reading parsing is fragile) — that fragility is exactly
why the LLM step earns its place. This feeds romaji/label generation and may overwrite the Indonesian-seed
labels and some queued labels → that's why it's front of queue. Not gated on Miraheze (jawiki reads +
Wikidata + local pipeline), so the 403 blackout doesn't touch it; it needs a **desktop** for the
all-article download + local pipeline run.

**⚠️ Do NOT confuse with the kana-*qualifier* cleanup.** `generate_kana_qualifier_add.py` / `_remove.py`
is Engishiki-only, undoing the ~1yr-old error where ancient-Japanese *katakana* readings (from the
Engishiki-chapter tables Emma put on jawiki) landed in top-level P1814 — wrong; P1814 wants modern
*hiragana*. That cleanup relocates the old reading onto the ojp-hani P1448 as a カミノヤシロ qualifier and
strips it from top-level, leaving those Engishiki items with NO modern P1814.
**Collision risk on the shared Engishiki items:** the new writer and the cleanup both touch P1814. Use
add-first / remove-later (two scripts; the remove only fires after a fresh SPARQL confirms the add landed —
CLAUDE.md rule), and gate the new writer so it never re-introduces what the cleanup is stripping. Get
Emma's eyes on this ordering before running the Engishiki subset.

**Target set (SPARQL).** Shinto shrines (`?item wdt:P31 wd:Q845945`) with a jawiki sitelink and NO
top-level P1814. Reuse the `all_shrines()` SPARQL shape in
`modern-quickstatements/generate_bunrei_quickstatements.py` (query-main endpoint, UA-compliant). Two
buckets:
- **(a) HAS en label** — most likely to carry romanization-derived errors (includes already-queued
  labels). Highest priority.
- **(b) NO en label but scheduled** — download the article, extract kana, and locally generate BOTH the
  P1814 and the new en label; enqueue both.

**Local pipeline (desktop):**
1. Download the jawiki **lead** for each target (lead is enough — the reading sits in the first sentence).
2. Opus extracts the kana reading.
3. **THE gate: exclude any katakana candidate** — P1814 wants modern hiragana; katakana signals the
   ancient-reading error. Otherwise do NOT over-gate on confidence (Emma): the LLM path is high-quality and
   *producing* kana is the priority. (If quality holds, the katakana exclusion may be all the gating we need.)
4. For bucket (b), also generate the en label — reuse `shinto-label-generator/` (`language_registry.py`,
   `generate_multilang_quickstatements.py`; `modern-quickstatements/kana_english.py` for kana→romaji) and
   drip via `select_label_proposals.py`.
5. Enqueue: P1814 line(s) into an atomic `.txt`; new en labels into the label-proposal drip.

**QS output.** `Qxxx|P1814|"<hiragana>"|S143|Q177837|S4656|"<jawiki url>"`, drained by the daily submitter.
Generation is NOT blocked by the 2026-08-10 Wikidata freeze — only submission is, so staging now is fine.

**CI/CD phase (items with no queued en label).** A new label-pipeline step BETWEEN "check P1814" and the
same-name/disambig step: save the jawiki article to Claude → extract kana → make P1814 → continue normally.
Model it on the `remote_queue.py` answer-marker + collector pattern (builder writes a work-file = lead +
`<!-- ANSWER: -->` marker; the remote routine fills it; a `collect_*` script turns answers into QS) — same
shape as `collect_label_typo_answers.py` / `collect_category_translations.py`.

## A0b. ✅ Mother house (P612) — ALL 444 READ IN FULL 2026-08-04 (345 Beppyo + 99 Ise)

**Done, and the 2026-08-03 keyword pass is superseded.** That pass judged from keyword-extracted
sentences, not full articles, which is why it produced 129 UNCLEAR. Emma called it: *"all 344 need
the same agentic full-read treatment."* Every one of the 444 articles has now been read in full by
an Opus agent and classified TRANSFER / NETWORK / AUTOCHTHONOUS / UNKNOWN —
**327 AUTOCHTHONOUS (74%), 78 TRANSFER, 33 NETWORK, 6 UNKNOWN.** Only six articles give no origin
at all; the lineage really is in the prose and essentially never findable by keyword.

**408 items staged** in `modern-quickstatements/beppyo_p612.txt` (one P612 line each, no subject
with two targets); the daily submitter delivers once the freeze lifts (2026-08-10).
Data: `lineage/agent_results.tsv`. Generator: `lineage/build_p612_quickstatements.py`
(`--supersede` drops an earlier line where the full read disagrees — 21 did, all still un-dripped
because the freeze has been on since before the file existed). Waves are restartable via
`lineage/wave.py`, which plans from what is missing rather than from session context.

Emma's two class rulings, 2026-08-04:
- **NETWORK → emit the inferred network head**, including where the article names only a deity
  (函館八幡宮 "八幡神" → 宇佐神宮, 笠間稲荷 勧請元不詳 → 伏見稲荷大社). `DEITY_HEAD` in the
  generator is the one place a value is not read off the article.
- **A non-shrine source still gets P612** — a palace, a place, a tomb (皇大神宮←笠縫邑,
  白峯神宮←白峯陵, 石上神宮←宮中). The edge is real; recording it beats losing it.
- Gates that stop a bad value: disambiguation-page targets are refused (京都の諏訪神社 resolves to
  the generic 諏訪神社 list), as are self-references (瀧原宮/瀧原竝宮 share one article and one QID).
  14 rows produce nothing and say why in `lineage/_p612_resolution.log`.

- **Membership comes from the jawiki CATEGORY, never Wikidata** (Emma 2026-08-03). One paginated
  `list=categorymembers` call; each QID from `pageprops.wikibase_item` in the same request. The
  builder issues zero SPARQL — see the "DO NOT HAMMER WIKIDATA" rule in `CLAUDE.md`.
- Two findings worth Emma's eye: 石清水八幡宮 → **宇佐神宮** (its own lead says so), and 宇佐神宮 →
  **大分八幡宮**, which its own 託宣集 calls 我本宮 — the head of ~44,000 Hachiman shrines naming a
  parent.
- The 178 autochthonous calls are the ones most likely to need correction; 護国神社 rest on
  三重県護国神社's own "靖国神社とは本社分社の関係にはない".
- ✅ **Suffix generator time-boxed** — `generate_bunrei_quickstatements.py` now stops on
  **2027-02-01** via a date gate (a rule, not a future commit-then-revert). It exits *before* the
  SPARQL and *before* opening the output, because `main()` writes with `"w"` and a post-sunset run
  would otherwise truncate `bunrei.txt` and destroy statements the drip had not yet delivered.
  4 tests, including one that the gate is not wired backwards.
- ✅ **enwiki re-read DONE 2026-08-04 — and it is close to exhausted.** Of the 129 UNCLEAR, only
  **81 have an enwiki article at all**, median 2,115 chars with 30 of them stubs. Scanning those 81
  for mother-house language found 12 candidates, and reading all 12 yielded **3 statements**:
  Q11381863 → 住吉大社 ("It is a branch shrine of Sumiyoshi-taisha"), Q500763 → 吉備津神社 (enwiki
  calls it "the parent shrine", matching 安仁神社's jawiki account), and Q335618 Kumano Hayatama →
  autochthonous (it is one of the three Kumano Sanzan heads). The other 9 were regex false
  positives — clan cadet branches, lists of a shrine's OWN outward branches — or claims that merely
  add a third competing tradition (Yasaka's Nunakuma origin) without settling anything.
  **~2% yield. Do not spend another pass on enwiki for this set.** 126 remain UNCLEAR and they are
  genuinely unsettled in both languages, not under-researched.
- ✅ **CORRECTED 2026-08-04 (Emma): a 勧請 in transit IS a real bunrei.** I had ruled the three
  shrines founded along 行教's 859 Usa→Iwashimizu journey UNCLEAR — 亀山八幡宮 (下関), 琴崎八幡宮,
  甲宗八幡神社. Emma: they are real bunrei. All three now point at 宇佐神宮 (Q715632). Named parents
  go 39 → 42 of 344 (12.2%).
- ▶ **Remaining:** Emma's review of the 327 autochthonous calls.
- **A more organized extraction technique is a job for Topaz, NOT this repo.**

## A0c. 🖥️ 神宮125社 — the Ise Jingū constituent shrines (Emma 2026-08-04)

**Emma's scope ruling:** every 別表神社 is notable enough to be worth high effort, and *"all of
these shrines are that way too"* — <https://ja.wikipedia.org/wiki/Category:神宮125社>.

**Measured 2026-08-04** (direct members only — never recurse a category, see `CLAUDE.md`):
- 99 ns-0 articles besides the list page; **76 have a Wikidata item**, so **23 articles have none**.
- **54 of the 76 lack P1814** — direct work for the A0 name-in-kana pipeline, and the obvious first
  pass. Includes 豊受大神宮, 荒祭宮, 風日祈宮 and 伊勢神宮 itself.
- **0 lack P361 (part of)** — every one is already linked as a constituent of the Jingū.

**✅ P612 question SETTLED 2026-08-04 — Emma: keep all 99.** The worry was that a 摂社/末社/別宮 is
a *constituent* (P361, already on all 76) rather than a branch. It is answered by how the read was
done: the agents were told explicitly that subordination is not lineage, so P612 here carries the
kami's origin and P361 carries membership — different claims, and they coexist. 80 of the 99 came
back AUTOCHTHONOUS (倭姫命 enshrining a local 国津神 in place; a river, well or stone that is itself
the kami), which is a statement no constituency relation can express. The 19 that name a parent
(瀧原宮←磯宮, 豊受大神宮←比沼麻奈為神社, 伊雑宮←皇大神宮) are staged with the rest. See A0b.

▶ **Still open here:** the P1814 pass over the 54, and the 23 articles with no Wikidata item.

## A1. 🤖 Cloud-answer collectors — live again, run them when a routine commit lands

The routine's push was fixed 2026-07-28 (it had no repo bound; `session_context.sources` is the field
— see `docs/remote_queue_routine_prompt.md`), so answers are landing again and these are no longer
idle. Ran the same day: 9 label typos, 1 ronsha ranking, 11 descriptions, 12 category moves. All four
are repo-local — no Miraheze request — so they stay runnable through the blackout.
- `collect_label_typo_answers.py` — 147 pending.
- Description-enrichment (224 pending), ronsha-ranking (34 pending), category-translation (361
  pending) collectors — same pattern. `docs/description_enrichment_pipeline.md`.

## A2. ⏭ Court-rank (P14005) people pipeline — pure Wikidata, finishable now

Tags PEOPLE with P14005 from the ja.wp [[Category:日本の位階受位者]] tree. Decisions settled: create
missing items, every rank held, primary-label rank map, skip 无位, no parent-rank double-tag.
- ✅ 26 sub-rank items created (Q140679480…Q140679509); base ranks already existed.
- ✅ Sub-rank parent links (P361) run; 外従五位 base created = **Q140679675** (part of 外位).
- ✅ Bidirectional category links run: 42 recipient categories linked rank↔category (P1792/P301);
  24 missing category items created (Q140685601…).
- ⏳ **Category English labels:** `court_rank_category_en_labels.txt` (42 lines), add-only. Emma runs it.
- ✅ **Wire-in done 2026-07-28** — the live rerun reported all **42 rank categories resolved** (the
  stated condition), so the generator is a step in `generate-quickstatements.yml` and
  `court_rank_people.txt` (12,605 lines, 12,326 people) is registered in `ATOMIC_FILES`, uncapped
  (~10% of the daily draw, same share as its size peers). Lands no earlier than the 2026-08-04 freeze
  lift.
- Note: base-rank items still carry sub-rank names as skos aliases (正四位 has "正四位上/下"); optional
  cleanup now that sub-ranks are their own items.

## A3. 🤖 Shrine external-ID entity resolution — Wikidata + external sites

- 🤖 **Genbu.net (P13930)** — `generate_genbu_ids.py` → `genbu_ids.txt` (**1257**, up from 1041 after the
  kyūjitai + province-disambiguation passes). Registered; drips. Only the *live-wiki citation* source
  is capped by the 403 — the genbu crawl itself is unaffected, so further coverage work runs now.
- 🤖 **Shinmei DB (P14391)** — `generate_shinmei_ids.py` → `shinmei_ids.txt` (**77**). Audited
  2026-07-28 and the count went DOWN on purpose: the matcher had no class gate at all (its sibling
  `generate_genbu_ids.py` always had one), so three category errors were staged and would have gone
  out when the freeze lifts — 気比大神→`Q11129346` (the SHRINE 氣比神宮), 筑紫島→`Q13987` (the modern
  island 九州), 波比岐神→`Q10928586` (座摩神). A deity/non-shrine gate now runs AFTER uniqueness; it
  rejects, it never disambiguates (applying it during the lookup turned two safely-ambiguous names
  into confidently wrong ones). Rejections are listed in `_site/shinmei_unmatched.txt`.
  - ❌ **The fuzzy/alias pass is settled: NOT worth doing — do not re-attempt.** The old note here
    said "256 kami have no exact-label match"; the real figure is **129** (+19 ambiguous). Suffix
    variants (strip/append 神/命/尊/大神/之命) over all 129 resolve just 3, and 2 of the 3 are wrong
    (穴戸神→`Q907382` 長門国, a province; 大土神→`Q11571306` 犯土, a calendrical term). 1-in-3
    precision on a deity identifier is not a trade worth making. The 129 are obscure Kojiki names
    with no Wikidata item; the 19 ambiguous ones need Emma to choose.
- ▶ **Prefectural shrine-association IDs → P973.** Emma decided 2026-07-28: **P973 now** (not a
  property proposal, not the private repo). No new property needed.
  - **Correction to the old framing:** there is no "rest of the CSV" to cover.
    `generate_jinjacho_p973.py` already emits **all 88** rows of
    `jinjacho/shrines_and_websites.csv` — that CSV is a *sample*, not a backlog, so re-running the
    generator adds nothing. Coverage grows only by resolving MORE shrine→URL pairs.
  - ✅ **Pipeline BUILT 2026-07-28** (`f97c85b74`): `jinjacho/crawl_jinjacho_shrines.py` →
    `crawled_shrines.csv` → `jinjacho/match_jinjacho_shrines.py` → `crawled_shrines_matched.csv` →
    `generate_jinjacho_p973.py` (now reads that file *and* the original 88-row sample). 16 tests,
    wired into `ci.yml`. External sites only, so it runs through the blackout.
  - ✅ **Shiga and Saitama are COMPLETE** (2026-07-28): 1,388 + 1,284 records. Both ended on miss
    tolerance, and that was verified to be the real end of the id space, not a gap — Saitama 404s
    past 10397, Shiga serves empty pages past 1560.
  - ⏳ **Gifu still crawling** — cursor in `crawl_state.json`; that host answers in ~20s/request, so
    its 2,600 ids are ~12h of wall-clock. Resume with
    `python crawl_jinjacho_shrines.py --family gifu --max-pages 2400`. **After each chunk:** re-run
    `match_jinjacho_shrines.py` then `generate_jinjacho_p973.py` and commit the three outputs —
    both are idempotent and simply extend the file.
  - **Precision is deliberately expensive.** The match gate is the MUNICIPALITY from the crawled
    address, not the prefecture (prefecture-gating produced verified-wrong matches: a 大垣市 天満神社
    → 天満神社 (高山市)), plus a collision guard dropping any item claimed by two crawled shrines.
    Expect a low yield; a missed shrine costs nothing, a wrong P973 is a wrong statement.
  - ✅ **Aichi is DONE and the "not yet covered" line here was stale** — 3,179 rows are already
    in `crawled_shrines.csv`, harvested by `harvest_aichi` in a single POST to the site's search
    API. Only Osaka is still uncovered.
  - ✅ **Mie + Kagoshima harvested via their sitemaps (2026-08-03).** They were filed as
    "name-slug paths, not enumerable"; both are WordPress and both publish a sitemap that
    robots.txt points at and permits. Mie's shrine post type is one file (**822** URLs);
    Kagoshima's shrines are ordinary posts across 92 monthly sitemaps, filtered by
    `/shrine-search/`. Run: `python crawl_jinjacho_shrines.py --index mie|kagoshima
    --max-pages N` — capped, resumable by URL (not cursor), URL list cached in
    `index_urls.json`. Re-run `match_jinjacho_shrines.py` + `generate_jinjacho_p973.py` after
    each chunk, same as the id families.
  - ⏳ **Osaka is the last one** — `www.osaka-jinjacho.jp` is static HTML
    (`funai_jinja/dai1shibu/nose-cho/01020kusasajinja.html`), no robots.txt and no sitemap, so
    it needs its section index pages walked rather than a sitemap read. Not started.
  - Add-only; the daily editor skips statements that already exist, so re-runs are no-ops.
  - ⚠️ **Mie's low yield is NOT the parser — corrected 2026-08-03 after measuring.** The parser fix
    below was real and lifted the total 1,151 → **1,441**, but almost all of that went to Kagoshima
    (129 → 283) and Osaka (97 → 213). **Mie went 17 → 16.** The actual cause: of its 300 rows, 202
    match a shrine name, but **171 of those match only same-named shrines in other prefectures**
    (三宅神社 → 亀岡市, 一色神社 → 掛川市, 三宮神社 → 神戸). Mie's own shrines mostly have no
    Wikidata item, so the earlier "thin data" guess was right and the parser diagnosis was wrong
    for this prefecture. Nothing to fix here — the gate is correctly refusing to attach Mie URLs to
    Kyoto and Shizuoka shrines. Crawling Mie's remaining 522 pages will add little; deprioritise it.
  - ▶ **Separate, real defect found while measuring: candidate items with NO P131.** 180 of the
    2,832 candidate items for Mie names (6%) have no P131 ancestor ending in 市/区/町/村 — e.g.
    Q135039445, Q135186750. These can never pass the municipality gate no matter how good the
    address parsing is, because there is nothing on the item to compare against. Worth measuring
    across all prefectures and deciding: either accept a prefecture-level match for items with no
    P131 at all (weaker gate, only for that subset), or leave them and treat it as a P131 backfill
    task. Do not weaken the gate for items that DO have P131.
  - ✅ **Municipality parser fixed 2026-08-03** — three bugs, all failing CLOSED (row dropped,
    never mismatched):
    the prefecture-stripper was `^.{2,4}?[都道府県]`, unanchored, so any address through a 国府町 /
    道明寺 lost its city; the 郡-stripper was `^.{1,5}?郡`, so 霧島市国分郡田 lost its city; and the
    token rule stops at the first mark, truncating 四日市市 → 四日市. Fixed with the real 47-name
    prefecture list, a lookahead requiring a 町/村 after 郡, and an explicit override list for the
    ~10 municipalities whose names contain a mark. 51 rows corrected. See the counter-example tests
    before touching this: 近江八幡市 + 市井町 is the same string shape as 四日市市 + 三滝町, so no
    general rule separates them.
  - ▶ **Better idea, not built: gate on P131 ancestor LABELS instead of parsing the address.** We
    already fetch every candidate's P131* ancestor ja labels; testing whether any ancestor label
    ending in 市/町/村 occurs in the crawled address removes address parsing entirely. Caveat that
    needs solving first: 区 labels are ambiguous across cities (港区 exists in Tokyo, Osaka and
    Nagoya), so 区 must be excluded or paired with its 市. Do not ship it without that.
  - ✅ **CI was reverting generated files it never generated (fixed 2026-08-04).**
    `generate-quickstatements.yml` backed up `*.txt` wholesale, pulled, then copied the lot back —
    reverting any file another push had updated meanwhile. `jinjacho_p973.txt` lost 205 matched
    pairs this way (1,526 → 1,236 lines against a 1,441-row CSV). Now backs up only
    `git diff --name-only` + untracked. **If a generated file ever looks smaller than its input
    justifies, suspect this shape before suspecting the generator.**
  - ✅ **`generate_soja_only.py` import-safety FIXED 2026-08-04.** It had no `__main__` guard, so
    importing it (to read one constant during the endpoint migration) fired its migration queries and
    rewrote its two output files; it also rebound `sys.stdout` at import and wrote its outputs to
    bare relative paths, so they landed wherever cwd happened to be. Body wrapped in `main()`, stdout
    rebinding moved inside it, outputs now `HERE`-relative. A scan of every `generate_*`/`fetch_*`/
    `resolve_*`/`submit_*`/`select_*` module found this was the ONLY generator missing the guard —
    the other unguarded files are import-only helpers (`kana_english`, `romaji_phonology`,
    `user_agent`, …). `tests/test_no_work_on_import.py` now asserts the guard across all generators.
  - ▶ **SPARQL endpoint migration — 9 left, ALL of them blocked.** `modern-quickstatements/` is
    DONE (15 migrated 2026-08-04, every one verified with a bounded `LIMIT 1` probe through its own
    constant). The 9 remaining all sit in `shinto_miraheze/` and import `mwclient`, which is not
    installed in the dev environment — so they cannot be imported, and a live check is impossible
    until the blackout lifts. They stay on the old endpoint rather than being changed blind.
    - **Verify these textually, never by importing.** 84 modules in this repo rebind `sys.stdout` at
      module scope — that is the documented script-template invariant in `CLAUDE.md`, not a defect,
      and it exists because these are CLI scripts needing UTF-8 output on Windows. Importing one
      replaces the caller's stdout and breaks it. Read the constant out of the source instead. (This
      is distinct from `generate_soja_only.py`, which additionally RAN ITS WORK on import — that was
      a genuine defect and is fixed.)
    mid-migration to `query-main.wikidata.org` (32 scripts already there). The old endpoint
    threw repeated 503/504 during the 2026-08-03 rematch's 17,549-candidate P131 pass;
    `generate_genbu_ids.py` was moved and verified live, which also fixed
    `match_jinjacho_shrines.py` (it imports that module's `_sparql`). The remaining 24 are a
    mechanical one-line change each, but each needs a live run to confirm — do them in
    batches, not as one blind sweep. `grep -rln "https://query\.wikidata\.org/sparql"`.

## A4. 🤖 Wikidata drip — staged, waiting on conflict_gate (NOT on the wiki)

All registered atomic files are staged-but-not-delivered by design until `conflict_gate` lifts
(~2026-08-08, or 7 days after ブルーノ・プラス goes quiet). Emma's caution gate, not a stall.
- **Engishiki list membership** — script 1 adds (`list_membership_rebuild.txt`), script 2 removals
  (`list_membership_removals.txt`, 2,236 pure removals). The 22 duplicate `part of` are report-only.
  `docs/ronsha_list_membership_2026-07.md`.
- **Province exclusions** — `province_exclusions.txt` (382 lines). ADD-ONLY, no removals ever.
  `docs/province_exclusion_residual_2026-07.md`.
- **Reisai** — 3,239 P837 lines staged (`reisai.txt`); live coverage still 195. Reassess (Mie
  prefectural scraper?) once the drip resumes and the real gap is measurable.
- 🤖 **Bruno archiver** — `archive_destroyed_items.py` runs in CI, auto-captures new damage.

## A5. ⏸ Parked — external, and not shintowiki either

- ⛔ **HUSK GUARD (2026-08-04).** Ten staged QuickStatements across five atomic files targeted the
  ブルーノ・プラス-repurposed items — including `Q123044569|Len|"Ōmiwa Shrine"`, which would have put
  an English label on the repurposed identity. They arrived honestly: the husk now IS the 大美和神社 /
  近殿神社 item on Wikidata, so any generator resolving a jawiki article to a QID by sitelink lands on
  one. Nothing went out only because the freeze was still on. Lines stripped; the durable guard is a
  refusal in `direct_daily_edits.item_is_editable()` — the single road to Wikidata — not in each
  generator, because the next generator written would miss it.
  `tests/test_repurposed_husks_never_edited.py` asserts both the gate and that no atomic file stages
  a husk edit. **Expect generators to keep re-emitting these lines on each CI regeneration; the gate
  is what makes that harmless.**


- **Repurposed-item damage** — Q123044569 (Kamo), Q134886554 (Chikadono), Q134736575 (見光寺),
  Q140476265 (junk). Emma: *document, don't touch; no contact* until we understand the editor. The
  Kikuna restoration is already queued to our item Q134926804. `docs/bruno_plus_analysis_2026-07.md`.
- **Bunrei paper sources** — 神社本庁『全国神社祭祀祭礼総合調査』(1995) etc.; needs a library, not
  scrapeable. Online 総本社 sources are exhausted (~10,650 cited edges).
- **Mother house (P612): active work is A0b** (Beppyo Opus Pass, individual lines). Suffix generator
  stays but time-boxed ~6 months (convention-establishment, not perpetual). Organized extraction →
  Topaz, not this repo.

---

# ═══════ §B — GATED ON SHINTOWIKI · DO NOT START UNTIL `WIKI_GATE: GO` ═══════

Everything below needs the wiki. While the blackout is on, these are not just blocked — **touching
them means touching Miraheze, which is the exact thing the blackout exists to prevent.**

## B0. 🤖 The gate itself

- **Weekly wiki edit-test** — `weekly-wiki-edit-test.yml`, Sundays. CI attempts a REAL edit to
  `User:EmmaBot/edit-test`. Success → unlocks for the week + marker GO; failure → 8-day lock + marker
  WAIT. Currently held by `blackout_until: 2026-08-09`, so it makes no request at all before then.
  Nothing to do — the Sunday test is the sole decider.
  Audit: `docs/wiki_403_audit_2026-07-11.md`. The block is a Cloudflare zone challenge on shinto
  (aelaki works from the same IP).
- **All wiki edits are stuck in the repo** — Open-questions responses committed to
  `git_synced/Open questions.wiki`, plus every cleanup/orchestrator edit. Not fixable from CI.
  [[reference_miraheze_antiddos_challenge]]

## B1. Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-07-13)

Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki`
(the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every
actionable item or Emma disposition not yet handled: decompose it into concrete steps, or act on it now
and prune the resolved bullet. Then delete THIS block. **Needs the live page → §B.**

## B2–B8. ❓ DECISIONS — fire ONE at a time, in order, once the gate opens

**Standing rule: EVERY decision carries a "walk me through it first / let's chat" option.** Emma often
doesn't have the context to pick A vs B cold — she picks "explain it first", the bot lays out the
situation in plain terms, they talk, THEN decide. Never treat a decision as "blocked on Emma" and skip
it; fire the question with the chat option so it can actually move.

> These can't be decided blind — Emma reviews them against the Open questions page **plus** the
> browsable tables. The tables are GitHub Pages and work right now, but the review pairs the two, so
> they wait for the gate (Emma 2026-07-13).

### B2. The 84 duplicate shrine pairs — link or merge?
84 living-shrine items duplicate their 927-register-entry twin (same Kokugakuin id / name).
Table: https://emmaleonhart.github.io/shintowiki-scripts/shikinaisha-orphans.html
- **ASK:** "Link each pair with 'said to be the same as', or merge them?" → *link* (I generate
  QuickStatements, add-only) / *merge* (manual/browser, I hand you the list) / *case-by-case*.

### B3. The 66 orphan Shikinaisha — mis-tagged, or missing entries?
66 confirmed-Shikinaisha with no twin: either modern shrines wrongly tagged as 927 entries, or real
entries the lists are missing. Same table as B2.
- **ASK:** "How do I treat the 66?" → *investigate case-by-case* / *treat as mis-tagged* (drop the
  class) / *treat as missing entries* (add to the list).

### B4. The 18 missing Kokugakuin ids — auto-fill or eyes?
18 register entries lack a Kokugakuin database id; the strict matcher found ZERO safe to add (two
adjacent DB entries can share a name).
Table: https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-missing-ids.html
- **ASK:** "Is exact name-matching good enough to auto-fill, or do the 18 need per-item eyes?" →
  *per-item eyes* / *auto-fill the exact matches*.

### B5. The ~66 items with two Kokugakuin ids — how to assign the section?
Each is a candidate for two different 927 entries, so its parent-link needs a "which entry" (P958)
qualifier. Emma earlier ruled all ambiguous.
Table: https://emmaleonhart.github.io/shintowiki-scripts/kokugakuin-multi-p13677.html
- **ASK:** "Go through these with me per-item now, or leave them for you to work off the table?" →
  *per-item with you* / *leave for you*.

### B6. The Awa list fix — how to delete the wrong statement?
Awa entry 3 should be 天神社 (add already queued); the wrong 下立松原 statement must be deleted, but it
can't be a QuickStatement (下立松原 sits at ordinals 3 AND 5, same value).
https://emmaleonhart.github.io/shintowiki-scripts/awa-entry-3.html
- **ASK:** "Sequential-misc unit (remove BOTH 下立松原 has-parts, re-add the correct #5), or you
  hand-delete the one statement?" → *sequential unit* (I build it) / *you hand-delete*.

### B7. Kokugakuin P13677 matcher — what did you actually want here?
Emma 2026-07-09: *"I don't even understand what this actual thing even is."* The matcher
(`match_kokugakuin_ids.py`) cut the missing-id set 94→18 (same set as B4).
- **ASK:** "This is the same 18 as B4 — is B4 the whole of it, or is there a separate thing you wanted
  from the matcher?" → *B4 covers it, drop this* / *there's more (you explain)*.

### B8. Empty-items — which to restore?
285 emptied items, 217 lost their P31 — restoration candidates, sorted by how much was lost.
https://emmaleonhart.github.io/shintowiki-scripts/empty-items.html
- **ASK:** "Generate restore-QuickStatements for a slice (e.g. the ones that lost their P31), or is
  this a browse-and-you-pick report?" → *generate restores for <slice>* / *browse-only for now*.

## B9. ⏸ Category-orchestrator speed-up *("the category thing")*

A POSSIBLE future optimization to make wiki category-page processing faster (skip some ops on ~3k
enwiki-junk cats, or shard the namespace). Only worth doing IF the Japanese-category-translation drain
proves too slow. It isn't a problem now → dormant.

---

## Pinned tail (keep last)

- [ ] Ensure the five session-local crons are running (this session: work-loop d6754ae5 :03,
  auto-flush 3d3cd832 :15, status-report 0df6273e :42, briefing 257eeecc 08:03, debrief ee782e80
  23:57). SYNC fast-forwards onto origin/main each tick.
- [ ] Run the status-report action once more independently as an end-of-session summary.
