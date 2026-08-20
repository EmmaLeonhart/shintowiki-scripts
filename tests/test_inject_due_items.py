"""Tests for the scheduled-item injector.

The mechanism exists because Emma does not want deferred work sitting in `queue.md` wearing
a PARKED label: *"it being visible in the queue as 'parked' adds clutter."* An item appears
on the day it becomes workable, which is also the first day anyone could act on it.

Most of what is pinned here is idempotence, because the failure it prevents is ugly in a
specific way: a re-injection does not error, it silently duplicates a block of prose inside
the file Emma reads to decide what to work on.
"""
import datetime
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scheduled"))

import inject_due_items as inj  # noqa: E402


ITEM = {
    "id": "demo-item",
    "due": "2026-09-21",
    "title": "demo",
    "targets": ["queue"],
    "queue_anchor": "## Pinned tail (keep last)",
    "injected": None,
    "body_md": ["## Scheduled — demo", "", "body text"],
    "body_wiki": ["* '''demo'''"],
}

QUEUE = "# Queue\n\n## Active\n\nstuff\n\n## Pinned tail (keep last)\n\n- last thing\n"


def _data(**over):
    item = dict(ITEM)
    item.update(over)
    return {"items": [item]}


# ───────────────────────────── the date gate ─────────────────────────────

def test_not_due_the_day_before():
    assert inj.due_items(_data(), datetime.date(2026, 9, 20)) == []


def test_due_on_the_day():
    assert len(inj.due_items(_data(), datetime.date(2026, 9, 21))) == 1


def test_still_due_after_the_day():
    """A missed run must not skip the item forever -- the gate is >=, not ==."""
    assert len(inj.due_items(_data(), datetime.date(2026, 12, 25))) == 1


def test_malformed_due_raises_rather_than_being_skipped():
    """A typo'd date must not silently mean 'never'."""
    with pytest.raises(ValueError):
        inj.due_items(_data(due="Sept 21"), datetime.date(2026, 9, 21))
    with pytest.raises(ValueError):
        inj.due_items({"items": [{"id": "x"}]}, datetime.date(2026, 9, 21))


# ───────────────────────────── injection ─────────────────────────────

def test_lands_before_its_anchor():
    out, how = inj.inject_queue(QUEUE, ITEM)
    assert out.index("## Scheduled — demo") < out.index("## Pinned tail (keep last)")
    assert "before" in how


def test_a_renamed_anchor_appends_instead_of_dropping_the_item():
    """Losing the item because a heading was renamed is the worst outcome available:
    the date passes, nothing appears, and nothing reports that anything was missed."""
    out, how = inj.inject_queue("# Queue\n\nno anchor here\n", ITEM)
    assert "## Scheduled — demo" in out
    assert "anchor not found" in how


def test_wiki_body_omitted_means_queue_only():
    out, how = inj.inject_wiki("page\n", dict(ITEM, body_wiki=[]))
    assert out == "page\n" and "skipped" in how


def test_wiki_creates_its_own_section_then_reuses_it():
    once, how1 = inj.inject_wiki("page\n", ITEM)
    assert inj.WIKI_SECTION in once and "created" in how1
    twice, how2 = inj.inject_wiki(once, dict(ITEM, id="other"))
    assert twice.count(inj.WIKI_SECTION) == 1, "must not create a second section"
    assert "into" in how2


# ───────────────────────── idempotence: the marker decides ─────────────────────────

def test_marker_is_written_and_detected():
    out, _ = inj.inject_queue(QUEUE, ITEM)
    assert inj.already_present(out, "demo-item")
    assert not inj.already_present(QUEUE, "demo-item")


def test_second_run_is_a_no_op(tmp_path):
    store, queue = _write_fixture(tmp_path)
    inj.main(["--today", "2026-09-21"])
    first = io.open(queue, encoding="utf-8").read()
    inj.main(["--today", "2026-09-21"])
    assert io.open(queue, encoding="utf-8").read() == first
    assert first.count("## Scheduled — demo") == 1


def test_the_json_flag_is_a_record_not_the_guard(tmp_path):
    """The guard must survive someone reverting or merge-resolving the json.

    If `injected` were the guard, a revert of that tracked file would re-fire every item and
    duplicate its prose into the queue. The marker lives in the file it protects.
    """
    store, queue = _write_fixture(tmp_path)
    inj.main(["--today", "2026-09-21"])
    first = io.open(queue, encoding="utf-8").read()

    data = json.load(io.open(store, encoding="utf-8"))
    data["items"][0]["injected"] = None            # simulate the revert
    json.dump(data, io.open(store, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    inj.main(["--today", "2026-09-21"])
    assert io.open(queue, encoding="utf-8").read() == first


def test_dry_run_writes_nothing(tmp_path):
    store, queue = _write_fixture(tmp_path)
    before_q = io.open(queue, encoding="utf-8").read()
    before_s = io.open(store, encoding="utf-8").read()
    inj.main(["--today", "2026-09-21", "--dry-run"])
    assert io.open(queue, encoding="utf-8").read() == before_q
    assert io.open(store, encoding="utf-8").read() == before_s


def test_unknown_target_does_not_crash_the_other_targets(tmp_path):
    store, queue = _write_fixture(tmp_path, targets=["nowhere", "queue"])
    assert inj.main(["--today", "2026-09-21"]) == 0
    assert "## Scheduled — demo" in io.open(queue, encoding="utf-8").read()


# ───────────────────────────── the real store ─────────────────────────────

def test_the_committed_store_parses_and_every_item_is_well_formed():
    data = inj.load()
    assert data["items"], "store is empty"
    for item in data["items"]:
        datetime.date.fromisoformat(item["due"])          # raises if malformed
        assert item["id"] and item["targets"]
        assert set(item["targets"]) <= set(inj.TARGETS), item["targets"]
        assert item.get("body_md") or item.get("body_wiki"), item["id"]


def test_nothing_in_the_committed_store_is_due_before_the_wikidata_lockout_lifts():
    """Every deferred item here waits on either the 2026-09-18 lockout or Emma's 09-21.
    An item dated earlier than that would fire on the next scheduled run, which is not
    what 'deferred' meant for any of them."""
    for item in inj.load()["items"]:
        assert datetime.date.fromisoformat(item["due"]) >= datetime.date(2026, 9, 18), item["id"]


def _write_fixture(tmp_path, **over):
    """Point the module at a temp store + queue, and undo it after the test."""
    store = tmp_path / "scheduled_items.json"
    queue = tmp_path / "queue.md"
    io.open(str(queue), "w", encoding="utf-8", newline="\n").write(QUEUE)
    json.dump(_data(**over), io.open(str(store), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    inj.STORE = str(store)
    # EVERY target is redirected, not just the one the test asserts on. A half-redirected
    # fixture is how an early run of this file wrote into the real `Open questions` page:
    # `queue` pointed at tmp while `open-questions` still pointed at the repo.
    inj.TARGETS = {name: str(tmp_path / os.path.basename(path))
                   for name, path in inj.TARGETS.items()}
    inj.TARGETS["queue"] = str(queue)
    return str(store), str(queue)


@pytest.fixture(autouse=True)
def _restore_module_paths():
    store, targets = inj.STORE, dict(inj.TARGETS)
    yield
    inj.STORE, inj.TARGETS = store, targets
