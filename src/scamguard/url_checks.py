import ipaddress
from urllib.parse import urlsplit
from .config import OFFICIAL_SOURCES

from .config import MAX_URL_CHARS


def analyze_url(raw_url: str) -> dict:
    value = raw_url.strip()
    signals: list[str] = []
    if not value:
        return {"valid": False, "host": "", "signals": ["No URL was provided."], "score": 0}
    if len(value) > MAX_URL_CHARS:
        return {"valid": False, "host": "", "signals": ["URL exceeds the 2,048-character input limit."], "score": 0}
    candidate = value if "://" in value else f"https://{value}"
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").rstrip(".").lower()
        _ = parts.port
    except ValueError:
        return {"valid": False, "host": "", "signals": ["URL structure is invalid."], "score": 0}
    if not host:
        return {"valid": False, "host": "", "signals": ["URL does not contain a hostname."], "score": 0}

    score = 0
    shorteners = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly", "rebrand.ly"}
    if host in shorteners:
        signals.append("The URL uses a shortening service, which hides the final destination.")
        score += 18
    if parts.scheme != "https":
        signals.append("The URL does not use HTTPS; this says nothing by itself about who operates the site.")
        score += 8
    if parts.username is not None or "@" in parts.netloc:
        signals.append("The URL contains @-style user information, which can obscure the actual destination host.")
        score += 30
    try:
        ipaddress.ip_address(host)
        signals.append("The destination uses a raw IP address instead of a conventional domain name.")
        score += 20
    except ValueError:
        pass
    if "xn--" in host:
        signals.append("The hostname contains punycode; check carefully for lookalike characters.")
        score += 20
    if len(host) > 55:
        signals.append("The hostname is unusually long.")
        score += 12
    labels = host.split(".")
    if len(labels) >= 5:
        signals.append("The hostname has many subdomain levels; confirm the registered domain from right to left.")
        score += 10
    known_hosts = [urlsplit(source).hostname for source in OFFICIAL_SOURCES.values()]
    for official_host in known_hosts:
        brand = official_host.split(".")[0]
        if brand in host and not (host == official_host or host.endswith("." + official_host)):
            signals.append(f"The hostname contains the name '{brand}' but is not under the configured official domain {official_host}.")
            score += 28
            break
    if any(token in host for token in ("login", "verify", "account", "secure", "claim", "bonus")):
        signals.append("The hostname uses wording commonly used to attract clicks; verify the registered domain independently.")
        score += 8
    if len(parts.path) > 100 or len(parts.query) > 150:
        signals.append("The URL has an unusually long path or query string.")
        score += 8
    return {"valid": True, "host": host, "signals": signals, "score": min(score, 100)}
