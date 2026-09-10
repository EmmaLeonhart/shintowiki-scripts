# Deriving P1814 for every en-labelled shrine — the measurement, 2026-09-10

Emma, 2026-09-09: *"Realistically, all of the shrines should have proper Kana names derived from
the Japanese put in them."*

This records how accurate that derivation actually is, because it turned out to be measurable
rather than a matter of opinion, and the measurement changed the design twice.

## The population

**16,753** shrines (`P31 = Q845945`) carry a Japanese label and an English label and have no
top-level `P1814` at all. That is the target set of `generate_derived_name_in_kana.py`.

The derivation is the existing `english_to_kana` — English label supplies the romanized stem, the
kanji label picks the shrine-type suffix — the same one `generate_katakana_reading_add.py` already
uses on four items. It refuses **4,810** of the 16,753 outright:

| refusal | n |
|---|---|
| en label does not end in the expected shrine word | 2,202 |
| ja label has no known shrine-type suffix (大社, 神宮, 〜神 are all deliberately absent) | 1,492 |
| multi-word stem — a gloss, not a single romanized name | 525 |
| stem will not romanize — an English word in the stem position | 416 |
| the shrine word alone, nothing left to romanize | 175 |

## The held-out set

**5,781 shrines carry BOTH an English label and a real `P1814`.** Deriving those and comparing
against the reading they already have says exactly how often the derivation is right. Nothing about
this needed jawiki, an LLM, or a judgement call.

### First result: 86.1%, and 63% of the errors were one bug

804 mismatches. **506 of them — every single macron-bearing derivation — were wrong**, because
`_MACRONS` collapsed `ō` to `o`:

    大神神社 / "Ōmiwa Shrine"   ->  おみわじんじゃ      actual おおみわじんじゃ
    東郷神社 / "Tōgō Shrine"    ->  とごじんじゃ        actual とうごうじんじゃ
    五條山天神社 / "Gojōzan …"  ->  ごじょざんてんじんじゃ  actual ごじょうざんてんじんじゃ

The macron is the label writing the vowel length **down**; collapsing it threw away the one piece of
information that was not lost. `expand_long_vowels` now expands it — `ō` → `おう`, `ū` → `うう`,
`ā`/`ī` → `ああ`/`いい`.

`ō` is the only ambiguous one, and the おお-vs-おう split was **tabulated, not guessed**: of the
held-out shrines whose English stem starts `Ō`, the leading kanji 大 (130), 太 (7), 意, 於, 青, 相,
小, 鷲 read おお, while 王 (9), 淡, 扇 read おう. `_OO_INITIAL` is that list. 皇 splits 1/1 and stays
on the おう default.

`ā` and `ī` are not long vowels in these labels at all — they mark a vowel **collision** at a
morpheme boundary (三島愛宕 / "Mishimātago" = みしま + あたご). `aa`/`ii` is right either way.

**After the fix: 93.5%.**

### Second result: the name-mates split the remainder sharply

Emma's own rule (`kana_name_mate_rulings.md`) is that *"the dominant hiragana reading wins and is
applied to every blank on that pair"* — items with the identical Japanese label vote on the reading.
That is a second, independent source, and splitting the held-out set by whether it agrees separates
the derivation's quality much more than anything about the derivation itself does:

| tier | test | n | precision |
|---|---|---|---|
| 1 | derived == the dominant name-mate reading | 3,190 | **97.74%** |
| 2 | no name-mate carries any reading — nothing to check against | 2,117 | **93.86%** |
| 3 | a name-mate reading exists and CONTRADICTS the derivation | 474 | **64.35%** |

Tier 1's real precision is **higher than 97.74%**, because a chunk of its "errors" are cases where
the existing value is the known-wrong one that `kana_name_mate_rulings.md` already rules on — じんしゃ
for じんじゃ (采女神社, 氷川神社, 八幡神社, 道祖神社), a truncated はちまん, a truncated ちかつ.

The name-mate rule **on its own** is worse than the derivation: 89.35% leave-one-out, 90.66%
restricted to unanimous mates. It is valuable as a *check*, not as a source.

## Emma's call, 2026-09-10

**Ship tiers 1 and 2 — 7,596 + 2,992 = 10,588 lines. Route tier 3 to the LLM queue.**

Tier 3 is 1,348 items, and the disagreements are real rather than noise:

| ja | en | derived | name-mates |
|---|---|---|---|
| 倭文神社 | Shitori Shrine | しとりじんじゃ | しどりじんじゃ |
| 神門神社 | Mikado Shrine | みかどじんじゃ | ごうどじんじゃ |
| 一宮神社 | Ikku Shrine | いっくじんじゃ | いちのみやじんじゃ |
| 建勲神社 | Kenkun Shrine | けんくんじんじゃ | たけいさおじんじゃ |
| 鹽竈神社 | Shigama Shrine | しがまじんじゃ | しおがまじんじゃ |

`build_kana_disagreement_queue.py` writes these into `name_in_kana/` work-files naming **both**
candidates, so the cloud routine reads the jawiki lead and picks. The lead usually settles it at
once — 倭文神社's first sentence is `倭文神社（しとりじんじゃ/しずりじんじゃ）`, i.e. the derivation was
right and the name-mates were wrong.

⚠ This is the **one** place an en-labelled shrine legitimately goes back to an article. CLAUDE.md's
*"do not try to reason about what the KANA reading would be on something with an English label"* is
about deriving a reading the label already carries. Here the label's reading has been derived and
the project's own data contradicts it, which is not a case that rule contemplates. Emma decided it
directly.

## Held: 天神社 + "Tenjin Shrine"

Seven items. Both てんじんじゃ and てんじんしゃ are attested per item, the English labels came from one
bulk batch and carry no per-item information, and `kana_name_mate_rulings.md` settles the pair from
jawiki as てんじんしゃ with てんじんじゃ correct only where the National Tax Agency registered it that
way. An item with no reading gives no way to tell. `"Tenjin-sha"`/`"Tenjinsha"` labels are **not**
held — jawiki backs てんじんしゃ and the label agrees.

## What cannot be fixed from a label

The residual 6.5% is mostly three shapes, and only the first is a candidate for further work:

* **192 different reading entirely** — the English label is a different naming from the kana.
  往馬坐伊古麻都比古神社 is labelled "Ikoma Shrine" but reads いこまにいますいこまつひこじんじゃ;
  賀茂別雷神社 is "Kamigamo Shrine" but reads かもわけいかづちじんじゃ. Nothing in the label points at
  this.
* **126 long vowel only** — a *macron-free* label that had a long vowel: "Ichijo Shrine" for
  いちじょう, "Tokyo Daijingu" for とうきょう. Unrecoverable by construction; this is the known loss.
* **53 ず/づ or じ/ぢ** — 焼津 やいづ romanizes to "Yaizu" and comes back as やいず. Rendaku on
  津/鶴/積 is the usual cause.

## Add-only

The target query requires `NOT EXISTS { ?item wdt:P1814 ?any }`. Nothing here can overwrite a
name-mate ruling, one of the 4,764 NTA-registered readings, or a katakana value the カミノヤシロ
pipeline is still relocating — by construction, not by a filter someone has to keep in step.
