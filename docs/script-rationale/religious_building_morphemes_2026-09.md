# How a religious-building label is assembled (2026-09-18)

Rationale doc for `shinto-label-generator/religious_building_morphemes.py`,
`romance_katakana.py` and `generate_religious_building_multilang.py`.

The problem: 22,548 churches, chapels, mosques and synagogues need ja/zh/ko labels, and the only
text we have for each is a Commons category name that is usually **not English** — `Kirche Rehden`,
`San Giovanni Battista`, `Madonna del Pero`. Emma, 2026-09-17: *"We look at common words and
morphemes across all of the things."* That is what this is.

---

## 1. The shape of a label

Every emitted label is the same three slots, in this order:

    <PLACE> の <DEDICATION> <TYPE>
    レーデン    の  聖ペトロ      教会

| slot | where it comes from | can it be missing? |
|---|---|---|
| **PLACE** | the item's `P131` (admin area), in its own ja/zh/ko label | **No.** Mandatory — see §5 |
| **DEDICATION** | parsed out of the source label, via the tables | No |
| **TYPE** | the item's `P31`, never the label | No |

The joiner is per language: ja `の`, ko `의 `, zh nothing (`雷登圣老楞佐教堂`).

⛔ **The TYPE never comes from the text.** Two thirds of the corpus carries no English type word at
all, so the label cannot be its source. `P31` is authoritative, and it wins even when the text
disagrees — a label reading "Chapel" on an item typed church building renders 教会.

---

## 2. The tables

Sizes as of 2026-09-18. Every entry was added from a **measured frequency list** of what the corpus
actually contains, never from a mental list of saints.

| table | entries | what it holds |
|---|---|---|
| `TYPES` | 9 | P31 QID → the type word per language |
| `TYPE_WORDS` | 98 | type words **in any source language**, stripped to find the name |
| `STOPWORDS` | 98 | connectives, articles, roles, denominations |
| `SAINT_MARKERS` | 35 | St / San / Santa / Sankt / Sveti / Sint / Św … |
| `NAMES` | 176 → **70 distinct people** | saint name spellings |
| `NAME_PHRASES` | 23 | compound saints that must read as one |
| `DEDICATIONS` | 163 → **68 distinct** | feasts, devotions, Marian titles |
| `EN_FROM_JA` | 101 | English form, keyed by the canonical ja rendering |
| `SELF_SAINT` | 4 | names with the marker fused in (Santiago = Sant+Iago) |

**176 spellings for 70 people** is the whole point. Bartholomew alone appears as
`bartholomew` / `bartholomäus` / `bartolomeo` / `bartolomeu` / `bartolomé` — 154 items between them.

---

## 3. Parsing: finding the name

`parse_name()` walks the label and drops everything that is not the dedication.

1. **Split** on whitespace, hyphens and **apostrophes**. The apostrophe split is needed for
   `Sant'Anna`, and it is also what creates the two commonest junk tokens in the whole corpus —
   the English possessive `s` (56) and the French `d'` (46), both now stopwords.
2. **Drop** stopwords, type words, saint markers. A marker sets a flag rather than contributing text.
3. **Strip glued type tails.** German welds the type on: `Jerusalemkirche` → `Jerusalem`,
   `St.-Petri-Kirche` → `St.-Petri`. Only fires when something is left, so bare `Kirche` is not
   reduced to nothing.
4. **Resolve each token through `name_key()`**, which handles the **genitive**: `Martinskirche`
   strips to `martins`, `Peterskirche` to `peters`, `St. Pauli` to `pauli`. The -s / -i / -is / -us
   / -en is grammar, not a different saint, so it is a rule rather than duplicate rows. Guarded:
   a suffix strip must not turn an unknown word into a known one.

---

## 4. Choosing the dedication: specific beats generic

Two groups, checked **in order**, longest-phrase-first within each:

1. **`SPECIFIC_DEDICATIONS`** (147) — feasts and named devotions. Assumption, Visitation,
   Transfiguration, Our Lady of Kazan, Perpetual Help, the Scapular, Częstochowa.
2. **`GENERIC_DEDICATIONS`** (16) — bare Marian titles. Our Lady, Madonna, Theotokos, Nostra
   Signora, Nosa Señora, Beata Vergine.

⛔ **Sorting by string LENGTH was wrong and cost real accuracy.** `Visitazione della Beata Vergine`
matched `beata vergine` (13 chars) over `visitation` (10) and lost the Visitation the table already
had. A feast names *which* dedication; a Marian title only names *who it is to*.

⛔ **And the ordering fix did nothing on its own**, which is the more useful lesson: the feast table
was **English-only** while the corpus is Italian, Spanish, Galician, Portuguese and German.
`visitation` is not a substring of `Visitazione`. The source-language forms had to be added before
the correct ordering could fire.

**Matching is accent-folded** on both sides — the corpus spells the same feast `Fátima`/`Fatima`,
`Asunción`/`Asuncion`. Output keeps its accents; only the comparison is folded.

---

## 5. Why the place is mandatory

