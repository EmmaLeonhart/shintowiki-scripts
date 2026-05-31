# Wiki-content backlog — scripting plans (2026-05-30)

**Status: DESIGN ONLY.** This document plans how scripts *could* drain the
remaining wiki-content backlog in `todo.md`. Nothing here has been built or run
against the wiki. It is the input for deciding what to actually implement next
session.

## Standing constraints (apply to every plan below)

- **Wiki writes run on GitHub Actions, never locally** — the dev session has no
  wiki write creds. Every writing script gets wired into `wiki-cleanup.yml` (or
  the cleanup loop) and runs there with `${{ secrets.WIKI_PASSWORD }}`.
- **`THROTTLE = 2.5`** between `page.save()`; ~`0.3s` between read-only API calls
  inside redirect/lookup followers; every script bounds its per-run page visits
  with an explicit cap (`MAX_PAGES_PER_RUN`-style) so it can never hang the loop.
- **`--apply` / `--max-edits` / `--run-tag`** on every writing script; default
  dry-run; `mwclient`; UTF-8 stdout wrapper; Miraheze-UA-compliant user agent.
- **Wikidata is edited by ONE path only**: generators emit QuickStatements lines
  (no edit summaries) into atomic `.txt` files under `modern-quickstatements/`;
  `submit_daily_batch.py` runs them, `direct_daily_edits.py` falls back to ~50.
  Never a bespoke direct-API Wikidata editor. **Wikidata freeze is in effect to
  2026-06-06** — anything Wikidata-side is built now, fires after.
- **Reviewable multi-cycle pacing**: migrations pass through human-readable
  intermediate states (a review category, a CSV, an on-page banner), each cycle
  advancing one observable step, but never *gated* on a human looking.

## Current detection state (what already exists after 2026-05-30)

| Backlog item | Tracking category | Populated by | Count |
|---|---|---|---|
| 2. ILLs w/o WD= | `Pages with unresolved QID in ill template` | `unresolved_ill_qid` op (NEW) | grows as orchestrator sweeps |
| 3. Duplicate-QID tail | `Double category qids` | historical | 7 |
| 4. Multiple `{{wikidata link}}` | `Pages with multiple wikidata links` | `multiple_wikidata_links` op (NEW) | grows as orchestrator sweeps |
| 5. Deleted Wikidata items | `Pages with deleted QID in ill template` | `deleted_qids_in_ill` op | 144 |

Detection for items 2 and 4 shipped this session as orchestrator ops. So the
plans below for those two are about the **fix / surface** stage, not detection.

---

## 1. Japanese category-name translation — THE big one (~1171 subcats)

`[[Category:Japanese language category names]]` holds **1171 subcategories** whose
titles are in Japanese script. Two very different populations live in it:

- **Dated maintenance cats** — e.g. `Articles lacking sources from 2016年5月31日 (火) 13:15 (UTC)`,
  `Articles lacking in-text citations from 2020年2月`, `WikiProject用テンプレート`.
  These came from imported enwiki/jawiki maintenance templates. Their English
  form is **deterministic** (a date/format transform), not a translation problem.
- **Content cats** — e.g. `さいたま市の神社` ("Shinto shrines in Saitama"),
  `いなべの Municipal History`. These need real translation/transliteration, but
  most follow a small set of productive patterns (`<place>の神社`, `<place>市`,
  `<place>県`).

### Trigger & shape

A **standalone generator** (`generate_category_translation_moves.py`) that emits
a `category_moves.csv`, consumed by the **existing `move_categories.py`** in a CI
step. Do NOT write a new mover — `move_categories.py` already does exactly the
right thing: recategorize members source→dest, move the page leaving a redirect,
and tag `{{category move error|DEST}}` when the destination already exists. The
only new code is the **naming logic** that produces the CSV.

This is NOT an orchestrator op — it's a category-enumeration + naming pass, not a
per-page namespace sweep.

### Enumerate

`categorymembers` with `cmtype=subcat` + continuation over
`Category:Japanese language category names` (1171 → ~3 paged requests, throttled).

### Classify (regex buckets, in priority order)

1. **Dated maintenance — `<English prefix> from <JP date>`.** Match a known set
   of imported maintenance prefixes; map the trailing JP date to English:
   - `YYYY年M月` → `Month YYYY` (`2020年2月` → `February 2020`).
   - The long malformed timestamp forms (`…2016年5月31日 (火) 13:15 (UTC)`) →
     normalise to the month form (`…from May 2016`); the day/time/weekday is
     import noise and should be dropped, collapsing many timestamp variants onto
     one canonical English month category (these MERGE — destination will often
     already exist, so `move_categories.py`'s conflict path recategorizes via the
     CSV and the duplicates drain).
   - Pure-template cats (`WikiProject用テンプレート` → `WikiProject templates`) get
     a small hand-maintained lookup table.
