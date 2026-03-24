# modern-quickstatements

Automated QuickStatements generation for Wikidata shrine property maintenance.

## Current: Modern Shrine Ranking Qualifiers

Adds `P459` (determination method or standard) → `Q712534` (modern system of ranked Shinto shrines) qualifier to all `P13723` (shrine ranking) statements on Wikidata.

This is prep work for generalizing `P13723` to support multiple shrine ranking systems, where the qualifier distinguishes which system determined the rank.

### Usage

```bash
python generate_modern_shrine_ranking_qualifiers.py
```

Outputs `modern_shrine_ranking_qualifiers.txt` — paste into [QuickStatements](https://quickstatements.toolforge.org/) to apply.

### Current output

- **4,179** statements across all shrines with `P13723`
- QuickStatements v1 format: `QXXX|P13723|QYYY|P459|Q712534`

## Automated Submission

A daily cron job (06:00 UTC) regenerates the QuickStatements files and submits the atomic Phase 1 lines via the [QuickStatements API](https://www.wikidata.org/wiki/Help:QuickStatements#Using_the_API_to_start_batches). A random 1–3600 second delay is added before submission.

Only atomic operations are submitted automatically:
- **Phase 1**: Add P459 qualifiers to existing P13723 (each line is independent)
- **P958**: Add P958 section qualifiers to P13677 (each line is independent)

Phase 3 migration lines (remove old property + add new P13723) are **non-atomic** and require manual submission.

### Required Secrets

| Secret | Description |
|--------|-------------|
| `QUICKSTATEMENTS_API_KEY` | API token from your [QuickStatements user page](https://quickstatements.toolforge.org/) |
| `QUICKSTATEMENTS_USERNAME` | Wikidata username associated with the token |

Set these in **Settings → Secrets and variables → Actions** on the GitHub repo.

Note: The QuickStatements API may reject requests from GitHub Actions IPs. If that happens, the job simply fails — no retries.
