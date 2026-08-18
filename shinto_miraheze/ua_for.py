"""Pick the right User-Agent for a URL — for scripts that talk to BOTH sites.

Most scripts talk to one site and should import that site's constant directly. Some genuinely
talk to both in one run (read a page from the wiki, look the item up on Wikidata). Those cannot
use a single module-level constant without sending one site's identity to the other, which is
exactly the leak Emma ruled out on 2026-08-18:

    "if you use the wrong one on either one of the bots, it'll basically be complete operational
     risk. We have strictly segregated user agents for the two of them. Wikidata cannot associate
     the wiki-side contact address with me."

So dual-site call sites resolve the UA from the URL **at request time**, which removes the class
of bug where a human (or a sweep) has to remember which endpoint a given line was talking to.

Fails CLOSED: an unrecognised host raises rather than falling back to a default. A default is how
the wrong identity reaches a host nobody thought about — a redirect, a new endpoint, a copied line.
"""
from urllib.parse import urlparse

from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

# Wikidata-side hosts: the wiki itself, the query service, QuickStatements, and the REST/OAuth
# endpoints that carry the same identity.
_WIKIDATA_HOSTS = ("wikidata.org", "query.wikidata.org", "quickstatements.toolforge.org",
                   "wikidata-todo.toolforge.org")
# Wiki-side hosts: Miraheze and Fandom share one identity, by Emma's instruction.
_WIKI_HOSTS = ("miraheze.org", "fandom.com", "wikia.com", "wikia.org")


def ua_for(url_or_host: str) -> str:
    """-> the correct User-Agent for this URL or bare hostname. Raises on anything unrecognised."""
    if not url_or_host:
        raise ValueError("ua_for() needs a URL or hostname, got an empty value")
    s = str(url_or_host).strip()
    host = urlparse(s).netloc if "//" in s else s.split("/")[0]
    host = host.split("@")[-1].split(":")[0].lower()
    if any(host == h or host.endswith("." + h) for h in _WIKIDATA_HOSTS):
        return WIKIDATA_USER_AGENT
    if any(host == h or host.endswith("." + h) for h in _WIKI_HOSTS):
        return USER_AGENT
    raise ValueError(
        f"ua_for(): no User-Agent is defined for host {host!r}. Add it to the right list in "
        "shinto_miraheze/ua_for.py — deliberately refusing to guess, because guessing is how one "
        "site's identity reaches another."
    )
