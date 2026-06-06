"""
wiki_login.py
=============
Shared ``login_with_retry`` for the standalone wiki-writing scripts.

Miraheze intermittently returns a spurious ``mwclient.errors.LoginError: The
supplied credentials could not be authenticated`` on a single login even when
the credentials are valid. Observed failing cleanup-loop run ``27036877968``
(2026-06-05): one un-retried ``site.login`` in ``delete_lowercase_template_
collisions`` raised and failed the entire ``cleanup`` job, while every other
step in the SAME run (including the ``undelete_*`` steps right after) logged in
and ran fine.

Every standalone script in this repo does a single un-retried ``site.login`` and
shares that vulnerability — a transient auth flake in any one step red-marks its
whole CI job. This helper centralises the retry so the flake is absorbed; the
final failure is re-raised so a GENUINE bad-credential error still surfaces
rather than being silently swallowed.

Usage::

    from wiki_login import login_with_retry
    login_with_retry(site, USERNAME, PASSWORD)

(Standalone scripts in ``shinto_miraheze/`` run as ``python3 shinto_miraheze/
X.py``, so their own directory is on ``sys.path`` and a bare ``import
wiki_login`` resolves to this sibling module.)
"""

import time


def login_with_retry(site, username, password, attempts=3, base_delay=5):
    """Log in, retrying on a transient login failure before giving up.

    Retries ``attempts`` times with linear backoff (``base_delay * attempt``
    seconds). Any exception from ``site.login`` (``mwclient.errors.LoginError``
    or a transient network error) triggers a retry; the exception from the
    final attempt is re-raised so a real bad-credential failure is not masked.
    """
    last = None
    for attempt in range(1, attempts + 1):
        try:
            site.login(username, password)
            return
        except Exception as e:  # mwclient.errors.LoginError + transient network
            last = e
            if attempt < attempts:
                print(f"  login attempt {attempt}/{attempts} failed ({e}); "
                      f"retrying in {base_delay * attempt}s")
                time.sleep(base_delay * attempt)
    raise last
