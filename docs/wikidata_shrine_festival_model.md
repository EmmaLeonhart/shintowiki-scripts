# Wikidata data model: shrine festivals, reisai, and bunrei

Set by Emma 2026-07-07 (after a day of iteration — treat this file as the
authority; do NOT re-derive the model from existing statements, which may
predate it). Violations of this model appeared and were repaired on
2026-07-07; the repair machinery is listed at the bottom.

## The reisai / annual-festival statement (single statement)

A shrine's annual festival day lives in ONE P837 statement carrying
everything:

```
<shrine>  P837 (day in year for periodic occurrence)  <day item | Q19798648 unknown value>
          qualifier P3831 (object of statement has role) = Q11385469 (Reisai)
          qualifier P793  (significant event)            = <festival item, if one exists>
          reference S4656 <jawiki URL>                     (when from the jawiki 例祭 import)
```

* **P3831 holds a ROLE item only** — normally Q11385469 (Reisai); other role
  items (e.g. Q70460346 "biannual event") are permitted. It must NEVER point
  at a specific festival item — that was the 2026-07-07 modeling error.
* **The festival item goes in P793** — as a QUALIFIER on the P837 statement
  ("significant event qualifier"), not competing with the role.
* Day = the shrine's date from our reisai QS (jawiki 例祭); if no date exists
  in our QS, use **Q19798648 (unknown value item)** as the P837 value — do
  NOT look dates up from the festival item or elsewhere.
* Main-statement P793 on shrines is for HISTORICAL significant events
  (fires, reconstructions, battles, relocations) — recurring festivals do
  not belong there.

## The bunrei / mother-house statement (single statement)

```
<shrine>  P612 (mother house)  <head-shrine item | Q135508874 autochthonous shrine>
          qualifier P1013 (criterion used) = Q195793 (Bunrei)
          reference S854 <source URL>       (per-source citation)
```

* Every P612 statement carries the P1013=Q195793 qualifier in the SAME
  statement — no bare P612.
* P612 points at the network HEAD (総本社), or Q135508874 for shrines with
  no mother house (autochthonous/indigenous origin).

## Repair / guard machinery

* `modern-quickstatements/generate_bunrei_qualifier_repair.py` — SPARQLs for
  bare shrine P612 statements and emits P1013 qualifier-add lines
  (self-healing, in the daily drip; wired in generate-quickstatements.yml).
* The P3831 model violation (festival items in the role qualifier) was
  repaired 2026-07-07 via a manual browser batch (statement remove +
  clean re-add with refs preserved). No automated guard exists: the fix
  shape is remove+re-add, which is NOT safe for the random-order daily
  drip (the remove could land without the add). If violations recur,
  rebuild the batch from live SPARQL — see the session notes in DEVLOG
  2026-07-07 — and have Emma run it sequentially in the browser.
* Monitors: {{Wikidata list}} tables on d:Talk:Q11385469 (reisai) and
  d:Talk:Q195793 (bunrei) — ListeriaBot-refreshed views of both models.