The first working version composed dedication + type only. Measured over the corpus it produced
**36 distinct outputs for 2,392 labels — 99.6% colliding**: 515 different Madonna churches all
became 聖母教会, 201 became 聖ニコラオス教会.

For this population **the "name" IS the dedication**, and hundreds of buildings share it. What
separates them is where they are. `P131` is present on **100%** of a 200-item sample with **192
distinct places per 200 items**, so it very nearly disambiguates on its own.

Confirmed against live data afterwards: bare `聖母教会` is already carried by **five separate items**
on Wikidata.

---

## 6. The generic-title rule

A generic Marian title emits **only when nothing is left over**.

    Madonna                  ->  聖母            (nothing lost)
    Madonna della Neve       ->  雪の聖母        (mapped devotion)
    Madonna del Cardello     ->  カルデッロの聖母  (qualifier transliterated, §7)
    Our Lady of Vladimir     ->  ウラジーミルの生神女

Emma, 2026-09-18: *"Refuse each one until the table individual qualifier is done."* A bare title on
an item whose source said "of the Snows" is true but less specific than the source, so it is refused
unless the qualifier can be named or read.

---

## 7. Transliterating the leftover qualifier — **ja only**

When the qualifier is a place (`Madonna di Campiglio`), `romance_katakana.py` reads it by rule.

**Three rule sets**, chosen from the item's **`P17` country**, not assumed:

| rules | `ce`/`ci` | `ge`/`gi` | `ll` | `z` |
|---|---|---|---|---|
| **it** | チェ affricate | ジェ | geminate `ッ` | ツ |
| **pt** | セ | ジェ | — | ズ |
| **es** | セ | ヘ | ヤ | ス |

⛔ **An unlisted country REFUSES.** It used to fall back to Italian, which on the real corpus meant
14,000+ items — the countries are Germany 5,490, Spain 4,169, **Italy 3,157**, Poland 2,664,
Russia 1,628, France 717. Italy is third. And the fallback leaked: French passes the Romance shape
gate, so `Notre-Dame-de-Pitié de Trouville-sur-Mer` came out **ピーチエ・トロウヴィッレ・スル・メル**.

**`is_romance_shaped()`** refuses anything that is not Romance: letters absent from native Romance
spelling (k, w, y), four or more consonants in a row, and word-initial clusters Romance does not
permit. `Rzhavets`, `Bąkowa`, `Zgierz`, `Kraków`, `Szczecin`, `Welschenrohr` all refuse.

**Vowel length** is applied by rule: Romance stress is penultimate unless written otherwise, and
Japanese writes a stressed *open* syllable long. `Fiore` → フィオーレ, `Loreto` → ロレート,
`Cardello` → カルデッロ (closed by the geminate, no ー). Stress is computed on the **source word's
vowel groups**, not on kana — ブラ is two morae and one syllable, and counting kana got `Coimbra`
wrong.

⛔ **zh and ko get no transliterator and must not.** There is no rule-based route from an Italian
village name to Chinese characters or hangul; those are conventions, not derivations. Those items
stay refused.

---

## 8. What is refused outright

- **Category-shaped labels** (8 patterns). ~818 of the corpus name a *grouping*, not a building:
  "Cultural heritage monuments in X", a **plural** "Synagogues", districts, estates.
- **No P31 mapping** — a type the tables do not render.
- **No P131**, or a place with no label in the target language (ja 44.8%, zh 56.2%, ko 24.5% have
  one; 42.2% have none of the three).
- **Any unknown token** on the names path. `San Xulián de Cela` refuses because `Cela` is a place
  the tables do not know.
- **A duplicate** — if two items still produce the same string, neither is emitted.

---

## 9. Registers, which are choices and not accidents

- **zh is Catholic**, consistently: 弥额尔 / 玛窦 / 厄里亚 / 安德肋, where Wikidata's own labels are
  often the Protestant 米迦勒 / 馬太 / 以利亞 / 安得烈. These are Catholic parish churches, so
  Catholic is right — but it was a silent decision until it was written down.
- **ko is current**, not historical: 주님 탄생 예고 for the Annunciation is the post-2011 Korean
  Catholic form; Wikidata still carries the older 성모 영보.
- **We translate the dedication.** Real ja practice mostly **transliterates** the native name
  (サンタ・マリア・デル・フィオーレ大聖堂, 7 of 8 sampled). Emma confirmed twice: impose our
  ontology, which is consistent and machine-derivable where theirs is descriptive.

---

## 10. Current output

| | lines |
|---|---|
| ja | 4,358 |
| zh | 4,840 |
| ko | 1,781 |
| stage-1 English replacements | 16 |

Zero duplicate labels, zero duplicate QIDs, zero malformed lines, **0 collisions in 250 sampled
against live Wikidata**. All in `shinto-label-generator/quickstatements/`, on the 20/day drip.

**14,551 still refuse**, and the tail is genuinely long: 7,000+ distinct unknown tokens, mostly
place names inside `San X de PLACE`. The cheap seam is worked out.
