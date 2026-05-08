# CLAUDE.md — conventions for this repo

## Runtime environment

* **Wiki bot scripts run on GitHub Actions**, not locally. Auth is
  `${{ secrets.WIKI_PASSWORD }}` + `${{ vars.WIKI_USERNAME }}`; the
  bot-password format is `EmmaBot@EmmaBot`. Use `mwclient` for all
  shinto.miraheze.org work.
* **Throttle: `THROTTLE = 2.5`** between edits in every script that
  writes to the wiki. Sustained edit rate must stay around 24/min —
  miraheze has raised server-load concerns.
* **Standard CLI flags**: every wiki-writing script accepts `--apply`
  (default dry-run), `--max-edits`, and `--run-tag`. CI passes a
  wiki-formatted `RUN_TAG=[[github:<run-url>|<cause>]]` so edit
  summaries link back to the workflow run.
* **State files use `.state`** (not `.json`) even if the contents are
  JSON, because `commit_state.sh` globs by extension.

## Editing pace philosophy

Bot edits must satisfy three constraints **simultaneously**:

1. **Easy on the wiki.** Stay at ~24 edits/min sustained (`THROTTLE = 2.5`); throttle read-only API calls inside redirect-chain followers etc. (~`0.3s`); bound any script's per-run page visits with an explicit cap. Never run an un-throttled walk over a category — that's the failure mode that hung the cleanup loop on 2026-04-24.

2. **Reviewable by a human.** Multi-step migrations should pass through human-readable intermediate states (e.g. `[[Category:Currently double category qids]]` review buffer, on-page merge-notice banners on Japanese cats being drained) rather than a single transactional rewrite. Someone glancing at the wiki should be able to see what the bot is doing and why.

3. **Not gated on a human reviewing.** The end state must arrive even if no human ever looks at the intermediate state. Don't gate on "audit reports nobody reads"; encode the next step into wiki state itself so the next cleanup-loop cycle picks it up automatically.

In tension: (2) wants slowness and visibility; (3) wants automation. They reconcile via **forced multi-cycle pacing** — each cycle moves the work one observable step forward, so a human can break in at any cycle but nothing is blocked on them doing so.

Worked example: `[[Category:Double category qids]]` cleanup, where two categories share a QID — one English-named, one Japanese-script.

| Cycle | Action | Wiki state after |
|---|---|---|
| N | `resolve_double_category_qids` drains: tags Japanese cat with `[[Category:crud categories]]` + merge-notice banner; appends English cat to every member; retags dab page from legacy → `Currently double category qids`. | Japanese cat is visibly being deprecated; members are double-categorized; dab page is in the review buffer. |
| N+k | `delete_unused_categories` sweep deletes the now-empty Japanese cat. | Japanese cat is gone. |
| N+k+1 | Resolver re-visits the dab page; only one of its two listed targets exists; single-existing-target branch fires. | Dab page becomes `#REDIRECT [[Category:English]]`. |

Every step is reversible by a human, but no step requires a human.

## Orchestrators (the load-bearing model)

Four per-page orchestrators sweep every wikitext namespace:

| Orchestrator | Namespace(s) | State file |
|---|---|---|
| `mainspace_orchestrator`  | 0 | `orchestrators/mainspace_orchestrator.state` |
| `category_orchestrator`   | 14 | `orchestrators/category_orchestrator.state` |
| `template_orchestrator`   | 10 | `orchestrators/template_orchestrator.state` |
| `miscellaneous_orchestrator` | 2, 4, 6, 12, 420, 828, 860, 862 (subject-side only; talk excluded; ns=8 MediaWiki excluded as too sensitive; last four are non-wikitext — history_offload only, no banner) | `orchestrators/misc_orchestrator.state` + `misc_orchestrator_cursor.state` |

Each orchestrator walks `allpages(ns)` and runs every op in its `OPS`
list against every non-redirect page. Ops are either:

* **Light op** (most) — exposes `apply(title, text) -> (new_text, summary)
  or (None, None)`. Pure text transform; orchestrator handles the save.
* **Heavy op** — exposes `HANDLES_SAVE = True` and
  `run(site, page, run_tag, apply) -> (modified, msg)`. Does its own
  API work (delete, recreate, edit a different page, etc.). Runs in a
  pre-pass; orchestrator refetches page text afterwards if modified.

Ops live in `shinto_miraheze/orchestrators/ops/` and are registered
by name in each orchestrator's `OPS` list.

## Migration criterion — when to port a legacy script to an op

**Port to an orchestrator op if** the script is a per-page sweep over
one or more namespaces — `allpages(ns)` + per-page text transform. That
is the orchestrator's purpose; duplicate walks waste server time.

**Keep as a standalone script if** any of the following apply:

* **Not a sweep.** SPARQL-driven batch work (e.g.
  `generate_p11250_quickstatements.py`), single-page writes,
  render-once-from-accumulated-state renderers
  (e.g. `find_duplicate_page_qids.py`).
* **Bidirectional wiki ↔ repo sync** (e.g. `sync_need_translation.py`,
  `sync_git_synced_pages.py`) — conflict detection and per-page
  revid/sha tracking don't fit the orchestrator pattern.
* **Input-file driven** (e.g. `reimport_from_enwiki.py` with a queue
  of titles) — not a category or namespace sweep.

**The wrong criterion** (used historically and discovered to be weak)
is "does the script eventually finish / drain its state?" — that
heuristic left per-page sweeps like `fix_template_noinclude.py` in
legacy form while their state files kept growing. Use the
sweep-vs-not-sweep distinction instead.

## State files

* **Orchestrator state** lives in `shinto_miraheze/orchestrators/` —
  one `<orchestrator>.state` per orchestrator, plus
  `duplicate_qids.state` (shared collector dict populated by all four)
  and `misc_orchestrator_cursor.state` (namespace cursor for the misc
  sweep).
* **Legacy script state** lives in `shinto_miraheze/` — one
  `<script>.state` per script. Only scripts that genuinely don't fit
  the orchestrator model should still have one here; any per-page
  sweep left in legacy form is a migration debt.

## Commit / push of state files

`shinto_miraheze/commit_state.sh` commits every `*.state`, `*.log`,
`*.errors` file it finds and pushes with retry. The retry loop
(added 2026-04-23) is load-bearing: without it, concurrent pushes
from other workflow jobs were silently rejecting orchestrator state
commits, and only one ever reached origin over many weeks. Keep
the retry — do not replace it with a single-shot push.

## Gotchas

* **Read the DEVLOG.md top entry** when making non-trivial changes;
  it captures recent refactors and constraints (server-load effort,
  retry loop, migration criterion) that aren't visible from the code
  alone.
* **Python interpreter** on Windows dev is `python` (not `python3`).
  CI uses `python3`.
* **`chmod +x` is in the git index** for `run_step.sh` and
  `commit_state.sh` — don't re-add workflow-level chmod lines for them.
* **Force-cancel, not cancel, for stuck runs.** `gh run cancel <id>`
  (and `POST .../actions/runs/{id}/cancel`) is *cooperative* — the
  runner only notices the signal between steps, and an orchestrator
  that's mid-walk with 2.5s throttles between `page.save()` calls may
  take a minute+ or never respond. For badly stuck runs, escalate to
  `POST .../actions/runs/{id}/force-cancel` via `gh api -X POST
  "repos/OWNER/REPO/actions/runs/ID/force-cancel"`. This terminates
  the run immediately. Needed fairly often — reach for it the moment
  a regular cancel hasn't propagated within ~1 minute.
