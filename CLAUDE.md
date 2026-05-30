# CLAUDE.md — conventions for this repo

## Follow Emma's instructions LITERALLY — do not optimize, guess, or improvise

On this project, treat every instruction Emma gives as **completely literal**.
When she describes a series of steps, implement **exactly that series of steps**,
in that order, even if it looks roundabout, inefficient, or suboptimal. Do NOT:
- substitute "a better way" or a cleaner algorithm,
- collapse/merge steps she listed separately (if she says "two separate
  scripts", make two separate scripts),
- infer extra scope or "what she probably meant" from vague-sounding wording —
  if it's genuinely unclear, ask; otherwise do precisely what was said.

**Why:** this project deals with hostile/uncooperative external APIs and
data-modelling constraints where the deliberately complicated, unintuitive,
locally-suboptimal procedure is the one that actually works. The "obvious
optimization" usually breaks against those constraints. The literal steps exist
for reasons that aren't always visible from the code. Reproduce them faithfully.

## Workflow Rules

- **Plan into `queue.md` FIRST, then execute.** When entering planning mode (or any multi-step think-before-do), the FIRST action is to write the plan into `queue.md` as concrete items. Only then begin executing. Chat context dies on session interrupt; the queue survives. This matters extra here because a lot of work is bot-driven sweeps that take a long time and a session may not survive to finish.
- **Update `queue.md` in the same commit as the work.** Delete completed items in the same commit — no checkmarks, no status markers. If an item is still in queue.md, it is not done.
- **Done items go to `DEVLOG.md` in the same commit.** When a queue item is completed: delete it from `queue.md` AND append a dated entry to `DEVLOG.md` describing what shipped (matching the existing `## YYYY-MM-DD` + `### Title` + **Files:** + prose format), in the SAME commit as the code change. `DEVLOG.md` is where "done" lives — `git log` alone loses too much context. Releases and notable incidents also go here.
- **Mirror `queue.md` into the task tool.** `TaskCreate` items as you add them; mark `in_progress` when starting; `completed` when done. The two views must not drift.
- **Flow:** `todo.md` (abstract horizons) → `queue.md` (concrete steps) → task tool (in-flight work) → `DEVLOG.md` + `git log` (history). Items only flow forward; do not leave done items behind in `todo.md` or `queue.md`.
- **Items migrate `todo.md` → `queue.md` → deleted on completion.** `queue.md` is for the active session; `todo.md` is longer-horizon. When pulling from `todo.md`, decompose the abstract goal into concrete executable steps before putting it in `queue.md`.
- **Items handed off to an autonomous backlog are deleted from `queue.md`.** When bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, etc.) is wired into `remote_queue.json` for the remote-Claude cron to consume, the work item leaves `queue.md` — its life is now in the autonomous queue, and duplicating the description in both places is bloat. Keep `queue.md` for items the *human* still needs to track (specific tooling tasks, decisions, scoping questions).
- **Commit each logical unit as you finish it.** A new op, a fix, a doc note, a paired script-and-workflow — once it's coherent and tested, commit it. Don't pile up uncommitted work across many turns waiting for some final batch moment; mid-session crashes and context limits lose uncommitted work, and one mega-diff at the end is harder to review than a clean linear history.
- **PUSH frequently — pushing is wired into CI/CD, hesitating causes problems.** Push after each commit (or each tight cluster of commits on a single feature) rather than batching pushes for a session end. `git push` on this repo triggers the cleanup-loop CI which is what actually applies edits to the wiki; if local commits sit unpushed for many turns, the wiki drifts further out of sync with the desired state than it would otherwise be — that drift is the cost. Emma has flagged this explicitly: don't be overly cautious. Standing consent — push without asking unless the change is genuinely risky (force-push, history rewrite of a published commit, large irreversible deletion). The old "push at session end" rule is **superseded** by this; see `feedback_batch_commits_before_push.md` in memory which now reflects the push-frequently policy.
- **Rebase against `origin/main` frequently — it is easy on this repo.** The CI pipeline pushes state-file commits (`chore(state): ...`, `chore(unique): ...`, `chore(duplicated-content): ...`) constantly, so a local working branch falls 10+ commits behind upstream within a few hours. **This is not a problem** here: those CI commits touch `*.state` files in `shinto_miraheze/orchestrators/` and pulled `.wiki` files in the sync dirs, which almost never overlap with feature work elsewhere in the tree. `git pull --rebase` almost always replays cleanly. Don't let divergence build up; rebase whenever the upstream is more than a handful of commits ahead, and always before any push. Standing consent — Emma has called this out as routine.

