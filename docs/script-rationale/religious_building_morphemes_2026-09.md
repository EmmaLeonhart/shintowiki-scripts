# How a religious-building label is assembled (2026-09-18)

Rationale doc for `shinto-label-generator/religious_building_morphemes.py`,
`romance_katakana.py`, `plain_latin_katakana.py` and
`generate_religious_building_multilang.py`.

*Sections 7a, 7b and 7c, and the current-output rows of section 10, added 2026-09-19.*

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

## 7b. No dedication means transliteration (2026-09-19)

Emma, 2026-09-18: ***"No dedication means transliteration."***

`dedication()` refuses the moment ONE name token is absent from `NAMES`, and over the corpus that
refusal was the pipeline's single biggest gate - **13,470 items** against 7,599 that resolved.
`Santo Andre de Lourizan` is not an unknown saint; it is Andrew, at a place the table has never
heard of. Section 7 already read a leftover qualifier for the *generic-title* branch; this extends
the same treatment to the *names* branch, which is where the 13,470 sit.

### The slots are the ones section 7 already established

    <place> no  <qualifier> no  <sei><dedicatee>  <type>

    Santo Andre de Lourizan   ->  ポンテベドラのロウリーサンの聖アンデレ教会
    San Francesco di Paola    ->  パルティニーコのパオーラの聖フランチェスコ教会
    Santa Maria della Grazia  ->  ヴェネツィアのグラーツィアの聖マリア教会

