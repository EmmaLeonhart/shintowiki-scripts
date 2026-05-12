# SYNCING.md — every sync pathway in this repo

shintowiki-scripts moves content between several wikis, the git repo,
and external services. This document catalogues every sync pathway so
you can tell at a glance: what's being copied, in which direction,
what triggers it, what state file backs it, and what happens on
conflict.

Conventions used below:
* **Source of truth** — when both sides change, who wins.
* **State file** — JSON map of `title → {revid, sha}` (or similar)
  used to detect divergence between cycles. Lives under
  `shinto_miraheze/` with a `.state` extension.
* **Trigger** — the GitHub Actions workflow that runs it.

---

## 1. Wiki ↔ Repo content sync (category-driven)

These five scripts all follow the same per-page-mirror pattern:
membership in a named category on the wiki maps 1:1 onto a `<title>.wiki`
file in a repo directory. Edits on either side are detected via
`revid` (wiki) and content `sha1` (repo) recorded in the state file
each cycle.

| Script | Repo dir | Wiki(s) | Category | Conflict policy | Trigger |
|---|---|---|---|---|---|
| `sync_need_translation.py` | `need_translation/` | shinto.miraheze | `Need translation` | skip + log | `wiki-cleanup.yml` |
| `sync_git_synced_pages.py` | `git_synced/` | shinto.miraheze (ns 0/10/14) | `Git synced pages` | repo wins | `git-synced-sync.yml` |
| `sync_miraheze_unique_pages.py` | `miraheze_unique/` | shinto.miraheze (ns 0/10/14) | `Independently git synced pages` | repo wins | `fandom-sync.yml` |
| `sync_fandom_unique_pages.py` | `fandom_unique/` | shinto.fandom (ns 0/10/14/828) | `Independently git synced pages` | repo wins | `fandom-sync.yml` |
| `sync_duplicated_content.py` | `duplicated_content/` | shinto.miraheze | `Pages with duplicated content` | skip + log | `wiki-cleanup.yml` |

**Resolution per page (shared logic):**
1. wiki changed, local unchanged → pull wiki → local
2. local changed, wiki unchanged → push local → wiki
3. both unchanged → no-op
4. both changed → conflict (skip + log) **or** repo wins (per-script)

**Opt-out semantics:** removing the category tag from the local
`.wiki` file causes the next cycle to push the change (removing the
category on the wiki too) and then delete the local file. This is how
a page graduates out of `need_translation/` once translation is done.

**No wiki↔wiki sync exists.** miraheze and fandom never talk directly
through these scripts; the repo is the hub. A page that lives in both
`miraheze_unique/` and `fandom_unique/` is intentionally divergent —
e.g. miraheze uses Lua/`{{q}}`/`d:` interwikis while fandom uses
Portable Infoboxes.

### Status: `Pages with duplicated content`

Wired into `wiki-cleanup.yml` on 2026-05-12. The next cleanup-loop
firing will populate `duplicated_content/<title>.wiki` for every page
currently in the category. The category requires per-page agentic
review (which title is canonical, paragraph-level reorganization);
a separate scheduled agent (see the routines list) picks up the
populated directory after sync and edits each file in place. Once a
local file no longer contains the category tag, the next cleanup-loop
cycle pushes the change and deletes the local copy.

---

## 2. Wiki → Wiki history mirror (miraheze → fandom)

The `fandom_mirror` helper (`shinto_miraheze/orchestrators/ops/fandom_mirror.py`)
mirrors a page's full revision history from shinto.miraheze to
shinto.fandom via `Special:Export` → `action=import`. It's called from
the `history_offload` heavy op as a pre-stage, so the wiki-to-wiki
mirror happens **before** the source page is truncated and revdel'd
on miraheze.

* **Direction:** one-way, miraheze → fandom only.
* **Trigger:** runs inside any orchestrator that registers
  `history_offload`, gated on `ENABLE_FANDOM_MIRROR=1`.
* **Best-effort:** if the fandom import fails, history_offload retries
  once and then continues without it. The XML archive (next section)
  is authoritative.
* **Hard cap:** fandom's `action=import` rejects uploads >10 MB.
  Pages with thousands of revisions fail with `badupload` and are
  skipped.

---

