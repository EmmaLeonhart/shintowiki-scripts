# Kana from name-mates — Emma's rulings, 2026-08-24

Live record of the pair-by-pair decisions. Method and population:
`modern-quickstatements/report_en_label_without_kana.py`.

## General rules she has given

- **The dominant hiragana reading wins** and is applied to every blank on that pair.
- **`じんしゃ` for `じんじゃ` is a typo** — corrected, not preserved. Applied universally.
  (`すわじんしゃ` ×11, `いなりじんしゃ` ×2, `はちまんじんしゃ` ×4, `あたごじんしゃ` ×1, `ひかわじんしゃ` ×1.)
- **Other clear typos are corrected the same way**: `しんんめいぐう` → `しんめいぐう`, and a
  reading containing a space (`くまの じんじゃ`) → no space.
- **A truncated lone form is completed**: `はちまん` → `はちまんじんじゃ`.
- **The ending is part of the name.** `社` ≠ `神社` ≠ `宮`: `諏訪社` is `すわしゃ`, `諏訪神社` is
  `すわじんじゃ`. A `宮` reading sitting on a `神社` item is an error of the same class as a typo.
- **Katakana readings are NOT ours to touch.** Her words: *"the pipeline should already be
  stripping the katakana and putting it as a qualifier on the official name, at which point the
  pipeline would just put in the proper name."* They must stay in place until that happens —
  removing them early would lose the reading before it reaches the official name.
  - ⚠ **Unresolved:** on 八幡神社 she wrote *"other katakana variants should have the english names
    stripped so the pipeline applies their proper names to them"*, and on 神明社 *"no the english
    label is not stripped lol, katakana does not strip english labels"*. I read the second as
    overturning the first; she says she does not know what is being superseded. **Not acted on
    either way.**
  - She is *"not 100% sure the degree it is happening correctly"* — so whether the kana-qualifier
    pipeline actually relocates these is itself unverified.

## Settled pairs

| pair | ruling |
|---|---|
| 諏訪神社 / Suwa Shrine | `すわじんじゃ`; overwrite `すわじんしゃ`; leave the katakana to the pipeline |
| 八幡神社 / Hachiman Shrine | `はちまんじんじゃ`; fix `はちまんじんしゃ`; `はちまん` → `はちまんじんじゃ` |
| 稲荷神社 / Inari Shrine | `いなりじんじゃ`; fix `いなりじんしゃ` |
| 熊野神社 / Kumano Shrine | `くまのじんじゃ`; the spaced one corrected |
| 八幡宮 / Hachimangū | `はちまんぐう` for all |
| 神明社 / Shinmei-sha | `しんめいしゃ` — *"this is not even question"* |
| 神明宮 / Shinmei-gū | `しんめいぐう`; `しんんめいぐう` is a typo, rule applied universally |
| 諏訪社 / Suwa Shrine | `すわしゃ`; correct by default, she will say if she disagrees after seeing the outlier |

## 天神社 / Tenjin-sha — RESOLVED by jawiki, after two wrong theories (mine and hers)

Her hypothesis: *"I think Tenjinja is an erroneous one that came from a typo in one of my scripts
that applied the label."* **The revision history says otherwise.**

`てんじんじゃ` ×47 and `てんじんしゃ` ×19 were set **by both editors, in the same batches, minutes
apart**:

    Higa4       2025-06-02 14:03  てんじんじゃ   読み仮名を登録
    Higa4       2025-06-02 14:03  てんじんしゃ   読み仮名を登録
    Higa4       2025-06-02 14:06  てんじんじゃ   読み仮名を登録
    Immanuelle  2025-06-27 02:39  てんじんじゃ
    Immanuelle  2025-06-27 02:45  てんじんしゃ

A script typo produces ONE reading uniformly across a batch. This is one editor in one sitting
assigning different readings to different shrines — and `Higa4` is a third party, with the summary
読み仮名を登録 ("registering the reading"), which reads as deliberate per-item work.

So the reading varies per shrine. 47/19 is not a dominant reading with a typo tail; it is two real
readings, and the 167 blanks on this pair must not be filled from a majority.

