import pytest

from app.services.ai.contract import (
    AnalysisInput,
    AnalysisOutput,
    BusinessContext,
    SiteEvidence,
)
from app.services.ai.mock_provider import MockAnalyzerProvider
from app.services.scraper.extractor import extract
from app.services.scraper.fetcher import FetchResult
from app.services.scraper.signals import compute


def _input(html: str, url: str) -> AnalysisInput:
    page = extract(html, url)
    fetch = FetchResult(url, url, 200, html, len(html), 120, {})
    sig = compute(page, fetch)
    return AnalysisInput(
        business=BusinessContext(
            business_name="Damascus Restaurant",
            website_url=url,
            industry="Restaurant",
            goal="Increase Sales",
            challenges=["Low Online Visibility"],
            business_stage="Small Business",
        ),
        site=SiteEvidence(
            final_url=url,
            http_status=200,
            fetch_duration_ms=120,
            rule_signals=sig.signals,
            rule_scores={
                "visual": sig.visual_score,
                "technical": sig.technical_score,
                "business": sig.business_score,
                "overall": sig.overall_score,
            },
            headings_h1=page.h1,
        ),
    )


@pytest.mark.asyncio
async def test_bad_page_produces_evidenced_findings(bad_html):
    result = await MockAnalyzerProvider().analyze(
        _input(bad_html, "http://x.example")
    )
    assert isinstance(result, AnalysisOutput)
    assert result.findings
    assert all(f.evidence for f in result.findings), "every finding must cite evidence"
    assert result.executive_summary


@pytest.mark.asyncio
async def test_recommendations_are_priority_sorted(bad_html):
    result = await MockAnalyzerProvider().analyze(_input(bad_html, "http://x.example"))
    priorities = [r.priority for r in result.recommendations]
    assert priorities == sorted(priorities)


@pytest.mark.asyncio
async def test_good_page_produces_fewer_findings(good_html, bad_html):
    good = await MockAnalyzerProvider().analyze(_input(good_html, "https://x.example"))
    bad = await MockAnalyzerProvider().analyze(_input(bad_html, "http://x.example"))
    assert len(good.findings) < len(bad.findings)
    assert good.scores.overall > bad.scores.overall


@pytest.mark.asyncio
async def test_output_is_deterministic(bad_html):
    """Same site in, same report out - otherwise the product is not defensible."""
    a = await MockAnalyzerProvider().analyze(_input(bad_html, "http://x.example"))
    b = await MockAnalyzerProvider().analyze(_input(bad_html, "http://x.example"))
    assert a.model_dump() == b.model_dump()


@pytest.mark.asyncio
async def test_mock_satisfies_the_provider_protocol():
    from app.services.ai.contract import AnalyzerProvider

    assert isinstance(MockAnalyzerProvider(), AnalyzerProvider)
