# How a religious-building label is assembled (2026-09-18)

Rationale doc for `shinto-label-generator/religious_building_morphemes.py`,
`romance_katakana.py`, `plain_latin_katakana.py` and
`generate_religious_building_multilang.py`.

*Section 7a and the mosque rows of section 10 added 2026-09-19.*

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

## 7a. The mosque family — a second slot system (2026-09-19)

Everything above is a Christian saint vocabulary, and **nothing in it can match a mosque**. All 245
mosques in the corpus produced zero labels, not because they were hard but because they were never
eligible: `build()` gated every item on `dedication(label, "ja")` returning something.

Emma, 2026-09-18: ***"translate the generic, transliterate the name"***, with three worked examples
— `Old Mosque` → 旧モスク, `Upper Mosque` → 上モスク, `Omer Mosque` → オメル・モスク.

**The measured shape of the 245**, which is what makes that instruction tractable:

| shape | n | example |
|---|---|---|
| bare type word only | 77 | `Mosque`, `Džamija`, `Masjid` |
| generic modifier only | 18 | `Old Mosque`, `Nova Džamija`, `Merkez-Moschee` |
| carries a name | 137 | `Omer Mosque`, `Surau Bulian` |
| not named as a mosque | 10 | `Nablus`, `WikiBanua 2.0`, `Donauwörther Straße 165` |
| category-shaped | 3 | `Mosques in Dubai` |

The first two buckets reach **all three languages** — a translation of *old* is a translation, not a
reading. The third is **ja only**, for the same reason section 7 gives.

**Slots:** `<place>の` `<name>` `<modifiers>` `<friday>` `<type>`.

⚠ **The modifier goes after the name, not before it.** Written the other way round first,
`Adana New Mosque` came out 新アダナ・モスク — a mosque in a place called *New Adana*, because a
Japanese prefix attaches to whatever follows it. アダナ新モスク is the new mosque at Adana.

**The generic-vs-name test is a lookup, not a heuristic.** A token is generic when
`MODIFIER_ALIASES` names it; everything surviving the type words, the modifiers, the stopwords, the
ordinals and the one-letter honorifics is a name. The aliases are measured spellings across the
corpus's actual source languages, not English only — `stara` / `eski` / `tuo` / `usang` for *old*,
`nova` / `yeni` / `baru` for *new*, `agung` / `raya` / `besar` / `kebir` for *great*.

**Three calls Emma made on 2026-09-19**, none of which the ontology settled by itself:

- **Jāmi' / juma / jama / jamik / cümə** (18 items) is the *congregational* mosque, and the
  distinction is **translated**: 金曜 / 聚礼 / 금요.
- **A surau is not a mosque** (9 items) — a small Malay prayer hall, filed under P31 mosque because
  Wikidata has no closer class. It keeps **its own word** (スラウ / 수라우), the call the TYPES table
  already makes for ワット and グルドワーラー. ⚠ The zh cell 苏劳 is mine, not hers.
- **The ko modifiers are native, not Sino-Korean**: 옛 / 새 / 위 / 아래 / 큰 / 중앙, over the
  구 / 신 / 상 / 하 / 대 that would have paralleled the ja column one-for-one.

### `plain_latin_katakana.py`, and why it is not `romance_katakana`

The name half needed a transliterator, and the Romance one is the wrong tool: its whole output rule
is Romance penultimate stress written as ー (Loreto → ロレート). Ömer is オメル, not オーメル. So a
sibling module, sharing the kana grid and nothing else, covering the three orthographies this
population actually uses — **186 of 245 items**:

| | languages | the digraphs that matter |
|---|---|---|
| `bs` | Bosnian / Croatian / Serbian-Latin / Macedonian-Latin | č ć š ž đ dž lj nj, c = ts, j = y |
| `tr` | Turkish / Azerbaijani | c ç ş ğ ı ö ü ə x |
| `ms` | Malay / Indonesian | sy kh gh th dh c q, ŋ |

⛔ **Everything else refuses**, and `rules_for_country` never defaults — the lesson section 7 records
the Romance module learning the expensive way. French (`Mosquée de Carpentras`), romanised Arabic
(`Abd Al-Mun'im Riyad`), Russian-romanised Tatar (`Bolshiye Kaybitsy`) and German
(`Donauwörther Straße`) all sit in this population and all get nothing.

**Two guards exist because the letters alone are not enough:**

- **Phonotactics.** `Rzhavets` is spelled entirely in legal Turkish letters and came back
  ルズハヴェツ. Turkish has no native initial consonant cluster and Malay only a short list, so an
  onset check catches what the alphabet cannot.
- **English vocabulary.** `Brunei International Airport Mosque` read as Malay gave
  ブルネイ・インテルナティオナル・アイルポルト・モスク. Every letter is legal; only the words give it
  away, so `ENGLISH_MARKERS` refuses the item outright.

⚠ **`MOSQUE_TYPE_WORDS` is deliberately NOT merged into the global `TYPE_WORDS`.** That set is
consulted for all 22,548 items and `_strip_compound_type` matches it as a suffix, so adding `cami`
or `mosk` there would change how 18,148 church labels parse for no gain. Regenerating after this
change removed **zero** existing lines, which is the check that it did not.

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

| | lines | of which mosque-family (2026-09-19) |
|---|---|---|
| ja | 4,618 | 76 |
| zh | 5,099 | 31 |
| ko | 1,940 | 30 |
| stage-1 English replacements | 16 | — |

Zero duplicate labels, zero duplicate QIDs, zero malformed lines, **0 collisions in 250 sampled
against live Wikidata**. All in `shinto-label-generator/quickstatements/`, on the 20/day drip.

**~14,500 still refuse**, and the tail is genuinely long: 7,000+ distinct unknown tokens, mostly
place names inside `San X de PLACE`. The cheap seam is worked out.

The mosque family went from **0 labels to 137** across 245 items. What it does not reach is the
Arab-world, French, Bangladeshi and Central Asian slices, which have no rule set and are not getting
one from a guess — and the 34 mosques whose P131 place carries no ja/zh/ko label at all, which is the
same ceiling every other item in the corpus hits.
