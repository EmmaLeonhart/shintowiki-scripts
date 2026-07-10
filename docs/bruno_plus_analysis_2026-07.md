# ブルーノ・プラス — editing-behaviour analysis

Compiled 2026‑07‑10 from the Wikidata API (`list=usercontribs`, all 513 retrievable edits).
Emma's read: *"I think this person is an LTA."* This document is the evidence base for the
caution policy in `conflict_gate.py`. **No Wikidata action was taken against this editor, and
none should be taken without Emma's say-so.** Per her instruction: *document, don't touch*, and
*no contact*.

Account: <https://www.wikidata.org/wiki/Special:Contributions/ブルーノ・プラス>
Registered 2021‑01‑22 · 523 lifetime edits · no advanced permissions.

## 1. Activity — dormant, then a sharp 2026 ramp

| Year | Edits |
|---|---|
| 2023 | 15 |
| 2024 | 2 |
| 2025 | 0 |
| **2026** | **496** |

Within 2026: March 1 · **April 71** · May 15 · **June 103** · **July 306 (partial month)**.

The work comes in **bursts**, not a steady drip:

| Day | Edits | Distinct items |
|---|---|---|
| 2026‑06‑30 | 81 | — |
| 2026‑07‑01 | 70 | — |
| 2026‑07‑05…08 | 3 · 2 · 2 · 1 | 1 each |
| 2026‑07‑09 | 93 | 44 |
| **2026‑07‑10** | **122** | **76** |

Last edit at the time of writing: **2026‑07‑10T02:13:29Z** — i.e. active *now*. 216 distinct
items touched overall.

## 2. What they actually do — and Emma's hunch was right

Of 197 term (label / description / alias) edits:

| Language | Edits |
|---|---|
| **ja** | **181** |
| en | 16 |
| mul / en-us / en-gb | 3 |

**They are not competing with our English-label programme.** They write Japanese descriptions
(141 `wbsetdescription-set`, 30 `-add`). Emma: *"they also might simply be adding better
labels."* Largely true.

Statements they **create** are ordinary geodata:

`P625` coordinates ×54 · `P131` admin unit ×38 · `P31` ×28 · `P17` country ×25 ·
`P140` religion ×15 · `P6375` address ×5 · `P18` image ×4

They also created 26 new items and added 22 sitelinks. Their subject range is broad — shrines,
temples, **baseball stadiums, an airport** — so they are a general Japanese-topics editor, not a
Shinto specialist shadowing us.

## 3. The problem: 38 claim removals, and two gutted items

Removals concentrate on 17 items. Properties removed:

`P825` enshrined deity ×6 · `P625` ×5 · `P18` ×5 · `P131` ×4 · `P31` ×4 · `P17` ×3 ·
`P931`, `P10689`, `P6375`, `P856`, `P2900`, `P1329` ×1 each

Two items were not cleaned up — they were **destroyed and reused**. Both had been edited by
Immanuelle.

### 3.1 `Q28069431` — Kikuna Shrine → an empty husk

On 2026‑07‑09 06:25–06:26 they removed, in order: `P31`, `P18`, `P17`, `P131`, then **five
separate `P825` enshrined-deity statements** (`Q317997`, `Q455602`, `Q461258` Yamato Takeru,
`Q1781862`, `Q1073668`), then `P1329` phone, `P2900` phone, `P856` website. They then removed
the `ja` and `en` labels, both descriptions, and the `ja` alias.

The item now holds **0 claims and 0 sitelinks**. The only labels left are the `fr`
("Sanctuaire de Kikuna") and `id` ("Kuil Kikuna") ones **Immanuelle added in July 2025** — they
now describe nothing.

菊名神社 currently resolves to **`Q134926804`**, which carries only **6 claims**. The five
deities, the image, the phone numbers and the website did **not** all survive the move. This is
a lossy manual merge that left a husk behind — the same pathology as the `Q135193070` husk
already recorded in `docs/kokugakuin_anomaly_review_scope_2026-07.md`.

### 3.2 `Q123044569` — Kamo Shrine → repurposed into 大美和神社

On 2026‑07‑10 01:36–01:44, in a single ten-minute run:

1. Removed `P31`, `P17`, `P131`, `P625`, `P825` (`Q11634943`), `P6375` (708 Kamonomiya,
   Odawara), `P10689`.
2. Removed labels `Kamo Shrine` / `加茂神社` and both descriptions.
3. Re-added label `大美和神社`, a new `ja` description, `P31`, `P17`, `P131`, and **new
   coordinates** (35°11′26″N 139°7′54″E — the old ones were 35°16′38″N 139°10′33″E).
