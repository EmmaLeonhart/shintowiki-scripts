# How far the shrine/temple data model has become the norm on Wikidata

Measured 2026-07-28, live against WDQS + the Wikidata read API. Reproduce with
`python modern-quickstatements/audit_model_adoption.py --attribution`
(read-only; safe under the edit freeze). Raw numbers: `modern-quickstatements/model_adoption.json`.

Populations: **30,274** Shinto shrines (P31=Q845945), **27,174** Japanese
Buddhist temples (P31=Q5393308).

Three separate questions, kept apart because they have three different answers:

* **Coverage** — of the population, how many items carry the statement at all.
* **Conformance** — of the statements that exist, how many carry the full
  modelled shape (required qualifier / reference).
* **Reach** — how much of that property's or role's use *across all of Wikidata*
  is this model, and whether anyone other than Immanuelle produces it.

## The short answer

The model has become the norm at the **ontology layer** and has not at the
**statement-shape layer**.

Seven Wikidata properties and the whole Shinto class vocabulary now exist
because of this work, and the community's own bots maintain data inside them —
that is adoption in the strongest available sense. But the reisai, bunrei,
shintai and sangō *statement shapes* are, on sampling, produced by one editor:
they are internally near-perfectly conformant and externally close to invisible.
Where the underlying property is one the wider community already used (P825 for
enshrined deities), the majority of the data is other people's and does not
follow the model.

## Layer 1 — the ontology: adopted

**Properties.** 20 property proposals opened; **7 became live properties**:

| Property | Proposed as | Created |
|---|---|---|
| P13723 shrine ranking | Modern Shrine Ranking | 2025-08-22 |
| P14005 Japanese court rank | Divine Rank | 2025-12-18 |
| P13677 Kokugakuin University Digital Museum entry ID | (same) | 2025-07-29 |
| P13930 Genbu.net ID | (same) | 2025-11-12 |
| P13991 Encyclopedia of Shinto ID | (same) | 2025-12-11 |
| P14332 heir apparent | (same) | 2026-04-10 |
| P14391 Shinmei database ID | (same) | 2026-05-04 |

Six were withdrawn (Engishiki Rank, Engishiki Funding Category, Engishiki
celebration category, Suijaku Kami, Gifu Prefectural Shrine Association ranking,
Kokugakuin god-name database ID); four closed *not done* (Source Shrine, Day of
Reisai, Honji Buddha, Grokipedia ID); three are unresolved. All proposals were
created and argued by Immanuelle; the properties themselves were created by the
standard property creators (ArthurPSmith).

**Classes.** The Shinto ranking/registry vocabulary these properties take as
values was created by Immanuelle outright — Shikinaisha (Q134917286, 2025-06-15),
Shikinai Ronsha (Q135022904, 2025-06-23), Disputed Shikinaisha or Shikigeisha
(Q135038714, 2025-06-24), Kokuhei-sha (Q135160342, 2025-06-30), Kokugakuin
University Shrine database (Q135159299, 2025-06-30), autochthonous shrine
(Q135508874, 2025-07-30).

**The decisive evidence is what other people's bots now do with them.** On
sampled items, the P14005 statements were not added by Immanuelle at all —
15 of 15 were added by **Louperibot**, with the edit summary *"Replacing P31
with P14005"* (2025-12-19), the community's standard post-creation migration.
The same bot came back on 2026-01-05 to update **P13723** qualifiers. Wikidata's
own maintenance machinery is now moving Shinto data into these properties and
maintaining the qualifier shape. That is the point at which a model stops being
one editor's convention.

## Layer 2 — statement shapes: high conformance, low coverage

