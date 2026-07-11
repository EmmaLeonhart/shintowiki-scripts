# How shrine & temple properties are modelled — systematic survey (2026-07-10)

Emma asked for a **statistical survey of the qualifiers and references across
shrine/temple properties** — to find the coherent, established models so we can
extend them (and reuse them on new properties and on Buddhist temples). Read
this in **absolute counts**, not percentages: a pattern followed by hundreds or
thousands of statements is a real model even if it's a small share.

Tool: `modern-quickstatements/investigate_property_modelling.py` (runs on any
class × property). Live SPARQL over query-main.

## The qualifier models that actually exist (Shinto shrines)

Property statement counts and the qualifiers riding on them:

| Property | Statements | The qualifier model on it (absolute counts) |
|---|---|---|
| **shrine ranking** | 16,750 | **how the rank was determined: 16,750 (all of them)** · when the rank ended: 7,918 · why it ended: 3,932 · conferred by: 517 · applies to jurisdiction: 266 |
| **official name** | 16,555 | which period the name was valid in: 5,126 · the name's kana reading: 4,346 |
| **part of** (list membership) | 6,384 | follows: 5,190 · followed by: 5,189 · position in the list (series ordinal): 5,163 |
| **said to be the same as** | 4,329 | a ranking of the identification: 3,924 · role of each side: ~1,650 |
| **dedicated to (deity)** | 14,408 | almost none — object named as: 80 · role: 11 · start/end time: ~38 |

**The correction to my earlier note.** I first surveyed only *dedicated to (the
deity property)* and concluded "qualifiers are barely used." That's true of that
one property — but it is the **exception**, the least-qualified content property
on shrines. Every other big property carries a rich, coherent qualifier model:

- **Shrine ranking is the richest.** Every single rank statement records *how the
  rank was determined*; roughly half also record *when* and *why* the rank ended
  (the 1946 abolition of the national ranking system). A rank statement is a small
  dated record, not a bare value. This is the ~16,750-strong model to imitate.
- **Official name** carries the name's **kana reading** (4,346) and the **period it
  was valid** (5,126) — names are modelled with their reading and their validity
  window.
- **Part of** is the ordered-list model: each membership carries its **position**
  and its **neighbours** (~5,180 each). This is the Engishiki-list machinery.
- **Said to be the same as** carries a **ranking** of how likely the identification
  is (3,924) — the ronsha-candidate model.

## "Object named as" — useful, and its derivation is simple

*Object named as* (the qualifier in Emma's first screenshot) appears on 80 deity
statements — all from the Kanagawa Prefecture Shrine Records import. Its **derivation
is the surface string from the source**: the exact spelling the source wrote for the
name, kept verbatim even when it differs from the item's own label (e.g. the item is
*Amaterasu* but the record wrote 天照皇大御神). The much larger cousin of this idea is
the **kana-reading qualifier on official name** (4,346) — same principle, "how this
name is written/read in the source." For our jawiki importers the derivation is the
wikilink's display text (`[[天照大神|天照皇大御神]]` → 天照皇大御神), which is what
`generate_saijin_deity_research.py` already emits.

## References (how statements are cited)

Deity statements: shrines 28% cited, temples 97%. The dominant citation is the
**"imported from Japanese Wikipedia" bundle**: *imported from Japanese Wikipedia* +
*the page URL* + *the date retrieved* (shrines ~3,371 / temples ~5,893 carry the
first of these). A smaller, higher-quality citation is a **printed source**: *stated
in <book>* + *page* + *NDL id* — the Kanagawa Shrine Records (77), 興除村史, 狛江村誌,
city cultural-property databases, information boards, field research.

**Our own jawiki importers cite less than the corpus standard.** The scripts that
copy fields from Japanese Wikipedia (the deity, festival, founding-date, honzon
importers) attach only the **page URL**. The established bundle is three things
together: *imported from Japanese Wikipedia* + *page URL* + *date retrieved*.
Matching it is a one-line change per script — but it changes how live data is cited,
so it's a decision to make deliberately, not a silent edit.

## Extension guidance

- **Each property has its own established qualifier model — match the property, not a
  global rule.** New rank-like data → record how it was determined (+ end time/cause).
  New name data → record the reading and validity period. New list membership →
  position + neighbours. New identification → a ranking.
- The **deity property is genuinely light**; the one qualifier worth carrying there
  is *object named as* (source spelling), which we already emit.
- Run `investigate_property_modelling.py --class <QID> --property <P…>` before building
  any new property import, to model to the existing convention instead of inventing one.
