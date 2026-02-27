# wikibot

A bot framework for editing MediaWiki wikis, primarily [shinto.miraheze.org](https://shinto.miraheze.org), with integration against Wikidata and the [pramana.dev](https://pramana.dev) server.

---

## Current state

The root directory and `shinto_miraheze/` contain hundreds of accumulated one-off scripts, log files, and data CSVs from several years of iterative work. Most of these are legacy ChatGPT-era scripts that are no longer needed. A cleanup pass is planned (see [VISION.md](VISION.md)).

The active, maintained scripts are documented in [SCRIPTS.md](SCRIPTS.md).

Current local orchestration baseline for cleanup runs is shinto_miraheze/cleanup loop.bat; this is the basis for the planned CI/CD bot pipeline migration.

## Operations policy

I, Emma Leonhart, am no longer doing normal mass-edit runs from my local computer. Standard bot operations must run through GitHub Actions so they are auditable and lower-anxiety to operate. Major changes should be made by editing the GitHub repository/workflows and letting the pipeline execute them. Local manual script runs are reserved for emergency intervention only.

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
| `shinto_miraheze/delete_unused_categories.py` | Deletes pages in Special:UnusedCategories, except pages containing `{{Possibly empty category}}` |

---

## Credentials / secrets

Active `shinto_miraheze/*.py` scripts now support environment-variable overrides:
- `WIKI_USERNAME`
- `WIKI_PASSWORD`

Until then, do not share this repo publicly.

Required credentials (to be moved to environment variables or a `.env` file):
- `WIKI_USERNAME` / `WIKI_PASSWORD` â€” MediaWiki bot password login (example username format: `EmmaBot@EmmaBot`)
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

A workflow is available at `.github/workflows/cleanup-loop.yml`.

Set these repository or environment secrets before running:
- `WIKI_USERNAME` (variable, bot username like `EmmaBot@EmmaBot`)
- `WIKI_PASSWORD`

The workflow runs on:
- manual dispatch (`workflow_dispatch`)
- every push (`push`)
- every 24 hours (`schedule`, at `00:00` UTC)

Pipeline behavior:
- Uses bot-password login (`WIKI_USERNAME` format `MainUser@BotName`)
- Writes a run-start status update to `[[User:EmmaBot]]` from `EmmaBot.wiki` + trigger metadata
- Runs unused-category deletion first (with `{{Possibly empty category}}` safeguard)
- Runs cleanup scripts sequentially with a per-script edit cap (`WIKI_EDIT_LIMIT=1000`)
- Commits updated `*.state` files back to the current branch after successful runs

---

## See also

- [VISION.md](VISION.md) â€” full architecture plan and future direction
- [SCRIPTS.md](SCRIPTS.md) â€” catalog of all scripts with status
- [API.md](API.md) â€” how every external service is accessed (mwclient, Wikidata, Wikipedia APIs)
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) â€” page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, category/template/talk page conventions, known issues
- [HISTORY.md](HISTORY.md) â€” wiki development timeline and context: origins, suspension/restoration, shikinaisha project, category system, WikiProject Shinto situation
- [TODO.md](TODO.md) â€” prioritized list of all known tasks