| Model | Shape | Coverage | Conformance |
|---|---|---|---|
| Shrine ranking | P13723 + P459 determination method | 8,188 items · 16,995 stmts | **16,995 / 16,995 = 100%**; 98.9% referenced; **0** legacy values left on P1552 |
| Court rank | P14005 | 936 items (923 shrines) · 2,000 stmts | 99.2% referenced; 16 distinct rank values |
| Reisai | P837 + P3831=Q11385469 (+P793) | 247 shrines (0.8%) · 256 stmts | **254 / 256 = 99.2%**; 101 (39%) carry the P793 festival qualifier; 88% referenced |
| Bunrei | P612 + P1013=Q195793 | 357 shrines (1.2%) · 359 stmts | **350 / 359 = 97.5%**; **9 bare P612 remain** |
| Engishiki list membership | one P361 + P1545 ordinal | 5,413 shrines · 6,343 stmts | 5,125 (80.8%) carry an ordinal; **647 items still carry more than one P361** |
| Shikinai Ronsha | P460 + P2868/P3831 roles | 2,323 ronsha, 2,058 with P460 | 1,613 (78%) carry P2868; 14 carry P3831; 0 typed Shikinaisha. 7 items carry a deprecated statement — see §1, that is correct, not a shortfall |
| Shintai | P825 + P3831=Q327532 | **6 statements** | 100%, on a population of 6 |
| Sangō | P1448 + P3831=Q11058522 | 139 stmts (135 on temples) of 8,469 temple P1448 statements = **1.6%** | 100% |
| Saijin | P825 on shrines | 11,582 shrines (38.3%) · 14,604 stmts | **4,243 (29%) referenced** |
| Honzon | P825 on temples | 6,264 temples (23.0%) · 6,327 stmts | **6,122 (96.8%) referenced** |
| Souken | P571 inception | 990 shrines (3.3%), 2,639 temples (9.7%) | — |
| Identifiers | on shrines | P13677 5,092 (16.8%), P11250 3,606 (11.9%), P6262 555 (1.8%) | — |
| English labels | — | shrines 25,350 (83.7%), temples **11,645 (42.9%)** | — |

Where the pipeline runs, it runs clean: P13723 is 100% qualified and 98.9%
referenced across 17k statements, and the legacy P1552 ranking population is
fully drained. Reisai and bunrei are ~98% conformant. The gap is not model
discipline, it is volume — reisai reaches 0.8% of shrines and bunrei 1.2%.

## Layer 3 — reach and attribution

**Reach of the qualifier shapes across Wikidata:**

* P837 (day in year for periodic occurrence): 7,096 statements exist Wikidata-wide;
  282 carry any P3831 role, and **262 of those 282 (93%) are the reisai role** —
  but that is only **3.7% of P837 overall**. Qualifying P837 with a role is
  essentially a Shinto-only practice.
* P612 (mother house): 1,196 statements Wikidata-wide. **350 (29.3%) now carry
  P1013=Q195793**, and every single P1013-qualified P612 on Wikidata is the
  bunrei model (350 of 350). Nearly a third of the world's P612 statements are
  this model, and zero are anyone else's use of the qualifier.
* P3831=Q327532 (shintai) and P3831=Q11058522 (sangō) remain what they were at
  creation: uses that exist only here (6 and 139).

**Who adds the statements** (15-item samples, attributed from the revision
comments that name the property):

| Model | Introduced by |
|---|---|
| Bunrei P612 | Immanuelle 15/15 |
| Ranking P13723 | Immanuelle 15/15 (Louperibot subsequently on 14/15) |
| Court rank P14005 | **Louperibot 15/15** (property migration) |
| Reisai P837 | Immanuelle 11/15, Mzaki 2/15 |
| Saijin P825 (shrines) | Immanuelle 6, Aiaiaiaiaia 5, Syced 3, Ultratomio 1, Akas1950 1, Higa4 1 |
| Honzon P825 (temples) | Aiaiaiaiaia 2, XIIIfromTOKYO 2 (11 of 15 unattributable — see caveats) |

The split is sharp. On the properties this project created, the statements are
either hers or a community bot's migration of them. On P825 — a property the
Japan-topic editors were already using — the model is a minority contributor to
a pre-existing pool, and the reference discipline shows it: temple honzon, which
this pipeline imported, is 96.8% referenced; shrine saijin, which is mostly
inherited community data, is 29% referenced.