**The qualifier is not part of the saint's name.** Written the other way first, `San Francesco di
Paola` came out 聖フランチェスコ・パオーラ - a person called Francesco Paola. The split is the first
genitive or locative linker (`_LINKERS`) or comma that follows at least one name token, so the `of`
in `Church of Santa Clara` links the TYPE to the dedicatee and does not split.

**A saint marker after the split is not read as one.** `Chapel of St Anne in San Pedro` is Anne, in
a town called San Pedro; prefixing 聖 to the qualifier would say the place is a saint.

**The dedicatee is NAMED where the table knows it and READ only where it does not**, so the two
paths mix inside one label: `Santa Margherita di Massignano` is 聖マルガリタ from the table plus
マッシニャーノ by rule.

### The place is not named twice

`Church of Santa Clara, Vitoria-Gasteiz` read
ビトリア＝ガステイスのヴィトーリア・ガーステイスの聖クラーラ教会 - the town twice, in two
spellings, because the first is Wikidata's ja label and the second is derived. `_echoes_place`
compares against the place's **English** label, which is the only thing in the same alphabet as the
source string; `generate_religious_building_multilang.py` now fetches `en` alongside ja/zh/ko for
every P131 place.

When *every* name token turns out to be the place - `Pancevo Synagogue` in Pancevo - there is
nothing left for the dedication slot and the label is `place + type`, the call `render_mosque`
already makes for `Mosque in Pirshagi`. **253 of the 6,722 ja lines are that shape.** A label with
no name at all (`Kirche`) is a different thing and stays refused: not named after its place, not
named.

**This is why Poland, Germany and Austria gained labels without gaining a transliterator** - 139, 92
and 39 of them. `Saint Anne church in Poznan` refused because `Poznan` was an unknown token; now
Anne comes from the table and the qualifier is dropped as the place.

### What still refuses, and it is a country map

**ja only**, for the third time and the same reason (`_QUALIFIER_LANGS`, `_MOSQUE_NAME_LANGS`): a
transliteration is a READING, and there is no rule-based route from a Galician village name to hanzi
or hangul.

Within ja, the gate is `rules_for_country`, and an unlisted country **refuses rather than guessing**.
Two of Emma's own three examples are on the wrong side of it - `Dorfkirche Joerdenstorf` (German)
and `Eglise du Pras de La Mulatiere` (French). The 6,627 still refused are led by Germany 2,964,
Poland 1,543, Austria 608, France 607, Russia 517, Czechia 337 and the Netherlands 273.

**`render`'s `rules` parameter now defaults to `None`**, i.e. to refusal - "unlisted means refuse,
never a default", the doctrine `romance_katakana` already states. It defaulted to `"it"`, which was
harmless while an unknown name was refused outright and became live the moment this fallback
existed: `Hofkapelle Aichet` is German and read as Italian. The generator was never exposed - it
passes `rules=_rules_for(p17)` - but **four existing tests were passing only because of the
default**, which is how it was found.

### Three things that were wrong first

- **The generator gates on `dedication()` BEFORE calling `render`**, so the first run of the fallback
  changed nothing at all: byte-identical output, skip counter still reading "unknown dedication
  13,470". The gate has to ask the fallback too.
- **The table lookup did not fold accents** where `dedication()` does, so `lucia` with an accent
  missed a saint the table has had all along - 20 of those, plus 19 `antonio`, 18 `roman` and
  200-odd more that would have been read instead of named.
- **Type words were being read as dedicatees** once something started reading whatever it found in
  the name slot: `Esglesia` (Catalan, 18), `gereja` (Indonesian, 14), `hermitage` (18), `convento`,
  `parroquia`, `santuario`, `abbazia`. A type word read as a name is the failure this module exists
  to avoid.

### Two fixes in the tables, and the line between them

**Spelling variants of saints the table ALREADY names** were added - `francisco`, `agata`,
`tommaso`, `benedetto`, `ana`, `nicolo`, `margherita`, `cristo`, `vito` - so ONE saint never gets
two Japanese forms. `francesco` was フランチェスコ from the table while `francisco`, absent, was read
as フランシースコ. That follows the table's own precedent: it already lists five spellings of
Nicholas and eight of John.

**A saint the table does NOT name was not added.** Gregorio, Filippo, Marco, Marta, Agostino,
Domenico, Biagio, Vittore, Bernardo, Roman and the Galician saints (Amaro, Breixo, Cibran, Comba,
Santaia, Xillao) are absent, and absent is what "no dedication means transliteration" is FOR. Naming
them is a per-saint translation call; reading them is the rule Emma gave.

### A bug in `romance_katakana` this surfaced

Italian `zz` is the geminate /tts/, and `z -> ts` turns `piazza` into `piatstsa`, where **no two
adjacent characters are equal** - so the geminate test could not see it and it came out ピアーツツァ.
12 emitted labels carried it: ポーツツォ for Pozzo, ラツツァーロ for Lazzaro. `to_katakana` now tests
for a repeated DIGRAPH (`ts`, `ch`, `sh`) before the single-character test. ピアッツァ.

**Two labels are still misparsed and are left that way.** `Santa Margherita Vergine e Martire`
matches the generic Marian title `vergine` and emits ロッカセッカの聖母教会, losing Margaret;
`Santa Maria Incoronata e Santa Lucia Vergine Martire` the same. The virgin-martyr epithet is not
the Virgin Mary. It is **2 items** in 22,548 and the fix would reach into the scan that 7,599
table-path items run through, so it stays as recorded. Edge cases be damned.

---

## 7c. Five orthographies, because Emma said all of them (2026-09-19)

Section 7b left **6,627** refused at the dedication gate, and it was no longer a tail of tokens but
a COUNTRY MAP: Germany 2,964, Poland 1,543, Austria 608, France 607, Russia 517, Czechia 337,
Netherlands 273. Asked which transliterators to build, and shown the French caveat in the question
itself, Emma answered ***"All of them, French included."***

Five new families in `plain_latin_katakana.py`. **6,627 -> 2,604**, and ja **6,722 -> 9,080**.

| family | countries | of the 6,627 |
|---|---|---|
| `de` | Germany, Austria, Switzerland, Liechtenstein | 3,357 |
| `pl` | Poland | 748 |
| `fr` | France, Belgium, Canada (Quebec), Luxembourg | 594 |
| `ru` | Russia, Ukraine, Belarus — a ROMANISATION, not an orthography | 529 |
| `cs` | Czechia, Slovakia | 289 |

### What each family needed that the Balkan/Turkic/Malay three did not

- **German** — umlauts (and ö is NOT the Turkish ö: Köln is ケルン, `_pre_turkic_rounded` would give
  ケョルン), written length, s-voicing, final devoicing, the four things `ch` spells, and a geminate
  rule the module had never needed. ⚠ German geminates OBSTRUENTS only; Müller is ミュラー.
- **Polish** — ł is /w/ while w is /v/, so ł parks on a sentinel or Łódź becomes ヴジュ, a different
  town. A palatal + i + vowel is one syllable (Kościan コシチャン). Final obstruents devoice, and the
  digraphs devoice as a unit.
- **Czech/Slovak** — the acutes are LENGTH, which is exactly what the Balkan family does not write.
  dě/tě/ně are palatals, not d + ye. `ř` reads as a plain r: /r̝/ has no kana at all, and ドヴォルザーク
  for Dvořák is a convention a village name cannot borrow.
- **French** — the hard one, and the one the repo had refused on purpose. Three ordering bugs, each
  producing a plausible-looking word:
  - **Softness before the mute e is dropped.** Softness is caused by the very letter the mute-e rule
    deletes. `Vincent` came out ヴァンク, `Hayange` エアン.
  - **The mute e before the accents are folded.** `é` is not mute; folding first made `Pitié` end in
    a droppable e.
  - **The nasal ン on a sentinel.** A nasal is a VOWEL and its n looked exactly like a silent final
    consonant to the next pass: `Jean` was ジェア.
  Also: the mute e is PARKED, not deleted, because it is what makes the consonant before it sound
  (`Dame` ダム, `Sainte` サント); `ch` restores to `sh`; a double consonant is one.
- **Russian** — reads a TRANSCRIPTION. Stage 1 writes Russian names in the English romanisation, so
  the digraphs are English conventions for Cyrillic letters (zh = ж, kh = х, shch = щ). Any diacritic
  at all refuses, because a romanised name is plain ASCII by definition.

### ⭐ The English guard, which Poland forced and which matters more than any one family

Stage 1's labels for Poland are mostly **English descriptions of Polish churches**. The moment `pl`
existed they were read with Polish rules:

    Blessed Jerzy Popiełuszko chapel   ->  ブレスセト
    Roman catholic church, Trebišov    ->  ロマン・ツァトホリツ
    Bar Confederation chapel           ->  ツォンフェデラティオン
    Ćmielów Castle                     ->  ツァストレ
    Saint Heribert of Cologne          ->  ツォログネ

Every one is a confident wrong reading of a word whose meaning we know. `_ENGLISH_CONTENT` lists the
English CONTENT words that survive the frame filters — a frame word is dropped by STOPWORDS or
TYPE_WORDS and never reaches a transliterator; these would.

⚠ **It refuses the LABEL, not the token.** Dropping the token silently would emit
ジェジ・ポピエウシュコ礼拝堂 for a chapel the source calls Blessed — less than the source said, which
is the call `_qualifier_residue` already makes.

### Two things that were quietly wrong all along and only now bit

- **The generator gates on `dedication()` before `render`**, so the first run of the whole
  transliteration fallback produced BYTE-IDENTICAL output and a skip counter still reading 13,470.
- **Bare `burg` and `orts` were type words.** `_strip_compound_type` matches any tail of 4+
  characters, so they ate the end of every -burg place name: `Yekaterinburg Synagogue` read
  イェカテリン・シナゴーグ, and Magdeburg, Hamburg and Regensburg were all one syllable short. Removing
  them cost exactly 2 labels, both `Hubertusburg` — a castle whose -burg was being stripped to reach
  St Hubert.

Also: **one label line per QID per language**. Stage 1 emitted two Commons categories for 6 items,
and while both were refused that cost nothing; once `de` could read them, QuickStatements would have
set one item's ja label twice.

### What is left, and it is still a country map

**2,604**, led by Germany 859 (labels German cannot read — digits, foreign words, the English
guard), Poland 337, Netherlands 258, Spain 232, Moldova 140, Russia 113, Sweden 83, Romania 81.
Dutch, Romanian, Swedish, Armenian, Finnish, Norwegian and Lithuanian have no family and have not
been asked about.

---

## 8. What is refused outright

- **Category-shaped labels** (8 patterns). ~818 of the corpus name a *grouping*, not a building:
  "Cultural heritage monuments in X", a **plural** "Synagogues", districts, estates.
- **No P31 mapping** — a type the tables do not render.
- **No P131**, or a place with no label in the target language (ja 44.8%, zh 56.2%, ko 24.5% have
  one; 42.2% have none of the three).
- **An unknown token the country has no reading rule for.** Until 2026-09-19 *any* unknown token
  refused; now it is read where `rules_for_country` gives a rule set and refuses where it does not
  (section 7b). `San Xulian de Cela` is read; `Dorfkirche Joerdenstorf` is not.
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

| | lines | of which mosque-family | of which READ, not named (7b/7c) |
|---|---|---|---|
| ja | 9,080 | 76 | 4,462 |
| zh | 5,434 | 31 | - (ja only) |
| ko | 2,065 | 30 | - (ja only) |
| stage-1 English replacements | 16 | - | - |

Figures as of 2026-09-19, after 7c. Before 7b: ja 4,618, zh 5,099, ko 1,940. **No QID lost a ja
label at any point**; zh and ko each lost 2, both `Hubertusburg`, explained in 7c.

Zero duplicate labels, zero duplicate QIDs, zero malformed lines, re-checked 2026-09-19 over all
16,579 lines. The **0 collisions in 250 sampled against live Wikidata** is from 2026-09-18 and was
NOT re-run against the 4,462 new lines — WDQS is not queried for this and the read API sample costs
a run of its own. All in `shinto-label-generator/quickstatements/`, on the 20/day drip.

**2,604 still refuse at the dedication gate**, down from 6,627 before the five families and
13,470 before the fallback existed. Still a country map: Germany 859, Poland 337, Netherlands 258,
Spain 232, Moldova 140, Russia 113, Sweden 83, Romania 81. Dutch, Romanian, Swedish, Armenian,
Finnish, Norwegian and Lithuanian have no family and have not been asked about.

The mosque family went from **0 labels to 137** across 245 items. What it does not reach is the
Arab-world, French, Bangladeshi and Central Asian slices, which have no rule set and are not getting
one from a guess — and the 34 mosques whose P131 place carries no ja/zh/ko label at all, which is the
same ceiling every other item in the corpus hits.
