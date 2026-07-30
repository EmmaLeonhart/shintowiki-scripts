# How long until the queued Wikidata edits are all through?

Measured 2026-07-29 at Emma's request: *"we want to do some estimation of our queued-up
edits and how long it'll take our total queued-up edits to all go through."* Counts are
read off the working tree, not estimated.

## Throughput

One editing path only: `direct_daily_edits.py`, fired once per UTC day by
`cleanup-loop.yml`'s window-gate (the QuickStatements API path was retired 2026-07-04).

- **`_DEFAULT_MAX_EDITS = 300`** lines per day, randomly sampled from every atomic file.
- Per-file daily caps override that for a few sources: `label_proposals_drip.txt` **20/day**,
  `description_adds.txt` 50, `sutra_profile.txt` 1.
- **Currently 0/day** — `FREEZE_WIKIDATA_UNTIL = 2026-08-04` forces `wikidata-daily-fire=false`.

## The committed queue: 106,166 lines

58 live atomic files (one listed file, `ronsha_ranking_qualifiers.txt`, does not exist).
Classified by QuickStatements column 2 — `L*`/`D*`/`A*` = language, `P*` = ontology.

| Bucket | Lines | Share | Days at 300/day |
|---|---:|---:|---:|
| **Ontology** (properties, qualifiers, references, removals, external IDs) | 84,631 | 79.7% | 282 |
| **Language** (labels, descriptions, aliases) | 21,531 | 20.3% | 72 |
| **Total** | **106,166** | | **354** |

**≈ 354 days — just under a year**, so roughly 2027-07 at the current rate, plus the freeze.

Largest single files: `p6262_fandom_links` 12,423 · `bunrei` 9,971 ·
`temple_identical_name_en_labels` 8,747 · `description_label_pairs` 7,897 ·
`sango_p1448` 7,709 · `saijin_deity_research` 6,939 · `saijin_p825` 5,795 ·
`list_membership_rebuild` 5,635 · `p11250_miraheze_links` 5,346 · `kana_qualifier_add` 4,965.

## The part that does not terminate: 5,250,144 lines

`shinto-label-generator/quickstatements/` holds **85 language files totalling 5.25 million
lines**, drip-fed into the daily batch 20 at a time by `select_label_proposals.py`. This is a
reservoir, not a backlog — the committed queue above does not contain it.

- At **20/day: ~262,500 days ≈ 719 years.**
- At the **full 300/day** budget, with everything else stopped: **~48 years.**

Throughput cannot fix this; only scope can. The driver is item count, not language count —
each language file covers the whole shrine/temple/deity corpus:

| Language file | Lines | Days at full 300/day |
|---|---:|---:|
| `ko` | 110,484 | 368 |
| `zh` and 8 zh-family variants (`zh-cn`, `zh-hans`, `zh-hant`, `zh-hk`, `zh-mo`, `zh-sg`, `zh-tw`, `gan`) | 106,904 each | 356 each |
| `dz`, `lo`, `mad`, `mai`, `new`, `shn` | 70,146 each | 234 each |
| `as`, `km`, `ur`, `ceb` | ~70,144 each | 234 each |

**One additional language costs roughly one year of the entire daily edit budget.** That is
the number that matters for any scope decision.

## Why this matches Emma's read

Her call, 2026-07-29: restraint on languages, *"let it rip"* on ontology, and she wants the
Wikidata work to **end on a relatively reasonable timeline.** The measurement supports the cut
exactly:

- **Ontology terminates.** 84,631 lines, 282 days, then done. Finite by construction — it is
  bounded by the number of shrines, deities and relationships that exist. Letting it rip costs
  under a year and buys a finished data model. This includes the items she named as possibly
  questionable (Motherhouse of Shrines and similar); they are a rounding error against 84k.
- **Languages do not terminate.** They are 20.3% of the committed queue but 98% of all
  outstanding work once the reservoir is counted.
- **Her "too dominated by the languages **in the future**" is precisely right**, and the
  mechanism is worth stating: the label drip is only 20 of 300 edits/day today — **6.7%**, not
  dominant. But it is the one source that never drains. When the atomic queue finishes in ~354
  days, the drip is the **only** thing left, and the edit stream becomes **100% language edits,
  permanently.** The domination is scheduled, not current.

## What would have to change for a fixed end date

Not a recommendation — the scope call is Emma's. The arithmetic:

