"""Robust transport to reach the Telegram Bot API on hostile networks.

The bot token is a secret, so it only ever travels straight to Telegram over
TLS. The "couple of services" (Cloudflare + Google DNS-over-HTTPS) are used ONLY
to look up Telegram's IP when the local DNS is poisoned/blocked — they never see
the token. Each request is attempted through several strategies until one works:

  1. direct        — normal DNS (with the OS cert store + IPv4 preference)
  2. DoH-resolved  — ask Cloudflare/Google over HTTPS for the real IP, connect to
                     it directly (defeats DNS blocking); SNI/cert stay for
                     api.telegram.org so TLS is still verified end-to-end
  3. known IPs      — a small built-in list of Telegram API IPs, as a last resort

The strategy that works is remembered and tried first next time.
"""

import contextlib
import socket
import threading

import requests

TELEGRAM_HOST = "api.telegram.org"

# Representative Telegram Bot API IPs (used only if DNS is unusable).
FALLBACK_IPS = [
    "149.154.167.220", "149.154.166.110", "149.154.175.50",
    "149.154.167.199", "149.154.171.5", "91.108.56.130",
]

# DoH endpoints addressed by IP literal so they need no local DNS themselves.
DOH_ENDPOINTS = [
    "https://1.1.1.1/dns-query",   # Cloudflare
    "https://8.8.8.8/resolve",     # Google
]

_TLS = threading.local()
_orig_getaddrinfo = socket.getaddrinfo
_installed = False


def install():
    """Prefer IPv4 and honour a per-thread forced IP for the connecting socket."""
    global _installed
    if _installed:
        return

    def patched(host, *args, **kwargs):
        forced = getattr(_TLS, "ip", None)
        if forced:
            port = args[0] if args else 0
            family = socket.AF_INET6 if ":" in forced else socket.AF_INET
            return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (forced, port))]
        results = _orig_getaddrinfo(host, *args, **kwargs)
        ipv4 = [r for r in results if r[0] == socket.AF_INET]
        return ipv4 or results  # IPv6-only networks still work

    socket.getaddrinfo = patched
    _installed = True


@contextlib.contextmanager
def force_ip(ip):
    previous = getattr(_TLS, "ip", None)
    _TLS.ip = ip
    try:
        yield
    finally:
        _TLS.ip = previous


def doh_resolve(host=TELEGRAM_HOST, timeout=8):
    """Resolve `host` to IPv4s via DoH (Cloudflare, then Google). [] on failure."""
    for url in DOH_ENDPOINTS:
        try:
            resp = requests.get(url, params={"name": host, "type": "A"},
                                headers={"accept": "application/dns-json"}, timeout=timeout)
            answers = resp.json().get("Answer", []) or []
            ips = [a["data"] for a in answers if a.get("type") == 1 and a.get("data")]
            if ips:
                return ips
        except Exception:
            continue
    return []


class Transport:
    def __init__(self):
        self._doh_ips = None      # None = not looked up yet
        self._preferred = None    # "" (direct) or an IP string

    def _doh(self):
        if self._doh_ips is None:
            self._doh_ips = doh_resolve()
        return self._doh_ips

    def _strategies(self):
        seen, order = set(), []

        def add(ip):
            key = ip or "direct"
            if key not in seen:
                seen.add(key)
                order.append(ip)

        if self._preferred is not None:
            add(self._preferred)
        add("")                       # direct via normal DNS
        for ip in self._doh():
            add(ip)
        for ip in FALLBACK_IPS:
            add(ip)
        return order

    def post(self, session, url, timeout, **kwargs):
        """POST trying each strategy; return the Response or raise the last error."""
        last = None
        for ip in self._strategies():
            try:
                if ip:
                    # a fresh session avoids reusing a pooled connection to a
                    # different IP for the same host
                    with force_ip(ip):
                        with requests.Session() as pinned:
                            resp = pinned.post(url, timeout=timeout, **kwargs)
                else:
                    resp = session.post(url, timeout=timeout, **kwargs)
                self._preferred = ip
                return resp
            except requests.RequestException as exc:
                last = exc
                continue
        raise last if last else requests.RequestException("all connection strategies failed")
