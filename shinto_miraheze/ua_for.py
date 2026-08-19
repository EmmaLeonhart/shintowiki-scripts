"""Pick the right User-Agent for a URL — for scripts that talk to BOTH sites.

Most scripts talk to one site and import that site's constant directly. Some read a page from the
wiki and look the item up on Wikidata in the same run; those resolve the UA from the URL at request
time, so no call site depends on remembering which endpoint a given line was talking to.

Fails CLOSED: an unrecognised host raises rather than falling back to a default.
"""
from urllib.parse import urlparse

from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

# Wikidata-side hosts: the wiki itself, the query service, QuickStatements, and the REST/OAuth
# endpoints that carry the same identity.
# Wikimedia projects other than Wikidata (en/ja Wikipedia, Commons, Wikisource...) are read by the
# gate checks and the label pipelines. They carry the SAME identity as Wikidata: they are the same
# account's footprint on the same federation, and sending the wiki-side agent to a Wikimedia project
# would put the two personas on one platform.
# Added 2026-08-19 after ua_for's fail-closed rule broke check_enwiki_mentions.py — see the test.
_WIKIDATA_HOSTS = ("wikidata.org", "query.wikidata.org", "quickstatements.toolforge.org",
                   "wikidata-todo.toolforge.org",
                   "wikipedia.org", "wikimedia.org", "wikisource.org", "wiktionary.org")
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
