"""A workflow step that runs `git commit` must first set an author identity.

On 2026-09-13 a newly added step in `generate-quickstatements.yml` ran `git add`
and `git commit` without `git config user.name` / `user.email`. The commit died
with "Author identity unknown", `continue-on-error: true` painted the step green,
and the staged changes were left in the index for the next commit step to trip
over. That step then hit a transient GitHub push rejection and its retry could
not run against the dirty tree, so the whole run's generated output was lost.

A commit step that cannot commit is worse than no commit step: it fails silently
and hands the mess downstream. This finds every step that commits and asserts it
can, rather than trusting each new one to remember.
"""

import os
import re

WORKFLOWS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows",
)


def _jobs(text):
    """{job name: [(step name, step body)]}, in file order.

    Order and job scope both matter. `git config` writes the repo config, so it
    persists across every LATER step of the same job — most workflows here set it
    once in a "Configure git" step near the top, and their commit steps rely on
    that. A first version of this test ignored that and flagged seven healthy
    workflows; asserting something false is worse than not asserting it.
    """
    out = {}
    body = text.split("\njobs:", 1)[-1]
    for chunk in re.split(r"\n  (?=[A-Za-z][\w-]*:)", body):
        job = chunk.split(":", 1)[0].strip()
        steps = [(b.split("\n", 1)[0].strip().strip('"'), b)
                 for b in re.split(r"\n      - name:", chunk)[1:]]
        if steps:
            out[job] = steps
    return out


def _steps_with_run(text):
    out = []
    for steps in _jobs(text).values():
        out.extend(steps)
    return out


def _workflow_files():
    for entry in sorted(os.listdir(WORKFLOWS)):
        if entry.endswith((".yml", ".yaml")):
            yield entry, open(os.path.join(WORKFLOWS, entry), encoding="utf-8").read()


def test_every_committing_step_has_an_identity_set_before_it():
    offenders = []
    for filename, text in _workflow_files():
        for job, steps in _jobs(text).items():
            configured = False
            for name, block in steps:
                commit_at = next((m.start() for m in
                                  re.finditer(r"^\s*git commit\b", block, re.M)), None)
                config_at = block.find("git config user.name")
                # Fine if an earlier step configured it, or if this very block
                # configures it before its own first commit — the common shape.
                if commit_at is not None and not configured:
                    if config_at == -1 or config_at > commit_at:
                        offenders.append(f"{filename} [{job}]: {name}")
                if config_at != -1:
                    configured = True
    assert not offenders, (
        "these run `git commit` with no `git config user.name` earlier in the same "
        f"job, so the commit dies with 'Author identity unknown': {offenders}")


def test_the_two_commit_steps_in_the_generator_job_do_not_stage_the_same_files():
    """`Commit generated files to repo` owns modern-quickstatements/*.txt and
    handles it with a backup/reset/clean/rebase/restore dance. The cloud-queue
    step must not stage the same set — two steps committing one file set in one
    job is a race by construction."""
    text = open(os.path.join(WORKFLOWS, "generate-quickstatements.yml"),
                encoding="utf-8").read()
    steps = dict(_steps_with_run(text))
    cloud = next(b for n, b in steps.items() if n.startswith("Commit: collected answers"))
    body = cloud.split("run: |", 1)[1]
    assert "modern-quickstatements/*.txt" not in body, (
        "the cloud-queue commit step stages the generated .txt files, which the "
        "'Commit generated files to repo' step below already owns")


def test_the_changed_file_list_is_asked_of_git_status_not_git_diff():
    """`git diff` compares the worktree against the INDEX, so a file another step
    has already staged is invisible to it.

    That is not hypothetical. On 2026-09-13 the step above staged
    `modern-quickstatements/*.txt` and then failed to commit (no git identity), so
    ~30 regenerated files were sitting staged when this step asked what had
    changed. `git diff --name-only` listed 25 of ~45; the rest were not backed up
    and the `git clean -fd` / `git checkout -- .` below reverted them to HEAD —
    `invalid_p825_removals.txt` from its regenerated 17 lines back to 16,
    `ronsha_role_qualifiers.txt` from 497 back to 502, silently.

    `git status --porcelain` reports staged, unstaged and untracked alike, in one
    root-relative format, which also retires the diff-vs-ls-files path-format
    disagreement that lost every brand-new file until 2026-09-12. One command
    cannot disagree with itself.
    """
    text = open(os.path.join(WORKFLOWS, "generate-quickstatements.yml"),
                encoding="utf-8").read()
    body = dict(_steps_with_run(text))["Commit generated files to repo"]
    listing = body[:body.index("/tmp/qs_files.txt")]
    # The comment block right above the command names both retired commands to
    # explain why they are retired. Assert against the CODE, not its own
    # explanation of itself — the same trap `test_invalid_p825` fell into.
    code = "\n".join(l for l in listing.splitlines() if not l.lstrip().startswith("#"))
    # `git -C … -c … status --porcelain`, so match the subcommand, not "git status".
    assert "status --porcelain" in code, (
        "the changed-file list is no longer built from `git status --porcelain`")
    assert "--untracked-files=all" in code, (
        "without --untracked-files=all git names a new DIRECTORY instead of the "
        "files in it, and the backup loop skips directories")
    assert '-C "$GITHUB_WORKSPACE"' in code, (
        "run it from the repo root — the `sed` below strips a "
        "'modern-quickstatements/' prefix that only root-relative output has")
    assert "git diff --name-only" not in code, (
        "`git diff --name-only` is index-relative and cannot see staged changes")
    assert "git ls-files --others" not in code, (
        "git status already reports untracked files, in the same path format")


