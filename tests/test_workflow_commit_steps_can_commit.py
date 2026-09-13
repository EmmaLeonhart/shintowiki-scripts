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