4. Attached the jawiki sitelink `大美和神社`.

The item's identity was **overwritten with a different shrine at a different location**. The
`P825` and `P31` removed were Immanuelle's, added 2025‑07‑21 via QuickStatements. Kamo Shrine
(Odawara) now appears to have no item at all.

Item repurposing is contrary to Wikidata convention — a new item should be created — and it
silently invalidates every external reference to the old QID.

## 3.5 Are they a constructive editor? — the record on ja.wikipedia

Emma: *"I don't know if this person has been doing anything that could be considered to be
constructive editing here … I don't know Japanese."* Translated summary of their **jawiki user
talk page** (`利用者‐会話:ブルーノ・プラス`), which is a running list of warnings:

| Date | Section | What it says |
|---|---|---|
| 2023‑09‑12 | `IPアドレス` | *Prefuture* asks whether they are also editing as IP `2407:C800:F00F:4::129A` — i.e. a **sockpuppetry / logged‑out‑editing** question. |
| 2023‑09‑17 | `改名提案の件` | *ねこざめ* warns them for **renaming a page without consensus**, against `Wikipedia:ページの改名`. |
| 2023‑11‑18 | ×2 file warnings | **Uploaded images with no source and no licence**; both slated for deletion. |
| 2023‑11 | ×3 more | `著作権上の問題があります` — **copyright problems** on three uploaded files. |
| **2026‑04‑22…24** | **`神社記事の編集について`** | **An active content dispute about shrine articles.** |

The shrine thread, in substance:

* **弁財3000** asks them to stop adding furigana (ruby) to the *name* field of shrine infobox
  templates — the reading is already in the article's first sentence, it is redundant, and it
  breaks the template's map display. Also asks them to stop inserting stray `{{-}}`.
* **ブルーノ・プラス refuses.** *"Is putting furigana on a non-difficult name a bad move? Is it
  vandalism? It comes from kindness beyond redundancy. Whether it is hard to read is only your
  opinion."* They say they will **continue** doing it.
* 弁財3000 says that if they insist, it becomes a matter for a **large discussion at
  `プロジェクト:神道` (WikiProject Shinto)**. They reply that invoking WikiProject Shinto *"over
  mere ruby is an exaggeration"* and *"an act denying the diversity of editing methods."*
* They accuse 弁財3000 — whom they themselves identify as **probably the most prolific shrine
  editor on ja.wikipedia** — of `唯我独尊` (self‑righteous egotism).
* **The line that matters to us:** 「神職が常駐していない神社」… 「もともと、そんな神社は記事
  立項してはいけません」 — *"shrines without a resident priest … such shrines should never have
  had articles created in the first place."*

**Assessment.** Some of their work is plainly constructive — coordinates, admin units,
`P31`/`P17`, Japanese descriptions, 26 new items. But the record shows a pattern of
**refusing correction**, a history of copyright and consensus violations, an unresolved
sockpuppetry question, and — on Wikidata — **item repurposing and lossy blanking**. Combined
with an explicit belief that minor shrines do not deserve articles, an eventual collision with
this project is plausible rather than paranoid.

Emma's read (*"this person is an LTA … who is going to get a lot of attention to themselves"*)
is consistent with the evidence. The operative risk is **not** that they out‑edit us; it is
that scrutiny of them extends to whoever is editing the same items.

## 4. Collision surface with our pipeline

**161 of their 215 items appear in our registered, executable `ATOMIC_FILES` batches.**

| Batch | Colliding items |
|---|---|
| `description_label_pairs.txt` | 78 |
| `souken_p571.txt` | 76 |
| `reisai.txt` | 58 |
| `saijin_p825.txt` | 46 |
| `bunrei.txt` | 30 |
| `honzon_p825.txt` | 18 |
| `temple_identical_name_en_labels.txt` | 15 |

Two collisions were **live** at the moment of writing:

* `description_label_pairs.txt` would have written a Ukrainian description onto `Q28069431` —
  the empty husk.
* `souken_p571.txt` would have written `P571 = 1671` onto `Q123044569` — the repurposed item.

Had the drip run, either edit would have looked to this editor like a bot reverting them.

## 5. Policy adopted (Emma, 2026‑07‑10)

Implemented in `modern-quickstatements/conflict_gate.py`:

1. **Global pause of the QuickStatements drip**, minimum one week (until **2026‑07‑17**).
2. **Resume only 7 days after this editor's last edit.** While they keep editing, the pause
   keeps extending.
