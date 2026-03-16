# modern-quickstatements

Automated QuickStatements generation for Wikidata shrine property maintenance.

## Current: Modern Shrine Ranking Qualifiers

Adds `P1027` (conferred by) → `Q712534` (modern system of ranked Shinto shrines) qualifier to all `P13723` (modern shrine ranking) statements on Wikidata.

This is prep work for generalizing `P13723` to support multiple shrine ranking systems, where the qualifier distinguishes which system conferred the rank.

### Usage

```bash
python generate_modern_shrine_ranking_qualifiers.py
```

Outputs `modern_shrine_ranking_qualifiers.txt` — paste into [QuickStatements](https://quickstatements.toolforge.org/) to apply.

### Current output

- **4,179** statements across all shrines with `P13723`
- QuickStatements v1 format: `QXXX	P13723	QYYY	P1027	Q712534`

## Future Plans

- GitHub Actions automation for regenerating QuickStatements
- Support for other shrine ranking system qualifiers
