# Court rank on people (P14005): handoff from shintowiki-scripts

## What this is

Japanese court rank (位階, P14005) on **people** on Wikidata, read from the Japanese Wikipedia
category tree under [[Category:日本の位階受位者]] (Japanese court-rank recipients). Each person
gets every rank they held, with a reference to the jawiki article the rank was read from.

## Why it is moving here

- **It is a property on people.** It came from a Shinto shrine project
  (`EmmaLeonhart/shintowiki-scripts`), and it is the only large job there that edits people rather
  than shrines, temples or kami. This repository edits people.
- **Emma considers court ranks extremely important**, and does not think anyone else is likely to
  add them. So they have to be delivered somewhere.
- **The shrine repo's daily drip is scarce and unreliable right now.** It lands 500 edits on a
  good day and zero on a bad one, and it is being trimmed to shrine work. Court ranks were 10% of
  its queue.
- It moves cleanly: no other file in the shrine repo depends on these edits landing, and they
  depend on nothing there.

**This repository applies these ranks under its own rules and its own editing machinery.** Nothing
below overrides how this repository edits Wikidata. The rules in the next section describe the
data: what to add and what to refuse.

## The rules for the data (carry these over)

1. **Source:** for each subcategory of [[Category:日本の位階受位者]] named `<rank>受位者` (e.g.
   正一位受位者, 従四位上受位者), the rank is the text before `受位者`.
2. **Rank → item:** match that rank text against the **ja label** of items used as P14005 values
   (class *court rank in Japan*, `Q99196082`). No hardcoded QID table. This match also filters out
   the special subcategories (失位・返上を命じられた者, 位階を持たない者, …), because they don't
   name a rank item. **42 rank categories resolve**, including the 26 sub-rank items Emma created
   (`Q140679480` … `Q140679509`).
3. **Skip 无位** (no rank, `Q11504610`).
4. **Members:** collect each rank category's article pages (namespace 0) recursively. Anything under
   a rank category still holds that rank. Resolve each page to its QID through jawiki `pageprops`
   (`wikibase_item`). **When recursing, don't also tag a person with a coarser parent rank** that
   only appears because a finer category sits under it.
5. **Every rank a person held**, not just the highest.
6. **Reference:** `S143 = Q177837` (imported from Japanese Wikipedia) + `S4656 = <jawiki article URL>`.
7. **Skip a person→rank pair whose statement already carries a reference.** If the statement exists
   without a reference, **add the reference to that statement**; don't create a duplicate.
8. **Add-only.** Never remove a P14005.
9. **Known risk:** being in a category is taken as proof of the rank. There is no article-text check.
10. **WDQS etiquette:** on HTTP 429, stop immediately.

## State at handoff (2026-09-27)

- **5,418 P14005 statements already exist** on Wikidata. About 2,354 are referenced; 3,064 are
  bare.
- **Pending:** 12,448 people → 12,380 lines. **9,316 are new statements**, and 3,064 add a
  reference to an existing bare statement.
- In the shrine repo it is paused from the drip and its generation step is removed from CI. None of
  those pending lines will be sent from there.

## Source code in the shrine repo (public)

Pinned to the handoff commit:

- Generator (375 lines):
  <https://github.com/EmmaLeonhart/shintowiki-scripts/blob/dc596f87f4ec58da75cfbb9659ad7aa9ee52898c/modern-quickstatements/generate_court_rank_quickstatements.py>
- Last generated output (12,380 QuickStatements lines,
  `QID|P14005|<rank QID>|S143|Q177837|S4656|"<jawiki url>"`):
  <https://github.com/EmmaLeonhart/shintowiki-scripts/blob/dc596f87f4ec58da75cfbb9659ad7aa9ee52898c/modern-quickstatements/court_rank_people.txt>

The generator imports three shrine-repo helpers that won't exist here: `shinto_miraheze.ua_contact`,
`shinto_miraheze.wikidata_user_agent` (the Wikidata User-Agent) and `wdqs_transport` (WDQS POST with
backoff). Replace them with this repository's own equivalents. Its flags are `--highest-only`,
`--max N` and `--dry-run`.

The pending list is regenerated from live Wikidata each run. **Re-run the generator logic here
rather than replaying the old .txt**, so pairs that landed since 09-26 aren't sent twice.