def test_the_push_retries_survive_a_dirty_tree():
    """The tree is never clean at that point — _site/ and the json reports are
    still modified — so a bare `git pull --rebase` in a retry path cannot run.
    That is what turned a transient GitHub rejection into a lost commit."""
    text = open(os.path.join(WORKFLOWS, "generate-quickstatements.yml"),
                encoding="utf-8").read()
    for match in re.finditer(r"git push \|\| \{ git pull --rebase([^&]*)&&", text):
        assert "--autostash" in match.group(1), (
            "a push-retry pulls with rebase and no --autostash; it will die on "
            "'cannot pull with rebase: You have unstaged changes'")


def _push_lines(block):
    """Lines that invoke `git push`, stripped, comments removed."""
    for line in block.splitlines():
        code = line.strip()
        if code.startswith("#"):
            continue
        if re.match(r"^git push(\s|$)", code):
            yield code


def test_no_workflow_pushes_without_a_recovery_path():
    """A bare `git push` with nothing after it loses the commit on any rejection.

    Two workflows had one, and both lost a day's work inside six days:

      * 2026-09-18 `submit-quickstatements.yml` — `! [rejected] main -> main
        (fetch first)`. An ordinary race: the cleanup loop runs 26 jobs, several
        push to main, and the rebase two lines above had already happened when
        another job's push arrived. The day's dated report JSON was computed and
        thrown away, so `generate_run_history.py` — which globs `reports/*.json`
        to build the published page — has no 09-18 row and never will.
      * 2026-09-15 `build-run-history.yml` — `! [remote rejected] main -> main
        (Internal Server Error)`, a transient on GitHub's side.

    ⚠ The other eighteen push sites in `.github/workflows/` were already fine:
    they retry in a loop, or guard with `if git push`, or `|| echo WARNING`. This
    is not a new convention — it is the two places that never got it. CLAUDE.md
    says the same thing about `commit_state.sh`: "concurrent pushes from other
    workflow jobs were silently rejecting orchestrator state commits, and only
    one ever reached origin over many weeks. Keep the retry."
    """
    offenders = []
    for filename, text in _workflow_files():
        for name, block in _steps_with_run(text):
            for code in _push_lines(block):
                # A recovery path is anything that reacts to the exit status:
                # `&& break`, `&& exit 0`, `|| { … }`, `|| echo WARNING`, or an
                # `if git push; then …` wrapper (which starts with "if", so it
                # never reaches _push_lines).
                if "&&" not in code and "||" not in code:
                    offenders.append("%s: %s" % (filename, name))
    assert not offenders, (
        "these push with no retry and no fallback, so one concurrent push or one "
        "GitHub 500 discards the commit: %s" % offenders)


def test_the_two_repaired_steps_retry_and_still_go_red():
    """Both halves. A retry alone would turn a persistent failure green, which is
    the trap `generate-quickstatements.yml`'s own comment describes — the work
    stops landing and nothing ever looks wrong."""
    for filename in ("submit-quickstatements.yml", "build-run-history.yml"):
        text = open(os.path.join(WORKFLOWS, filename), encoding="utf-8").read()
        block = next(b for n, b in _steps_with_run(text) if n.startswith("Commit"))
        body = "\n".join(l for l in block.splitlines()
                         if not l.strip().startswith("#"))
        assert "for attempt in 1 2 3 4 5; do" in body, filename
        assert "git pull --rebase --autostash" in body, (
            "%s retries with a pull that cannot run against its own dirty tree"
            % filename)
        assert body.rstrip().endswith("exit 1"), (
            "%s falls out of the retry loop green" % filename)
