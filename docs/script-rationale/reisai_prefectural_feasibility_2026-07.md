# Reisai dates from the prefectural 神社庁 databases — feasibility

Measured 2026‑07‑10, before building anything. Emma chose this avenue on the strength of the
research page's claim that the 47 prefectural jinjachō "publish per‑shrine pages … many state
勧請 provenance" and, by extension, 例祭日. The numbers below are what the sites actually give.

## 1. Where we already are

`reisai.txt` holds **3,239 pending `P837` lines** harvested from jawiki, waiting only on
`conflict_gate`. Live coverage today is **197** shrine items with `P837`, out of **30,263**
`P31 = Q845945` items. So the drip alone takes coverage from 197 to roughly 3,400.

Kokugakuin cannot help: its 式内社データベース record has **no 例祭 field** (verified — the record
carries 旧郡名, 座数, 官幣・国幣, 社格, 神階の変遷, テキスト内容, 現社名など, 緯度経度).

## 2. The 47 prefectural sites are 47 different problems

`jinja-net.jp`, the platform that serves Mie, hosts exactly **two** prefectures:

| Probed | Result |
|---|---|
| `jinja-net.jp/jinjacho-mie` | **200**, structured per‑shrine records |
| `jinja-net.jp/jinjacho-kumamoto` | **200** |
| gifu · shiga · wakayama · osaka · kyoto · hyogo · okayama · hiroshima · tokyo · chiba · saitama · kanagawa · shizuoka · niigata · nagano · fukuoka | **404** |
| aichi · nara | **403** |

Probing the prefectures' own domains: `tokyo-jinjacho.or.jp`, `kanagawa-jinjacho.or.jp` and
`fukuoka-jinjacho.jp` did not resolve at all; `hyogo-jinjacho.com`, `saitama-jinjacho.or.jp` and
`aichi-jinjacho.or.jp` return a homepage with no per‑shrine index at the root. Each prefecture is
a bespoke scraper, exactly as the research page warned.

## 3. Mie is the best case, and it is thin

Mie's record has a **`主な祭典`** field. It is free text, not a date field. Sampled live:

| Shrine | `主な祭典` | Parses? |
|---|---|---|
| 鳥出神社 | `例祭8月15日　かに祭9月23日　蛭子祭7月20日` | ✅ 8/15 |
| 梶賀神社 | `例祭 4月15日` | ✅ 4/15 |
| 八幡神社 | `例祭１０月、祈年祭２月、天王祭7月` | ❌ month, no day |
| 大西神社 | `秋祭り１０月体育の日前日　八幡祭７月第４土日` | ❌ no 例祭 label |
| 島勝神社 | `１０月第２日曜（神饌に特徴あり…` | ❌ relative date |
| 尾津神社 · 愛宕社 · 黒田神社 · 大国玉神社 | *(empty)* | ❌ |

Of 9 records sampled: **5 have the field filled, 3 contain any month/day, 2 yield a clean 例祭
date.** Roughly **22%**.

`modern-quickstatements/jinjacho_reisai.py` parses exactly this shape — fullwidth digits
normalised, the date bound to the **例祭** label so a neighbouring かに祭 cannot stand in for it,
and month‑without‑day and relative dates refused. 22 tests, every fixture real.

## 4. The blocker is matching, not parsing

A jinjachō record gives a **name** and a **鎮座地**. It carries no Wikidata id. On the Wikidata
side, for Mie (`P131*` = `Q128196`):

| | |
|---|---|
| Shinto shrine items | **593** |
| distinct Japanese labels | 472 |
| **labels shared by more than one item** | **141** |
| items carrying a Japanese address to disambiguate on | **280** |
| already carrying `P837` | 10 |

So a name alone cannot identify a shrine — 八幡神社 and 神明社 recur endlessly — and fewer than
half our Mie items have an address to match against.

## 5. The arithmetic

Best case for Mie: ~280 address‑bearing items × ~22% parseable ≈ **60 statements**, for one
bespoke scraper plus a name+address matcher. Extrapolating naively across 47 prefectures gives
low thousands — comparable to the **3,239 lines the jawiki harvest already produced from a single
script that is written, tested, and waiting on the gate.**

This is not an argument that the avenue is worthless. It is an argument that it is *expensive per
statement*, that its yield is unknown for 45 of 47 prefectures, and that nothing should be built
until the already-harvested 3,239 have landed and the real remaining gap is measurable.

**Emma's decision is pending.** The parser is built and tested; no scraper exists; nothing has been
emitted.
