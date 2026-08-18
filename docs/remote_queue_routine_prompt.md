# The remote-queue routine — canonical prompt (paste-ready)

**Why this file exists.** On 2026-07-27 Emma switched Claude accounts and the claude.ai routine that
drains `remote_queue.json` did not come with her. Recreating it meant reconstructing its prompt from
`docs/remote_queue_pipeline.md` plus DEVLOG entries that happened to quote fragments of it — the prompt
itself was stored **only inside the claude.ai console**, which is exactly the thing an account switch
takes away. That is now fixed: the canonical text lives here, in the repo, and any future session can
rebuild the routine from it in one paste.

**Keep this file in sync.** If the routine's prompt is edited in the console, update this file in the
same sitting. A drifted copy is worse than none.

**A Claude data export will not recover it — don't try again.** Checked on 2026-07-27 against a full
export of the old account (`<WIKIDATA_UA_CONTACT>`): the archive contains `users.json`, one
starter project, `memories.json`, and `conversations.json` (~97 MB, 2000 conversations across two
batches) and nothing else. Zero hits for `Drain remote_queue`, `5 random`, `gating category`, or
`duplicated content`. Exports cover conversations, projects, and memories; automations and Claude Code
cloud sessions are out of scope, so a routine's definition and its daily runs are simply absent. The
only place the original prompt exists is the console of the account that owns the trigger — which is
precisely why it is now committed here.

## How to (re)create the routine

The API works. **The repo binds through `job_config.ccr.session_context.sources`** — an array of
`{"git_repository": {"url": "https://github.com/OWNER/REPO"}}`. Set that, plus a real
`environment_id`, and the routine gets a checkout it can push from.

```jsonc
"session_context": {
  "model": "claude-sonnet-4-5",
  "sources": [{"git_repository": {"url": "https://github.com/EmmaLeonhart/shintowiki-scripts"}}],
  // ...
}
```

Fixed 2026-07-28. Corrections to what this file said before, so nobody re-derives them:

- **The earlier claim that "the API has no field for attaching a repo" was wrong.** `git_repo`,
  `repository`, and `session_context.git_repo` were all tried on 2026-07-27 and silently dropped — but
  those are simply the wrong names. `sources` is the right one and it persists. The lesson that
  generalises is the one that misled: **unknown fields vanish with HTTP 200 and no error**, so always
  re-`get` the trigger after a create/update and confirm the field is actually stored.
- **`environment_id` matters too.** The broken routine carried `env_011111111111111111111117`, a
  placeholder that is not a real environment. The live one is discoverable from the `schedule` skill,
  which lists the account's environments (`env_019bPKmVeahebSCChu7kMpeh`, "Default").
- **`action: "update"` still replaces `job_config` wholesale** rather than merging. A partial
  `job_config` deletes the `events` block — i.e. the prompt. Always resend the complete `job_config`
  including `events`.

Symptom this fixes: the routine did its work, committed locally, then died on
`fatal: unable to access 'http://127.0.0.1:<port>/git/OWNER/REPO.git/': The requested URL returned
error: 403`. The sandbox proxy allows an anonymous clone of a public repo but refuses a push when no
repo is bound to the session. Every run looked green and lost everything it did.

Verified: after the update, a manual `RemoteTrigger run` produced commit `f4a1a494c`
("chore(remote-queue): address 5 items via remote routine") — the first successful push since the
account switch on 2026-07-27.

The console's **+ New routine** flow (which has a repository picker) is still a fine way to create
one; it is how the original `trig_013F9aeKeL3hx8zo7weKj3Ed` was set up, and it ran daily for months.
It is no longer the *only* way.

Settings to match the original:

| Setting | Value |
|---|---|
| Name | Drain remote_queue.json (5 random/day) |
| Repo | `EmmaLeonhart/shintowiki-scripts`, branch `main` (**pick it in the repo selector**) |
| Model | Sonnet |
| Schedule | daily, ~07:41 UTC (the old routine's commits landed ~07:46 UTC) |

## The prompt

Paste this verbatim into the console routine. It assumes the repo is **already attached via the
repo selector**, so it does not clone anything — the session starts inside the checkout. (An earlier
draft opened with `git clone https://github.com/...`; that belongs only in an API-created routine with
no repo bound, and it is wrong here.)

```
You are already in the EmmaLeonhart/shintowiki-scripts checkout, branch main. This is an
unattended scheduled run — nobody is watching, so do not ask questions; make the edits
and push.

Start by running `pwd` and `git remote -v` to confirm you are in the right repo. If you
are NOT in a checkout of shintowiki-scripts, stop and say so as your final message.

If the push fails for ANY reason (auth, network, permissions), do NOT stop silently.
Report the exact failing command and its full error output as your final message.

## Task: drain remote_queue.json — 5 random items

1. Read remote_queue.json at the repo root. Shape:
   {schema_version, generated_at, item_count, items[]}; each item is
   {id, file, category, instruction}. It is regenerated daily from the actual current
   wiki content mirrored into the repo, so it is always "what still needs work".

2. Pick 5 items at RANDOM from items. Random selection (NOT in-order) is the whole
   point. There is NO cursor and NO state file. DO NOT read or write
   consume_remote_queue.state — ignore it entirely.

3. For each of the 5, open item.file and do exactly what item.instruction says. The
   instruction is self-contained and authoritative — follow it LITERALLY. Do not
   substitute your own idea of the task, do not "improve" the approach, do not widen
   the scope. (Historic failure: the routine deduped infobox parameters when the
   instruction was about merging whole duplicated article bodies. Read the
   instruction, do that.)

4. When an item is genuinely finished, remove its gating category from the file (the
   instruction names the category). The repo<->wiki sync treats a file that has lost
   its gating category as done and deletes it, so removing the category is how work
   drains. If an item is NOT genuinely finished, leave the category in place and leave
   it for a later run — never strip a category to fake completion.

5. Touch NOTHING else in the repo. No refactors, no unrelated cleanup, no edits to
   scripts, workflows, docs, or queue files.

6. Files are UTF-8 Japanese/English wikitext. Preserve encoding exactly; do not
   normalize or transliterate characters, and do not reflow unrelated lines.

7. Commit and push to main with the message:

   chore(remote-queue): address N items via remote routine [skip ci]

   where N is how many items you actually completed. The [skip ci] suffix is REQUIRED.
   If the push is rejected, git pull --rebase and retry. Never force-push and never
   reset --hard.

If remote_queue.json is missing or has zero items, do nothing and make no commit — and
say so explicitly in your final message.
```

## Where the constraints come from

Each numbered rule encodes a failure the pipeline already had. Do not "simplify" them away:

- **5 random, no cursor** — the original walked a counter in `consume_remote_queue.state` and never
  revisited, so files that were fixed-but-not-yet-synced were skipped forever and ~105 pages were
  processed under the wrong instruction. Fixed 2026-05-23.
- **Follow `instruction` literally** — the routine once read "duplicated content" as duplicated
  *infobox parameters* and deduped those, when the real task is merging whole article bodies copied in
  two or three times. The per-item `instruction` is authoritative precisely because the category names
  are ambiguous.
- **Remove the gating category only when genuinely done** — category removal is what tells the sync a
  file is finished, and the sync then deletes the local file. Stripping it early destroys queued work.
- **Touch nothing else** — the routine runs unattended against a repo with live CI; scope creep here
  lands unreviewed.

See `docs/remote_queue_pipeline.md` for the end-to-end pipeline and how to debug each stage.
