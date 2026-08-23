"""Canonical User-Agent for Wikidata requests.

Separate from the Miraheze/Fandom constant in `user_agent.py` by design — the two are never shared,
never merged, and neither imports the other. `tests/test_user_agent_segregation.py` enforces that.

The contact address is the `WIKIDATA_EMAIL` repo secret, resolved at runtime; see ua_contact.py.

Bootstrap, as elsewhere in this repo:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact

WIKIDATA_USER_AGENT = (
    "ImmanuelleBot/1.0 "
    "(https://www.wikidata.org/wiki/User:Immanuelle; "
    f"{contact('wikidata')})"
)
