# CLAUDE.md — conventions for this repo

## Skills

Workflow behaviors live as skills in `.claude/skills/` (auto-discovered by Claude Code):
`emergency-stop`, `cron-is-local`, `autonomous-loop`, `queue-driven-workflow`,
`writing-style`, `cleanvibe-update-check`. They are vendored into this repo and kept
current by the `cleanvibe-update-check` skill.

- **Last cleanvibe update check:** `2026-06-07` (cleanvibe v1.15.0; all 6 vendored skills current at v1.14.0+, no revisions applicable — v1.15.0 only affects `cleanvibe replicate` projects, which this is not)
- **Updates source:** <https://cleanvibe.emmaleonhart.com/updates.md>


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

## queue.md conventions (rules live HERE, not in the file header)

queue.md is a queue, not a state snapshot: DELETE items when done (never annotate "DONE" —
finished work lives in `DEVLOG.md` + git log). Keep items TERSE (checkbox + 1-2 lines). Numbers
are priority order, not identity. Nothing is "parked" — every item gets done. Bulk LLM-grunge
(duplicated_content, need_translation, fandom fixup) lives in `remote_queue.json`, not here.
Items metabolised from the wiki [[Open questions]] Wiki-based queue go at the END.

## Reports expire after a week

Emma 2026-07-08: reports and similar write-ups (on the wiki page, in `_site/`, in `docs/` status
snapshots) are cleared once they are a week old — they are working artifacts, not archives.
History lives in DEVLOG.md + git.

## `[[Open questions]]` page — structure & rules (rules live HERE, not on the page)

