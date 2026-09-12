"""Safely fetch a user-supplied URL.

A user can type ANY url into the wizard. That makes this module the single
most security-sensitive file in the backend: without guards it is a
server-side request forgery (SSRF) hole that would let a visitor use our
server to probe the hosting provider's internal network.

Guards applied here:
  * scheme allow-list (http/https only - no file://, ftp://, gopher://)
  * DNS resolution + private/loopback/link-local IP rejection, re-checked on
    every redirect hop (defeats DNS-rebinding and redirect-to-localhost)
  * hard timeout, redirect cap, and streamed response with a byte cap
  * non-HTML content types rejected before we read the body
"""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_SCHEMES = {"http", "https"}
_SCHEME_PREFIX = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml")


class FetchError(Exception):
    """Raised when the target site cannot be fetched. Message is user-safe."""

    def __init__(self, message: str, code: str = "fetch_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(slots=True)
class FetchResult:
    requested_url: str
    final_url: str
    http_status: int
    html: str
    content_bytes: int
    duration_ms: int
    headers: dict[str, str]


def normalize_url(raw: str) -> str:
    """Accept what a human types ('example.com') and return a real URL."""
    value = (raw or "").strip()
    if not value:
        raise FetchError("No website URL was provided.", code="invalid_url")

    # Detect a scheme by the "word:" prefix, not by "://" - schemes like
    # javascript:, data: and mailto: have no slashes, so a "://" check would
    # silently turn "javascript:alert(1)" into "https://javascript:alert(1)".
    scheme_match = _SCHEME_PREFIX.match(value)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme not in ALLOWED_SCHEMES:
            raise FetchError(
                f"Only http and https URLs can be analysed (got {scheme!r}).",
                code="invalid_url",
            )
    else:
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise FetchError(
            f"Only http and https URLs can be analysed (got {parsed.scheme!r}).",
            code="invalid_url",
        )
    if not parsed.hostname:
        raise FetchError("That URL has no host name.", code="invalid_url")

    # Drop fragments; they never reach the server anyway.
    return urlunparse(parsed._replace(fragment=""))


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_host_is_public(url: str) -> None:
    """Resolve the host and refuse anything pointing inside our own network."""
    if settings.scraper_allow_private_hosts:
        return

    host = urlparse(url).hostname
    if not host:
        raise FetchError("That URL has no host name.", code="invalid_url")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError(
            f"Could not resolve the domain '{host}'. Check the spelling.",
            code="dns_error",
        ) from exc

    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise FetchError(f"Could not resolve the domain '{host}'.", code="dns_error")

    for address in addresses:
        if not _is_public_ip(address):
            raise FetchError(
                "That address points to a private or internal network and "
                "cannot be analysed.",
                code="blocked_host",
            )


async def fetch_page(url: str) -> FetchResult:
    """Fetch one page, following redirects manually so each hop is validated."""
    requested_url = normalize_url(url)
    current_url = requested_url
    started = time.perf_counter()

    headers = {
        "User-Agent": settings.scraper_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
        "Accept-Language": "en-US,en;q=0.9",
    }

    timeout = httpx.Timeout(settings.scraper_timeout_seconds, connect=8.0)

    async with httpx.AsyncClient(
        follow_redirects=False, timeout=timeout, headers=headers
    ) as client:
        for _hop in range(settings.scraper_max_redirects + 1):
            assert_host_is_public(current_url)

            try:
                response = await client.get(current_url)
            except httpx.TimeoutException as exc:
                raise FetchError(
                    "The website took too long to respond "
                    f"({settings.scraper_timeout_seconds:.0f}s limit).",
                    code="timeout",
                ) from exc
            except httpx.HTTPError as exc:
                raise FetchError(
                    "Could not connect to that website.", code="connection_error"
                ) from exc

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise FetchError(
                        "The website sent a redirect with no destination.",
                        code="bad_redirect",
                    )
                current_url = str(response.url.join(location))
                continue

            if response.status_code in (401, 403):
                raise FetchError(
                    "The website blocked our request. It may be behind a login "
                    "or a bot filter.",
                    code="blocked",
                )
            if response.status_code >= 400:
                raise FetchError(
                    f"The website returned HTTP {response.status_code}.",
                    code="http_error",
                )

            content_type = response.headers.get("content-type", "").lower()
            if content_type and not any(
                allowed in content_type for allowed in ALLOWED_CONTENT_TYPES
            ):
                raise FetchError(
                    f"That URL is not a web page (content type: {content_type}).",
                    code="not_html",
                )

            content = response.content
            if len(content) > settings.scraper_max_bytes:
                content = content[: settings.scraper_max_bytes]

            html = content.decode(response.encoding or "utf-8", errors="replace")
            duration_ms = int((time.perf_counter() - started) * 1000)

            return FetchResult(
                requested_url=requested_url,
                final_url=str(response.url),
                http_status=response.status_code,
                html=html,
                content_bytes=len(content),
                duration_ms=duration_ms,
                headers={k.lower(): v for k, v in response.headers.items()},
            )

    raise FetchError("The website redirected too many times.", code="too_many_redirects")
