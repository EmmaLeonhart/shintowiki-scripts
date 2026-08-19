"""Canonical User-Agent for MIRAHEZE + FANDOM requests.

One definition, imported everywhere; it used to be copy-pasted into ~86 places with drifting values.
Separate from the Wikidata constant in `wikidata_user_agent.py` by design — never shared, never
merged. `tests/test_user_agent_segregation.py` enforces that.

The contact address is the `MIRAHEZE_EMAIL` repo secret, resolved at runtime; see ua_contact.py.

The farm allowlists bots by User-Agent, so changing this string can un-allowlist the bot. Tell them
before changing it. And keep it truthful — no browser impersonation on any path that touches the wiki.

Bootstrap, as elsewhere in this repo:

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