Emma 2026-07-07: the page must stay lean — no "system prompt" prose on the wiki side. All
conventions live in this file; the page carries only content. Structure: `== Open questions ==`
(blockers needing Emma's judgement; answer inline; agent deletes each bullet SILENTLY once acted
on — no removal narrative), `== Wiki-based queue ==` (Emma's standing work queue: agents read it
every session and every work-loop tick; each item is METABOLISED — appended to the '''end''' of
`queue.md`, never the front — and its bullet is removed from the page at pickup, not at
completion), `== Notes ==` (Emma's scratch). The page is wiki-wins: always pull the live wiki
version before editing repo-side.

## ⛔ NEVER drop `[[Category:Git synced pages]]` when editing a `git_synced/` file

That trailing category is the sync's **membership test**, not decoration. Remove it and
`sync_git_synced_pages.py` behaves exactly as written: it pushes your text to the wiki with the
summary *"removed from Git synced pages category"*, then `local_path.unlink()`s the file. Both
halves are correct — the page leaves the sync set because you told it to.

Happened 2026-08-23 to `git_synced/Open questions.wiki`. A session rewrote the page wholesale to trim
it — which Emma had asked for three times — and did not carry the last line across. The CI sync
pushed the categoryless text at 04:03:59Z and deleted the local file nine seconds later. Nothing was
lost (the wiki kept the content, git kept everything) but the page silently left the sync set and the
only symptom was the file vanishing on the next `git pull`.

**When rewriting any `git_synced/` file, diff the old and new tails before committing.**
`shinto_miraheze/tests/test_open_questions_stays_synced.py` pins it for the one file in that
directory that is hand-edited; the other ~2,850 are written by the sync itself.

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

### `shinto-label-generator/` (the multilingual label sub-project)

Folded here 2026-07-04 from the subtree's own `claude.md` (deleted — a sub-dir
doesn't carry its own Claude instructions). Generates multi-language labels for
shrines/temples (and, via the BFS expansion, texts/concepts/deities — roadmap:
`docs/mass-label-expansion-plan.md`). **`language_registry.py` is the single
source of truth for which language has which generator/method.** Pipelines:
`generate_multilang_quickstatements.py` (all transliteration-based languages,
`ALL_LANGS`), `generate_chinese_quickstatements.py` (kana→man'yōgana + OpenCC;
zh family + gan/zh-mo), `generate_korean_quickstatements.py` (koreanize for
Japan, `hanja` sino-Korean elsewhere), `fetch_shrines_tokiponize.py` (Toki
Pona), `generate_indonesian_proposals.py` (the id-label seed for
Japanese-only shrines). Outputs land in `quickstatements/<lang>.txt`, browsed
via `docs/index.html` (GitHub Pages) and drip-fed to Wikidata by
`select_label_proposals.py`. CI: `label-generator-regenerate.yml` (root
workflows only — the subtree's own workflow dir was inert and is deleted);
tests in `shinto-label-generator/tests/`, collected by root `ci.yml`.
Local full rebuild: `!regenerateQuickStatements.bat`.

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

## Never write anything outside the repo

Emma 2026-07-10: *"What even are these files that you're making and constantly asking for
permission to make? … they're making it so that the repository is not transparent. I prefer
that you make stuff in the repository, even if it becomes something that isn't used and then
later gets deleted, because I don't know what's going on here. You're in auto mode, but you're
still asking for permission!"*

**Do not put helper scripts, commit messages, or intermediate data in the system temp
directory** (`AppData\Local\Temp\claude\…`) or anywhere else outside the working tree. Every
write outside the repo raises a permission prompt in auto mode, and it hides the work from
Emma. A throwaway file committed and later deleted is strictly better than an invisible one.

The habit came from shell heredocs breaking on quoting. The fix is not a temp file:

* **One heredoc per `Bash` call.** The failures were always two heredocs in one command
  (a `python - <<'PY'` immediately followed by `git commit -F- <<'MSG'`). Split them.
* **Commit messages**: `git commit -F-` with that heredoc as the *only* heredoc in the call,
  or plain `-m` for short ones.
* **Multi-step edits**: use the `Edit`/`Write` tools directly on repo files, which is what
  they are for. If a real script is needed, put it in the repo and delete it in the same
  session if it was throwaway.
* **Scratch data** (before/after snapshots for a diff): write it into the repo and `git
  checkout`/`rm` it afterwards, or hold it in the Python process.

## Gotchas

* **Urgency: corrupted/time-sensitive DATA beats pipeline glitches.** A broken
  automated *pipeline* (cleanup-loop, an orchestrator timing out) is often the
  LEAST urgent thing — it's durable infrastructure, fixable any time, and a delay
  only delays automated draining. What's MOST urgent is corrupted / one-shot /
  time-sensitive DATA — QuickStatements that can only be run today, corrupted
  single-use data that leaves things long-term STUCK. Do the time-sensitive
  disposable data FIRST; defer the pipeline repair (even when you've just
  root-caused it). Emma 2026-07-05: chasing the cleanup-loop root cause while
  the run-today category QuickStatements waited was exactly backwards.
* **Almost every weird thing on the shinto wiki is SIGNAL, not corruption.** Emma
  built the wiki solo with idiosyncratic, deliberate conventions, never expecting
  agents or other humans to edit it (stated 2026-07-05). Unusual template params,
  odd category names, empty-looking `{{wikidata link||ja|Category:X}}`, repeated
  `legacy legacy legacy` suffixes, weird dab formatting — all encode real meaning.
  DO NOT normalize / clean up / delete a weird pattern on the assumption it's an
  error. Even genuine-looking corruption is usually recoverable signal: e.g. a bad
  jawiki target `19世紀のKokugakuist` is not hallucinated — it's a real target damaged
  by a bad text replacement (`国学者`→`Kokugakuist`), to be CORRECTED, never deleted.
  Investigate what a weird thing was meant to be and repair it; ask Emma if unsure.
* **DO NOT "fix" the `Pages without wikidata legacy[ legacy[ legacy]]` category
  state, and do not auto-edit the Q-titled `[[Category:Double category qids]]`
  dab pages.** Emma did this *surgically and intentionally* (2026-06-08). The
  rationale: `Pages without wikidata` is a crud category being drained, so
  stripping the literal tag off a page races against the self-categorizing
  `{{wikidata link}}` template reintroducing it — a reintroduction collision.
  Moving the legacy population onto a distinct `legacy`-suffixed category name
  that nothing auto-reintroduces removes that race. **The repeated `legacy`
  suffix and the odd dab-page formatting are intentional, not corruption** — it
  is self-healing *unless an agent actively interferes*. Never normalize/revert
  the suffix, never "repair" those dab pages, never point an op at them.
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

## ⛔ LIST MEMBERSHIP BELONGS TO THE ENTRY ITEM, NOT THE MODERN SHRINE (Emma, 2026-07-09)

Her ruling, from `[[Open questions]]`: *"Ronshas should not even have list membership"*, and the
model behind it — **list membership belongs to the entry item, so the candidate loses it.** That is
"Reading A" in the 2026-07-09 decision, and it is what `generate_list_membership_removals.py`
implements.

The shape, worked through 出雲大神宮:

| item | what it is | how it relates |
|---|---|---|
| `Q135040491` 出雲神社 | the **Engishiki entry** | `P361 → Q11368560` with `P1545: 1`, `P155`, `P156` — **this is the membership** |
| `Q10896675` 出雲大神宮 | the **modern shrine** | `P460 → Q135040491`, plus two bare `P361` into the list — **import damage, remove** |

- **A modern shrine carrying `P361` into a 神名帳 list is the defect the removal drip exists to
  fix**, whether or not the register names it, and whether or not the statement carries an ordinal.
  The `~2,151` in `list_membership_removals.txt` were selected **as ronsha**, so they are ronsha by
  construction — not by any test of what the register says.
- **`P527` on the list item is the RIGHT source for the guard**, and it is not a "partial
  transcription". Its members are the **entry items**. A modern shrine is correctly absent from it.
- ⚠ **The trap, walked into twice on 2026-08-23 and both times reported as a data-loss hazard:**
  the register's modern-identification column names the shrine, so it looks like the shrine belongs
  to the list. It does not. Being an entry's modern identification is expressed as **`P460` from the
  shrine to the entry**, never as `P361` into the list. Emma: *"pretty sure this is intended
  behaviour"* — it is. Do not re-derive "the register names it, therefore the membership is real."
- **Before calling any P361 removal wrong, check the item for `P460`.** If it points at a
  `Q135…`-era entry item, the item is a modern shrine and its `P361` is the thing being removed.

## P13677 + P958: identity is the PAIR, and section 0 is not unique (Emma, 2026-08-19)

Her correction, verbatim, after a session reported Kokugakuin ids as duplicates: *"these do not in
fact match — you are not looking at the section qualifiers. They are meant to be unique by the
combination of Kokugakuin University Digital Museum entry ID (P13677) and its qualifier section
(P958)… because each ID is supposed to have many different entries, because there are multiple things
on each page, and they're supposed to be unique by their qualifier — except if their qualifier is
zero, at which point they do not even need to be unique."*

- **One Kokugakuin page = one 927 register entry**, and the page lists that entry's 論社 as numbered
  blocks (`現社名など（１）（２）（３）…`). **P958 is which numbered candidate the item is.**
- **A shared P13677 is NOT a duplicate.** Many items legitimately share an id and are separated by
  P958. Any check that reports duplicates on the id alone is reporting normal data as a defect.
- **`0` and `n/a` carry no uniqueness** — they mean "not one of the numbered candidates", so two
  items may hold the same id with section `0` and neither is wrong.
- This was recorded only in `queue.md` prose until 2026-08-23. It is a data-model rule, so it lives
  here.

## Descriptions and labels — the four-step path

**The authoritative spec is [`docs/description_label_policy.md`](docs/description_label_policy.md)**
(Emma, 2026-08-21, all languages). Core rule: Wikidata's uniqueness constraint is on the
**(label, description) PAIR**, so a description on an item with no label in that language is
**actively harmful** — it costs a label. Order: remove orphan description → add label → add a
programmatic fill-in-the-blanks description → iterate if rejected. The doc also records why a
blanket removals file is the wrong shape (the existing `generate_description_fixes.py` resolves
most orphans by supplying the missing label; removal is only for the residue). Read it before
generating any label or description QuickStatements.

## Wikidata data model for shrine festivals & bunrei

**The authoritative model is [`docs/wikidata_shrine_festival_model.md`](docs/wikidata_shrine_festival_model.md)**
(Emma, 2026-07-07). Core invariants: a shrine's annual festival = ONE P837 statement
(day or unknown-value Q19798648, qualifier P3831 = Q11385469 Reisai — a ROLE, never a
festival item — plus the festival item as a P793 qualifier); bunrei = ONE P612 statement
with P1013 = Q195793 in the same statement. Never put a festival item in P3831; never
emit a bare P612. Read the doc before generating any P837/P612/P793 QuickStatements.

## NEVER "deliberately hold" anything — do it, or fire an AskUserQuestion

Emma 2026-08-04: *"Don't deliberately hold something. Don't narrate it. Just do it and ask
me questions if you need to. Keep in mind I never get any questions that are not
AskUserQuestions."*

**Emma does not see prose questions.** A question written into a report, a commit message,
a queue item, or a chat paragraph is not a question — it is a thing that never gets
answered and silently stalls the work. The ONLY channel that reaches her is the
`AskUserQuestion` tool.

So there are exactly two legal outcomes for anything uncertain:

1. **Do it.** Default. Uncertainty about which of two reasonable options is better is not
   grounds for stopping — pick, act, and say which you picked.
2. **Fire an `AskUserQuestion`** with the concrete options. Immediately, in the same turn
   you discover the need — not in the next report.

Never a third thing: "held pending Emma's word", "waiting on a decision", "flagged for
review". Those are all just *not doing the work* with better vocabulary.

## NEVER walk a MediaWiki category recursively unless Emma asked for it

Emma 2026-08-04: *"Any MediaWiki thing where you do recursive category search is almost
always wrong unless I told you to do recursive category search."*

A category's **direct** members are the set.

**The reason this is not a style preference: MediaWiki categories are not a taxonomy.**
A subcategory is not reliably a *subset* — it is whatever some editor thought was
related. Recursing from a shrine category picks up architecture categories, prefecture
and era trees, festivals, priests, and articles that are not shrines at all, and the
code cannot detect any of it, because every page it collected was genuinely "in the
category". The result is a worklist that looks complete, is silently wrong, and costs
far more API requests than the set anyone asked for. `Category:神宮125社` is 125 shrines;
a recursive walk from it is not "the 125 shrines, thorough".

* Use `list=categorymembers` with `cmnamespace=0` and **do not follow `cmnamespace=14`
  results**. Checking whether sub-categories exist is fine; descending into them is not.
* If a task genuinely seems to need the sub-tree, ASK. Do not infer it from the task
  "feeling incomplete".
* This applies to shinto.miraheze.org and to ja.wikipedia alike.

## DO NOT HAMMER WIKIDATA — and do not use it as a lookup source

Emma 2026-08-03: *"This wikidata is hard to use, so you don't use wikidata. Wikidata is
something that you use for wikidata purposes — it's something we use for our gradual
stuff. You don't fucking hammer it."*

**Wikidata is a DESTINATION, not a database to query for working data.** It exists here
for the gradual QuickStatements drip. It is not the place to look things up.

* **To enumerate a set of shrines, use the Japanese Wikipedia CATEGORY**, via the
  MediaWiki API (`list=categorymembers`) — one cheap paginated call. Emma 2026-08-03,
  on the Beppyo pass: *"Are you seriously trying to get the Beppyo shrines from
  Wikidata? Don't! Get them from the Japanese Wikipedia category for them!"* The QID of
  each article comes free from the same API (`prop=pageprops` → `wikibase_item`), so a
  SPARQL round-trip is not needed for that either.
* **Never issue a large batched SPARQL sweep.** The failure that produced this rule:
  `match_jinjacho_shrines.py` fired ~365 queries per run — 300 of them P131
  transitive-closure batches — at 0.5s spacing, three times in one evening, and drew
  repeated 503/504 which were then blamed on the endpoint. `WDQS_THROTTLE = 2.5` in
  `generate_genbu_ids.py` is now the floor, with exponential backoff (15/45/135s).
* **429 → bail immediately** (existing rule). 503/504 → back off hard, do not retry
  tightly.
* If a task seems to need a broad Wikidata query, prefer: a jawiki category, a jawiki
  article's own content, an already-generated local file, or ask Emma. A slow correct
  source beats a fast one that damages a service we depend on.

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
- **⛔ ENWIKI-MENTION GATE — no Wikidata editing while "Immanuelle" is named on
  [[Wikipedia:AI noticeboard]] or [[Wikipedia talk:WikiProject Japan]]** (Emma,
  2026-08-06). A **condition, not a date**: `cleanup-loop.yml`'s window-gate runs
  `shinto_miraheze/check_enwiki_mentions.py` live and forces `wikidata-daily-fire=false`
  while it is closed; `enwiki-mention-check.yml` records the result daily into
  `enwiki_mention_gate.state`. It **fails closed** (an unreadable page is not absence)
  and **opens by itself** when the threads archive off — do not attach a date to it and
  do not route around it. **This gates Wikidata only** — Emma, same day: *"the freeze
  thing there is a wikidata thing, based on the enwiki thing, shintowiki if it still runs
  is not an issue."* A shintowiki-side hold was built first and reverted; do not re-add
  it. Rationale: `docs/enwiki_mention_gate_2026-08-06.md`.
- **⛔ WIKIDATA LOCKOUT until 2026-09-18 — a month, Emma 2026-08-18:** *"I want a gate
  to be set up that there will be no wikidata editing for a month."* **One state file
  governs every Wikidata write path**, and that is the whole point of it:
  `shinto_miraheze/wikidata_editing_lockout.state` (`locked`, `locked_until`, `reason`),
  read by `shinto_miraheze/wikidata_edit_allowed.py` — exit 0 allowed, exit 1 locked,
  the Wikidata sibling of `wiki_edit_allowed.py` (which gates shinto.miraheze; two wikis,
  two independent lockouts). What checks it:
  - **In code**, in all three scripts that hold `MW_BOTNAME`/`BOT_TOKEN` —
    `direct_daily_edits.py`, `create_items.py`, `substitute_source_shrine_proposal.py` —
    as the first thing in `main()`, so a **local or manual** run is covered, not just CI.
    A locked run prints `SKIPPED:` and exits 0: nothing was attempted, so nothing broke.
  - **In CI**, in `cleanup-loop.yml` (window-gate → `wikidata-daily-fire=false`),
    `create-items.yml`, `direct-daily-edits.yml`, `substitute-source-shrine-proposal.yml`.
    Note `substitute-source-shrine-proposal.yml` has its own September cron and would
    otherwise have fired its one-shot talk-page edit on 2026-09-04, inside the lockout.
  - **By hand**, in the `funding-and-networking` repo: `!quickstatements_now.bat` refuses
    to open QuickStatements while locked, and `wikidata-review/RUN/RUNSHEET.md` carries the
    banner. The hand-run paste batches are a write path like any other.
  - **In the `geni` repo**, which has a **separate** Wikidata editor on a **different bot
    account** (`scripts/wikidata-edit-run.py`, `wikidata-edits.yml`, `START_DATE: 2026-09-01`
    — inside this lockout). Its `scripts/wikidata_lockout.py` reads **this** state file over
    HTTPS, since this repo is public; the date is not copied there. Worth remembering when you
    think a Wikidata gate is finished: the shintowiki bots are not the whole write surface.
  - **To lift or extend: edit that ONE state file.** Do not lift a lockout by editing a
    workflow, a script, or the `.bat` — that is precisely the failure this replaced.
- **Why it is a state file and not a date in the YAML.** It used to be
  `FREEZE_WIKIDATA_UNTIL="…"` pasted into `cleanup-loop.yml` *and* `create-items.yml`. A
  freeze duplicated per-workflow is a freeze one workflow can miss — and one did:
  `create-items.yml`, the only thing in the repo that can create an item, never consulted
  `wikidata-daily-fire` and on 2026-08-16 was hours from creating two items straight through
  the 2026-08-06 enwiki-mention freeze. Those hardcoded dates are gone; do not reintroduce one.
  Do not shorten a lockout without Emma's say-so. (Prior freezes: 2026-05-23→06-06 two weeks;
  2026-07-18→07-20 24h; 2026-07-28→08-04 week; 2026-08-03→08-10 week.)
- This rule was added 2026-05-23 after bespoke direct-API editors
  (P459/kana qualifier scripts with descriptive summaries) were built and run;
  they were deleted. Don't reintroduce that shape.

## Long command series run in strict order
When Emma gives a long series of commands, treat it as a long series of commands to be
executed in relatively STRICT ORDER, one after another, EVEN IF the order seems not to
make sense or seems inefficient. The sequencing is intentional — she organizes the steps
so states change in the order she wants. Do not reorder, merge, or skip steps.
