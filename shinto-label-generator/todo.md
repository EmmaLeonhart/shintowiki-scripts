# Todo

## Long-term goal

Every Shinto shrine, temple, deity, and related entity on Wikidata should have labels in all supported languages. Reference example: [Ise Jingu (Q687168)](https://www.wikidata.org/wiki/Q687168) — ideally every language column filled.

---

## New language support

- Expand to cover the top 10-20 most spoken languages
- ~~Hindi (Devanagari)~~ Done

## Japanese-only shrine labels (~10,000 shrines)

Many shrines on Wikidata only have a Japanese label. We need a pipeline to generate proposed Indonesian labels from kanji/kana, which then feeds into all other language pipelines.

- [x] Build a pipeline that generates Indonesian proposed labels from kanji and kana for Japanese-only shrines
  - Use furigana/reading data from Wikidata items when available
- [x] Output to a dedicated CSV file with proposed Indonesian labels
- [x] Use these proposed Indonesian labels as input for all other language pipelines (English, French, and all existing languages)
- [x] Keep proposed-label QuickStatements separate (at the bottom of the page / in a distinct section) since they are less established

## Fill gaps in English, French, and Indonesian labels

Some shrines have labels in some of these languages but not all three — usually due to past technical issues.

- [ ] Analyze existing English, Indonesian, and French labels to identify gaps
- [ ] Build a regularization pipeline to fill missing labels where the other two exist
- [ ] Generate proposed labels for the gaps

## QuickStatements transparency

- [ ] Add comments to QuickStatements output showing the source/derivation of each label
  - Most languages derive from the Indonesian label — show the Indonesian and English labels alongside
  - Chinese labels derive from Japanese kanji — show the Japanese source
  - Korean labels should note whether they come from sino-Korean reading (kanji) or romanization (Indonesian label)

## Expand beyond shrines

See **[PLAN.md](PLAN.md)** for the formal expansion roadmap.

- [ ] Translate names of deities (kami, Buddhas) into all supported languages
- [ ] Translate Engishiki-related entities (shrine ranks, etc.) into all supported languages
- [ ] Translate Wikidata property names into all supported languages (investigate whether QuickStatements can edit property labels)
- [ ] Some deity/entity names can be done algorithmically; others will need AI-assisted translation

## Temple handling

- [x] Clarify and document current temple handling in the pipeline (Added support for Wihara prefix and Temple suffix logic)
- [x] Ensure temples are treated consistently across all languages

## Build / CI

- [x] Investigate and fix any build failures in GitHub Actions
