# Religious-building labels — stage 2 design (decision for Emma)

Stage 1 (`generate_religious_building_labels.py`) shipped 2026-07-11: **22,548 English labels**
copied from the Commons category for churches/chapels/mosques/synagogues with no English label.
Stage 2 was left as "multilang, to come, seeded from the English label" — mirroring the shrine
multilang generator. This doc says why that mirror is **wrong** here and proposes what to do
instead. Emma's call.

## The shrine model does not transfer

The shrine multilang engine **transliterates** a Japanese name into every script (Hindi, Arabic,
Greek, …) because a Japanese shrine has *no* native name in those languages — a phonetic
transliteration is the only thing available and it is the right thing.

Religious buildings are the opposite. They are overwhelmingly Western buildings with **real
native names**. Live counts on the 21,945 church+chapel candidates that lack an English label:

| already has a label in… | count | share |
|---|---:|---:|
| German (de) | 6,631 | 30% |
| Italian (it) | 3,188 | 15% |
| Polish (pl) | 2,460 | 11% |
| French (fr) | 910 | 4% |
| Spanish (es) | 906 | 4% |
| Dutch (nl) | 494 | 2% |

So a large fraction already carry a real native name, and the rest are the same *kind* of thing.
Phonetically transliterating "Church of Saint Leonard" into Arabic/Greek/Hindi would produce
nonsense labels for buildings that either have, or should have, a real local name — the exact
failure the shrine pipeline avoids only because shrines have no such name.

## Options

1. **No stage 2 — English label only (recommended for now).** Stage 1 stands alone; native
   labels accrue from the wider Wikidata community (they already do — see the table). Zero risk
   of fabricated names. This is the honest default given the data.
2. **Latin-script cross-fill (a real, safe generalization).** For a building that has a
   Latin-script label in *some* language (de/it/pl/…) but is missing it in another Latin-script
   language, copy the existing native label across. Church names are frequently identical or
   near-identical across Latin-script European languages ("San Giovanni Battista", "Sankt Marien").
   This uses *real* names, never transliteration. It needs a per-language safety rule (don't copy
   a `(Berlin)`-style disambiguator; respect obvious language-specific forms) and is a genuine
   build, but a defensible one.
3. **Transliterate into non-Latin scripts — rejected.** Wrong for the reasons above; would
   manufacture names for buildings that have real ones.

## Recommendation

**Option 1 now** (English-only; stage 1 is the deliverable), with **Option 2 as the real "stage 2"
if Emma wants multilang coverage** — a Latin-script cross-fill from existing native labels, NOT a
transliteration. `generate_religious_building_multilang.py` should be built to Option 2's shape,
not the shrine engine's. Do **not** point the shrine transliterators at religious buildings.

Open question for Emma: is multilang coverage of foreign religious buildings even in scope for the
Shinto project beyond the English seed, or is stage 1 the intended endpoint?
