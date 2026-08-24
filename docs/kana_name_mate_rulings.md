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

## 天神社 / Tenjin-sha — DO NOT majority-fill. Investigated, hypothesis disproved.

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
