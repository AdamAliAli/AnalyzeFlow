"""Deterministic, rule-based measurements computed from PageContent.

Why this exists even though an AI does the analysis:

  1. The AI needs *facts*, not raw HTML. Feeding it "has_viewport_meta: false"
     produces a grounded finding; feeding it 200KB of markup produces guesses.
  2. Anything measurable should be measured, not inferred. A missing meta
     description is a fact - it must never depend on model temperature.
  3. If the AI provider is down, these signals alone still produce a usable
     report (see mock_provider.py). The product degrades, it doesn't break.

Each signal carries `ok`, a human label, and the evidence behind it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse

from app.services.scraper.extractor import PageContent, has_cta
from app.services.scraper.fetcher import FetchResult

SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
)


@dataclass(slots=True)
class Signal:
    key: str
    label: str
    ok: bool
    value: str
    category: str  # visual | technical | business
    weight: int = 1  # how much a failure costs the sub-score

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SiteSignals:
    """Persisted as site_snapshots.signals and passed to the AI provider."""

    signals: list[dict] = field(default_factory=list)
    visual_score: int = 0
    technical_score: int = 0
    business_score: int = 0
    overall_score: int = 0
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _score(signals: list[Signal], category: str) -> int:
    relevant = [s for s in signals if s.category == category]
    if not relevant:
        return 100
    total_weight = sum(s.weight for s in relevant)
    earned = sum(s.weight for s in relevant if s.ok)
    return round(100 * earned / total_weight)


def compute(content: PageContent, fetch: FetchResult) -> SiteSignals:
    headers = fetch.headers
    parsed = urlparse(fetch.final_url)
    signals: list[Signal] = []

    def add(key, label, ok, value, category, weight=1):
        signals.append(Signal(key, label, bool(ok), str(value), category, weight))

    # ---------------- TECHNICAL ----------------
    add("https", "Served over HTTPS", parsed.scheme == "https",
        parsed.scheme, "technical", 3)
    add("response_time", "Responds in under 2 seconds",
        fetch.duration_ms < 2000, f"{fetch.duration_ms} ms", "technical", 2)
    add("page_weight", "HTML payload under 500 KB",
        fetch.content_bytes < 500_000,
        f"{fetch.content_bytes // 1024} KB", "technical", 1)
    add("compression", "Response is compressed",
        "content-encoding" in headers, headers.get("content-encoding", "none"),
        "technical", 1)
    add("caching", "Sends cache-control headers",
        "cache-control" in headers, headers.get("cache-control", "none"),
        "technical", 1)

    present_security = [h for h in SECURITY_HEADERS if h in headers]
    add("security_headers", "Sets common security headers",
        len(present_security) >= 3,
        f"{len(present_security)}/{len(SECURITY_HEADERS)}: "
        f"{', '.join(present_security) or 'none'}",
        "technical", 2)

    add("script_count", "Loads fewer than 25 scripts",
        content.script_count < 25, content.script_count, "technical", 1)
    add("analytics", "Has analytics installed",
        bool(content.analytics_detected),
        ", ".join(content.analytics_detected) or "none detected", "technical", 2)

    # ---------------- VISUAL / UX ----------------
    add("viewport_meta", "Declares a mobile viewport",
        content.has_viewport_meta,
        "present" if content.has_viewport_meta else "missing", "visual", 3)
    add("title", "Page has a title", bool(content.title),
        content.title or "missing", "visual", 2)
    add("single_h1", "Has exactly one H1 heading",
        len(content.h1) == 1, f"{len(content.h1)} found", "visual", 2)
    add("heading_structure", "Uses sub-headings to break up the page",
        len(content.h2) >= 2, f"{len(content.h2)} H2 headings", "visual", 1)

    total_images = len(content.images)
    missing_alt = sum(1 for i in content.images if not i.has_alt)
    add("image_alt", "Images have alt text for accessibility",
        total_images == 0 or missing_alt == 0,
        f"{missing_alt} of {total_images} images missing alt", "visual", 2)

    add("favicon", "Has a favicon", content.has_favicon,
        "present" if content.has_favicon else "missing", "visual", 1)
    add("lang_attribute", "Declares a page language", bool(content.lang),
        content.lang or "missing", "visual", 1)
    add("inline_styles", "Avoids heavy inline styling",
        content.inline_style_count < 30,
        f"{content.inline_style_count} elements with inline style", "visual", 1)
    add("content_depth", "Has enough copy to explain the offer",
        content.word_count >= 300, f"{content.word_count} words", "visual", 2)

    # ---------------- BUSINESS ----------------
    add("meta_description", "Has a meta description for search results",
        bool(content.meta_description),
        content.meta_description[:120] or "missing", "business", 2)
    add("social_preview", "Has Open Graph tags for link previews",
        bool(content.og_title and content.og_description),
        "present" if content.og_title else "missing", "business", 1)
    add("call_to_action", "Has a clear call to action",
        has_cta(content.buttons, content.links),
        ", ".join(content.buttons[:3]) or "none found", "business", 3)
    add("contact_route", "Offers a way to get in touch",
        bool(content.emails or content.phones or content.forms),
        f"{len(content.forms)} forms, {len(content.emails)} emails, "
        f"{len(content.phones)} phones", "business", 3)
    add("lead_capture", "Captures leads with a form",
        any(f.has_email_field for f in content.forms),
        f"{sum(1 for f in content.forms if f.has_email_field)} email forms",
        "business", 2)
    add("social_presence", "Links to social profiles",
        bool(content.social_links), f"{len(content.social_links)} links",
        "business", 1)
    add("structured_data", "Publishes structured data for rich results",
        content.has_structured_data,
        ", ".join(content.structured_data_types) or "none", "business", 1)
    add("value_proposition", "States a value proposition above the fold",
        bool(content.h1 and len(content.h1[0]) > 15),
        content.h1[0][:120] if content.h1 else "no H1 found", "business", 3)

    visual = _score(signals, "visual")
    technical = _score(signals, "technical")
    business = _score(signals, "business")

    return SiteSignals(
        signals=[s.as_dict() for s in signals],
        visual_score=visual,
        technical_score=technical,
        business_score=business,
        overall_score=round((visual + technical + business) / 3),
        passed=[s.key for s in signals if s.ok],
        failed=[s.key for s in signals if not s.ok],
    )