## Where it is not the norm, and why

1. **Ronsha deprecation never happened — and on the evidence it should not.**
   (Corrected 2026-07-28 after Emma pushed back on the first draft, which filed
   this as an unmet obligation. It is not one.) The claim that a ronsha's
   Engishiki statements need deprecating comes from the global CLAUDE.md task
   card, not from this repo's model doc, and the data does not support it:

   * **The dispute is already modelled without touching rank.** **0** of 2,323
     ronsha are typed Shikinaisha — the P31 layer never asserts "this IS the
     Engishiki shrine." 2,058 carry P460 (disputed identity) and 1,613 carry the
     P2868 role on it. The hedge is in the class and the qualifier, which is
     where it belongs.
   * **Deprecation is the most conspicuous mechanism available**, and this repo's
     standing rule is that visibility on Wikidata is a worse outcome than losing
     data. Flipping 5,362 P13723 statements across 2,300 items to deprecated rank
     is about as visible as a bot can be. For scale: **61** deprecated statements
     exist across all 30,274 shrines on Wikidata.
   * **Emma's own later decisions chose removal, not deprecation** — 2026-07-09:
     *"on the actual shrine item, remove every part-of→Shikinaisha-list
     statement"*, *"Ronshas should not even have list membership."* That is
     `generate_list_membership_removals.py`, and it needs no rank support.

   So 7 is the right order of magnitude, not a shortfall. The real residue is
   **2,256 ronsha carrying P361 list membership when the lists name only ~126 of
   them** — a genuine defect with a sanctioned add-first/remove-later fix that
   never required rank.

   What IS broken is the documentation: the global CLAUDE.md still lists
   "Shikinai Ronsha Property Deprecation" as ⭐ CURRENT TASK, pointed at
   `deprecate_engishiki_shrine_properties.py`, a bespoke direct-API editor that
   does not exist in this repo and whose shape the one-path Wikidata rule
   retired. Neither QuickStatements v1 nor `direct_daily_edits.py` can set a
   statement rank, so that card describes a workflow that cannot run.
2. **The two shapes with no reach are the two the community declined.** *Source
   Shrine* and *Day of Reisai* were both closed **not done**; the P612+P1013 and
   P837+P3831 constructions are the workaround built on generic properties after
   the dedicated properties were refused. Nobody else uses them because nobody
   else was told to — unlike P13723/P14005, no property page, constraint set, or
   bot migration advertises them. If those two models are meant to spread, the
   lever is a documented constraint on the qualifier, not more statements.
3. **List membership is 12% dirty.** 647 shrines still carry more than one P361
   list statement — the piped-link import damage the rebuild script targets.
   19% of list statements have no ordinal.
4. **Shintai (6) and sangō (139) never landed.** Both generators exist and both
   models are 100% conformant on what exists; the imports have not been run at
   volume.
5. **Temple English labels sit at 42.9%** against 83.7% for shrines. The temple
   label pipeline is roughly where the shrine one was several passes ago.

## Caveats on the method

* Attribution samples are 15 items drawn from a `LIMIT 400` result set, which
  WDQS does not randomise — directional, not a population estimate.
* Attribution reads MediaWiki auto-comments, which name the property
  (`[[Property:P825]]`). Statements added in an item-creation edit
  (`wbeditentity`) carry no property in the comment, so they are unattributable;
  that is why the honzon sample only resolved 4 of 15, and it biases against
  bulk-created items.
* Counts are `COUNT(DISTINCT ?statement)` per metric, one metric per query.
  Do not reintroduce OPTIONAL joins: a statement with two references gets
  counted twice, which inflated the first pass of this audit (P13723 read
  19,939 statements against a true 16,995).
* Populations use direct `P31` only, matching the rest of the repo. Shrines
  typed solely by a subclass (Q135160342 Kokuhei-sha etc.) are outside the
  denominator.
