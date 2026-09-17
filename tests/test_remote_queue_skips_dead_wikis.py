"""While both wikis are down, the cloud queue must not spend its budget on them.

Emma, 2026-09-15: *"I think that almost all of the non-labelling grunge is shit that
is just straight up 100% blocked by the wiki being dead. Both wikis are dead so forget
about them."*

The wiki-bound categories all drain the same way — the worker edits the mirrored file,
drops its gating category, and a sync pushes the page and deletes the local copy. With
Miraheze behind a Cloudflare managed challenge from the runners and Fandom out too,
that push cannot happen, so an answered item is an edit that reaches no wiki. It still
costs one of the five slots the routine spends per day.

Measured when this landed: 2,091 items of which 1,124 (54%) were wiki-bound, so more
than half of every day's budget went on work that could not land. After: 967 items,
all of them bound for Wikidata via the QuickStatements collectors.

⚠ This does NOT test the rate. The routine still takes 5 random items/day and
CLAUDE.md's rule that the slowness is deliberate is untouched — what is pinned here is
WHICH items are eligible, not how many are drawn.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import remote_queue

# Categories whose only route to being "done" is a push to shinto.miraheze.org or
# shinto.fandom.com.
WIKI_BOUND = {
    "duplicated_content",
    "need_translation",
    "fandom_unique",
    "miraheze_unique",
    "git_synced",
}

# Categories that end at Wikidata, via a collector writing QuickStatements lines (or,
# for category_translation, rows in category_moves.csv). Reachable with both wikis down.
WIKIDATA_BOUND = {
    "name_in_kana",
    "category_translation",
    "description_enrichment_en",
    "ronsha_ranking_review",
    "beppyo_p612",
    "label_typo_review",
    # Added 2026-09-17. Stage 4 of the English-label pipeline, folded in after its
    # own cloud routine was lost in the 2026-07-27 account move. Wikidata-bound
    # end to end: the worklist comes from SPARQL, the answer becomes a `Len`
    # QuickStatement via collect_en_labels.py, and nothing touches Miraheze. This
    # is the "labelling" Emma's quote at the top of this file is contrasting the
    # blocked grunge against.
    "en_label",
}


def test_the_flag_is_off():
    assert remote_queue.WIKI_REACHABLE is False, (
        "WIKI_REACHABLE was flipped on; if the wikis really are back that is correct, "
        "but this test is the record that it was a deliberate change")


def test_no_wiki_bound_items_are_queued():
    cats = {i["category"] for i in remote_queue.build_queue()}
    leaked = cats & WIKI_BOUND
    assert not leaked, (
        f"{sorted(leaked)} reached the queue while WIKI_REACHABLE is False — those "
        "items consume the routine's daily budget on edits that cannot be pushed")


def test_the_labeling_queues_are_still_there():
    """The other half of the point. A queue with nothing in it is worse than a long
    one — CLAUDE.md: the pending items are the only way to observe the routine works
    at all."""
    cats = {i["category"] for i in remote_queue.build_queue()}
    assert cats, "the queue is empty; the routine has nothing to chew on"
    assert cats <= WIKIDATA_BOUND, (
        f"unexpected categories {sorted(cats - WIKIDATA_BOUND)} — a new section was "
        "added without deciding which side of the wiki-reachability line it is on")


def test_every_gated_section_can_come_back():
    """The sections are SKIPPED, not deleted: the wikis returning is the expected end
    state, and the instructions/filters must survive until then. Guards against a
    later cleanup pass reading the `if WIKI_REACHABLE:` block as dead code."""
    import inspect
    src = inspect.getsource(remote_queue.build_queue)
    for name in ("duplicated_content", "need_translation", "fandom_unique",
                 "miraheze_unique", "git_synced"):
        assert f'"{name}"' in src, (
            f"the {name} section was deleted rather than gated; flipping "
            "WIKI_REACHABLE back on will no longer restore it")