3. **Hard cap: 2026‑08‑08** ("a week into August"). If they are still editing then, the
   pipeline resumes regardless — the gate must not become an indefinite self-block.
4. **Per-item freshness gate, permanent and general:** never edit an item that any other user
   has edited within the last 7 days. This is not aimed at one person; it dodges every future
   contributor and removes the whole class of edit-conflict.
5. **Document, don't touch.** No restoration, no reverts, no cleanup of the husk's stray
   labels, no talk-page contact. Visibility is worse than data loss.
6. **Three attention signals, deliberately not collapsed into one.** All of them override
   `HARD_RESUME`: the cap exists so a busy editor cannot veto our pipeline for ever, not to force
   us to edit into a live dispute.

| Signal | Venue | Rule | Why |
|---|---|---|---|
| **Indefinite hold** | jawiki `Wikipedia:井戸端` (the Japanese project chat) | Their name present in the page text → **no edits, no expiry date** | Emma: *"it has a 90-day expiration on conversations in it … it has a tendency to necro a bit more. If this person's name … is ever present in Japanese Wikipedia Project Chat, then we put it on hold. Just no edits."* A dated pause is wrong when a dormant thread can be revived. The hold lifts when the name leaves the page. |
| **30 days from activity** | their talk pages (both wikis) | *Any* activity → 30-day pause from that activity | *"If there has been any activity within a month on their talk page, then there will be a month of no edits."* Activity, not mention — their name is trivially on their own talk page, so a presence rule would pin the gate shut for ever. |
| **30 days from mention** | admin noticeboards + discussion venues | Name present → 30-day pause | *"If there has been a mention of them on the administrators' notice board within the last month, then no editing."* |

Watched noticeboards / venues: `Wikidata:Project chat` · `Wikidata:Administrators' noticeboard` ·
`Wikidata:Requests for deletions` · `Wikidata talk:WikiProject Japan` ·
`Wikipedia:管理者伝言板/荒らし` · `Wikipedia:管理者伝言板/投稿ブロック` ·
`Wikipedia:コメント依頼` · `プロジェクト‐ノート:日本`

`watch_conflicting_editor.py` is **read-only**: it never edits, never posts, and never names our
operation anywhere. It writes `conflict_watch.state`, which the editor reads.

**First scan, 2026‑07‑10:**

* jawiki 井戸端 — **clean**, no indefinite hold.
* All eight noticeboards / venues — **clean**.
* jawiki talk page — last activity **2026‑04‑24** (the shrine dispute above). 30 days later is
  2026‑05‑24, already past, so it does not currently bind.
* Wikidata talk page — does not exist.

The drip is therefore held by the **routine** gate: **no edits before 2026‑07‑17**, and later
still while they keep editing (they edited on 2026‑07‑10).

Everything **fails closed**: a missing or corrupt `conflict_watch.state` is read as "they edited
today"; an unreachable 井戸端 is treated as a hold, because absence of the name cannot be shown;
and an item whose revision history cannot be fetched is not edited.

## 5.1 Emma's exit condition

*"If they are regular, going into August, and they don't have any talk page activity or mentions
in these areas, then that would indicate that they're likely assimilated enough into the
community … they will probably not be drawing enough attention to themselves so that our pipeline
is visible to the community."*

That is exactly what `HARD_RESUME = 2026-08-08` encodes: a steadily-editing, un-discussed editor
is a community member, not a threat, and the pipeline resumes. The attention signals are what
distinguish that case from the other one.

She accepts the worst case explicitly: *"the worst-case scenario in the safe one is that we have
not been editing for an extended period, and then they get blocked … and then a month later our
pipeline starts again."*

## 6. Deferred — to be done a week after they stop editing

Emma: *"we might want to, at some point, a week after they have stopped editing … re-add the
properties to fix that one. We might want to create a new item for the shrine that they
significantly repurposed. However, that one is a bit up for debate."*

* Re-add the lost statements for 菊名神社 to **`Q134926804`** (ADD-only): the five `P825`
  deities, `P18`, `P856`, `P1329`/`P2900`, `P625`. Sourced, not restored blindly.
* Decide whether Kamo Shrine (Odawara) needs a **new item**, since `Q123044569` no longer
  represents it. Emma has flagged this as debatable.
* Consider removing the orphaned `fr`/`id` labels from the `Q28069431` husk — but that is a
  removal on an item they are active on, so it waits.

Nothing in this section is actionable until the gate opens.
