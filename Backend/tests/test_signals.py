from app.services.scraper.extractor import extract
from app.services.scraper.fetcher import FetchResult
from app.services.scraper.signals import compute


def _fetch(url: str, headers: dict | None = None, duration: int = 100) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        http_status=200,
        html="",
        content_bytes=10_000,
        duration_ms=duration,
        headers=headers or {},
    )


def test_good_page_scores_higher_than_bad_page(good_html, bad_html):
    good = compute(
        extract(good_html, "https://x.example"), _fetch("https://x.example")
    )
    bad = compute(extract(bad_html, "http://x.example"), _fetch("http://x.example"))

    assert good.overall_score > bad.overall_score
    assert good.business_score > bad.business_score
    assert good.visual_score > bad.visual_score


def test_scores_are_percentages(good_html):
    result = compute(extract(good_html, "https://x.example"), _fetch("https://x.example"))
    for score in (
        result.visual_score,
        result.technical_score,
        result.business_score,
        result.overall_score,
    ):
        assert 0 <= score <= 100


def test_http_is_flagged_but_https_is_not(good_html):
    page = extract(good_html, "https://x.example")
    assert "https" in compute(page, _fetch("https://x.example")).passed
    assert "https" in compute(page, _fetch("http://x.example")).failed


def test_security_headers_signal(good_html):
    page = extract(good_html, "https://x.example")
    headers = {
        "strict-transport-security": "max-age=1",
        "content-security-policy": "default-src 'self'",
        "x-content-type-options": "nosniff",
    }
    assert "security_headers" in compute(page, _fetch("https://x.example", headers)).passed
    assert "security_headers" in compute(page, _fetch("https://x.example")).failed


def test_every_signal_carries_evidence(bad_html):
    result = compute(extract(bad_html, "http://x.example"), _fetch("http://x.example"))
    for signal in result.signals:
        assert signal["label"]
        assert signal["value"] != ""
        assert signal["category"] in ("visual", "technical", "business")
