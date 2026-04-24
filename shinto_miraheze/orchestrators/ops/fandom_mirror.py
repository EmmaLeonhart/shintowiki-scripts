"""
fandom_mirror helper
====================
Mirrors a page's full revision history from shinto.miraheze.org to
shinto.fandom.com via Special:Export → action=import. Called from
history_offload as a pre-stage, so the wiki-to-wiki mirror happens BEFORE
the source page gets truncated and revdel'd.

Best-effort: if the mirror fails, history_offload retries once and then
continues anyway. The GitHub XML archive (history_offload Stage 1) is
the authoritative backup, so a missing fandom copy is recoverable. Not
gating on fandom prevents a fandom outage from stalling the entire
offload queue.

Credentials:
  FANDOM_USERNAME  — bot-password login (e.g. "Their Eminence@BotName")
  FANDOM_PASSWORD  — bot password token

Gate:
  ENABLE_FANDOM_MIRROR=1 in history_offload's pre-stage check.

Fandom quirks:
  * action=import hard-caps the uploaded XML at 10 MB. Pages with
    thousands of revisions may exceed this and fail with
    code=badupload. Those pages should be skipped by the caller.
  * interwikiprefix is required on XML upload; we set "shintowiki" so
    remote usernames show as "shintowiki>Name" rather than colliding
    with local fandom accounts.
"""

import os

import mwclient

FANDOM_HOST = "shinto.fandom.com"
FANDOM_API = f"https://{FANDOM_HOST}/api.php"
INTERWIKI_PREFIX = "shintowiki"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # fandom hard cap
USER_AGENT = (
    "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) "
    "fandom-mirror (shintowiki-scripts)"
)

# Cached across calls within a single run.
_fandom_site: mwclient.Site | None = None


def _get_fandom_site() -> mwclient.Site:
    global _fandom_site
    if _fandom_site is not None:
        return _fandom_site
    user = os.getenv("FANDOM_USERNAME")
    pw = os.getenv("FANDOM_PASSWORD")
    if not user or not pw:
        raise RuntimeError(
            "FANDOM_USERNAME / FANDOM_PASSWORD not set — cannot mirror to fandom."
        )
    site = mwclient.Site(FANDOM_HOST, path="/", clients_useragent=USER_AGENT)
    site.login(user, pw)
    _fandom_site = site
    return site


def _fetch_source_xml(source_site: mwclient.Site, title: str) -> str:
    """Full-history XML for `title` via the source wiki's Special:Export.

    Reuses source_site.connection (the logged-in requests.Session) so we
    inherit cookies/user-agent without a second login.
    """
    host = source_site.host
    path = source_site.path
    url = f"https://{host}{path}index.php"
    # `curonly` must be OMITTED for full history — SpecialExport.php uses
    # getCheck(), which treats any present value (even "0") as truthy.
    resp = source_site.connection.post(
        url,
        data={
            "title": "Special:Export",
            "pages": title,
            "history": "1",
            "wpDownload": "1",
        },
        timeout=300,
    )
    resp.raise_for_status()
    xml = resp.text
    if "<mediawiki" not in xml:
        raise RuntimeError(
            f"Source export didn't return MediaWiki XML. "
            f"First 200 chars: {xml[:200]!r}"
        )
    return xml


def mirror_page(source_site: mwclient.Site, title: str, run_tag: str) -> tuple[bool, str]:
    """Mirror `title`'s full history to shinto.fandom.com.

    Returns (success, message). Best-effort: the caller (history_offload)
    retries once and then proceeds even on failure, since the GitHub XML
    archive is the authoritative backup.
    """
    try:
        xml = _fetch_source_xml(source_site, title)
    except Exception as e:
        return False, f"source export failed: {e}"

    size = len(xml.encode("utf-8"))
    if size > MAX_UPLOAD_BYTES:
        return False, (
            f"XML {size:,} bytes exceeds fandom cap {MAX_UPLOAD_BYTES:,} — "
            f"cannot mirror via single upload"
        )

    try:
        fandom = _get_fandom_site()
    except Exception as e:
        return False, f"fandom login failed: {e}"

    try:
        token = fandom.get_token("csrf")
    except Exception as e:
        return False, f"fandom csrf token failed: {e}"

    try:
        resp = fandom.connection.post(
            FANDOM_API,
            data={
                "action": "import",
                "format": "json",
                "token": token,
                "summary": f"Mirror from shintowiki {run_tag}",
                "interwikiprefix": INTERWIKI_PREFIX,
            },
            files={
                "xml": ("export.xml", xml.encode("utf-8"), "application/xml"),
            },
            timeout=300,
        )
    except Exception as e:
        return False, f"fandom import POST failed (transport): {e}"

    # Capture status + body snippet BEFORE attempting JSON parse. Historically
    # the error surfaced as the opaque "Expecting value: line 1 column 1 (char
    # 0)" JSONDecodeError, which can't distinguish 429 vs 403 IP-block vs 503
    # vs Cloudflare interstitial vs session-expired login HTML. Logging the
    # status code and first 200 chars of the body makes the next failure
    # diagnosable at a glance.
    status = resp.status_code
    snippet = (resp.text or "")[:200].replace("\n", "\\n")
    try:
        body = resp.json()
    except Exception as e:
        return False, (
            f"fandom import POST non-JSON response "
            f"(HTTP {status}, body[:200]={snippet!r}): {e}"
        )

    if "error" in body:
        err = body["error"]
        return False, f"fandom API error: {err.get('code')} — {err.get('info')}"

    imported = body.get("import", [])
    if not imported:
        # Idempotent no-op: every revision in the XML already exists on
        # fandom. This is success — the page IS mirrored.
        return True, "already mirrored (0 new revisions)"
    entry = imported[0]
    return True, (
        f"mirrored {entry.get('revisions', 0)} revisions "
        f"({size:,} XML bytes)"
    )