## `[[Open questions]]` page — read at session start, prune as items resolve

`git_synced/Open questions.wiki` (mirrored to the wiki page [[Open questions]] on shinto.miraheze.org, https://shinto.miraheze.org/wiki/Open_questions) is the human↔bot interface for blockers, design questions, and instructions Emma wants the bots to act on. Agents are responsible for keeping it accurate — it is not a write-once seed list.

* **Read it at the start of every session and at every work-loop cron tick.** Emma may have answered questions, struck items, or added new instructions on the wiki side since you last looked. The wiki version wins (the page has a sync-policy exception described in its own bottom note: wiki-wins despite living in `git_synced/`).
* **Update it whenever items resolve.** If a bullet says "Needs Emma to X" and you can verify the work has actually been done (e.g. `RemoteTrigger get` shows the routine prompt is already the post-fix version, a `git log` / `git show` confirms the code shipped, a grep confirms the field/state no longer exists), DELETE that bullet in the same commit. Don't leave stale "open questions" lying around — that's the failure mode Emma flagged on 2026-05-27 ("if it is already fixed, fix it in the goddamn documentation").
* **Investigate before declaring something blocked-on-Emma.** When a queue or todo item looks like it needs Emma's input, actually check the code/state first. Search the repo, run the relevant `--dry-run`, fetch the relevant API response. Defaulting to "needs Emma's input" without investigation is the failure mode she called out: many items framed as blockers are either already resolved or are autonomous work the agent is just refusing to start.
* **Newly-surfaced blockers go on the page, not lost in chat.** When you hit a real blocker mid-session (an ambiguous instruction you cannot resolve from context, a wiki-side action only Emma can take, a credential need), add it under the relevant section of `git_synced/Open questions.wiki` with enough context for Emma to answer without re-deriving the problem. Commit + push so the next sync cycle propagates to the wiki where Emma can edit answers.
* **Sync-policy exception applies.** This page is wiki-wins for conflict resolution (see its bottom note). Always treat the wiki version as authoritative when committing repo-side edits — pull and merge rather than overwriting Emma's wiki edits.

## Repository layout & organizational discipline

**Keep stricter organizational discipline with the file structure than this
project has historically.** Crud (scratch scripts, stale output `.txt`, one-off
data dumps, empty placeholder dirs, orphaned `.wiki` files, retired tools)
accumulated in the repo root over time and made it hard to tell what is actually
live. Do not let that happen again. The root was cleaned up on 2026-05-23 — keep
it clean.

**The root is reserved for a small, fixed set.** Only these belong loose in the
repo root:

* Core docs / workflow files: `README.md`, `CLAUDE.md`, `DEVLOG.md`, `todo.md`,
  `queue.md`.
* Remote-queue files: `remote_queue.py`, `remote_queue.json`,
  `consume_remote_queue.state`. These **must** stay in root — the claude.ai
  remote routine reads `remote_queue.json` at the repo root and its prompt
  can't be edited from this repo, and `remote_queue.py` writes the JSON next to
  itself.
* Dotfiles / launcher: `.gitignore`, `.gitattributes`, `.nojekyll`,
  `!runClaude.bat`.

**Everything else goes in a purpose-named directory.** Where things live:

| Kind of thing | Goes in |
|---|---|
| Wiki-editing bot sweep scripts + orchestrators + `*.state` | `shinto_miraheze/` |
| Wikidata QuickStatements generation/submission | `modern-quickstatements/` |
| GitHub Pages site generator | `site/` |
| shinto.fandom import scripts + their input lists | `fandom/` |
| Multilingual shrine-label sub-project | `shinto-label-generator/` |
| Reference docs (anything beyond the 5 core root docs) | `docs/` |
| Retired / one-off / superseded scripts | DELETE — don't archive (2026-05-28 audit found nothing in `archive/` had irreplaceable technique; directory removed; git history retains the code) |
| Wiki↔repo per-page content sync | the named dir (`need_translation/`, `git_synced/`, `miraheze_unique/`, `fandom_unique/`, `duplicated_content/`) |

**Rules:**

* **New files go straight into the right subdir** — never drop a new script,
  data file, or generated output loosely in the root "for now."
* **A script and the data/template it owns live together** (e.g. an input
  `.txt` next to its consumer; resolve such paths `__file__`-relative, not
  cwd-relative), *except* `*.state` files, which stay in `shinto_miraheze/` so
  `commit_state.sh` commits them.
* **When you move a referenced file, grep the whole repo and fix every
  reference** (workflows, scripts' internal paths, doc links) in the same
  change. Use `git mv` so history is preserved.
* **Delete retired/scratch/stale scripts; do NOT keep an `archive/`
  directory.** The `archive/` directory was audited and deleted on
  2026-05-28 after Emma asked whether any of its contents held
  irreplaceable technique — none did, all techniques were either
  already captured in active code or trivially reproducible. Git
  history retains everything anyway. Going forward: when a script
  becomes retired or superseded, delete it from the working tree;
  if there's a real reusable technique worth preserving, write a
  brief note in the relevant doc or in `DEVLOG.md`.
* **If you're unsure where something belongs, ask** — do not default to the
  root.

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

* **Never postpone a wiki edit for lack of local credentials — wire a
  script into CI instead.** The dev session has NO wiki write creds
  (reads work fine with a compliant User-Agent; writes do not). The rule
  is NOT "defer it / hand it to Emma" — it is: write a small script that
  performs the edit and add a step that runs it in the pre-orchestrator
  GitHub Actions pipeline (`wiki-cleanup.yml`), where the creds live. It
  is a *lagging* action (runs on the next CI fire), but it gets done with
  zero local creds. **Usual protocol for a one-off edit:** a date-gated
  script that, once its date arrives, performs the single edit on that
  day and then no-ops (see `add_wikidata_crud_categories.py` /
  `remove_wikidata_crud_categories.py` for the pattern). **If we ever have
  to do another one of these single-edit-via-CI things,** that's the
  signal they're starting to accumulate — at that point start formalising
  the process (a small generic orchestrator for single-edit scripts)
  rather than hand-wiring each one.

## Pinned operational notes (moved out of queue.md 2026-05-30)

* **`[[Category:Need translation]]` removal is destructive — and so are the
  duplicated_content / git_synced category removals.** When a wiki page loses its
  gating category, the sync (`sync_need_translation.py` etc.) DELETES the local
  file from the synced dir. The legitimate path is the cloud-queue worker removing
  the category from a *genuinely-finished* page. NEVER bulk-strip a gating category
  from pages by a filename/title heuristic without verifying the body — that mass-
  deletes synced content. (Reversible from git history, but don't.)
* **Sync scripts are stateless as of 2026-05-30** — no `sync_*.state` files;
  conflict resolution is most-recent-edit timestamp; see each script's `load_state`
  docstring and `docs/deferred_verification.md`.
* **Script-template invariants.** Wiki-writing scripts take `--apply` /
  `--max-edits` / `--run-tag`; use `mwclient`; `THROTTLE = 2.5`; set a
  Miraheze-UA-policy-compliant `User-Agent` (a generic UA gets 403);
  `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`.
* **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.

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

## Wikidata editing — ONE path only, no edit summaries

**Wikidata is edited by exactly one mechanism: the daily QuickStatements
pipeline.** Generators emit QuickStatements lines (which carry NO edit
summaries) into the atomic `.txt` files in `modern-quickstatements/`;
`submit_daily_batch.py` attempts them via the QuickStatements API; if that
fails, `direct_daily_edits.py` executes ~50 of the SAME generated lines via the
API. That is the entirety of it: build a big list of QuickStatements, try to run
them, fall back to running ~50. Nothing else touches Wikidata.

- **NEVER write a bespoke direct-API Wikidata editor** (no script of your own
  calling `wbsetqualifier` / `wbcreateclaim` / `wbremoveclaims` / `wbsetlabel`
  etc.), and **never attach a descriptive/explanatory edit summary** to a
  Wikidata edit. Edits go out via QuickStatements with no summary.
- **All new Wikidata work** (qualifiers, labels, references, removals) must be
  expressed as QuickStatements lines: add/extend a `generate_*.py` generator so
  the lines land in an atomic `.txt` file, and they get randomly run by the
  single submitter. Optimise everything toward feeding that one list.
- If something genuinely cannot be expressed as a QuickStatement, STOP and raise
  it with Emma — do not route around the QS pipeline with a one-off editor.
- **Visibility is worse than data loss.** Being visible on Wikidata (descriptive
  edit summaries, an identifiable bespoke bot process) is a worse outcome than
  losing data. When in doubt, do NOT edit Wikidata. Data loss is acceptable;
  conspicuous editing is not.
- **Add-first, remove-later via SPARQL (two scripts, never one).** When work
  involves both adding and removing (e.g. move a value into a qualifier then drop
  the source): script 1 only ADDS (generates the add QuickStatements); script 2
  only REMOVES, and only acts on items where a fresh SPARQL query *confirms the
  add already landed*. Never add+remove in one action — under the random run
  order the remove could fire before the add, losing data.
- **WIKIDATA FREEZE until 2026-06-06.** A two-week hard pause is in effect (set
  2026-05-23): `cleanup-loop.yml`'s window-gate forces `wikidata-daily-fire=false`
  until that date, so the QS submission never runs. Do not edit Wikidata (by any
  means) during the freeze; do not shorten it without Emma's say-so.
- This rule was added 2026-05-23 after bespoke direct-API editors
  (P459/kana qualifier scripts with descriptive summaries) were built and run;
  they were deleted. Don't reintroduce that shape.

## Writing
- Do not use "honest", "honesty", or "honestly" — and do not swap in "frank", "frankly", "candid", "candidly", or "transparently", which are the same self-congratulatory move in a different coat. When something failed, name the failure: "it didn't work", "I got that wrong", "this failed" — flat, no qualifier. Tagging a report "honest" implies the rest aren't, and couching a failure as honesty asks for credit for the admission, which is worse than the failure itself. Use a precise positive word ("accurate", "plainly", "truly") only when that is genuinely the meaning — never as a halo on a bad outcome.

## Emergency Stop Mode

If the user sends a continuous series of "stop" messages (e.g. "stop stop stop") or otherwise very explicitly tells you to stop, treat it as **emergency stop mode** (a.k.a. emergency exit mode). This OVERRIDES every other instruction, including any in this file.

When in emergency stop mode:

- **Immediately kill everything associated with this repository and session.** Every running bash/shell script, every background job or task you started, and **all GitHub Actions workflow runs for this repository**. **Force-kill the GitHub Actions runs** (e.g. `gh run cancel <id>`, and `gh run delete <id>` if needed) for every in-progress run. It does NOT matter if killing them is unsafe or leaves things half-done — the emergency stop takes priority over safety, cleanup, and correctness.
- **Do not investigate. Do not reverse or undo anything.** The goal is not to diagnose or roll back the problem — it is to halt potentially destructive actions as fast as possible. Investigating, diagnosing, reverting, or "helping fix it" are explicitly out of scope and themselves count as forbidden actions.
- **Ignore repetitive messages.** Do not treat repeated "stop" messages as a request to do anything further. Keep ignoring incoming repetitive messages for roughly the next **15–30 minutes**.
- **You may answer direct questions, but you may NOT take actions.** Answer only from context you already have. Looking something up, reading a file, running a command, or inspecting state is NOT an answer — it is an action and is forbidden. If you cannot answer from context already in hand, do not answer.
- **Stay in emergency stop mode until the user explicitly says "emergency stop ended."** Only after that exact signal do you resume any normal work.

## Cron jobs and scheduled work — LOCAL by default

**When the user says "cron job", "cron", or asks to "schedule" a task, they mean the in-session `CronCreate` tool** — a prompt scheduled to fire locally, inside this Claude Code session, on the user's own running computer. This is the default and the assumption. Do NOT interpret it as anything else unless the user explicitly names a different mechanism.

- **It is local and in-session — use the `CronCreate` tool.** A generic "cron" request is NOT an OS crontab, NOT a GitHub Actions / CI `schedule:` trigger, and NOT a cloud scheduler. (Repos may *also* contain their own GitHub Actions cron schedules — those are a separate thing and are not what the user means when they ask *you* to set up a cron.) The user leaves the computer on and this session running so the scheduled prompt can execute.
- **The user is deliberately away from the keyboard.** They schedule work precisely so it runs while they are out of the house and not physically present. Their absence is the normal, expected condition for these jobs — it is NEVER a reason to delay the work, ask "are you sure?", wait for them to return, or refuse to proceed.
- **Standing consent — just set it up.** Cron / `CronCreate` requests are pre-authorized. Create the job immediately and locally, then report what was scheduled. Do not block on confirmation or follow-up questions. Treating a routine cron request as something that needs hand-holding is itself the obstacle this section exists to remove.

## Autonomous productivity loop — the three-cron playbook

**For any session involving relatively extensive work — above all, any large-scale population of `queue.md` with created tasks — this is the default way of working.** It is three local `CronCreate` jobs that turn "barrel through `queue.md`, and when it's empty atomise the next `todo.md` item into it" into a self-sustaining hourly cadence with a commit/push backstop and a heartbeat. The crons are **session-local** (`durable: false` — they die when the session ends), so they are recreated at the start of every session.

Stagger the minutes so the three ticks don't collide:

1. **Work-loop cron — `3 * * * *` (hourly at :03).** The engine. Each tick does, in order:
   - **(a) SYNC** — `git fetch origin`; fast-forward or rebase the working branch (never force-push, never `reset --hard`, never discard a sibling machine's work).
   - **(b) WORK** — take the top actionable item from `queue.md` and do it. If nothing in `queue.md` is actionable (all blocked / needs user / a product decision), promote the next *genuinely-unblocked, bounded, verifiable* `todo.md` item — **plan it into `queue.md` first**, mirror to the task tool, then execute.
   - **(c) HARD RAILS** — never fake; never weaken / skip / delete a test to make it pass; never claim "works" / "verified" / "passes" without having actually RUN it and measured. A real defect → strict `xfail` or a precise documented blocker, never a loosened assertion. Don't implement what you don't 100% understand — write the spec / queue item instead. Name unbuilt or hard things plainly; don't paper over difficulty. Verify CI green, not just local — local-green does not imply CI-green.
   - **(d) COMMIT** — commit early/often with *why*; update `queue.md` in the same commit (delete completed items); append the dated entry to `devlog.md`; mark task-tool items done; push.
   - **(e) REPORT** — one line: the commit shas advanced, or `nothing actionable; <reason>`.

2. **Auto-flush cron — `15 * * * *` (hourly at :15).** The backstop. Commit + push all pending work so nothing sits uncommitted between manual pushes; report shas or "nothing pending". Only commit / push when something is actually pending — no empty commits.

3. **Status-report cron — `42 * * * *` (hourly at :42).** The heartbeat — **reporting only, no code changes.** Covers: what advanced since the last report (shas + one-line each); current `queue.md` state; how the work held the hard rails (and any place it brushed one); blockers / items deliberately not done autonomously and why; test-suite health.

**Why this exists:** the most common autonomous-agent failure is doing a large amount of work and silently losing the thread of what it is doing. The work-loop forces steady, verifiable, committed progress; the auto-flush guarantees nothing is lost between ticks; the status-report keeps the thread legible.

**Lifecycle around a large-scale queue fill:**

- **(a) START all three crons at the beginning of any extensive work session.** A fresh session has none of them running, so the opening move — the first queue item — is to *create them*.
- **(b) On a mid-session large-scale queue RE-FILL** (a planning burst that repopulates the queue), the FIRST item of that fill **kills the running crons**, then the work items follow top to bottom, and the pinned tail restarts them.
- **(c) Entering planning mode DISABLES the crons.** Their restart therefore lives at the **end** of the queue, not the beginning of the next burst.
- **(d) The LAST TWO queue items, always kept pinned at the tail, are:**
  1. **Ensure the three crons are running** — start them if this session never did, restart them if a planning burst / queue re-fill killed them.
  2. **Run the status-report action once more, independently** — an end-of-session summary of everything that happened this session.

In short: a fresh session **starts** the crons up front and the tail **ensures they are still running** + summarizes; a mid-session re-fill **kills** them up front and the tail **restarts** them + summarizes. Either way the queue both opens and closes on the cron set.

## Check cleanvibe for skill updates (weekly)

This `CLAUDE.md` carries cleanvibe-shaped sections (writing rules, emergency stop, cron policy, the productivity loop). cleanvibe ships new sections / skills over time — when one lands, this file should pick it up.

**The check is weekly, not per-session.** At the top of any session, look at the *last cleanvibe update check* date below. If it has been more than 7 days, do this:

1. **Fetch the current skill index** — `WebFetch https://cleanvibe.emmaleonhart.com/updates.md`. This is the canonical, hand-maintained page describing every section / skill / convention cleanvibe templates currently ship, keyed by the cleanvibe version that introduced it.
2. **Compare against the version below.** If `updates.md` lists sections introduced in later versions, fold those sections into THIS `CLAUDE.md`. Match the wording from `updates.md`; don't paraphrase. Repo-specific carve-outs already in this file stay — only the generic sections are kept in sync.
3. **Update the version + date below** to reflect the check. Commit the changes with a message describing which sections were folded in.

If the fetch fails (offline, DNS, page not yet up), leave the date alone and try next session — the check is opportunistic, not mandatory.

- **Last synced cleanvibe version:** `1.11.0`
- **Last cleanvibe update check:** `2026-05-26`
- **Updates source:** <https://cleanvibe.emmaleonhart.com/updates.md>
