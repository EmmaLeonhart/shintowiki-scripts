# docs/script-rationale

**Docs that explain why a RUNNING SCRIPT behaves the way it does.** Emma, 2026-09-17, on where these
belong: *"specific directory for docs explaining running scripts that is different from general docs
and style guide."*

⛔ **The one-week report-expiry rule does not apply here.** `docs/` holds reports — working artifacts
that get cleared once they are a week old, because history lives in `DEVLOG.md` and git. These are
not reports. Each one is cited by a live script or workflow as its RATIONALE: the reason the code
makes the choice it makes. `report_list_structure.py`, `generate_ontology_census_page.py`,
`generate_p958_qualifiers.py`, `direct_daily_edits.py`, `jinjacho_reisai.py`, `conflict_gate.py`,
`lost_shrine_gate.py` and about a dozen more point at files in here.

They are dated because they were written as investigations. The date is when the reasoning was done,
not a shelf life.

**Adding one:** move it here only if a script or workflow actually cites it. If nothing cites it, it
is a report and belongs in `docs/` under the expiry rule.

**Moving one out, or deleting one:** `git grep -l <filename>` across the whole repo first. That check
is the whole reason this directory exists — a five-file scan said only 3 of 29 dated docs were live
and was wrong by fifteen.
