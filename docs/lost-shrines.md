# The three lost shrines

Three Wikidata items were **repurposed onto different subjects** during the ブルーノ・プラス
editing episode of 2026-07-10. The shrines those items used to describe now have no item
anywhere on Wikidata. This is the batch that gives them one again.

**It is not part of [`ALL.txt`](../_site/emergency-batch/ALL.txt).** Creations are a different
QuickStatements shape — `CREATE` followed by `LAST|…` lines — and have been switched off in the
past, so the file is kept separate and is registered in no `ATOMIC_FILES` list. Wiring it in is a
deliberate act, never a side effect of running the generator.

**It is additive and touches nothing.** The repurposed items are left exactly as they are. The
standing rule is *document, don't touch* and *no contact*; creating a fresh item for the shrine
that was displaced is independent of whatever becomes of the old one.

---

## What was lost

| item | described | now describes | the new item |
|---|---|---|---|
| [`Q123044569`](https://www.wikidata.org/wiki/Q123044569) | Kamo Shrine 加茂神社, Odawara | 大美和神社, at different coordinates | Kamo Shrine 加茂神社 |
| [`Q134886554`](https://www.wikidata.org/wiki/Q134886554) | Chikadono Shrine 近殿神社, Kumagaya | 近殿神社 in Yokosuka — a different prefecture | Chikadono Shrine 近殿神社 |
| [`Q134736575`](https://www.wikidata.org/wiki/Q134736575) | Kenkō-ji 見光寺, Hannō, Saitama | a different temple | Kenkō-ji Temple 見光寺 |

**Only three of the twenty-four archived items.** `modern-quickstatements/destroyed_items/` records
every item that editor damaged. Twenty-one of them were damaged *as themselves* — a property
stripped, a label removed — so they still describe the shrine they always did, and creating a
second item for one of those would be a plain duplicate. These three are different in kind: the
item was pointed at a different subject, so the original shrine was left with nothing.

## Where the content comes from

The archive stores the **pre-damage revision id**, not the content, so the labels, descriptions and
statements are read back from that revision through the API. It is the only surviving description
of these shrines.

| item | revision | dated | authored by |
|---|---|---|---|
| `Q123044569` | 2449158156 | 2025-12-30 | Peter James |
| `Q134886554` | 2386624283 | 2025-08-01 | Immanuelle |
| `Q134736575` | 2515769578 | 2026-07-10 | ブルーノ・プラス — the revision immediately before their own destructive edit |

## The references travel with the values, and that is load-bearing

近殿神社's kana reading is **`ちかどのじんしゃ`** — the じんしゃ-for-じんじゃ spelling. The standing
rule is that a **cited** reading is preserved and an **uncited** one is corrected, and this one is
cited to `houjin-bangou.nta.go.jp`, the National Tax Agency registry: it is the corporation's
legally registered フリガナ.

A first draft of the generator emitted the statements without their references. That would have put
a bare `ちかどのじんしゃ` on a brand-new item, and the next pass of the pipeline — seeing an uncited
じんしゃ — would have "corrected" a legally registered reading. **The citation is what protects the
value**, so eight of the nineteen statements carry their `S854` *reference URL* through.

## One description is deliberately dropped

見光寺's pre-damage `ja` description read 「横浜市保土ケ谷区にある浄土宗の仏教寺院」 — a temple in
Hodogaya, Yokohama — while the item's own `P131` *located in the administrative territorial entity*
(`Q850472` Hannō), its coordinates, its address and its English description all say Hannō, Saitama.
It is contradicted by every other statement on its own item, so it is not re-imported. Nothing is
invented in its place: the new item simply has no `ja` description.

## Every description has a label beside it

Wikidata's uniqueness constraint is on the **(label, description) pair**, so a description with no
label in that language stakes the half that matters least and can block the label that later
arrives — see [`description_label_policy.md`](description_label_policy.md). All eight `D` lines in
this batch have an `L` line in the same language.

## What is carried, and what is not

`CARRY` is a whitelist of eight properties:

`P31` *instance of* · `P17` *country* · `P131` *located in the administrative territorial entity* ·
`P625` *coordinate location* · `P825` *dedicated to* · `P6375` *street address* ·
`P1814` *name in kana* · `P1448` *official name*

Four properties present on the pre-damage items fall outside it and are **not** re-asserted:
`P281` *postal code*, `P3225` *Corporate Number (Japan)*, `P1454` *legal form*, and
`P10689` *OpenStreetMap way ID*. Identifiers tying the record to the old item are excluded on
purpose — the new item is a new record of the same shrine, not a clone, and re-asserting an
external id that now resolves to the repurposed subject would propagate the damage.

---

## The batch

`modern-quickstatements/lost_shrine_creates.txt` — **3 creations, 12 labels, 8 descriptions,
19 statements**, 42 non-blank lines.

```
CREATE
LAST|Lde|"Kamo Schrein"
LAST|Len|"Kamo Shrine"
LAST|Lfr|"sanctuaire de Kamo"
LAST|Lid|"Kuil Kamo"
LAST|Lja|"加茂神社"
LAST|Dde|"Shinto-Schrein in Odawara, Kanagawa, Japan"
LAST|Den|"Shinto shrine in Odawara, Kanagawa, Japan"
LAST|Did|"kuil Shinto di Prefektur Kanagawa, Jepang"
LAST|Dja|"小田原市にある神社"
LAST|P31|Q845945
LAST|P31|Q137640533
LAST|P17|Q17
LAST|P131|Q267258
LAST|P625|@35.27712826106289/139.17583480745927
LAST|P825|Q11634943
LAST|P6375|en:"708 Kamonomiya, Odawara, Kanagawa 250-0874, Japan"

CREATE
LAST|Len|"Kenkō-ji Temple"
LAST|Lid|"Wihara Kenkō-ji"
LAST|Lja|"見光寺"
LAST|Den|"Buddhist temple in Hannō, Japan"
LAST|P31|Q5393308
LAST|P17|Q17
LAST|P131|Q850472|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"
LAST|P625|@35.838036/139.337402|S854|"https://geocode.csis.u-tokyo.ac.jp/home/simple-geocoding/"
LAST|P6375|ja:"埼玉県飯能市岩沢1092"|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"
LAST|P1814|"けんこうじ"|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"

CREATE
LAST|Len|"Chikadono Shrine"
LAST|Lfr|"sanctuaire de Chikadono"
LAST|Lid|"Kuil Chikadono"
LAST|Lja|"近殿神社"
LAST|Den|"Shinto shrine in Saitama Prefecture, Japan"
LAST|Did|"kuil Shinto di Prefektur Saitama, Jepang"
LAST|Dja|"埼玉県熊谷市下増田にある神社"
LAST|P31|Q845945
LAST|P17|Q17
LAST|P131|Q41106|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"
LAST|P625|@36.209057/139.336243|S854|"https://geocode.csis.u-tokyo.ac.jp/home/simple-geocoding/"
LAST|P6375|ja:"埼玉県熊谷市下増田749"|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"
LAST|P1814|"ちかどのじんしゃ"|S854|"https://www.houjin-bangou.nta.go.jp/download/zenken/index.html"
```

**The item values, spelled out:** `Q845945` *Shinto shrine* · `Q137640533` *Kamo shrine* (the
shrine-type item) · `Q5393308` *Buddhist temple* · `Q17` *Japan* · `Q267258` *Odawara* ·
`Q850472` *Hannō* · `Q41106` *Kumagaya* · `Q11634943` *Kamo Wake-ikazuchi*, the enshrined deity.

## The gate

`modern-quickstatements/lost_shrine_gate.py` decides whether this may run. It **carries no date of
its own** — deliberately, because a freeze duplicated per-file is a freeze one file can miss. It
asks two things, and any error fails closed:

1. **The Wikidata lockout**, via `shinto_miraheze/wikidata_editing_lockout.state`. That one state
   file is the single authority for every write path in the repo.
2. **The conflict gate** — the ブルーノ・プラス caution window the daily drip also consults. It
   matters more here than anywhere: this batch exists *because* of that editor, and creating
   replacements while they are actively editing is precisely the visibility that ranks as worse
   than data loss.

Emma registered the batch on 2026-08-24 to deliver on **2026-09-18**, and registration was
implemented as *"when the lockout lifts"* rather than as that date. The lockout's `locked_until`
was moved to **2026-09-01** on 2026-09-06, so **the gate now reports open** — CI at 21:20Z that
day: `open: wikidata lockout clear and conflict_gate clear`. Nothing has run it; whether it should
go now or wait for the 18th is a decision, not a bug.

## Regenerating

```
python modern-quickstatements/generate_lost_shrine_creates.py
```

This is also what re-checks that the three shrines still have no item: there is no duplicate guard
at run time, by instruction. The original check is in
[`bruno_plus_analysis_2026-07.md`](bruno_plus_analysis_2026-07.md) §4 — none of the eight 加茂神社
items is the Odawara one, no item holds Chikadono any more, and 見光寺's item now asserts a
different temple.
