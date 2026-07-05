 ▐▛███▜▌   Claude Code v2.1.201
▝▜█████▛▘  Opus 4.8 · Claude Max
  ▘▘ ▝▝    ~\Documents\Github\shintowiki-scripts

 ▎ Fable 5 is back.
 ▎ Until July 7, you can use up to 50% of your plan's weekly usage limit on Fable 5. If you hit your limit, you can continue on Fable 5 with usage credits. Fable 5 draws down usage faster than Opus 4.8. Learn more (https://support.claude.com/en/articles/15424964-claude-fable-5-promotional-access)

> I notice a lot of uncommitted changes. Do you have the context to figure out what these changes are and whether they should be committed? Well actually just for safety I am going to commit them and you analyze whether these were appropriate changes or some kind of error, since a session was interrupted and I am not 100% sure what it was doing, but also it is relatively common that errors like this occur. Once this is resolved please try to figure out what is going on on the wiki, run any necessary tests (like the original handoff things had some tasks that were needed to do and not ure if they are verified to be fixed) so we can know what is going on.

I'll start by reading the required session-start files and analyzing the uncommitted changes. Let me gather context in parallel.

  Read 1 file, ran 2 shell commands

> Original handoff I mean when I was planning on leaving this a few weeks ago and human commits were minimal for a long time


  Searched for 3 patterns, ran 1 shell command

Now it's clear. The interrupted session was executing a planned, scheduled task: backlog item id:1 "retire-terminating-scripts," which was explicitly scheduled for July 2026 (today is 2026-07-05). It deleted 4 terminating cleanup scripts. This looks legitimate, not an error — but I need to verify the deletion was complete. The grep shows wiki-cleanup.yml still references those script names, which would break CI if they weren't unwired. Let me check.

  Searched for 3 patterns


cleanup_loop.sh was last touched 2026-03-19 (~4 months ago) and cleanup loop.bat in Feb — both predate the current orchestrator/per-workflow architecture and neither is wired into any workflow. They're dead local launchers. My verdict on the commit is nearly formed. Now let me run the tests, read the full backlog (the "8 things"), and the DEVLOG top entry.

  Read 1 file, ran 2 shell commands

I have the full picture of the commit now. Let me run the test suite to verify nothing broke from the deletions.

  Ran 1 shell command
deletion of shiki_list_progress.json — normal state housekeeping). All recent CI runs are green, but the top 20 are all sync jobs — I don't see the wiki-editing cleanup-loop/orchestrator runs. Let me check those specifically since they're what actually edits the wiki.

  Ran 1 shell command

cleanup-loop.yml is the live wiki-editing workflow. Latest run (Jul 5 06:17 UTC) succeeded, but the two prior days (Jul 3 & Jul 4) failed. Let me check why those failed and confirm the failures aren't related to the script deletions.

  Ran 1 shell command


  Ran 3 shell commands

Now the full picture is clear. Let me do one final check of queue.md to confirm the current active work-item, then I'll report.

  Ran 1 shell command

I've verified everything. Here's the complete picture.

Verdict on the interrupted-session commit (57bcb140): Appropriate, not an error

That commit executed a documented, date-gated planned task — backlog item id:1 "retire-terminating-scripts," explicitly scheduled for July 2026 (today is 2026-07-05). It deleted 4 terminating cleanup scripts + their 2 huge .state files, and removed the now-satisfied reminder from todo.md and generate_pages.py's backlog. I confirmed each
precondition the plan required:

