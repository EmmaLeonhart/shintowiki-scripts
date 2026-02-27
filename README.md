# wikibot

A bot framework for editing MediaWiki wikis, primarily [shinto.miraheze.org](https://shinto.miraheze.org), with integration against Wikidata and the [pramana.dev](https://pramana.dev) server.

---

## Current state

The root directory and `shinto_miraheze/` contain hundreds of accumulated one-off scripts, log files, and data CSVs from several years of iterative work. Most of these are legacy ChatGPT-era scripts that are no longer needed. A cleanup pass is planned (see [VISION.md](VISION.md)).

The active, maintained scripts are documented in [SCRIPTS.md](SCRIPTS.md).

Current local orchestration baseline for cleanup runs is shinto_miraheze/cleanup loop.bat; this is the basis for the planned CI/CD bot pipeline migration.

---

## Active scripts (shinto.miraheze.org pipeline)

| Script | Purpose |
|--------|---------|
| `shinto_miraheze/resolve_category_wikidata_from_interwiki.py` | Resolves Wikidata QIDs for category pages by querying their interwiki links |
| `shinto_miraheze/create_category_qid_redirects.py` | Creates `Q{QID}` redirect pages in mainspace pointing to their category |
| `shinto_miraheze/fix_ill_destinations.py` | Fixes broken ILL template destinations |
| `shinto_miraheze/add_moved_templates.py` | Adds `{{moved to}}` / `{{moved from}}` templates after page moves |
| `shinto_miraheze/resolve_duplicated_qid_categories.py` | Merges CJK/Latin duplicate QID category pairs; tags Latin/Latin pairs as erroneous |
| `shinto_miraheze/create_wanted_categories.py` | Creates wanted category pages (categories with members but no page) |
| `shinto_miraheze/remove_crud_categories.py` | Strips all subcategories of Category:Crud_categories from member pages |

---

## Credentials / secrets

Active `shinto_miraheze/*.py` scripts now support environment-variable overrides:
- `WIKI_USERNAME`
- `WIKI_PASSWORD`

Until then, do not share this repo publicly.

Required credentials (to be moved to environment variables or a `.env` file):
- `WIKI_USERNAME` / `WIKI_PASSWORD` â€” MediaWiki bot account (`EmmaBot` on shinto.miraheze.org)
- Pramana server credentials (future)

For local development, copy `.env.example` to `.env` and set real values in your shell or environment manager.

---

## Setup

```bash
pip install mwclient requests
```

Run any script directly:
```bash
python create_category_qid_redirects.py
python shinto_miraheze/resolve_category_wikidata_from_interwiki.py
```

Run the Ubuntu cleanup loop locally:
```bash
bash shinto_miraheze/cleanup_loop.sh
```

---

## GitHub Actions (Ubuntu)

A manual workflow is available at `.github/workflows/cleanup-loop.yml`.

Set these repository or environment secrets before running:
- `WIKI_USERNAME`
- `WIKI_PASSWORD`

Then run the workflow via `workflow_dispatch`.

---

## See also

- [VISION.md](VISION.md) â€” full architecture plan and future direction
- [SCRIPTS.md](SCRIPTS.md) â€” catalog of all scripts with status
- [API.md](API.md) â€” how every external service is accessed (mwclient, Wikidata, Wikipedia APIs)
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) â€” page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, category/template/talk page conventions, known issues
- [HISTORY.md](HISTORY.md) â€” wiki development timeline and context: origins, suspension/restoration, shikinaisha project, category system, WikiProject Shinto situation
- [TODO.md](TODO.md) â€” prioritized list of all known tasks

