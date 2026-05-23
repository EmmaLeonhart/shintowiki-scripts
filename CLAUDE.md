# CLAUDE.md — conventions for this repo

## Workflow Rules

- **Plan into `queue.md` FIRST, then execute.** When entering planning mode (or any multi-step think-before-do), the FIRST action is to write the plan into `queue.md` as concrete items. Only then begin executing. Chat context dies on session interrupt; the queue survives. This matters extra here because a lot of work is bot-driven sweeps that take a long time and a session may not survive to finish.
- **Update `queue.md` in the same commit as the work.** Delete completed items in the same commit — no checkmarks, no status markers. If an item is still in queue.md, it is not done.
- **Done items go to `DEVLOG.md` in the same commit.** When a queue item is completed: delete it from `queue.md` AND append a dated entry to `DEVLOG.md` describing what shipped (matching the existing `## YYYY-MM-DD` + `### Title` + **Files:** + prose format), in the SAME commit as the code change. `DEVLOG.md` is where "done" lives — `git log` alone loses too much context. Releases and notable incidents also go here.
- **Mirror `queue.md` into the task tool.** `TaskCreate` items as you add them; mark `in_progress` when starting; `completed` when done. The two views must not drift.
- **Flow:** `todo.md` (abstract horizons) → `queue.md` (concrete steps) → task tool (in-flight work) → `DEVLOG.md` + `git log` (history). Items only flow forward; do not leave done items behind in `todo.md` or `queue.md`.
- **Items migrate `todo.md` → `queue.md` → deleted on completion.** `queue.md` is for the active session; `todo.md` is longer-horizon. When pulling from `todo.md`, decompose the abstract goal into concrete executable steps before putting it in `queue.md`.
- **Items handed off to an autonomous backlog are deleted from `queue.md`.** When bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, etc.) is wired into `remote_queue.json` for the remote-Claude cron to consume, the work item leaves `queue.md` — its life is now in the autonomous queue, and duplicating the description in both places is bloat. Keep `queue.md` for items the *human* still needs to track (specific tooling tasks, decisions, scoping questions).

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

Twelve per-page orchestrators sweep every wikitext namespace:

| Orchestrator | Namespace(s) | State file |
|---|---|---|
| `mainspace_orchestrator`  | 0 | `orchestrators/mainspace_orchestrator.state` |
| `category_orchestrator`   | 14 | `orchestrators/category_orchestrator.state` |
| `template_orchestrator`   | 10 | `orchestrators/template_orchestrator.state` |
| `user_orchestrator`       | 2 | `orchestrators/user_orchestrator.state` |
| `project_orchestrator`    | 4 | `orchestrators/project_orchestrator.state` |
| `file_orchestrator`       | 6 | `orchestrators/file_orchestrator.state` |
| `help_orchestrator`       | 12 | `orchestrators/help_orchestrator.state` |
| `geojson_orchestrator`    | 420 (non-wikitext — history_offload only, no banner) | `orchestrators/geojson_orchestrator.state` |
| `module_orchestrator`     | 828 (non-wikitext — Lua/Scribunto) | `orchestrators/module_orchestrator.state` |
| `item_orchestrator`       | 860 (non-wikitext — Wikibase Item) | `orchestrators/item_orchestrator.state` |
| `property_orchestrator`   | 862 (non-wikitext — Wikibase Property) | `orchestrators/property_orchestrator.state` |
| `talk_orchestrator`       | 1, 3, 5, 7, 9, 11, 13, 15, 421, 829, 861, 863 (all 12 talk namespaces share one budget; low-stakes content) | `orchestrators/talk_orchestrator.state` + `talk_orchestrator_cursor.state` |

ns=8 MediaWiki is intentionally excluded from every orchestrator —
interface messages and system pages there are too sensitive to touch
with the space-saving ops.

Per-namespace edit budgets are set in `cleanup-loop.yml`'s window-gate:
mainspace 100, template 100, category 500 (catch-up window 2026-04-23 →
2026-06-01: it has never completed a full cycle), and each misc
namespace 10. The 9 misc orchestrators (8 subject-side + talk) cost ~80
edits per cleanup-loop fire combined.

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

## Cron requests are local and immediate

When the user says "a cron job," "a cron," "a CronCreate," "set up a cron," or "schedule X for Yh from now," that means the local **`CronCreate`** tool — **ALWAYS local, NEVER a remote routine**, and **never ask "local or remote?"**. The word "cron" === local CronCreate. Use it **immediately**: do not ask whether they meant local vs remote, whether they'll be at the computer, what timezone, or for confirmation on the schedule time. The user uses local cron specifically to schedule work for when they are *not* present and treats it as resilient infrastructure — pausing for a follow-up question defeats the purpose. Assume present-availability is irrelevant; assume local is correct; assume the task should fire. If a parameter is genuinely missing (e.g. unclear *what* to run), make the reasonable call rather than asking. Prefer `durable: true` for any cron meant to survive across sessions — the 2026-05-20 crash killed every in-memory cron in flight. Note: cron-driven *wiki editing* still has to go through GitHub Actions (the §"Runtime environment" rule above) — local cron in this repo is for orchestration / kicking off CI runs, not for direct `mwclient` calls.

**Local cron vs remote routine — do not conflate (this has gone wrong before):**
* **Local `CronCreate`** = anything the user calls a "cron"/"cron job." Orchestration, polling, kicking off CI, periodic *local agentic* work (which runs in the current local model, e.g. Opus). Default for the word "cron."
* **Remote claude.ai routine** (`RemoteTrigger`) = only when the user explicitly says "remote," "on the cloud," "a Claude remote thing," names a cloud model for a recurring job (e.g. "a daily Sonnet run"), or invokes the `/schedule` command. These are for bulk LLM grunge work done by Claude in the cloud (translations, dup-content merges, the remote-queue consumer).
* Picking the wrong one is a real error. A "cron" request must never be downgraded into a remote routine, and you must not ask the user to choose — infer from their exact words: "cron" → local; "remote/cloud/Sonnet-routine/`/schedule`" → remote.

## Writing
- Do not use "honest", "honesty", or "honestly" — and do not swap in "frank", "frankly", "candid", "candidly", or "transparently", which are the same self-congratulatory move in a different coat. When something failed, name the failure: "it didn't work", "I got that wrong", "this failed" — flat, no qualifier. Tagging a report "honest" implies the rest aren't, and couching a failure as honesty asks for credit for the admission, which is worse than the failure itself. Use a precise positive word ("accurate", "plainly", "truly") only when that is genuinely the meaning — never as a halo on a bad outcome.