┌────────────────────────────────┬──────────────────────────────────────────────────┬─────────────────────────────┐
│         Deleted script         │                      │          Verified           │
├────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────┤
│                                │                                                  │ Registered in               │
│ normalize_category_pages.py    │ Ported →                                         │ category_orchestrator.py    │
│ (+.state)                      │ orchestrapage.py     │ (OPS lines 21/49), ran      │
──────────────────────────────────┼─────────────────────────────┤
│ remove_legacy_cat_templates.py │ Ported →                                         │ Registered (OPS lines       │
│  (+.state)                     │ orchestrators/ops/remove_legacy_cat_templates.py │ 22/48), ran green in prod   │
│                                │                                                  │ Jul 5                       │
├────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────┤
│                                │ Drained (0 imports across runs; input queue      │ Commented out in            │
│ reimport_from_enwiki.py        │ empty)                                           │ wiki-cleanup.yml since      │
│                                │                                                  │ before this commit          │
├────────────────────────────────┼──────────────────────────────────────────────────┼─────────────────────────────┤
│ migrate_talk_pages.py          │ Retired 2026-04-22                               │ Comment-only in             │
│                                │                      │ wiki-cleanup.yml            │026-03-19, superseded by the current per-workflow + orchestrator architecture. So they don't break CI; they're just dead files now pointing at deleted scripts (also name-dropped in DEVLOG.md and docs/SCRIPTS.md). Worth cleaning up for org discipline, but harmless.

What's going on on the wiki

- cleanup-loop.yml (the live wiki-editing pipeline) runs daily. Latest run (Jul 5 06:17 UTC) — all green, including category-orchestrator in 6m27s.
- Jul 3 & Jul 4 runs failed, but the failure was isolated to the category-orchestrator step timing out at 160 min — the long-known category-orchestrator slowness (CLAUDE.md flags it as "never completed a full cycle"). Not a code
error, not a regression, and unrelated to the Jul 5 commit; the orchestrator uses the


● Update(docs\SCRIPTS.md)
Removed 1 line
|--------|--------|-------------|
| `run_step.sh` | ACTIVE | Wrapper for each cleanup loop step. Updates `User:EmmaBot` stage before/afte
r execution. |
| `commit_state.sh` | ACTIVE | Commits changed `*.state`, `*.log`, `*.errors` files after each chunk. |
| `cleanup_loop.sh` | LEGACY | Original local orchestrator script. Superseded by the GitHub Actions wor
kflow chain, but kept for reference. |

---


Now the DEVLOG entry. Let me add it at the top (most recent first), keeping existing mentions intact.

  Read 1 file

ml job chain) + the per-namespace
orchestrators. They were legacy monolithic local loops (last meaningfully edited
2026-02-26 / 2026-03-19), superseded by the current per-workflow + orchestrator
architecture. Deleted both from the working tree (git history retains them);
removed the `cleanup_loop.sh` LEGACY row from `docs/SCRIPTS.md`. Older DEVLOG
mentions of these scripts left intact for history. Verdict on the interrupted-
session commit `57bcb140` that deleted the 4 scripts: correct — date-gated
planned task, ported ops registered + green in prod, 317 tests pass, no live CI
ref, no Python imports.

## 2026-07-05 — Provenance rollout Crean/chinese/tok already had it— today). All preconditions verified: the 2 ported scripts are registered as orchestrator ops and ran green in production Jul 5; the other 2 were drained/retired; no live CI reference; no Python imports; 317 tests pass.

What I did beyond analysis:
1. Merged the git divergence — clean auto-merge of your commit with origin's CI state commit (097094af). No conflicts.
2. Deleted the two dead launchers (cleanup_loop.sh, cleanup loop.bat) per your call — they still named the 4 deleted scripts but weren't wired into any workflow. Removed the cleanup_loop.sh row from docs/SCRIPTS.md, kept older DEVLOG mentions, added a DEVLOG note that they were removed. Committed as 7df8bb39.

Wiki state (all healthy):
- cleanup-loop.yml latest run (Jul 5 06:17 UTC) — fully green, including category-orchestrator in 6m27s.
- The Jul 3 & Jul 4 failures were a category-orchestrator step timeout (160 min) — the long-known category slowness flagged in CLAUDE.md, not a code error, and unrelated to the deletions (both predate them; the orchestrator uses the ported ops, never the deleted scripts).
- Sync jobs, QuickStatements submit, and direct-daily-edits all green. Wikidata freeze (to 2026-06-06) is over. Open
Questions page has no unresolved items.

