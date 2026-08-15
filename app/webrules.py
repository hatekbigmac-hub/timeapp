"""Pure URL matching for the website blocklist (domain + path aware)."""


def normalize_url(url: str) -> str:
    u = (url or "").strip().lower()
    for scheme in ("https://", "http://", "ftp://"):
        if u.startswith(scheme):
            u = u[len(scheme):]
            break
    if u.startswith("www."):
        u = u[4:]
    return u.rstrip()


def normalize_pattern(pattern: str) -> str:
    p = normalize_url(pattern)
    if len(p) > 1:
        p = p.rstrip("/")
    return p


def _host_matches(host: str, dom: str) -> bool:
    return host == dom or host.endswith("." + dom)


def match(url: str, patterns) -> str:
    """Return the first pattern that blocks `url`, else ''."""
    norm = normalize_url(url)
    if not norm:
        return ""
    host = norm.split("/", 1)[0]
    path = norm[len(host):]  # '' or '/...'
    for pattern in patterns or []:
        pn = normalize_pattern(pattern)
        if not pn:
            continue
        if "/" in pn:
            phost, ppath = pn.split("/", 1)
            ppath = "/" + ppath
            if _host_matches(host, phost) and path.startswith(ppath):
                return pattern
        else:
            if _host_matches(host, pn):
                return pattern
    return ""
