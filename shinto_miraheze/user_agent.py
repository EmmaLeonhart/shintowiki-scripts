"""THE canonical User-Agent for MIRAHEZE + FANDOM. Wikidata has its own — never share them.

    shinto_miraheze/user_agent.py           USER_AGENT          -> shinto.miraheze.org + fandom
    shinto_miraheze/wikidata_user_agent.py  WIKIDATA_USER_AGENT -> wikidata.org / WDQS / QuickStatements

Emma, 2026-08-18: the two identities are strictly segregated, and using the wrong one on either bot
is an operational risk. Do not merge the constants, import one from the other, or add a shared
fallback. `tests/test_user_agent_segregation.py` enforces both directions.

The contact address is the `MIRAHEZE_UA_CONTACT` repo secret, not a literal here — see ua_contact.py.

The farm allowlists bots BY User-Agent, so changing this string can un-allowlist it. Tell them first.
Scripts import it via the usual run-context-independent bootstrap:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.user_agent import USER_AGENT
"""
from shinto_miraheze.ua_contact import contact

USER_AGENT = (
    "EmmaBot/3.1 "
    "(https://shinto.miraheze.org/wiki/User:EmmaBot; "
    "+https://github.com/EmmaLeonhart/shintowiki-scripts; "
    f"{contact('miraheze')})"
)
