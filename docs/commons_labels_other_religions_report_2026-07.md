# Speculative report — extending Commons-label derivation to other religious buildings (2026-07-08)

Emma's wiki-queue ask: size how the shrine/temple Commons→English-label derivation
(`modern-quickstatements/generate_commons_labels.py`) would extend to Mosques, Churches,
Hindu Temples, non-Japanese Buddhist Temples, Synagogues, Gurdwaras. **Report only — no
generator built, no edits proposed.**

## Sizing (query-main SPARQL, 2026-07-08; items with a Commons sitelink or P373 and NO English label)

| Class | P31 | Targets | Sample derived labels |
|---|---|---:|---|
| Mosque | Q32815 | **256** | Darolaman Mosque; Azghad Mosque; Adana New Mosque; Erenköy İstasyon Camii |
| Church building | Q16970 | **18,377** | Matthäuskirche; Zur heiligen Dreifaltigkeit; Ägidiuskirche; Kościół Najświętszego Zbawiciela w Poznaniu |
| Synagogue | Q34627 | **459** | (samples 502'd; count solid) |
| Hindu temple | Q842402 | **5** | Sobhaneswara Temple; Sri Sri Korunamoyee Kalibari; Hindutempel Basel |
| Buddhist temple, non-Japan | Q866985 − P17:Q17 | **0** | — |
| Gurdwara | Q841977 | **0** | — |

Total ≈ 19,100, of which 96% is churches.

## The transfer problem: Latin script ≠ transliteration outside Japan

The shrine pipeline's core assumption is that a Latin-script Commons category name for a
Japanese subject is a *romanization* — inherently the right English label ("Engaku-ji").
That assumption **breaks for churches**: their Commons names are native-language text that
happens to be Latin script (Matthäuskirche, Kościół Najświętszego Zbawiciela). Deriving
`Len` from those imports German/Polish/etc. names as English labels. Wikidata does accept
same-string proper-name labels across languages, but that's a policy call, not a
mechanical extension — and the plausibility guard (`must contain Latin letters`) can't
distinguish transliteration from native text.

Uniqueness would also gut the church set: common dedications (Matthäuskirche, dozens of
cities) collide with existing (label, description) pairs en masse, so realizable yield is
far below 18,377 and each survivor drags in the description-enrichment machinery.

## Assessment

* **Plausible, small, clean:** mosques (256) + synagogues (459) + Hindu temples (5) ≈ 720
  items. Mosque/synagogue Commons names in the samples are already Anglophone-register or
  established local names — same character as the shrine set. A one-flag class extension
  of the existing generator would cover them.
* **Not a mechanical extension:** churches. Needs Emma's call on whether native-language
  Latin names are acceptable as `Len`, plus tolerance for heavy collision loss. If wanted,
  it should be its own tranche, not folded into the shrine file.
* **Empty:** non-Japanese Buddhist temples and gurdwaras — zero targets under these P31s
  (their commons-linked items either already carry English labels or use other classes).

No action taken; awaiting Emma's read.
