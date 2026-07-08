# jawiki infobox import review — shrines, temples, kofun (2026-07-08)

Emma's wiki-queue ask: comprehensively review the jawiki infoboxes for Buddhist
temples and Shinto shrines (+ kofun) for anything more we can import onto
Wikidata — existing properties or creative repurposing (as the reisai P837
import did). Parameter sets pulled live from the templates.

Import machinery precedent: `generate_reisai_quickstatements.py` (walks jawiki
articles, parses one infobox field, emits cited QS with S4656 jawiki-URL refs).
Every candidate below can reuse that exact shape.

## Template:神社 (shrine) — 54 params

| Field | Meaning | Wikidata mapping | Verdict |
|---|---|---|---|
| 例祭 | annual festival day | P837 + P3831 Reisai | **DONE** (3,239 stmts, 2026-07-07) |
| 所在地 | address | P6375 | **DONE** (address imports + citation backfill) |
| 社格 | shrine rank | P13723 | migrated — BUT the field is an untapped **reference source for the ~92 unsourced MODERN ranks** (Son/Ken/Gō-sha) from the 2026-07-08 triage: where the jawiki infobox states the rank, cite S4656. Highest-leverage small build. |
| 祭神 | enshrined deities | P825 (dedicated to) | **HIGH VALUE** — feeds the deity-name description plan directly; parse deity names, match to kami items (the recreation crossref machinery matches ja kami names already). Multi-deity + 主祭神 distinction via qualifier. |
| 創建 | founding date | P571 (inception) | HIGH — era-date parsing needed (伝-prefixed legendary dates → sourcing circumstances qualifier Q18122778 "presumably"). |
| 本殿 | honden architectural style | P149 (architectural style) | MEDIUM — style items exist and are already labeled by misc-terms (nagare-zukuri etc.); needs a style-name→QID table (hand-verified, small). |
| 別名 | alternate names | ja aliases (Aja) | EASY — alias adds, dedup against existing. |
| 札所等 | pilgrimage circuits | P361 (part of) circuit items | MEDIUM — circuit items partially exist; needs matching. |
| 神事 | notable rites | (no clean property) | SKIP for now — free text; overlaps festival model. |
| 神体 | shintai | (no clean property) | SKIP — creative-repurposing candidate needing Emma's modeling call. |

## Template:日本の寺院 (temple) — 36 params

| Field | Meaning | Wikidata mapping | Verdict |
|---|---|---|---|
| 法人番号 | corporate number | **P3225 (Japan Corporate Number)** | **EASY + AUTHORITATIVE** — exact-match identifier, government-issued; best quick win in the whole review. |
| 公式HP | official website | P856 | EASY. |
| 宗派 / 宗旨 | sect / denomination | P140 (religion) or P611 (religious order) | HIGH — sect items exist (labeled via misc-terms); needs sect-name→QID table. |
| 本尊 | principal image | P825 (dedicated to) | HIGH — the temple analog of 祭神; Buddhist deity items exist (buddhist_deity labels shipped). |
| 開山 / 開基 | founding priest / patron | P112 (founded by) | MEDIUM-HIGH — person matching; distinguish 開山 vs 開基 via qualifier. |
| 創建年 | founding year | P571 | HIGH — same parser as shrines. |
| 山号 / 院号 | mountain/cloister name | (name components) | SKIP for now — modeling call (P1449 nickname? part of official name?). |
| 寺格 | temple rank | (P13723 is shrine-scoped) | Emma's call — creative repurposing of P13723 vs a new approach. |
| 文化財 | cultural property designations | P1435 (heritage designation) | MEDIUM — designation items exist; parsing lists is the work. |
| 鎮守神 | guardian kami | P825 with role qualifier? | Emma's modeling call. |

## Template:日本の古墳 (kofun) — 36 params

| Field | Meaning | Wikidata mapping | Verdict |
|---|---|---|---|
| 形状 | mound shape (前方後円墳…) | P1419 (shape) — or P31 subclass | HIGH — small closed vocabulary (~10 shapes), items exist. |
| 築造時期 / 築造年代 | construction period | P571 (century precision) | HIGH — "5世紀後半"-style parsing, precision=century. |
| 史跡指定 / 指定文化財 | designations | P1435 | MEDIUM — same machinery as temples. |
| 被葬者 | interred person | (no clean forward property) | creative candidate: P547 (commemorates)? The person side is P119 (place of burial) — reverse-emitting P119 on the PERSON where the person item exists is cleaner. Emma's call. |
| 陪塚 | satellite tombs | P527 (has part) | MEDIUM — needs item existence for the satellites. |
| 規模 | dimensions (墳丘長…) | P2043 (length) etc. | MEDIUM — unit parsing. |
| 陵墓 | imperial mausoleum status | P31 addition (Q royal tomb classes) | MEDIUM. |
| 出土品 | excavated finds | (free text) | SKIP. |

## Build outcomes (2026-07-08, same night)

* **P3225 corporate numbers — built** (`generate_p3225_quickstatements.py`), but the
  法人番号 field is almost never filled on jawiki (~1% of temple articles in
  sampling); full-walk yield recorded in the output file. Kept as a standing
  tool; low volume is the field's reality, not a bug.
* **社格-as-reference — built (`generate_shakaku_references.py`) and structurally
  EMPTY:** all ~106 unsourced modern-rank statements sit on items with ZERO
  jawiki sitelinks (shinto-wiki-native items), so jawiki can never source them.
  The generator stays as a self-draining tool for future jawiki-linked cases.
  The actual candidate source for these items' ranks is the shinto wiki page
  itself (they're P11250-linked) — whether Emma wants her own wiki cited as a
  Wikidata reference is a modeling call, flagged.

## Recommended build order

1. **P3225 corporate numbers (temples)** — trivial parser, authoritative ID.
2. **社格-as-reference for unsourced modern ranks** — closes most of the
   unsourced-rankings triage residual with citations we already trust.
3. **P825 deities/本尊 (shrines + temples)** — biggest data value; unblocks the
   deity-name description disambiguation test at scale.
4. **P571 founding dates (all three)** — one era-date parser, three templates.
5. **Kofun P1419 shapes + P571 periods** — new class, small vocabularies.
6. The modeling-call fields (神体, 山号, 寺格, 被葬者, 鎮守神) wait on Emma.

All emit through the standard pipeline: generator → atomic .txt with S4656
jawiki citations → daily drip. No new mechanisms needed.
