"""Validates the `base_url` input of .github/workflows/load-test.yml before k6 sends any traffic.

A load test is a traffic generator, so the target must be an explicitly allow-listed public HTTPS
host, never an internal address, a credential-bearing URL or an arbitrary host a dispatcher typed.

Rules (every failure exits 1 with the reason):
  * scheme is https;
  * no user:pass@ in the URL, no query, no fragment, no path other than "/";
  * the host is a DNS name: IP literals (v4, v6, bracketed, decimal/hex/octal forms) are refused,
    and so are localhost and the .local/.internal/.localhost/.localdomain suffixes;
  * the host is in the repository variable LOAD_TEST_HOSTS (comma separated, exact match);
  * the name resolves only to public addresses (private, loopback, link-local, reserved and
    multicast ranges are refused), which also catches an allow-listed name pointed at an
    internal address.

Usage (the workflow passes values through the environment, never through the shell line):
    BASE_URL=... LOAD_TEST_HOSTS=... python tests/load/validate_base_url.py
Prints the normalised base URL on success.
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import sys
from typing import Callable, Iterable, List, Optional
from urllib.parse import urlsplit

BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".localdomain", ".lan", ".home.arpa")
_NUMERIC_HOST = re.compile(r"^(0x[0-9a-f]+|[0-9]+)(\.(0x[0-9a-f]+|[0-9]+))*$", re.I)
_DNS_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.I)


class InvalidBaseUrl(ValueError):
    pass


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified or not ip.is_global)


def system_resolver(host: str) -> List[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})


def validate(base_url: str, allowed_hosts: Iterable[str],
             resolver: Optional[Callable[[str], List[str]]] = None) -> str:
    """Returns the normalised base URL or raises InvalidBaseUrl. ``resolver`` None skips DNS."""
    if not base_url or base_url != base_url.strip() or any(c in base_url for c in "\r\n\t \\"):
        raise InvalidBaseUrl("empty URL or whitespace/backslash in it")
    parts = urlsplit(base_url)
    if parts.scheme != "https":
        raise InvalidBaseUrl("only https:// is allowed")
    if "@" in parts.netloc or parts.username is not None or parts.password is not None:
        raise InvalidBaseUrl("credentials in the URL are not allowed")
    if parts.query or parts.fragment or "?" in base_url or "#" in base_url:
        raise InvalidBaseUrl("no query string or fragment")
    if parts.path not in ("", "/"):
        raise InvalidBaseUrl("no path: give the origin only")
    try:
        port = parts.port
    except ValueError:
        raise InvalidBaseUrl("invalid port") from None
    if port not in (None, 443):
        raise InvalidBaseUrl("only the default https port is allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise InvalidBaseUrl("no host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise InvalidBaseUrl("IP literals are not allowed")
    if ":" in host or _NUMERIC_HOST.match(host):
        raise InvalidBaseUrl("IP literals (including numeric forms) are not allowed")
    if host == "localhost" or host.endswith(BLOCKED_SUFFIXES):
        raise InvalidBaseUrl("local or internal host names are not allowed")
    if "." not in host or not all(_DNS_LABEL.match(label) for label in host.split(".")):
        raise InvalidBaseUrl("not a fully qualified DNS name")
    allowed = {h.strip().lower().rstrip(".") for h in allowed_hosts if h.strip()}
    if not allowed:
        raise InvalidBaseUrl("LOAD_TEST_HOSTS is empty: set the repository variable first")
    if host not in allowed:
        raise InvalidBaseUrl("host is not in LOAD_TEST_HOSTS")
    if resolver is not None:
        try:
            addresses = resolver(host)
        except OSError:
            raise InvalidBaseUrl("host does not resolve") from None
        if not addresses:
            raise InvalidBaseUrl("host does not resolve")
        bad = [a for a in addresses if not _is_public(a)]
        if bad:
            raise InvalidBaseUrl("host resolves to a non-public address")
    return f"https://{host}"


def main() -> int:
    try:
        print(validate(os.environ.get("BASE_URL", ""), os.environ.get("LOAD_TEST_HOSTS", "").split(","),
                       resolver=system_resolver))
    except InvalidBaseUrl as exc:
        print(f"::error::base_url rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