## Items she asked to see

- `Q101781998` 諏訪社 / `すわじんじゃ` — the odd one out on that pair
- `Q135260029`, `Q135259820` 八幡宮 / `はちまんじんじゃ` — adjacent QIDs, likely one import block
- `Q11590316` 神明神社 / `しんめいぐう`, `Q135464105` 神明神社 / `しんめいしゃ` — wrong-ending cases
- `Q135935015` 春日神社 / `カスガジンジャ` — modern reading in katakana, not an Old Japanese one.
  Her ruling: *"force open, if I say nothing then overwrite it."*


## ⭐ THE DECIDING RULE — the NTA citation, not how the reading looks (Emma, 2026-08-24)

She looked at the two 八幡宮 outliers and found the answer: *"this one is weird it has citations
indicating the mistake might be legally binding. I would even want to put some sort of 'sic' on it
as a qualifier or something. I think this is right to preserve."*

Both are sourced to **`houjin-bangou.nta.go.jp`** — Japan's National Tax Agency **corporate-number
registry**, which records a religious corporation's registered name *and its registered フリガナ*.
So はちまんじんじゃ on a 八幡宮 is not our error; it is what the corporation is legally registered as.

**Her ruling: PRESERVE, BUT MARK THEM.** Preserve every NTA-sourced reading, and flag the odd ones
so they read as deliberate rather than as our mistakes.

**⚠ This overturns three rulings she gave twenty minutes earlier, and the numbers are why.** The
"clear typos" she told me to overwrite are mostly legally registered:

| reading | items | NTA-sourced |
|---|---|---|
| すわじんしゃ | 11 | **11** |
| しんんめいぐう | 1 | **1** |
| はちまん | 1 | **1** |
| はちまんじんしゃ | 5 | 4 |
| いなりじんしゃ | 4 | 2 |
| あたごじんしゃ | 1 | 1 |
| ひかわじんしゃ | 1 | **0** |
| くまの じんじゃ | 1 | **0** |
| カスガジンジャ | 1 | **0** |

**4,764 `P1814` statements across 4,763 items** carry that citation. Overwriting them by name-mate
majority would replace legally-registered readings with a guess — the largest destructive risk this
programme has.

**The rule predicts her judgement.** She ruled on four items independently and the citation matched
every time:

| item | reading | NTA | her ruling |
|---|---|---|---|
| `Q135259820`, `Q135260029` 八幡宮 | はちまんじんじゃ | yes | *"right to preserve"*, sic |
| `Q135464105` 神明神社 | しんめいしゃ | yes | *"an erroneous legal registration so a sic thing"* |
| `Q11590316` 神明神社 | しんめいぐう | yes | not yet ruled — predicted sic |
| `Q101781998` 諏訪社 | すわじんじゃ | **no, no refs at all** | *"should have the kana fixed, it appears to be just an error"* |
| `Q135935015` 春日神社 | カスガジンジャ | **no, no refs at all** | *"this one in katakana is just an error"* |

So: **cited to the registry → preserve and mark. No citation → fix.**

### The "sic" marker — there is no sanctioned property, and I am not inventing one

Checked rather than guessed. `Q192003` "sic" is the **Latin adverb**, not a Wikidata workflow item,
and there is no property meaning "this is wrong but the source says it".

The nearest legitimate mechanism is **`P1932` "object named as"** — *"use as qualifier to indicate
how the object's value was given in the source"*. That is a **reference** qualifier and it says only
"the source wrote it this way", not "and that is wrong". `P7452` (reason for preferred rank) and
`P2241` (reason for deprecated rank) both exist but both change a statement's rank, which is a
bigger claim than she asked for.

⛔ **NEEDS-DECISION before anything is written**, and nothing can be delivered before the Wikidata
lockout lifts on 2026-09-18 in any case.

### And it independently settles 天神社

`てんじんじゃ` is **44 of 47** NTA-sourced; `てんじんしゃ` is **11 of 19**. Both readings are legally
attested, which is exactly why the 2025-06-02 batch alternates between them minutes apart. The pair
must not be majority-filled — confirmed twice now, by two different methods.


