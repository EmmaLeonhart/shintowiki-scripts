"""Contact addresses for the bot User-Agents — kept OUT of the source.

The addresses are repo secrets (`MIRAHEZE_EMAIL`, `WIKIDATA_EMAIL`) so the repo cannot be
mined for them. Workflows pass them through as env vars; locally they come from
`shinto_miraheze/.ua_contacts.json`, which is gitignored.

Missing value = raise. A UA with no contact address is what gets a bot blanket-blocked, and a silent
fallback would send one.
"""
import json
import os
import pathlib

_LOCAL = pathlib.Path(__file__).with_name(".ua_contacts.json")


def contact(kind: str) -> str:
    """kind is 'miraheze' or 'wikidata'."""
    env = {"miraheze": "MIRAHEZE_EMAIL", "wikidata": "WIKIDATA_EMAIL"}[kind]
    val = os.environ.get(env, "").strip()
    if val:
        return val
    if _LOCAL.exists():
        try:
            val = str(json.loads(_LOCAL.read_text(encoding="utf-8")).get(kind, "")).strip()
        except Exception:
            val = ""
        if val:
            return val
    raise RuntimeError(
        f"{env} is not set. It is a repo secret; pass it into the workflow's env, or for local runs "
        f"put {{\"miraheze\": \"...\", \"wikidata\": \"...\"}} in {_LOCAL.name} (gitignored). "
        "Refusing to build a User-Agent with no contact address."
    )
