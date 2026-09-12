# How long until the queued Wikidata edits are all through?

First measured 2026-07-29 at Emma's request: *"we want to do some estimation of our queued-up
edits and how long it'll take our total queued-up edits to all go through."* Counts are read off
the working tree, not estimated.

⚠ **Re-measured 2026-09-12.** Every number below changed and two of the July figures described
machinery that no longer exists. The July text is not kept alongside — this file is the answer, not
a log, and a stale answer to a question someone asked is worse than none. What it used to say is in
`git log -- docs/wikidata-completion-estimate.md`.

## Throughput

One editing path only: `direct_daily_edits.py`, fired once per UTC day by
`cleanup-loop.yml`'s window-gate (the QuickStatements API path was retired 2026-07-04).

- **`_DEFAULT_MAX_EDITS = 500`** lines per day, randomly sampled from every atomic file.
  *(July said 300.)*
- Per-file daily caps: `description_label_pairs.txt` **100/day**, and `description_adds.txt`
  **50/day** until 2027-01-01, when that one lifts by date rule. *(July also listed
  `label_proposals_drip.txt` 20/day; that cap is gone. `sutra_profile.txt` 1/day and
  `sutra_label_rename.txt` 3/day were removed with the Sutra drip on 2026-09-12.)*
- **Currently running.** *(July said 0/day under `FREEZE_WIKIDATA_UNTIL = 2026-08-10`. That
  mechanism no longer exists: freezes are now one state file,
  `shinto_miraheze/wikidata_editing_lockout.state`, and the last Wikidata lockout expired
  2026-09-01. Never quote a freeze date — ask the state file.)*

## The committed queue: 124,429 lines

**81 files registered** in `direct_daily_edits.ATOMIC_FILES`, **78 present**. The three absent are
`souken_p571_citations.txt` and `saijin_named_as.txt` — generated but never committed until the
2026-09-12 `--full-name` fix to `generate-quickstatements.yml` — and `name_in_kana.txt`, which the
cloud routine's collector appends as answers arrive. Classified by QuickStatements column 2:
`L*`/`D*`/`A*` = language, `P*` = ontology.

| Bucket | Lines | Share | Days at 500/day |
|---|---:|---:|---:|
| **Ontology** (properties, qualifiers, references, removals, external IDs) | 105,421 | 84.7% | 211 |
| **Language** (labels, descriptions, aliases) | 19,008 | 15.3% | 38 |
| **Total** | **124,429** | | **249** |

**≈ 249 days — about eight months**, so roughly 2027-05 at the current rate.

The queue grew 106,166 → 124,429 while the rate rose 300 → 500, so the estimate *fell* from 354 days
to 249 despite 18,263 more lines.

Largest single files: `p6262_fandom_links` 12,779 · `derived_name_in_kana` 10,531 · `bunrei` 9,976 ·
`court_rank_people` 9,686 · `temple_identical_name_en_labels` 7,834 · `sango_p1448` 6,850 ·
`p11250_miraheze_links` 6,134 · `description_label_pairs` 5,869 · `saijin_deity_research` 5,426 ·
`list_membership_rebuild` 5,069.

⚠ **249 days is a floor, not a forecast.** It assumes 500 lines land every day. They do not: a line
whose statement already exists returns "Skipped (already exists)" and still consumes one of the 500,
the drip samples randomly rather than draining a file, and any lockout stops the day entirely.

## The part that does not terminate: the label reservoir

`shinto-label-generator/quickstatements/` holds the per-language proposal files, drip-fed into the
daily batch by `select_label_proposals.py`. This is a reservoir, not a backlog — the committed queue
above does not contain it, and it is not meant to drain.

⭐ **And none of this is a rate to improve.** CLAUDE.md, Emma 2026-08-24: *"We're not trying to be
fast with this project… This project is supposed to be slow."* The number exists to answer a
question she asked, not to set a target.
