"""THE canonical User-Agent for WIKIDATA. Miraheze/Fandom has its own — never share them.

    shinto_miraheze/user_agent.py           USER_AGENT          -> shinto.miraheze.org + fandom
    shinto_miraheze/wikidata_user_agent.py  WIKIDATA_USER_AGENT -> wikidata.org / WDQS / QuickStatements

Emma, 2026-08-18: strictly segregated identities; the wrong one on either bot is an operational
risk. This string carries the Immanuelle identity and nothing from the wiki side — no contact
address from there, and no `github.com/EmmaLeonhart/...` source link, which is the easy way to hand
Wikidata the association. Do not merge the constants or add a shared fallback.
`tests/test_user_agent_segregation.py` enforces it both ways.

The contact address is the `WIKIDATA_EMAIL` repo secret, not a literal here — see ua_contact.py.

Scripts import it via the usual run-context-independent bootstrap:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
"""
from shinto_miraheze.ua_contact import contact

WIKIDATA_USER_AGENT = (
    "ImmanuelleBot/1.0 "
    "(https://www.wikidata.org/wiki/User:Immanuelle; "
    f"{contact('wikidata')})"
)
