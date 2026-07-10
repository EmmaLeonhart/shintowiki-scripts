# Commons-romaji → house English-label normalization — design

**Date:** 2026-07-10 · **Status:** approved (Emma), pre-implementation · **Scope:** Japanese Shinto shrines + Buddhist temples only

## Why

A Wikimedia Commons category name is a *confirmed reading* of a subject's name — useful signal. The
retired `generate_commons_labels.py` conflated that with "the Commons category name **is** the
English label", which is almost never true: a Commons name is native-language / raw-romaji text, not
a house-convention English label. Copying it imports the wrong title.

The thing we never built is the **normalizer**: take the Commons category name and render it into the
house convention — the way `temple_english.py` turns a temple into `"<Stem>-<suffix> Temple"`. This
project builds that normalizer for **Commons romaji input**, and — crucially — **proves it against
enwiki titles before any Wikidata edit is ever proposed.**

Emma's framing (2026-07-10): *"this is just one part of our pipeline that will come immediately
before the same Japanese label part."* So the normalizer is a **pipeline stage**, sharing suffix and
macron conventions with the existing kana→label stage. This build is its proving ground; once the
accuracy is approved it becomes a real label source.

## Scope

**In:** Japanese Shinto shrines (`P31 = Q845945`) and Japanese Buddhist temples
(`P31 = Q5393308`, `P17 = Q17`) that have a Commons category (commonswiki sitelink or `P373`).

**Out (deferred to later, separately-proven tranches):**
- All non-Japanese religious buildings — churches, mosques, synagogues, Hindu temples, non-Japanese
  Buddhist temples. Emma: these need much more testing; do not fold them in.
- Any Wikidata edit. This build emits a **report only** — no `.txt`, nothing in `ATOMIC_FILES`, no
  QuickStatements. Edits wait until Emma has seen the accuracy and the failure cases and set a bar.
- Kana fallback (the "Approach B" idea). Rejected: romaji normalization stands on its own; where it
  can't recover a macron, that's acceptable output (below), not a reason to reach for kana here.
- LLM normalization.

## Approach — normalize the Commons romaji directly

Input is the Commons category name (already Latin script for Japanese subjects, e.g.
`Category:Kiyomizu-dera`, `Category:Meiji Jingū`, `Category:Sensou-ji`). The normalizer:

1. **Strip** the `Category:` prefix and any bracketed disambiguator (`（）()〔〕`, e.g.
   `Kasuga-taisha (Nara)` → `Kasuga-taisha`).
2. **Detect the class suffix** and render the house form (the suffix *conventions* are reused from
   `temple_english.py` / `kana_english.py`; the romanization functions there are **not** — the input
   is already romaji, there is no kana to romanize):
   - **Temple** endings → `"<Stem>-<suffix> Temple"`: `-ji`, `-dera`/`-tera`, `-in`, `-an`, `-do`,
     `-bo`. If the Commons name already ends in ` Temple`, keep it.
   - **Shrine** endings → the established `kana_english.py` shrine renderings: `Jinja` →
     `"<Stem> Shrine"`; `Jingū`/`Jingu` → `"<Stem> Grand Shrine"`; `Taisha` → `"<Stem> Grand Shrine"`;
     `Daijinja` → `"<Stem> Daijinja"`; `-sha` → `"<Stem>-sha Shrine"`; `-gu`/`-gū` →
     `"<Stem>-gu Shrine"`. If the Commons name already ends in ` Shrine`, keep it.
3. **Macron restoration — best-effort, and deliberately different from the kana stage.** Apply
   `ou → ō`, `uu → ū`, `oo → ō` (and the long-vowel spellings that actually occur) **to the romaji
   spelling**. This is a real divergence to call out: the kana stage *collapses* long vowels
   Kyoto-style (`Senso-ji`, no macron), whereas this Commons stage *restores* them (`Sensō-ji`) —
   which is what enwiki does too, so it grades better. Where the Commons name gives no signal (a bare
   `Sensoji` that cannot be *known* to be `Sensō-ji` from romaji alone), output the un-macroned form.
   **A missed macron is acceptable output — the least-bad kind of romaji error — and is never a
   defect.** Consequence Emma has accepted: an item caught by the Commons stage gets a macroned label
   while one caught by the kana stage gets a collapsed one; the two stages' macron styles differ, and
   that is fine.
