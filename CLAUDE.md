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

## Orchestrators (the load-bearing model)

Four per-page orchestrators sweep every wikitext namespace:

| Orchestrator | Namespace(s) | State file |
|---|---|---|
| `mainspace_orchestrator`  | 0 | `orchestrators/mainspace_orchestrator.state` |
| `category_orchestrator`   | 14 | `orchestrators/category_orchestrator.state` |
| `template_orchestrator`   | 10 | `orchestrators/template_orchestrator.state` |
| `miscellaneous_orchestrator` | 2, 4, 6, 8, 12, 420, 828, 860, 862 (subject-side only; talk excluded; last four are non-wikitext — history_offload only, no banner) | `orchestrators/misc_orchestrator.state` + `misc_orchestrator_cursor.state` |

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