## 天神社, finished — and it took an outside source, not more Wikidata

Emma: *"do a bit more research on Tenjinja vs Tenjinsha in ones without kana to make a decision on
which way to go. Like more research not just wikidata surveying lol."* She was right that surveying
our own data could not settle it. **jawiki's article on 天神社 states the answer in its first
sentence:**

> 天神社（**てんじんしゃ**）は、「天神社」の社名を持つ神社。読みには「**てんじんしゃ**」、
> 「**あまつかむやしろ**」などがある。

**てんじんしゃ, with あまつかむやしろ as a documented alternative. てんじんじゃ is not listed at all.**

**Three theories died getting here, in order:**

1. *Hers:* てんじんじゃ came from a typo in one of her own scripts. **No** — the revision history
   shows both readings set by both editors in the same batches minutes apart, which is per-item work.
2. *Mine:* the typo was in the ENGLISH, since "Tenjin-sha" on all 232 came from one QuickStatements
   batch (`#temporary_batch_1753098414048`, 2025-07-21). **Also no** — that bulk label matches
   jawiki exactly. It was right by default; it is only wrong on the items registered as じゃ.
3. *Hers, second:* trust the English where it reads Tenjin-sha and generate kana from it. Circular
   as stated — the label was never per-item — but it lands on the right answer anyway, because the
   label happens to agree with jawiki.

**The settled picture:**

| group | count | disposition |
|---|---|---|
| no reading, label `Tenjin-sha` | 167 | fill with **てんじんしゃ** — jawiki-backed, matches the label |
| reading てんじんじゃ, NTA-sourced | 43 | **preserve the reading**, fix the ENGLISH to `Tenjinja` |
| reading てんじんじゃ, unsourced | 3 | no citation — fixable to てんじんしゃ under the uncited rule |
| reading てんじんしゃ | 19 | correct already, nothing to do |
| あまつかむやしろ | 1 | **legitimate** — jawiki lists it. I had been treating it as noise. |

- ▶ Her instruction stands: **fix the English from the kana** where a reading exists.
- ⚠ Nothing staged. Wikidata lockout to 2026-09-18.


## Omitting the word "shrine" — Emma, 2026-08-24, and it is NOT the sic rule

> *"Anything with a name in Kana that just omits the word 'shrine' should have the word 'shrine'
> put into it. The ones that seem like they're spelling mistakes or something like that, if they
> have citations, we don't do it."*

So an **omission** is repaired even when cited; a **spelling difference** that is cited is preserved
as sic. Two different faults, two different dispositions.

**Measured: 57 items** whose ja label ends in a shrine word (神社/神宮/大社/八幡宮/天満宮) but whose
reading does not end in any shrine-word reading. **9 are NTA-sourced.**

⚠ **But only some are omissions, and a bulk pass would corrupt the rest.** Four shapes are mixed in:

| shape | example | disposition |
|---|---|---|
| genuine omission | 八幡神社 → `はちまん` *(NTA)* | **her rule applies** — add じんじゃ, citation notwithstanding |
| **historical kana** | 福岡縣護國神社 → `ふくをかけんごこくじんじや` | ⛔ NOT an omission. `じんじや` is 旧仮名遣い for `じんじゃ` — the shrine word is already there, in old orthography. Also 宗我坐宗我都比古神社, 平群坐紀氏神社, 萬四郎神社. |
| truncated katakana | 磐椅神社 → `-サキ` | the kana-qualifier pipeline's population; leave it |
| **wrong value entirely** | 一之宮神社 → `スサノオ` (a deity), 駒形嶽駒弓神社 → `お` (one character), 吉沼八幡神社 → `つくば` (a place) | ⛔ appending じんじゃ produces nonsense. These are wrong *fields*, not short readings. |

- ▶ The rule is right; the **selector** is what needs care. Matching on "does not end in a shrine
  reading" catches all four shapes, and three of them must not be touched.
- A correct selector has to treat `じんじや` / `しや` / `ぐう` in historical orthography as complete,
  exclude anything already carrying the hyphen signature, and exclude values that are not readings
  of the name at all.
