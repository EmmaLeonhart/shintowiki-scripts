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
