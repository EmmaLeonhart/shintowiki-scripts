# Katakana in top-level `P1814` — the whole population, measured 2026-09-09

Emma, 2026-09-09, correcting what her queue note meant: *"When I said the katakana should be
replaced, this is something that very specifically refers to katakana that are in the raw name,
as Kana category. The raw name is Kana, as a top-level property. I don't think there are that
many that have katakana there anymore."*

She is right about the size. **27 statements on 26 items.**

## The measurement

One SPARQL query over `?item wdt:P31 wd:Q845945` with `p:P1814`, filtered client-side for values
carrying katakana and no hiragana (Blazegraph has no `\p{IsHiragana}`).

| | |
|---|---|
| shrine `P1814` statements in total | 9,314 |
| katakana-only values | 772 |
| …on items that carry an **ojp-hani `P1448`** | 745 |
| …on items that do **not** | **27** |

The 745 are the カミノヤシロ kana-qualifier pipeline's own population — Old Japanese readings it
relocates onto the ojp-hani official name and then strips from top-level. They are not this job.

The 27 are what is left over. ~~Nothing in the repo can reach them~~ — see the correction below.

## ⛔ CORRECTION, 2026-09-10 — "nothing can reach them" was wrong for 15 of the 27

The claim above was that these items have no ojp-hani `P1448`, so no generator in the kana-qualifier
pipeline can select them. The first half is true and the conclusion does not follow.

**Every one of the 15 hyphen-bearing items links to its Engishiki entry item with `P460`, and every
one of those entry items carries the ojp-hani `P1448`.** The reading sits on the 論社; the official
name sits on the entry. That is the correct modelling, and the same shape as CLAUDE.md's
list-membership rule — the Engishiki-era facts belong to the entry item and the candidate points at
it with `P460`.

**And the entry items ALSO carry the same katakana at top level**, which is what makes the pipeline
reach them after all: `generate_kana_qualifier_add.py`'s SEED branch selects on
*(ojp-hani name, no `P1814` qualifier, top-level katakana on the same item)*, and the ENTRY satisfies
all three. Its seven lines were already in `kana_qualifier_add.txt` before anyone looked. A `P460`
branch written for the add generator on 2026-09-10 produced a byte-identical file and was deleted as
dead code.

Measured across the 15, by their `P460` target:

| state of the entry item's ojp-hani `P1448` | 論社 | disposition |
|---|---|---|
| already carries `<that exact reading>カミノヤシロ` | 4 items / 5 statements — 博西, 飛鳥川上坐宇須多伎比賣命, 健御名方富命彦神別 (×2), 伊勢御祖 | the top-level copy on the 論社 is **already redundant** |
| carries the ojp-hani name, **no** kana qualifier yet | 8 items / 7 distinct values | SEED already emits the add; nothing new needed |
| carries a **different** reading | 3 items | ⛔ leave alone — see below |

**So the only thing genuinely unreachable is the REMOVAL.** `generate_kana_qualifier_remove.py`'s
top-level branch requires the ojp-hani name and the top-level katakana on the same item, so a 論社's
own copy is never removed however long the entry has carried the relocated reading. That branch —
and only that branch — is what this job adds, mirroring the add side across the `P460` hop with an
exact-value confirmation.

### ⛔ The three where the entry carries a different reading

| 論社 | its reading | `P460` entry | the entry's reading |
|---|---|---|---|
| `Q135040970` 天若日子神社 | `-アメワカヒコノ` | `Q135040959` 阿須伎神社 | `アスキノ` |
| `Q135041051` 韓國伊太弖奉神社 | `-イタテ-` | `Q135041050` 曽枳能夜神社 | `ソキノヤノ` |
| `Q135199795` 銀山神社 | `シロカネ-` | `Q135041546` 銀山上神社 | `カナヤマノヘノ` |

In the first two the 論社's reading belongs to a **同社坐 sub-entry** — 出雲's jawiki list carries
`同社坐天若日子神社` and `同社坐韓国伊太弖奉神社` as their own 神名帳 rows — and that sub-entry has no
item of its own, so `P460` points at the parent shrine instead. In the third, 対馬's list carries
`銀山神社` (シロカネ-) and `銀山上神社` (カナヤマノヘノ) as two separate entries and the `P460` points
at the wrong one.

Appending the 論社's reading to the name that IS there would attach a reading to a name it is not the
reading of. The `NOT EXISTS ?st pq:P1814` guard in the add generator already excludes all three, and
the remove generator's exact-value confirmation cannot match them. **Left alone deliberately;** the
`P460` on `Q135199795` looks like a genuine mis-link worth a separate look.

### Where the katakana and the hyphen come from