The "8 things" = the 8 backlog items on your GitHub Pages board (site/generate_pages.py). The session finished the
provenance rollout, then closed id:1. Items

Two things left for you:
- Push — local main is ahead of origin by your commit, the merge, and my cleanup commit. I held off since you usually push at session end.
- Optional follow-up: if you want, I can start on any of backlog items 2–8 next.

✻ Crunched for 9m 33s

not a build task                                                │
├─────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 4   │ duplicate-QID tail             │ Drained to ~7 pages; auto-handled in loop — nearly done, not a build     │
│     │                                │ task                                                                     │
├─────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 5   │ Japanese category names        │ Phases a+b shipped; phase (c) gazetteer is genuinely buildable ← real    │
│     │                                │ work                                                                     │
├─────┼────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 6   │ multiple wikidata links        │ Detection+report SHIPPED in CI; residual is per-case human review — not  │
│     │                                │ a build task                                                             │
├─────┼────────────────────────────────┼──────────────────────────────────────────────┤

Let me scope both builds before writing code.

  Listed 1 directory, ran 1 shell command

Both are real, well-specified builds. Let me plan them into queue.md first (per the workflow), then execute. Let me read the full existing generator to know where phase (c) plugs in.

  Read 2 files, listed 1 directory

Now let me analyze the residual list to findctive patterns worth building for phase (c).

Let me plan this into queue.md and mirror to the task tool, then build.

● Update(queue.md)
Added 23 lines

---

## Backlog board barrel-through (2026-07-05 session)

