"""SSRF-safe URL fetching. Every outbound fetch of a user-supplied URL in this
codebase must go through safe_fetch() — no raw httpx.get/requests.get on user input
anywhere else."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app import config


class SSRFError(Exception):
    """Raised when a URL (or a redirect hop) targets a blocked/private network."""


@dataclass
class FetchResult:
    url: str
    status_code: int
    content_type: str
    text: str
    headers: dict[str, str]


def validate_url_format(url: str) -> tuple[bool, str | None]:
    """Cheap structural validation — does not touch the network or DNS."""
    if not url or not isinstance(url, str):
        return False, "URL is empty"
    url = url.strip()
    if len(url) > 2048:
        return False, "URL is too long"
    try:
        parsed = urlparse(url)
    except ValueError as e:
        return False, f"Malformed URL: {e}"
    if parsed.scheme not in ("http", "https"):
        return False, "URL must use http or https"
    if not parsed.hostname:
        return False, "URL has no hostname"
    if parsed.hostname.lower() in config.BLOCKED_HOSTNAMES:
        return False, f"Host '{parsed.hostname}' is not allowed"
    return True, None


def _resolve_and_check(hostname: str) -> None:
    """Resolve hostname via socket.getaddrinfo and reject if ANY resolved IP
    falls in a blocked network — guards against DNS-rebinding."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFError(f"Could not resolve host '{hostname}': {e}") from e

    if not infos:
        raise SSRFError(f"Could not resolve host '{hostname}'")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in config.BLOCKED_NETWORKS:
            if ip in network:
                raise SSRFError(
                    f"Host '{hostname}' resolves to blocked address {ip_str}"
                )


def _validate_hop(url: str) -> None:
    ok, reason = validate_url_format(url)
    if not ok:
        raise SSRFError(reason or f"Invalid URL: {url}")
    hostname = urlparse(url).hostname
    assert hostname is not None
    _resolve_and_check(hostname)


async def safe_fetch(
    url: str,
    *,
    max_size: int = config.MAX_RESPONSE_SIZE,
    timeout: float = config.REQUEST_TIMEOUT,
    max_redirects: int = config.MAX_REDIRECTS,
) -> FetchResult:
    """Fetch a user-supplied URL with SSRF protections: validates and resolves
    every hop (manual redirect handling, no httpx auto-redirects), streams the
    body with a hard size cap, and restricts allowed content types."""
    ok, reason = validate_url_format(url)
    if not ok:
        raise SSRFError(reason or f"Invalid URL: {url}")

    current_url = url
    redirects_followed = 0

    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        while True:
            _validate_hop(current_url)

            async with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    redirects_followed += 1
                    if redirects_followed > max_redirects:
                        raise SSRFError("Too many redirects")
                    location = response.headers.get("location")
                    if not location:
                        raise SSRFError("Redirect response missing Location header")
                    current_url = str(response.url.join(location))
                    await response.aclose()
                    continue

                content_type = response.headers.get("content-type", "").split(";")[0].strip()
                if content_type and content_type not in config.ALLOWED_CONTENT_TYPES:
                    raise SSRFError(f"Disallowed content type: {content_type}")

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_size:
                        raise SSRFError(f"Response exceeded max size of {max_size} bytes")

                text = body.decode(response.encoding or "utf-8", errors="replace")
                return FetchResult(
                    url=str(response.url),
                    status_code=response.status_code,
                    content_type=content_type,
                    text=text,
                    headers=dict(response.headers),
                )
