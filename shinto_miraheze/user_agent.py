"""THE single canonical bot User-Agent — the one and only spot it is defined.

Emma 2026-07-14: every wiki/API request the bot makes must use this exact
User-Agent. It used to be copy-pasted into ~86 places with drifting values;
now it lives here and everything imports it. To change the bot's UA, edit the
one string below.

Consumers import it with a run-context-independent bootstrap (the scripts are
launched both as `python3 dir/foo.py` and as `python3 -m shinto_miraheze.foo`,
from several directories), e.g.:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.user_agent import USER_AGENT
"""

USER_AGENT = "EmmaBot/2.0 (https://shinto.miraheze.org/wiki/User:EmmaBot; emmaleonhart999@gmail.com)"