## 3. Wiki → Local XML archive (miraheze → backup repo)

`history_offload` Stage 1 exports every page's full revision history
to the [shintowiki-history](https://github.com/) XML archive repo before
the destructive delete + recreate. This is the authoritative backup —
fandom is best-effort, the XML archive is not.

* **Direction:** one-way, miraheze → XML archive.
* **Trigger:** runs from every orchestrator that registers
  `history_offload`, gated on `ENABLE_HISTORY_OFFLOAD=1`.
* **State:** no per-page state file; the archive itself is the record.

---

## 4. External wiki → miraheze import (enwiki → miraheze)

`reimport_from_enwiki.py` pulls XML exports (with `templates=1`,
`curonly=1`) from enwiki, mangles the timestamps so the import always
overwrites whatever is on miraheze, and re-imports via `action=import`.

* **Direction:** one-way, enwiki → miraheze.
* **Driver:** input file of page titles, one per line — not a sweep.
* **Trigger:** manual (`wiki-cleanup.yml` has a step gated off in the
  current catch-up window).
* **Note:** imported pages historically arrived with stray categories
  in the middle of the wikitext; the new `categories_to_bottom` op
  re-flows those back to the bottom on the next cleanup pass.

---

## 5. miraheze → Wikidata (via QuickStatements)

Several `generate_*_quickstatements.py` scripts read miraheze state
and produce CSV files for human upload at
[QuickStatements](https://quickstatements.toolforge.org/).

* `generate_p11250_quickstatements.py` — P11250 (page on shintowiki)
* `generate_p6262_quickstatements.py` — P6262 (Fandom article ID)
* `generate_en_labels_quickstatements.py` — English labels

This is asymmetric — nothing pulls *from* Wikidata back into the wiki
on a sweep basis. (Per-page enrichment ops like `wikidata_lookup`
read Wikidata live; they don't sync state.)

---

## 6. Aggregated wiki reports (orchestrator-collected)

A small set of ops act as **read-only collectors** that build up a
shared state dict across the four namespace orchestrators, then a
separate renderer script publishes the result as a wiki page.

| Collector op | Renderer script | Output page |
|---|---|---|
| `duplicate_qids` | `find_duplicate_page_qids.py` | `[[Duplicate page QIDs]]` |

The collector is registered on every namespace orchestrator (mainspace,
category, template, talk, plus the misc-namespace orchestrators) and
populates `shinto_miraheze/orchestrators/duplicate_qids.state`. Each
orchestrator visits every page in its namespace once per cycle and
refreshes the entry, so the dict converges to a wiki-wide snapshot
across the four sequential runs. The renderer reads it, groups by
QID, and writes the report page on a separate workflow
(`render-duplicate-qids.yml`).

---

## 7. State-file persistence (git ↔ Actions)

Sync state files (`*.state`) live in `shinto_miraheze/`. After every
workflow run, `shinto_miraheze/commit_state.sh` commits every changed
`.state`/`.log`/`.errors` file and pushes with retry. The retry loop
is load-bearing — without it, concurrent pushes from other workflow
jobs silently rejected orchestrator state commits, and the cleanup
loop fell out of sync for weeks before the retry was added on
2026-04-23.

This means: any sync script's `--apply` run produces a CI commit
landing the updated state, which the next CI run reads. State is
not in-memory across runs; it is persisted in git.

---

## Cheat sheet: "where does this page sync?"

If a page on shinto.miraheze.org is in...

| Category | It syncs to | Conflict winner |
|---|---|---|
| `Need translation` | `need_translation/<title>.wiki` | skip + log |
| `Git synced pages` | `git_synced/<title>.wiki` | repo |
| `Independently git synced pages` (miraheze) | `miraheze_unique/<title>.wiki` | repo |
| `Independently git synced pages` (fandom) | `fandom_unique/<title>.wiki` | repo |
| `Pages with duplicated content` | `duplicated_content/<title>.wiki` | skip + log |
| (any namespace + any page with history) | history mirrored to shinto.fandom + XML archive repo | one-way export |

If a page contains `{{wikidata link|Q...}}` it is also recorded into
`orchestrators/duplicate_qids.state` and surfaced on
`[[Duplicate page QIDs]]` if it shares its QID with another title.