2. **Productive content patterns — suffix/gazetteer mapping.**
   - `<place>の神社` → `Shinto shrines in <place-EN>`; `<place>の寺` → `Temples in
     <place-EN>`; `<place>県` → `<place-EN> Prefecture`; `<place>市` →
     `<place-EN> (city)` / `<place-EN>`. Needs a **place-name gazetteer**
     (Japanese → English) — bootstrap it from Wikidata labels of the place items.
3. **Wikidata-anchored fallback (strongest single signal).** If the category page
   carries `{{wikidata link|Q…}}` (or one resolves), fetch that item's **English
   label / enwiki sitelink** and use it as the canonical English title. This
   trumps pattern-guessing when available.
4. **Residual human queue.** Anything none of the above resolves confidently is
   written to a report (and tagged into a review category, below) — **never
   guessed**.

### Canonical-name choice rule

Wikidata English label/sitelink (3) > deterministic date transform (1) >
pattern+gazetteer (2) > human. Emit the chosen destination and the *reason* into
the CSV as a comment column so the human review artifact explains itself.

### Migrate via a review buffer (NOT a transactional rename)

Mirror the `resolve_double_category_qids` review-buffer pattern:

| Cycle | Action | Wiki state after |
|---|---|---|
| N | Generator tags each in-scope Japanese cat with a merge-notice banner + `[[Category:Proposed category translations]]`, and appends its `(source,dest,reason)` row to `category_moves.csv` (committed to the repo — the human-readable review artifact). | Japanese cats visibly proposed-for-move; CSV reviewable in the repo/PR. |
| N+k | `move_categories.py` consumes the CSV (bounded by `--max-edits`): recategorizes members, moves page→redirect, or tags `{{category move error}}` on collisions. | Members on English cats; Japanese cats become redirects; collisions visibly flagged. |
| N+k+1 | `delete_unused_categories` sweep removes now-empty redirected Japanese cats per existing policy; residual `{{category move error}}` pages await human merge. | Clean English cats; only genuine conflicts remain for a human. |

The CSV is the review surface — a human can edit/delete rows before the move
step runs. The banner + `Proposed category translations` category make it visible
on-wiki. Nothing is gated on the human; absent intervention the moves proceed.

### Pacing / throttle / reviewability

`THROTTLE=2.5`; `--max-edits` small per cycle (e.g. 50–100) so 1171 drains over
many cleanup cycles, each observable. The recategorize-then-move ordering is
already conflict-safe in `move_categories.py` (edit-conflict retry built in).

### Effort: **LARGE.** The mover exists; the naming logic is the work — the date
transform and template lookup are quick wins; the place gazetteer + Wikidata-label
resolver are the bulk; the residual human queue is unavoidable. Phase it:
(a) dated/maintenance (deterministic, biggest single chunk), (b) Wikidata-label
resolvable, (c) gazetteer patterns, (d) human queue.

---

## 2. ILLs without `WD=` / "Unknown" targets — fill the resolved ones

**Detection done** (`unresolved_ill_qid` op → `Pages with unresolved QID in ill
template`). Remaining: a filler that resolves the QID where it can, *without
blind overwrite*.

### Trigger & shape

`fix_ill_destinations.py` — a **standalone, category-driven** script (input is the
tracking category, not a namespace sweep → not an orchestrator op). Bounded by
`--max-edits`, stateless.

### Resolution strategy (only fill when confident; never overwrite an existing qid)

For each page in the category, for each `{{ill}}` lacking a valid `qid=Q\d+`
(skip `qid=DELETED_QID` — that's item 5):

1. **enwiki pageprops (strongest).** Take the call's English target (canonical
   positional[0] or an `en|Target` pair), query `en.wikipedia.org` `action=query
   prop=pageprops` for `wikibase_item`. If it returns a QID → that's the target.
   This catches cases the sitelink matcher in `normalize_ill_wikidata` Mode B
   misses (Mode B only resolves from the cleaned interwiki pairs).
2. **Mode-B sitelink resolution** for non-en pairs (reuse
   `wikidata_lookup._resolve_qid_from_sitelink`): a *single* unique QID across all
   pairs → use it; **2+ distinct QIDs → do NOT fill**, leave for review.
3. **Literal "Unknown" / no resolvable target →** leave untouched; it stays in the
   category and surfaces on the dashboard as work that needs a human or a new
   enwiki article.

Fill only writes `qid=Q…` into a call that had none — never changes an existing
value. The `unresolved_ill_qid` op then self-heals the page out of the category
on the next sweep once all its ills carry a qid.

### Note

`normalize_ill_wikidata` already does Mode-B resolution but is gated behind
`ENABLE_NORMALIZE_ILL_WIKIDATA` (per-cycle API churn). `fix_ill_destinations.py`
adds the **enwiki-pageprops** resolver (step 1), which is the new capability;
consider whether to fold it into that op instead of a separate script once proven.

### Effort: **MEDIUM.** Resolution logic is well-understood; enwiki pageprops is a
clean strong signal. Reviewability = a report of the ambiguous (2+ QID) cases.

---

## 3. Duplicate-QID tail — surface the 7 for human review

