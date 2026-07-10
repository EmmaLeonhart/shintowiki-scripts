# P825 (deity) modelling on shrines & temples — statistical survey (2026-07-10)

Emma asked for a **statistical investigation of the qualifiers and references on
the deity property**, to find the established modelling so we can extend it — to
other properties, and to Buddhist temples. Tool: `investigate_property_modelling.py`
(reusable for any class × property). Live SPARQL over `query-main`.

## The numbers

| | Shinto shrine (Q845945) | Buddhist temple (Q5393308) |
|---|---|---|
| P825 statements | 14,408 over 11,496 items | 6,319 over 6,260 items |
| **Referenced** | **28.1 %** | **96.8 %** |

**Qualifiers — essentially unused (<1 %).** There is no established qualifier
convention on P825 to extend.

| Qualifier | Shrine | Temple |
|---|---|---|
| P1932 object named as | 80 (0.6 %) | — |
| P580 start time | 13 | — |
| P3831 object has role | 11 | 4 |
| P518 applies to part | 3 | 4 |
| everything else | ≤2 each | ≤2 each |

The **only** qualifier with any adoption is **P1932 "object named as"** — all 80 from
the Kanagawa Prefecture Shrine Records import (the model in Emma's screenshot). So
that model is a real but *minority* convention, not the norm.

**References — this is where the modelling actually lives.** Both classes are
dominated by the **"imported from" triple**:

| Reference property | Shrine | Temple |
|---|---|---|
| P143 imported from Wikimedia project (= Q177837 Japanese Wikipedia) | 3,371 (23 %) | 5,893 (93 %) |
| P4656 Wikimedia import URL | 1,453 (10 %) | 5,170 (82 %) |
| P813 retrieved | 1,430 (10 %) | 1,926 (31 %) |
| P854 reference URL | 587 (4 %) | 206 (3 %) |
| P248 stated in + P304 page + P9836 NDL Persistent ID | ~99 / 82 / 154 | ~12 |

Two coherent reference models, then:

1. **Bulk jawiki-import model (dominant):** `P143 = Q177837` (Japanese Wikipedia) +
   `P4656 = <import URL>` + `P813 = <retrieved date>`.
2. **High-quality sourced model (minority, growing):** `P248 = <work>` + `P304 = page` +
   `P9836 = NDL Persistent ID`. Works seen: Kanagawa Prefecture Shrine Records (77),
   興除村史, 狛江村誌, museum/city cultural-property databases, `information board`,
   `field research`.

## What this means for extension

- **Extending a property to shrines/temples is a REFERENCE problem, not a qualifier
  problem.** To add or extend any property (deities, founding dates, ranks, styles…),
  carry a proper reference; the house standard for a jawiki-field import is the
  imported-from triple `P143 Q177837 | P4656 url | P813 date`.
- **Our own jawiki field-importers currently emit only `S4656` (P4656 URL)** — a
  *subset* of the dominant triple (they omit `P143 imported from` and `P813 retrieved`).
  `generate_saijin_deity_research.py`, `saijin`, `honzon`, `reisai`, `souken` all do this.
  **Decision for Emma:** upgrade them to the full triple to match the corpus convention,
  or keep the lighter S4656-only form. This is a one-line change per generator; I did not
  make it unilaterally because it changes the reference model on live data.
- **The one qualifier worth carrying is P1932 "object named as"** (the source's exact
  name string) — already emitted by `generate_saijin_deity_research.py`. `P3831` primary-
  deity role is a deliberate new addition (Emma's), inherently sparse.
- The Kanagawa `P248 + P304 + P9836` book model is the template if we ever cite printed
  shrine records rather than jawiki.

## Reusable

`python investigate_property_modelling.py --class <QID> --property <P…>` runs the same
survey for any class/property (e.g. P571 inception, P149 architectural style, P140
religion) before we design its import — so we model to the existing convention instead of
inventing one.