Working the 8 `BACKLOG_ITEMS` (`sitne this session;
* The July-gated terminating-script "still
  producing edits?" gap (the one open piece) was closed by #1 (all 4 confirmed inert +
  deleted). Verify nothing else wired into `wiki-cleanup.yml` is silently inert, then
  remove #2 from the backlog board + todo.md.
- [ ] **#5(c) Japanese category names — jawiki-anchored resolution phase.** Add a phase
  (c) to `generate_category_translation_moves.py`: for residual cats with no local
  `{{wikidata link}}`, resolve via the *jawiki* category of the same title → its enwiki
  category sitelink (authoritative cross-wiki, NOT place-name guessing). Unresolved →
  residual. Unit-test the pure sitelink-extraction helper. Targets the 578-entry residual
  (144 `の歴史` + 69 `の建築物` are the bulk).
- [ ] **#8 recreate-deleted-WD — bustatements.py`.** Walk
  `[[Category:Pages with deleted QID in ill template]]`, render `CREATE` + minimal claim
  set (P11250|"shinto:…") to a HUMAN-REVIEW .txt (NOT auto-submitted — WD item creation
  is human-gated). Tests for the block rendering.

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are ru
nning; start them if this session hasn't.
- [ ] Run the status-report action n end-of-session summary.

Starting with #2 (quick close). Let me verifript in wiki-cleanup.yml is silently inert.

  Searched for 1 pattern

reimport_from_enwiki.py shows as actively invoked — but that file was deleted in the interrupted commit! If it's a live (uncommented) step, CI would break. Let me check the actual line immediately.

 producing edits? wiki-state-driven "
                 "(keep) vs genuinely inert (retire). Not a delete-spree.",
        "kind": "repo_workflow",
        "workflow": ".github/workflows/wiki-cleanup.yml",
    },
    {
        "id": 3, "slug": "ill-missing-wikidata",
        "title": "ILLs without WD= / \"Unknown\" targets",
        "blurb": "Interlanguage-link templates whose Wikidata target is unset or "

● Update(todo.md)
 keep/fix/retire verdicts already exist in [`docs/program_aud
it_2026-06.md`](docs/program_audit_2026-06.md) §3/§8; the empirical "still producing edits?" confirmati
on for the July-gated terminating scripts is the remaining gap (overlaps the July-2026 reminder above).
 **Retired 2026-06-06:** `audit_double_category_qids.py` (was the one unconditional-retire verdict — di
sabled + superseded).
- [x] **Audit which pre-orchestrator legacy scripts still run.** _DONE 2026-07-05._ Catalogue + keep/fi
x/retire verdicts live in [`docs/program_audit_2026-06.md`](docs/program_audit_2026-06.md) §3/§8; the o
ne remaining empirical gap — confirming the July-gated terminating scripts (`reimport_from_enwiki`, `mi
grate_talk_pages`, `normalize_category_pages`, `remove_legacy_cat_templates`) were genuinely inert — wa
s closed when they were confirmed inert and deleted (`57bcb140`, backlog #1). Re-verified no other acti
vely-wired `wiki-cleanup.yml` script*Retired 2026-06-06:** `audit_double_ca
chine: CI invocation graph, orchestrators+ops, legacy CI scri
pts, the Wikidata QS path, the sync/cloud-queue loop, known kludges, in-flight migrations, keep/fix/ret
ire verdicts.

- [x] **Audit which pre-orchestrator legacy scripts still run.** _DONE 2026-07-05._ Catalogue + keep/fi
x/retire verdicts live in [`docs/program_audit_2026-06.md`](docs/program_audit_2026-06.md) §3/§8; the o
ne remaining empirical gap — confirming the July-gated terminating scripts (`reimport_from_enwiki`, `mi
grate_talk_pages`, `normalize_category_pages`, `remove_legacy_cat_templates`) were genuinely inert — wa
s closed when they were confirmed inert and deleted (`57bcb140`, backlog #1). Re-verified no other acti
vely-wired `wiki-cleanup.yml` script points at a deleted file. **Retired 2026-06-06:** `audit_double_ca
tegory_qids.py`.

Now a DEVLOG entry for #2 and commit this task.

● Update(DEVLOG.md)
Added 13 lines

---

## 2026-07-05 — Backlog #2 audit-legacy-scripts CLOSED

The legacy-script audit's keep/fix/r
`docs/program_audit_2026-06.md` §3/§8 since 2026-06-05; the only open piece was the
empirical "are the July-gated terminating scripts actually inert?" confirmation —
and that was closed by backlog #1 (all 4 confirmed inert + deleted, `57bcb140`).
Re-verified this session that no *other* actively-wired script in `wiki-cleanup.yml`
points at a deleted file (the reimport/overwrite steps that name now-touchy scripts
are all commented out; every uncommented `python3 …` step resolves to an existing
file). Removed #2 from the `generate_pages.py` backlog board and from `todo.md`.
Backlog board now: #1/#2 done, #3/#4/#6/#7 shipped-automation (residual = inherent
human review / remote routine), #5/#mainder.

## 2026-07-05 — Removed dead local launchers cleanup_loop.sh + "cleanup loop.bat"

Follow-up to the id:1 "retire-termine day). Both

  Ran 1 shell command

Now #5(c). Before writing code, let me validoach against real Wikidata data — query a few
more common ones (district/郡, prefecture, dissolved municipality) that will appear, then finalize the allowlist.

  Ran 1 shell command

Confirmed place classes (town/city/ward/village/special-city/prefecture/municipality of Japan, etc.). Districts appear as bare names (not の歴史/の建築物 stems), so they're correctly out of scope. Now let me implement phase (c). First the constants + pure helpers:

● Update(shinto_miraheze\generate_category_translation_moves.py)
Added 55 lines
# WikiProject用テンプレート → Q7054879 → "Category:WikiProject templates").
_TEMPLATE_LOOKUP: dict[str, str] = {}

# ─── phase 4: place-name gazetteer (authoritative, NOT guessing) ─────────
# Productive "<place>の<topic>" con half is a fixed
tem is a Japanese place (gate against a
# stem that happens to match a non-place jawiki article — e.g. a religion or a
# company). Verified labels 2026-07-05.
_PLACE_CLASSES: frozenset = frozenset({
    "Q1054813",   # municipality of Japan
    "Q494721",    # city of Japan
    "Q1059478",   # town of Japan
    "Q4174776",   # village of Japan
    "Q137773",    # ward of Japan
    "Q1145012",   # special city of Japan
    "Q17221353",  # capital of pref

            stem = name[: -len(suf)]
            if stem:
                return stem, fmt
    return None


def place_category(fmt: str, enwiki: str, p31: "list[str]") -> "str | None":
    """Given a resolved place stem (its enwiki article title + P31 classes) and a
    topic format, return the English ``Category:…`` name — but ONLY if the item is
    a confirmed Japanese place (P31icle. Otherwise
    None (→ residual). Pure — no network."""
    if not enwiki or enwiki.startswith("Category:"):
        return None
    if not any(p in _PLACE_CLASSES for p in p31):
        return None
    return "Category:" + fmt.format(enwiki)


def get_subcats() -> tuple[list[str], bool]:
    """Return (members, complete). aginated request
    failed (e.g. a Miraheze 502 mid-walk) so the caller can flag the run as a

Now the network fetcher, inserted after fetch_wd_category_names:

● Update(shinto_miraheze\generate_category_translation_moves.py)
Added 35 lines
ns {stem: (enwiki_title, [P31 QIDs])} for
    stems that have a Wikidata item; the caller applies the place gate. Batched by
    50 (wbgetentities cap). ``normalize`` is NOT sent — Wikidata rejects it for
    multi-title requests."""
    out: "dict[str, tuple[str, list[str]]]" = {}
    uniq = sorted(set(stems))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json(WD_API, {
            "action": "wbgetentities", "sites": "jawiki",
            "titles": "|".join(batcms",

            place_stems.append(pp[0])
    place_res = fetch_place_resolutions(place_stems) if place_stems else {}
    print(f"  place stems to resolve: {len(set(place_stems))}  "
          f"(jawiki→WD items: {len(place_res)})")

    new_rows: list[tuple[str, str, str]] = []   # (source, dest, reason)
    residual: list[str] = []
    for c in todo:

        if dest is None and c in _T
 gazetteer (jawiki '{stem}' → enwiki)"

        if dest and dest != src:
            new_rows.append((src, dest, reason))

Now update the docstring which currently says place-name patterns are not attempted:

● Update(shinto_miraheze\generate_category_translation_moves.py)
Added 13 lines, removed 3 lines
   imported enwiki maintenance categories whose only Japanese part is the date.
3. **Hand-maintained template-prefixemplate cats with
 Stems with no clean jawiki→enwiki chain
   (e.g. prefecture-prefixed ``埼玉県美里町`` whose article is ``美里町 (埼玉県)``)
   also fall to residual — never machine-guessed.

Place-name gazetteer patterns (``<place>の神社`` etc.) are deliberately NOT
attempted here — that's where guessing risk lives; those land in the residual
report for the follow-on gazetteer phase.
Other place-name patterns (``の神社`` when no category QID, ``の重要文化財``,
``の旧県社`` shrine-rank-by-place, ``の画像提供依頼`` maintenance, bare ``<place>郡``
districts, …) are still left to the residual report for later phases.


● Update(shinto_miraheze\tests\test_category_translation.py)
Added 45 lines
    for n, name in g._JP_MONTHS.items():
        out = g.dated_transform(f"Foo from 2021年{n}月")
        assert out == f"Category:Foo from {name} 2021"


# ─── phase 4: place-name gazetteer ──────────────────────────
def test_parse_place_history():
    assert g.parse_place_pattern("三History of {}")


def test_parse_place_buildings():
    assert (g.parse_place_pattern("三宅村の建築物")
            == ("三宅村", "Buildings and structures in {}"))


def test_parse_place_empty_stem_is_none():
    # A bare suffix with no place st
    assert g.parse_place_pattern("の歴史") is None


def test_parse_place_non_pattern_is_none():
    assert g.parse_place_pattern("下県郡") is None            # bare district, no suffix
    assert g.parse_place_pattern("三 a shrine, not <place>の…
    assert g.parse_place_pattern("三省堂の国語辞典") is None    # unhandled suffix


{}", "Christianity", ["Q9174"]) is None


def test_place_category_rejects_missing_enwiki():
    assert g.place_category("History of {}", "", ["Q494721"]) is None


def test_place_category_rejects_category_titled_enwiki():
    # An enwiki sitelink that is itself a Category: is not an article place name.
    assert g.place_category("History of {}", "Category:Foo", ["Q494721"]) is None

  Ran 1 shell command

13/13 pass. Now let me exercise the real network path end-to-end (not mocked) to confirm the wiring produces correct rows:

  Ran 1 shell command
 jawiki-anchored resolution phase.** Add a phase
  (c) to `generate_category_translation_moves.py`: for residual cats with no local
  `{{wikidata link}}`, resolve via the *jawiki* category of the same title → its enwiki
  category sitelink (authoritative cross-wiki, NOT place-name guessing). Unresolved →
  residual. Unit-test the pure sitelink-extraction helper. Targets the 578-entry residual
  (144 `の歴史` + 69 `の建築物` are the bulk).
- [ ] **#8 recreate-deleted-WD — build `generate_recreate_quickstatements.py`.** Walk
  `[[Category:Pages with deleted QID in ill template]]`, render `CREATE` + minimal claim
  set (P11250|"shinto:…") to a HUMAN-REVIEW .txt (NOT auto-submitted — WD item creation

● Update(DEVLOG.md)
ts enwiki sitelink (canonical English place
name), and apply the fixed English category convention ("History of X" / "Buildings and
structures in X"). The place name is authoritative (Wikidata cross-wiki), never
transliterated/guessed. A P31 gate requires the item to be a Japanese administrative
division (city/town/village/ward/special-city/prefecture/…), so a stem matching a
non-place jawiki article is rejected → residual; prefecture-prefixed stems whose jawiki
article is disambiguated (`埼玉県美里町` → article `美里町 (埼玉県)`) also fall to residual.
Measured hit rate on a 60-cat sample: 54/60 (90%) resolve to correct enwiki place names
(三条市→Sanjō, Niigata; 三宅村→Miyake, Tokyo; …). New rows append to `category_moves.csv`
(consumed by the monthly `move_categories.py`); unresolved stay in the residual report.
8 new unit tests on the pure parse/gtern, place_category);
e `<place>郡` districts — later phases.

## 2026-07-05 — Backlog #2 audit-legacy-scripts CLOSED

The legacy-script audit's keep/fix/retire verdicts have lived in

  Ran 1 shell command

Now #8. First let me understand the data model (how deleted QIDs are recorded on pages) and — critically — exactly which files the auto-submit pipeline reads, so the review output lands nowhere near it.

  Read 1 file

Key finding: the tagger replaces the deleted QID with the literal DELETED_QID on the page and logs the original QID→page mapping to deleted_qids_report.txt. So the semantics of "what to recreate" (the ill target topic vs the shinto page) matters and isn't obvious. Per the Wikidata-caution rules, I need to investigate the actual page structure before building anything that could create items wrong. Let me inspect the live category and a sample page.

  Ran 2 shell commands

The submitter reads a fixed allowlist of filview file with any other name is safe fromauto-submission. But before building anything that emits CREATE blocks, I need to resolve a real semantic risk: these
pages are in the category because they contated target — the page's own subject mayalready have a Wikidata item, so a naive CREATE ... P11250→page could make duplicates (the exact "re-deleted" failure). Let me inspect sample pages to see the actual structure.

  Ran 1 shell command

I also notice a dd=Q… param on some ills (e.g. dd=Q135500704). Let me check whether that already carries a replacement QID before deciding anything.

  Ran 1 shell command

Decisive finding: the dd=Q… param preserves the original deleted QID (28/28 sampled are indeed deleted on Wikidata). So the recreation targets are the ill sub-topics (medieval people, minor shrines) — many of which were likely deleted for non-notability, which is exactly what re-creating them risks repeating.

This means building an autonomous CREATE-bloeveral hard rules (WD item creation is


Now tests. The script's in a new dir, so I'll add a tests/ there and wire it into CI. Let me write the tests and update ci.yml.

● Write(recreate-deleted-wikidata\tests\test_recreate_quickstatements.py)
Wrote 63 lines to recreate-deleted-wikidata\tests\test_recreate_quickstatements.py
"""Unit tests for the pure logic in generate_recreate_quickstatements.

The wiki/Wikidata fetchers are network; here we test the ill parser, the QS
string sanitiser, and the CREATE-blociki examples.
"""

import os
import sys
vhyvBsY

Emma's refinement for #8: recreation (submission) is out of scope this session, but the info-gathering generator is the deliverable — make the CREATE QuickStatements as info-rich as possible, include reference comments to the old QIDs, and look up what we can from Wikidata. My separate-dir/human-gated structure matches. Let me first validate the base, then add Wikidata enrichment (ja-article existence + whether the ja article is already linked to a live item, so we don't propose duplicates and only sitelink real articles).

  Ran 1 shell command

> I hope that we can get this stuff done relattext limited right now in terms of how long
ource_page: str) -> list[str]:
def render_create_block(target: dict, source_page: str,
                        ja_article_exists: "bool | None" = None,
                        existing_qid: str = "") -> list[str]:
    """Render one ``CREATE`` block (list of QuickStatements lines) for a deleted
    ill target. Pure — no network. jawiki sitelink is added only when a valid ja
    link exists (notability anchor). A ``#`` provenance comment records the
    original deleted QID + source page (comments are for the human reviewer; this
    file is never auto-submitted)."""
    ill target. Pure — no network.

    A ``#`` provenance comment records the original deleted QID (from ``dd=``) +
    source page. The jawiki sitelink (the notability anchor) is emitted only when
    the ja link is present, NOT flagged invalid, and the article is not known to
    be missing (``ja_article_exists`` False suppresses it; None = unknown, keep).
    If ``existing_qid`` is set, the ja article is already linked to a LIVE item —
    a ``# ⚠ ALREADY …`` note is prepended so the reviewer skips a duplicate.
    Comments are for the human reviewer; this file is never auto-submitted."""
    lines: list[str] = []

    lines.append(f"# recreate deleted ill target ({prov}) — from [[{source_page}]]")
    if existing_qid:
        lines.append(f"# ⚠ ALREADY: ja article is linked to live {existing_qid} — "
                     "likely a DUPLICATE; verify before creating.")
    lines.append("CREATE")
    if target["label"]:

    uniq = sorted(set(t for t in ja_titles if t))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json(WD_API, {
            "action": "wbgetentities", "sites": "jawiki",
            "titles": "|".join(batch), "props": "sitelinks", "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue


def fetch_ja_article_existence(ja_titles: "list[str]") -> "set":
    """Return the set of ja titles whose jawiki article currently exists (so a
    sitelink would resolve). Uses the jawiki API `query` (missing flag)."""
    exists: set = set()
    uniq = sorted(set(t for t in ja_titles if t))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json("https://ja.wikipedia.org/w/api.php", {
            "action": "query", "tit
e", ""))
        time.sleep(READ_THROTTLE)
    return exists


def deleted_targets_for_page(text: str) -> "list[dict]":
    seen: set = set()
    targets: list[dict] = []

Now thread the enrichment through main():

cle exists: {len(ja_exists)}")

    def _enrich(t):
        ja = next((ti for l, ti in t["langlinks"] if l == "ja"), "")
        return {"existing_qid": existing.get(ja, ""),
                "ja_article_exists": (ja in ja_exists) if ja else None}

    with_qid = sum(1 for _, t in entries if t["deleted_qid"])
    with_sitelink = sum(1 for _, t in entries
                        if any(l == "ja" for l, _ in t["langlinks"]) and not t["ja_invalid"])
    safe_sitelink = sum(1 for _, t
                        if (e := _enrich(t))["ja_article_exists"] and not e["existing_qid"]
                        and not t["ja_invalid"])
    dup = sum(1 for _, t in entries])
    print(f"Distinct deleted targets: {len(entries)}  |  with original QID "
          f"(dd=): {with_qid}  |  with valid jawiki sitelink: {with_sitelink}")
          f"(dd=): {with_qid}  |  stelink}  |  "
          f"probable duplicates: {dup}")
    print("Sample CREATE:")
    for p, t in entries[:3]:
        for ln in render_create_block(t, p):
        e = _enrich(t)
        for ln in render_create_block(t, p, **e):
            print("  " + ln)

* · with valid jawiki sitelink "
                f"(notability anchor): **{with_sitelink}**. QuickStatements in "
                f"(`dd=`): **{with_qid}** · safe jawiki sitelink (notability "
                f"anchor): **{safe_sitelink}** · probable duplicates (ja already "
                f"linked to a live item): **{dup}**. QuickStatements in "
                "`recreate_quickstatements.txt` — human-gated, not auto-submitted."
                "\n\n")
        if not complete:
            f.write("> **⚠ PARTIAL PASS** — incomplete.\n\n")
        f.write("Targets **without** a valid sitelink are most at risk of "
                "re-deletion — vet \n\n")
        f.write("Targets **without** a notability anchor (no existing ja article "
                "to sitelink, and not already a live item) are most at risk of "
                "re-deletion — do per-item research before submitting:\n\n")
        for p, t in entries:

            links = ", ".join(f"{l}:{ti}" for l, ti in t["langlinks"]) or "—"
            f.write(f"- **{t['label']}** ({links}) · `{t['deleted_qid'] or 'QID lost'}` "

  Ran 1 shell command

Tests green. Now let me run it end-to-end against the live wiki (--apply) to generate the actual output and validate the enrichment works:

  Ran 1 shell command



    label = positional[0] if positional else ""
    # Data-integrity recovery: an earlier bug wrote the DELETED QID into the link
    # TITLE slot (positional[0]), destroying the English name. If the label slot
    # is a bare QID, it is NOT a name — it is the recovered original deleted QID;
    # the English name is lost (other-language labels below may survive).
    if _QID_RE.match(label):
        if not deleted_qid:
            deleted_qid = label
        label = ""

            continue
        if not t["label"] and not t["langlinks"]:
            continue  # nothing recoverable (no name in any language)
        key = (t["label"], tuple(t["langlinks"]))
        if key in seen:
            continue

● Update(recreate-deleted-wikidata\generate_recreate_quickstatements.py)
Added 1 line, removed 1 line
    entries: "list[tuple[str, dict]
ate_quickstatements.py)
Added 13 lines
    assert t["ja_invalid"] is True            # ja_comment marks it invalid


def test_parse_qid_written_into_label_slot_is_recovered():
    # The earlier bug wrote the deleted QID into the link-title slot, destroying
    # the English name. positional[0] being a bare QID must be recovered as the
    # deleted_qid, NOT emitted as a label; other-language labels survive.
    t = g.parse_deleted_ill("Q135491453|de|One Day Spa|ja|ワンデイ・スパ|qid=DELETED_QID")
    assert t["label"] == ""

    t = g.parse_deleted_ill("Foo|ja|フー|en|Foo bar|qid=DELETED_QID")
    assert t["langlinks"] == [("ja", "フー"), ("en", "Foo bar")]

  Running 1 shell command…
  ⎿  $ cd "C:/Users/Immanuelle/Documents/Github/shintowiki-scripts" && python -m pytest recreate-deleted-wikidata/tests/ -q 2>&1 | tail -6 && echo "=== re-run --apply ===" && timeout 500 python recreate-deleted-wikidata/generate_recreate_quickstatements.py --apply 2>&1 | head -18 (28s · 4 lines)
     (ctrl+b to run in background)

* Building #8 recreate-deleted-WD generator… (
√ Close backlog #2 audit-legacy-scripts
√ Build #5(c) jawiki-anchored category resolution
■ Build #8 generate_recreate_quickstatements.py