`[[Category:Double category qids]]` holds **7** pages — the residual
*multiple-distinct-existing-target* cases that `resolve_double_category_qids.py`
deliberately leaves for a human (the single-target ones already auto-redirect).

### Trigger & shape

A **render-once standalone** (`report_double_qid_tail.py`, like
`find_duplicate_page_qids.py`) — no state, no writes to content pages. For each of
the 7 dab pages: list the competing category targets, whether each exists, its QID
(from the category's `{{wikidata link}}`), and its member count. Output to a wiki
review page (e.g. a subpage of a maintenance project) or a `docs/` report.

Once a human picks the winner, the decision feeds `move_categories.py` (recategorize
losers → winner) or a manual `#REDIRECT`. No new mover needed.

### Effort: **SMALL.** 7 pages; the resolver already classifies them — this is a
read-only presentation of the residual it set aside.

---

## 4. Multiple `{{wikidata link}}` on one page — surface competing QIDs

**Detection done** (`multiple_wikidata_links` op → `Pages with multiple wikidata
links`). These are almost always a Wikidata disambiguation issue (the page maps to
2+ items; usually one is correct, or the page should be split).

### Trigger & shape

A **render-once standalone** (`report_multiple_wikidata_links.py`) consuming the
category. For each tagged page, extract the QIDs from each `{{wikidata link|Q…}}`,
fetch each item's label/description, and present them side by side so a human can
pick the correct one (delete the others) or decide the page needs splitting.
Read-only on content; output a review report/page.

### Effort: **SMALL.** Pure surfacing; the op does the detection and self-heals the
page out of the category once it's down to one link.

---

## 5. Recreate deleted Wikidata items — QuickStatements CREATE blocks

`[[Category:Pages with deleted QID in ill template]]` holds **144** pages whose
`{{ill}}` pointed at a Wikidata item another editor deleted (marked
`qid=DELETED_QID` by `deleted_qids_in_ill`). Recreate them via the QS pipeline.

### ⚠️ Social-sensitivity flag (decide with Emma before building)

These items were **deleted by another editor**, presumably for notability. Mass
recreation could be contentious and conspicuous — exactly the "visibility is worse
than data loss" risk the Wikidata rules call out. **This one needs an explicit
go-ahead and a defensible minimum claim set before anything is generated.** The
plan below is conditional on that.

### Trigger & shape

`generate_recreate_quickstatements.py` — standalone generator emitting an atomic
`.txt` under `modern-quickstatements/`. **QS pipeline only, no edit summaries,
respect the freeze to 2026-06-06** (built now, fires after).

Because the original QID is gone, we **CREATE new items** (we can't restore the old
IDs). For each DELETED_QID ill, render a CREATE block:

```
CREATE
LAST|Len|"<English label from the ill target>"
LAST|Den|"Shinto shrine"            # or the appropriate description
LAST|P31|Q<class>                   # instance of — the minimum-notability claim
LAST|P11250|"shinto:<PageName>"     # link back to the shintowiki article
```

The **minimum claim set** (`P31` + label + `P11250` sitelink) is the crux — the
original deletion is the signal that bare items get removed. Define it with Emma;
P31 + a real cross-wiki anchor (P11250) is the floor.

### Two-step add-first / repoint-later (never one script)

QS `CREATE` does not hand us the new QID, so repointing the ill from
`DELETED_QID` to the new item is a **separate** script that runs *after*
creation: a SPARQL query finds the new item by `P11250="shinto:<PageName>"`,
confirms it exists, then a second generator rewrites the ill `qid=`. Per the
add-first/remove-later rule, **script 1 only CREATEs; script 2 only repoints, and
only on items a fresh SPARQL confirms landed.** Never both in one action.

### Effort: **MEDIUM–LARGE**, and **gated on Emma's notability decision** + the
freeze. The generator is straightforward; the risk and the minimum-claim-set
design are the real work.

---

## Summary

| # | Item | Trigger | New code | State model | Effort | Blocked on |
|---|---|---|---|---|---|---|
| 1 | Japanese category names (1171) | generator → existing `move_categories.py` in CI | naming logic + CSV + review-buffer tagger | CSV in repo + `Proposed category translations` cat | **LARGE** | — |
| 2 | ILLs without WD= | standalone, category-driven, CI | `fix_ill_destinations.py` (enwiki-pageprops resolver) | stateless | MEDIUM | — |
| 3 | Duplicate-QID tail (7) | render-once standalone | `report_double_qid_tail.py` | none | SMALL | — |
| 4 | Multiple `{{wikidata link}}` | render-once standalone | `report_multiple_wikidata_links.py` | none | SMALL | — |
| 5 | Recreate deleted WD items (144) | QS generator(s) → `modern-quickstatements/` | `generate_recreate_quickstatements.py` + repoint script | SPARQL-confirmed repoint | MED–LARGE | **Emma decision + freeze to 2026-06-06** |

**Recommended order to build:** 3 & 4 first (small, pure-surface, immediately
useful), then 2 (medium, unblocks the dashboard count), then 1 (large, the real
prize — phase it), and 5 last (needs a decision and waits on the freeze).
