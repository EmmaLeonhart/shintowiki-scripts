# archive/

Retired / one-off scripts kept for reference only. **Nothing here is wired
into CI** — no workflow invokes these, and they are not part of any active
pipeline. Do not assume they still run against current APIs or schemas.

- `import_to_fandom.py` — local manual single-page miraheze→fandom history
  import (superseded by the `fandom_mirror` op + `fandom/` import workflows).
- `test_fandom_login.py` — local smoke test for fandom mwclient auth.
- `process_dupl.py` — local duplicated-content section merger (superseded by
  the claude.ai remote routine that consumes `remote_queue.json`).
- `wikidata_scripts/` — older Wikidata-side scripts (interwiki restore,
  category tidy, infobox sync, label patches, Streamlit proposal viewer).
  All Wikidata writes now go through the QuickStatements pipeline only
  (see `CLAUDE.md`), so these are not used.

If you resurrect something here, move it back out of `archive/` into the
appropriate directory rather than running it in place.