- NEEDS-DECISION on the wrong-value ones — `スサノオ` on 一之宮神社 is a deity in a reading field,
  which is a different defect worth its own look.


## Spaces, shrine words, and katakana — Emma, 2026-08-24 (closing the collision)

> *"you need a gazillion different shrine words there but really anything with us there shouldn't be
> a space in it. Anything that's in the katakana should be removed by our pipeline."*

**Spaces: there is no case where a reading contains one.** Not a judgement about which reading is
right — a kana reading of a shrine name simply has no space in it. So the earlier collision between
"correct the spaced ones" and "preserve the katakana ones" was not a collision at all: **remove the
space, and the value still goes to the pipeline as katakana.** Both rules apply to the same item and
they do not conflict.

Five items carry one, three of them the same value: `イハタノ イシタ` on three separate 石田神社
(`Q135068851`, `Q135068853`, `Q135270104`), plus `ヲチカハノ オチカハ` (`Q135038757`) and
`アナフキノ フエフキ` (`Q135038817`). She had seen "only two such ones" — that is 3 distinct patterns.

**Shrine words: my selector was far too narrow, and it produced false positives on correct data.**
It knew じんじゃ / じんしゃ / じんぐう / たいしゃ / ぐう / しゃ / みや and nothing else, so it
flagged six items whose readings end in **やしろ** — which IS 社 — including **出雲大社 →
いずもおおやしろ**, which is simply correct. Any future selector needs the full set: やしろ, みや,
ぐう, じんぐう, たいしゃ, おおやしろ, かみのやしろ, the historical じんじや / しや forms, and the
katakana equivalents.

**Katakana: preserve, and the pipeline is supposed to remove them over time** — *"they need to be
removed by the right part of the timeline"*. Whether it actually does is now its own queue item,
because every katakana ruling today rests on it.

⚠ **This splits the katakana rule in two, and both halves are hers:**
- **Old Japanese katakana readings** (`ツノサリ-`, `-トヨタマヒメノ`) → preserve for the pipeline.
- **A modern reading merely typed in katakana** (`カスガジンジャ`, `Q135935015`) → *"this one in
  katakana is just an error"*. Not the pipeline's; fix it.


## A wrong reading takes every non-Japanese label with it — `Q97162781`, 2026-08-24

Emma, looking at it: *"all non-Japanese names are wrong"*, then *"name in Kana is wrong too for
that one"*. Both true, and the second causes the first.

[`Q97162781`](https://www.wikidata.org/wiki/Q97162781) is **若林八幡宮**, which reads
**わかばやしはちまんぐう**. What it actually carries:

| lang | value | |
|---|---|---|
| ja | 若林八幡宮 | ✅ the only correct field |
| `P1814` | ほむたわけのみこと | ❌ the enshrined deity, not the shrine |
| en | Homutawakenomikoto | ❌ romanised from the bad reading |
| fr | sanctuaire d'Homutawakenomikoto | ❌ |
| id | Kuil Homutawakenomikoto | ❌ |

**The cascade is the point.** The reading is the root, and every other language was generated from
it, so one bad `P1814` produced three bad labels. **Fixing the reading alone leaves the item wrong
in three languages** — the labels have to be regenerated from the corrected reading. Any repair pass
that touches `P1814` has to say what happens to the derived labels.

It also earns its fix cleanly: that reading carries **no references at all**, so the uncited rule
applies without touching the NTA question.

### The deity signature is nearly useless as a selector — 2 of its 3 hits are correct

Searching for readings ending in のみこと / のかみ / ノカミ found **3** items, and **two are right**:

- `Q17211756` 御酒殿**神** → みさかどのの**かみ** — the shrine is literally named 〜神
- `Q6543779` 四至**神** → ミヤノメグリノ**カミ** — same
- `Q97162781` 若林八幡**宮** → ほむたわけのみこと — **the only real defect**

A deity-shaped reading is only suspicious when the item's own name does **not** end in 神. Third
selector today to report correct data as broken by not knowing the domain — after the shrine-word
list that did not know やしろ, and the mismatch detector that did not know jawiki's disambiguation
convention.
