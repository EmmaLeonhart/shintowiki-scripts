# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

- **Seven batches built and waiting on one date**

  BLOCKED-ON-EXTERNAL, single blocker: `wikidata_editing_lockout.state`, **2026-09-18**. Each
  regenerates on every CI build and delivers through the normal drip when it lifts. No work left on
  any of them.

  `orphan_membership_removals.txt` 829 · `p958_by_entry.txt` 109 · `multi_ordinal_removals.txt` 63 ·
  `tenjinsha_en_labels.txt` 47 · `lost_shrine_creates.txt` 44 · `p958_from_kokugakuin.txt` 40 ·
  `p958_corrections.txt` 7

  `_site/membership-removals.html` renders the largest of them for review. It is built and wired into
  `generate-pages.yml`, which only fires from `cleanup-loop`, so it publishes on the next scheduled
  loop — not something this session triggers.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running. Verified live, this session: work-loop
    `0a52da5c` :03, auto-flush `aa735a3c` :15, status-report `f371ceee` :42, briefing `ff8886e6`
    08:03, debrief `924d2b08` 23:57. Crons are session-local, so a recorded ID is only ever evidence
    about the session that made it.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
