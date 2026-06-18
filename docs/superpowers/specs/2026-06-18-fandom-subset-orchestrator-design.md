# Fandom subset orchestrator — design

**Date:** 2026-06-18
**Author:** Emma (via Claude)
**Status:** Approved-pending-spec-review

## Purpose

Make shinto.fandom.com a strict subset/mirror of shinto.miraheze.org by
sweeping every Fandom page and, for each one with no real equivalent on
miraheze, either deleting it or — in one specific redirect case —
overwriting it with the miraheze redirect.

This is the Fandom-side counterpart to the miraheze cleanup
orchestrators, but it runs against a *different* wiki and so does not use
the miraheze `common.run_orchestrator` framework.

## Definitions

* **Equivalent** = the miraheze page with the *identical namespaced
  title*. Title normalization is identical on both wikis (both
  MediaWiki), so an exact-title lookup is the comparison. No
  interwiki/Wikidata mapping.
* **S** = the miraheze page at F's title. **F** = the Fandom page being
  considered.
* **Redirect** = MediaWiki considers the page a redirect
  (`prop=info` `redirect` flag for S; `page.redirect` / `#REDIRECT`
  wikitext for F).

## Per-page decision logic

For each Fandom page F (in a swept namespace), in order:

1. If a `fandom_unique/<title>.wiki` file exists for F's title →
   **skip** (protect guard). Emma's note: these overlap with miraheze
   anyway, so this is belt-and-suspenders.
2. If F is the Fandom Main Page → **skip** (never delete the main page).
3. Look up S on miraheze (batched read).
4. If S does **not** exist → **delete F**.
5. If S exists and is **not** a redirect → **skip** (a real equivalent
   exists; ongoing content sync remains the job of the existing sync
   scripts, not this orchestrator).
6. If S exists and **is** a redirect:
   * F is **also** a redirect → **delete F**.
   * F is **not** a redirect → **copy over**: overwrite F's wikitext
     with S's raw redirect wikitext, so Fandom becomes the same
     redirect S is.

This is the literal rule Emma gave: "delete if there is no equivalent on
Shinto, including when the Shinto page is a redirect — assuming the
Fandom one is not a redirect, in which case copy it over instead."
Copy-over direction is **Shinto redirect → Fandom** (confirmed
2026-06-18).

## Namespace scope

Sweep **all namespaces except**:

* **ns 6 (File:)** — excluded for now. The same `fandom-cleanup.yml`
  workflow imports Commons files into Fandom's File: namespace; if
  miraheze has no local File: pages this sweep would delete every
  imported file each cycle and fight the importer. Revisit once we
  confirm whether miraheze hosts local File: pages.
* **ns 8 (MediaWiki:)** — excluded. Interface/system messages; almost
  none have a miraheze equivalent, so the rule would mass-delete the
  Fandom UI. Consistent with every miraheze orchestrator excluding ns 8.

Virtual namespaces (Special -1, Media -2) are not walkable and are not
in scope. All other namespaces — including Template (10), Category (14),
Module (828), User (2), Project (4), Help (12), Wikibase item/property
namespaces if present, and all talk namespaces — are swept.

## Architecture

* **Single standalone script:** `fandom/fandom_subset_orchestrator.py`.
* **State:** `fandom/fandom_subset_orchestrator.state` (JSON; committed
  by `commit_state.sh`'s repo-wide `find . -name '*.state'`).
* **Auth:** writes to fandom via `FANDOM_USERNAME` / `FANDOM_PASSWORD`
  (bot-password, same as `fandom_mirror`). Reads from miraheze are
  anonymous with a UA-policy-compliant User-Agent.
* **Wired into** `.github/workflows/fandom-cleanup.yml` as a new step
  after the wanted-files import.

### Walk + state

* Walk swept namespaces in a fixed order; within each, `allpages(ns)`.
* Cursor state = `{"ns": <int>, "from_title": <str>}` so each run
  resumes where the previous one stopped. When the last namespace
  finishes, the cursor wraps to the first namespace (continuous loop,
  like the miraheze orchestrators' cyclic walk).
* `--max-edits` caps **writes** (deletes + copy-overs) per run; reads do
  not count. When the cap is hit, save the cursor at the next unprocessed
  title and exit.

### Read batching

* miraheze existence + redirect status fetched via
  `action=query&prop=info&titles=...` up to 50 titles per call, with
  `redirects` handling so we can tell "exists & redirect" from "exists &
  article" from "missing." Read calls lightly throttled (~0.3s) per the
  redirect-follower precedent; not at the 2.5s write throttle.

### Writes

* Delete: `fandom_page.delete(reason="Bot: no Shinto equivalent <run_tag>")`.
* Copy-over: `fandom_page.save(<S redirect wikitext>, summary="Bot: mirror Shinto redirect <run_tag>")`.
* `THROTTLE = 2.5` between every write.

### Guards / safeguards

* `fandom_unique/` protect guard (step 1).
* Never delete Fandom Main Page (step 2).
* ns 6 / ns 8 excluded (scope).
* `FANDOM_SUNSET_DATE = 2027-01-01`: past this date the script no-ops
  (all fandom writes stop). Constant inlined as in
  `bootstrap_seed_fandom_unique_from_miraheze.py` (sys.path quirk), kept
  in sync with `shinto_miraheze/orchestrators/ops/fandom_mirror.py`.
* Default run is **dry-run**; `--apply` required to write.

## CLI

Standard project template: `--apply` (default dry-run), `--max-edits N`,
`--run-tag <wiki-formatted tag>`. `sys.stdout` reconfigured to utf-8.
`USER_AGENT` set per Miraheze UA policy for the read side.

## Known risks / must-verify

* **Fandom delete rights.** The fandom bot account must be a sysop to
  call `page.delete`. If it lacks the right, the API errors; the script
  logs and skips that page rather than aborting the run. First `--apply`
  run will confirm whether deletes succeed. (Raise on `[[Open questions]]`
  if deletes are denied.)
* **Both-redirect deletion.** When S and F are both redirects, F is
  deleted (literal rule), even if they point to the same target. This is
  intentional per the instruction; noted so it isn't "fixed" later.
* **Copy-over broken redirects.** If S's redirect target doesn't exist on
  Fandom, the copied redirect is broken on Fandom — but it faithfully
  mirrors Shinto's state, which is the goal.

## Out of scope

* Content sync of real (non-redirect) equivalents — stays with the
  existing sync scripts.
* File: (ns 6) — deferred.
* Any miraheze-side edits — this script never writes to miraheze.