jawiki's per-province `…国の式内社一覧` pages are the source, and they explain the shape exactly. The
神名帳 column gives each entry's 社名 and its 読み in katakana — `健御名方富命彦神別神社 /
タケミナカタトミノ- / タケミナカタトム-` is verbatim `Q135069835`'s two values — and the page's own
legend says what the hyphen is:

> 読みの「-」部分は、「神社」以外で仮名が振られていない部分。

So `-シトリ-ハツチノ-` is 葛木(-)倭文(シトリ)坐(-)天羽雷命(ハツチノ)神社: the hyphens mark the parts
the source left un-kana'd. They are not truncation damage.

## The 27

Every one of these items **already has an English label**, which is why they are a derivation job
and not a research job — CLAUDE.md: *"the English label IS the KANA reading"*, and where a kana
value is wanted on such an item it is derived mechanically from the English label plus the shrine
suffix taken from the Japanese.

`refs` is references on the `P1814` statement itself.

### Hyphen-bearing Old Japanese fragments — 17

The trailing or leading `-` is the truncation signature of the ancient-reading import. These are the
same shape as the pipeline's 745, stranded on items with no ojp-hani name to move them to.

| item | value | refs | ja label | en label |
|---|---|---|---|---|
| Q135040970 | `-アメワカヒコノ` | 2 | 天若日子神社 | Amewakahikono Shrine |
| Q135041051 | `-イタテ-` | 2 | 韓國伊太弖奉神社 | Karakuniitatematsuruno Shrine |
| Q135069027 | `-シトリ-ハツチノ-` | 2 | 博西神社 | Hakanishi Shrine |
| Q135069118 | `アスカカハカミ-` | 2 | 飛鳥川上坐宇須多伎比賣命神社 | Asukakawakamizausutakihimeinochi Shrine |
| Q135069520 | `アナサハノ-` | 2 | 穴沢天神社 | Anazawa Tenjin Shrine |
| Q135069835 | `タケミナカタトミノ-` | 2 | 健御名方富命彦神別神社 | Takeshigyomeihoutomiinochihikoshinbetsu Shrine (Shinano Province) |
| Q135069835 | `タケミナカタトム-` | 2 | ″ | ″ |
| Q135069939 | `モロヲカ-` | 1 | 諸岡比古神社 | Morookahiko Shrine |
| Q135070107 | `-カラクニイタテノ` | 2 | 嘉羅久利神社 | Karakuri Shrine |
| Q135070108 | `-カラクニイタテノ` | 2 | 佐久多神社 | Sakuta Shrine |
| Q135070193 | `タツチウラノ-` | 2 | 高島神社 | Takashima Shrine |
| Q135070346 | `-アマテラスミオヤノ` | 2 | 伊勢御祖神社 | Ise Mioya Shrine |
| Q135193006 | `-オホトシノ` | 2 | 神明神社 | Shinmei Shrine |
| Q135193011 | `-オホトシノ` | 2 | 伊那上神社 | Inakami Shrine |
| Q135198701 | `-オホクニタマノ` | 2 | 嶋大國魂御子神社 | Shima Okunitama Miko Shrine |
| Q135198701 | `-オホクタマ` | 2 | ″ | ″ |
| Q135199795 | `シロカネ-` | 2 | 銀山神社 | Ginzan Shrine |

Two items carry **two** such values (Q135069835, Q135198701).

### No hyphen — 10

| item | value | refs | ja label | en label | note |
|---|---|---|---|---|---|
| Q10928586 | `イカスリノミカンナギノマツルカミ` | 1 | 座摩神 | Ikasuri no Kami | |
| Q11352355 | `スサノオ` | 0 | 一之宮神社 | Ichinomiya Shrine Yokohama | ⛔ **a deity in a reading field** — already flagged in `kana_name_mate_rulings.md` as a wrong *field*, not a short reading |
| Q11430613 | `タクツノ` | 1 | 多久頭魂神社 | Takuzudama Shrine | |
| Q11444481 | `フトノトノ` | 1 | 太祝詞神社 | Futonorito Shrine | |
| Q11474068 | `ミユノ` | 1 | 岩井温泉 | Iwai Onsen | ⚠ an **onsen**, not a shrine, and it already carries `いわいおんせん` — the only item here with a hiragana sibling |
| Q135069931 | `カサノノ` | 1 | 笠野神社 | Kasano Shrine | pair with the next; see the duplicate-QID note in CLAUDE.md |
| Q135069932 | `カサノノ` | 1 | 笠野神社 | Kasano Shrine (Kaga Province) | ″ |
| Q135195212 | `イソヘノ` | 0 | いそ部神社 | Isobe Shrine (Miwakare Park) | |
| Q135935015 | `カスガジンジャ` | 0 | 春日神社 | Kasuga Shrine | ⭐ **already ruled** — Emma, 2026-08-24: *"this one in katakana is just an error"* → かすがじんじゃ |
| Q6543779 | `ミヤノメグリノカミ` | 1 | 四至神 | Miyanomeguri-no-Kami | ✅ **correct as it stands** — the shrine is literally named 〜神; `kana_name_mate_rulings.md` establishes this |

So of the ten, one is already ruled a fix, one is already ruled correct, one is a wrong field, and
one is not a shrine. **Six are ordinary derivation work.**

## How a replacement is expressed

A top-level `P1814` is its own statement, so replacing it is two whole-statement operations, which
QuickStatements can do — unlike the qualifier case that destroyed four official names the same day
(DEVLOG 2026-09-09). It still has to follow the repo's **add-first, remove-later, two scripts, never
one** rule: script 1 adds the derived hiragana; script 2 removes the katakana value *only* where a
fresh SPARQL confirms the hiragana has landed. Under the drip's random order, a single add+remove
file could run the remove first and leave the item with no reading at all.

⚠ 22 of the 27 statements carry references, and a removal takes them. That is correct here — they
reference the katakana value, which is the thing being retired — but it means the added hiragana
statement needs its own reference rather than inheriting one.
