"""URL normalisation and SSRF guards - the security-critical surface."""

import pytest

from app.services.scraper.fetcher import FetchError, assert_host_is_public, normalize_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("  example.com  ", "https://example.com"),
        ("http://example.com/path", "http://example.com/path"),
        ("https://example.com/a#frag", "https://example.com/a"),
    ],
)
def test_normalize_url_accepts_human_input(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "file:///etc/passwd", "ftp://example.com", "javascript:alert(1)"],
)
def test_normalize_url_rejects_bad_schemes(raw):
    with pytest.raises(FetchError):
        normalize_url(raw)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://10.0.0.5",
        "http://192.168.1.1",
        "http://[::1]/",
    ],
)
def test_private_hosts_are_blocked(url, monkeypatch):
    """Without this, a visitor could make our server probe the host network."""
    from app.core import config

    monkeypatch.setattr(config.settings, "scraper_allow_private_hosts", False)
    with pytest.raises(FetchError) as exc:
        assert_host_is_public(url)
    assert exc.value.code in ("blocked_host", "dns_error")