4. **Be conservative.** If the name has no recognised shrine/temple suffix, or the stem still
   contains non-Latin script, or it's obviously not a building (a festival, a deity, a sect), return
   `None` — no label rather than a wrong one. This mirrors the existing deterministic generators.

Output: a candidate house-style English label string, or `None`.

## Architecture — three isolated units

| Unit | Kind | Responsibility |
|---|---|---|
| `modern-quickstatements/commons_normalize.py` | pure, no I/O | `commons_name → candidate house label \| None`. Every rule lives here. Reuses the *suffix conventions* of `temple_english.py` / `kana_english.py` (not their kana-romanization functions — the input is already romaji). This is what the unit tests hammer. |
| `modern-quickstatements/report_commons_label_accuracy.py` | I/O + orchestration | Fetch the in-scope items (Commons category, and enwiki title for the gradeable subset), run the normalizer, grade, write the report. Uses `query-main.wikidata.org/sparql`, CSV bodies, 429-bails, throttled. |
| the report | output | `docs/commons_label_accuracy_<date>.md` + a machine-readable mismatch dump (`commons_label_mismatches.json`). Not registered anywhere. |

## The grader — score the *reading*, not the macrons

The naïve `candidate == enwiki title` reads ~0% for a dumb reason: enwiki writes `Kiyomizu-dera`,
the house style is `Kiyomizu-dera Temple` — the suffix is a deterministic house addition. So the
grader compares the **core reading** (stem + romanized suffix), treating the ` Temple`/` Shrine`
suffix as house-appended and macrons as best-effort. Each gradeable item (has Commons category **and**
enwiki title) lands in exactly one bucket:

- **exact** — core reading matches the enwiki title after normalizing case/whitespace and the house
  suffix.
- **macron-only** — differs *solely* by macrons. **Counted as acceptable, not a failure** — reported
  so Emma can see the rate, never held against the pipeline.
- **house-suffix-only** — differs solely by the ` Temple`/` Shrine` the house style adds and enwiki
  omits. Acceptable (it's the convention working), reported.
- **mismatch** — a genuinely different reading: wrong stem, wrong suffix, wrong hyphenation.
  **These are the real failures.** Every one is dumped in full (`qid`, Commons name, candidate,
  enwiki title) for inspection.
- **rejected** — normalizer returned `None`. Reported with why, to confirm it's rejecting junk and
  not real shrines.

**Headline metric:** core-reading accuracy = `(exact + macron-only + house-suffix-only) / gradeable`,
with the `mismatch` bucket enumerated so the failures are visible, not hidden behind a percentage.

## Success criteria / the no-edits gate

The build succeeds when it produces the report: coverage counts (in-scope items, gradeable overlap),
the bucket breakdown, the headline accuracy, and the full `mismatch` + `rejected` enumerations.
**No generator, no `.txt`, no edit** until Emma has read it and set an acceptance bar. That bar is
hers to set once the number exists.

## Testing

- `commons_normalize.py` is pure → a thorough unit suite over **real fixtures**:
  - macron restoration: `Sensou-ji → Sensō-ji`; and a bare `Sensoji → Sensoji` (missed macron is a
    *pass*, not a fail).
  - suffix detection: `-ji`/`-dera`/`-in`/`-an`/`-do`/`-bo` → ` Temple`; `Jinja`/`Jingū`/`Taisha` →
    house shrine form; already-suffixed input kept.
  - disambiguator stripping: `Kasuga-taisha (Nara) → Kasuga-taisha …`.
  - conservatism: non-building junk in the P31 sets (festival, deity, sect, `教会`) → `None`.
- The grader's bucketing is tested against hand-built `(candidate, enwiki-title)` pairs — one fixture
  per bucket, including a macron-only pair that must land in `macron-only` (acceptable) and not
  `mismatch`.

## Out-of-scope reminders (YAGNI)

No cross-language / nativized output, no foreign buildings, no edits, no kana, no LLM, no new
`ATOMIC_FILES` entry. This build is exactly: the romaji normalizer, its test suite, and the
accuracy report on Japanese shrines + temples.