- **Ontology only, drip off** → done in **~282 days**, one clean end date.
- **Ontology + finish the committed language files, drip off** → **~354 days.**
- **Ontology + N whole extra languages** → add **~234–368 days per language.**
- **Leave the drip on at 20/day** → no end date exists, by construction.

There is no throughput setting that makes the reservoir finite; the only lever is how many
languages are in scope.

## Emma's position, 2026-07-29 — held, not decided

She chose **hold and decide after the freeze** (Wikidata unfreezes 2026-08-04; nothing drains
before then either way). Her stated position, to be read as a live question rather than a
ruling:

- **The language labels are NOT being dropped.** She wants them to continue as part of the
  project **to some extent** — *"the degree of it is definitely questionable."* She is
  questioning them strategically, not rejecting them.
- **The queued ontology is very useful** and she wants it to run.
- **"Too hot to run"** is her concern about the language labels specifically — she expects a
  too-hot-to-run situation with them.
- **She appreciates the pipeline.** The question is scope, not machinery.
- Overall read: *"probably going to be able to get away with this, but it's not certain."*

### The two senses of "dominated" — both her statements are correct

She said both *"my edits are still mostly ontology-driven"* and *"what we're doing is dominated
by the language labels."* These are not in conflict; they use different denominators, and
keeping them apart is what makes the decision tractable.

| Denominator | Ontology | Language |
|---|---:|---:|
| **Daily flow** (300 edits/day, drip capped at 20) | **93.3%** | 6.7% |
| **Total outstanding** (committed queue + 5.25M reservoir) | 1.6% | **98.4%** |

What is currently *visible on-wiki* is ontology work. What is *committed* is overwhelmingly
language work. Both readings are live at once.

### Why "too hot" is corroborated, not just an instinct

`wikipedia-ai-cleanup-2026-07/RESEARCH-escalation-base-rate.md` (in the `funding-and-networking`
parent) names the live Wikidata-side grievance as **the Japanese shrine label disputes**. So the
language labels are not merely the theoretically most legible automated-editing signature — they
are the surface that has **already** drawn a complaint on the one wiki where a block would
matter. The ontology work has not.

### DECISION 2026-07-29: leave it running, languages included

Superseding the hold above (same day, after further thought). **No change to the pipeline.**

- **Let the language labels drip in.** Not ideal as a long-term scenario, by her own read, but
  fine to run in the short term.
- **Ontology continues** — *"just kind of fine to continue letting it go."*
- She expects to want to change this **maybe a month or 90 days out**, and is deliberately not
  doing it now. **That is her own estimate, not a deadline, and nothing is scheduled against
  it.** No cron, no calendar event, no board reminder. Do not re-surface it.

### The real question is programme shutdown, not language trimming

Her explicit reframe, and the better axis: *"it's more in the realm of — are we just going to
shut down this entire programme at some point."* The how-many-languages framing above was the
wrong cut.

On that axis there is a structural fact worth holding: **the decision point arrives on its own.**
The atomic queue drains in ~354 days, and on that day the programme either ends or converts into
pure language drip, because nothing else remains in it. No date needs to be invented or
scheduled for the question to present itself.

This also makes the short-term run cheap. At 300/day with the drip capped at 20, output stays
**~93% ontology for the next ~282 days** no matter what. Composition barely moves until the
ontology work is nearly finished, so deferring the call costs almost nothing.

### Cheapest scope cut available, if she wants one later

The reservoir's 85 files are not 85 distinct languages of content. **Nine zh-family variants —
`zh`, `zh-cn`, `zh-hans`, `zh-hant`, `zh-hk`, `zh-mo`, `zh-sg`, `zh-tw`, `gan` — carry an
identical 106,904 lines each**, ~962,000 lines total, for what is substantially one language's
content replicated across variant codes. That is simultaneously the largest single block in the
reservoir and the pattern that reads most like mass-produced filler. Collapsing it to one or two
variants removes ~18% of the reservoir at close to zero loss of actual language coverage.

Recorded as an option for the post-freeze decision. Not a recommendation and not scheduled.

## Method

Line counts from `direct_daily_edits.ATOMIC_FILES` (a superset of
`submit_daily_batch.ATOMIC_FILES`), non-empty lines only, classified on the second
pipe-delimited column. Reservoir counted over `shinto-label-generator/quickstatements/*.txt`.
No Wikidata or wiki requests were made — the Miraheze blackout runs to 2026-08-09 and the
Wikidata freeze to 2026-08-04.
