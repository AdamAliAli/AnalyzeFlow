"""Rule-based analyzer. The default, and the fallback.

Two jobs:
  * The backend is fully testable and demoable today, with no API key, no
    network and no waiting on the AI teammate.
  * If the real provider fails at runtime, the pipeline degrades to this
    instead of handing the user an error page.

Output is deterministic: the same website always yields the same report,
which is what makes the end-to-end tests meaningful.
"""

from __future__ import annotations

from app.models.enums import EffortLevel, FindingCategory, ImpactLevel, Severity
from app.services.ai.contract import (
    AnalysisInput,
    AnalysisOutput,
    Finding,
    FrameworkAnswers,
    RecommendationOut,
    Scores,
)

# Maps a failed rule signal to the finding + recommendation it justifies.
_PLAYBOOK: dict[str, dict] = {
    "https": {
        "severity": Severity.CRITICAL,
        "title": "Site is not served over HTTPS",
        "description": (
            "The site loads over plain HTTP. Browsers mark it 'Not secure', "
            "which visibly damages trust, and search engines rank it lower. "
            "Any form on the page transmits data unencrypted."
        ),
        "rec_title": "Enable HTTPS with a free certificate",
        "rec_description": (
            "Install a Let's Encrypt certificate and redirect all HTTP "
            "traffic to HTTPS. Most hosts provide this at no cost."
        ),
        "first_step": "Check whether your host offers one-click SSL in its control panel.",
        "priority": 1,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "viewport_meta": {
        "severity": Severity.CRITICAL,
        "title": "Page is not mobile-responsive",
        "description": (
            "No mobile viewport tag was found, so phones render the desktop "
            "layout zoomed out. More than half of web traffic is mobile, so "
            "this affects the majority of visitors."
        ),
        "rec_title": "Add a mobile viewport and test on a phone",
        "rec_description": (
            "Add the standard viewport meta tag to the page head, then audit "
            "the layout at 375px width and fix anything that overflows."
        ),
        "first_step": (
            'Add <meta name="viewport" content="width=device-width, '
            'initial-scale=1"> to the page head.'
        ),
        "priority": 1,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "call_to_action": {
        "severity": Severity.CRITICAL,
        "title": "No clear call to action",
        "description": (
            "No button or link tells the visitor what to do next. Visitors "
            "who are interested have no obvious path to becoming customers, "
            "so interest does not convert into revenue."
        ),
        "rec_title": "Add one primary call to action above the fold",
        "rec_description": (
            "Decide the single most valuable action a visitor can take, then "
            "make it the most prominent element on the page and repeat it at "
            "the bottom."
        ),
        "first_step": "Write the one sentence you want every visitor to act on.",
        "priority": 1,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "contact_route": {
        "severity": Severity.CRITICAL,
        "title": "No way for a customer to make contact",
        "description": (
            "No contact form, email address or phone number was found. A "
            "visitor ready to buy has no route to you, so demand is lost "
            "silently."
        ),
        "rec_title": "Publish a contact route on every page",
        "rec_description": (
            "Add a short contact form, plus an email address and phone "
            "number in the footer where visitors expect them."
        ),
        "first_step": "Put your email address in the footer today.",
        "priority": 1,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "value_proposition": {
        "severity": Severity.HIGH,
        "title": "Value proposition is not stated clearly",
        "description": (
            "The main heading does not explain what the business offers or "
            "who it is for. Visitors decide within seconds whether a page is "
            "relevant to them, and an unclear headline loses that decision."
        ),
        "rec_title": "Rewrite the headline to name the customer and the outcome",
        "rec_description": (
            "State who you help and what changes for them. Specific beats "
            "clever: a reader should understand the offer without scrolling."
        ),
        "first_step": "Complete the sentence: 'We help ___ to ___.'",
        "priority": 2,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "meta_description": {
        "severity": Severity.MEDIUM,
        "title": "Missing meta description",
        "description": (
            "Search engines have no summary to show under the page title, so "
            "they invent one from page text. That reduces click-through from "
            "search results even when rankings are fine."
        ),
        "rec_title": "Write a 150-character meta description",
        "rec_description": (
            "Summarise the offer and include the phrase customers actually "
            "search for."
        ),
        "first_step": "Add a description meta tag to the page head.",
        "priority": 3,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.MEDIUM,
    },
    "analytics": {
        "severity": Severity.HIGH,
        "title": "No analytics installed",
        "description": (
            "Nothing is measuring visitor behaviour, so there is no way to "
            "know which pages work, where visitors leave, or whether any "
            "change helps. Every decision after this is guesswork."
        ),
        "rec_title": "Install analytics before changing anything else",
        "rec_description": (
            "Add a privacy-friendly analytics tool and record a baseline for "
            "at least two weeks so later changes can be judged against it."
        ),
        "first_step": "Create an analytics property and paste the snippet into the page head.",
        "priority": 2,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.HIGH,
    },
    "image_alt": {
        "severity": Severity.MEDIUM,
        "title": "Images are missing alt text",
        "description": (
            "Images without alt text are invisible to screen readers and to "
            "image search. This is both an accessibility gap and a missed "
            "source of traffic."
        ),
        "rec_title": "Describe every meaningful image",
        "rec_description": (
            "Add alt text describing each image's content or purpose. "
            "Decorative images should have an empty alt attribute."
        ),
        "first_step": "Start with images in the hero and product sections.",
        "priority": 3,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.MEDIUM,
    },
    "security_headers": {
        "severity": Severity.MEDIUM,
        "title": "Security headers are missing",
        "description": (
            "Common protective headers are absent, leaving the site more "
            "exposed to clickjacking and content-injection attacks than it "
            "needs to be."
        ),
        "rec_title": "Add baseline security headers",
        "rec_description": (
            "Set X-Content-Type-Options, X-Frame-Options, Referrer-Policy "
            "and a Content-Security-Policy at the web server or CDN."
        ),
        "first_step": "Add X-Content-Type-Options: nosniff - it is the safest to start with.",
        "priority": 4,
        "effort": EffortLevel.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
    },
    "response_time": {
        "severity": Severity.HIGH,
        "title": "Slow server response",
        "description": (
            "The page took over two seconds to respond. Visitors abandon slow "
            "pages, and speed is a direct ranking factor."
        ),
        "rec_title": "Reduce time to first byte",
        "rec_description": (
            "Put a CDN in front of the site, enable caching, and check for "
            "slow database queries or unoptimised hosting."
        ),
        "first_step": "Run the URL through a page-speed tool and note the largest contributor.",
        "priority": 2,
        "effort": EffortLevel.MEDIUM,
        "impact": ImpactLevel.HIGH,
    },
    "lead_capture": {
        "severity": Severity.MEDIUM,
        "title": "No lead capture",
        "description": (
            "There is no form collecting an email address, so visitors who "
            "are not ready to buy today leave without a way to be reached "
            "again."
        ),
        "rec_title": "Add an email capture with a reason to subscribe",
        "rec_description": (
            "Offer something concrete in exchange for an email address, and "
            "keep the form to a single field."
        ),
        "first_step": "Decide what you would send subscribers in the first month.",
        "priority": 3,
        "effort": EffortLevel.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
    },
    "content_depth": {
        "severity": Severity.MEDIUM,
        "title": "Not enough content to explain the offer",
        "description": (
            "The page has very little copy. Visitors cannot evaluate an offer "
            "they cannot read about, and search engines have little to index."
        ),
        "rec_title": "Expand the page to answer buyer questions",
        "rec_description": (
            "Add sections covering what you do, who it is for, what it costs, "
            "and what happens next."
        ),
        "first_step": "List the five questions customers ask most, and answer them on the page.",
        "priority": 3,
        "effort": EffortLevel.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
    },
    "single_h1": {
        "severity": Severity.LOW,
        "title": "Heading structure is unclear",
        "description": (
            "The page does not have exactly one H1. Screen readers and search "
            "engines both use the H1 to identify the page's subject."
        ),
        "rec_title": "Use one H1 per page",
        "rec_description": "Make the main headline the only H1 and demote the rest to H2.",
        "first_step": "Audit the page outline and fix the heading levels.",
        "priority": 4,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.LOW,
    },
    "structured_data": {
        "severity": Severity.LOW,
        "title": "No structured data",
        "description": (
            "The page publishes no schema markup, so search engines cannot "
            "show rich results such as ratings, hours or prices."
        ),
        "rec_title": "Add schema.org markup for your business type",
        "rec_description": (
            "Publish JSON-LD describing the organisation, and the product or "
            "local business where relevant."
        ),
        "first_step": "Add an Organization JSON-LD block with name, URL and logo.",
        "priority": 5,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.LOW,
    },
    "social_preview": {
        "severity": Severity.LOW,
        "title": "Links share badly on social media",
        "description": (
            "Open Graph tags are missing, so shared links render without a "
            "title, description or image."
        ),
        "rec_title": "Add Open Graph tags",
        "rec_description": "Set og:title, og:description and a 1200x630 og:image.",
        "first_step": "Paste the URL into a social debugger to see what is shown today.",
        "priority": 5,
        "effort": EffortLevel.LOW,
        "impact": ImpactLevel.LOW,
    },
}

_CATEGORY_BY_SIGNAL = {
    key: FindingCategory(entry_category)
    for key, entry_category in {
        "https": "technical",
        "response_time": "technical",
        "security_headers": "technical",
        "analytics": "technical",
        "viewport_meta": "visual",
        "image_alt": "visual",
        "single_h1": "visual",
        "content_depth": "visual",
        "call_to_action": "business",
        "contact_route": "business",
        "value_proposition": "business",
        "meta_description": "business",
        "lead_capture": "business",
        "structured_data": "business",
        "social_preview": "business",
    }.items()
}


class MockAnalyzerProvider:
    """Deterministic analyzer driven entirely by the rule signals."""

    name = "mock"

    async def analyze(self, payload: AnalysisInput) -> AnalysisOutput:
        site = payload.site
        by_key = {s["key"]: s for s in site.rule_signals}

        findings: list[Finding] = []
        recommendations: list[RecommendationOut] = []
        per_category: dict[FindingCategory, int] = {c: 0 for c in FindingCategory}

        for key, entry in _PLAYBOOK.items():
            signal = by_key.get(key)
            if signal is None or signal.get("ok"):
                continue

            category = _CATEGORY_BY_SIGNAL.get(key, FindingCategory.TECHNICAL)
            if per_category[category] >= payload.max_findings_per_category:
                continue
            per_category[category] += 1

            findings.append(
                Finding(
                    category=category,
                    severity=entry["severity"],
                    title=entry["title"],
                    description=entry["description"],
                    evidence=f"{signal['label']}: {signal['value']}",
                    related_challenge=None,
                )
            )
            recommendations.append(
                RecommendationOut(
                    category=category,
                    title=entry["rec_title"],
                    description=entry["rec_description"],
                    priority=entry["priority"],
                    effort=entry["effort"],
                    impact=entry["impact"],
                    first_step=entry["first_step"],
                )
            )

        recommendations = recommendations[: payload.max_recommendations]
        scores = site.rule_scores or {}

        return AnalysisOutput(
            scores=Scores(
                overall=scores.get("overall", 0),
                visual=scores.get("visual", 0),
                technical=scores.get("technical", 0),
                business=scores.get("business", 0),
            ),
            executive_summary=self._summary(payload, len(findings), scores),
            framework=self._framework(payload),
            findings=findings,
            recommendations=recommendations,
            provider=self.name,
            model="rule-engine-v1",
        )

    @staticmethod
    def _summary(payload: AnalysisInput, finding_count: int, scores: dict) -> str:
        business = payload.business
        overall = scores.get("overall", 0)
        verdict = (
            "in good shape" if overall >= 80
            else "workable but leaking opportunities" if overall >= 55
            else "holding the business back"
        )
        challenge_text = (
            f" You told us the main problems are {', '.join(business.challenges).lower()}."
            if business.challenges
            else ""
        )
        return (
            f"{business.business_name}'s website scores {overall}/100 overall and is "
            f"currently {verdict}. We ran {len(payload.site.rule_signals)} automated "
            f"checks against {payload.site.final_url} and found {finding_count} issues "
            f"worth acting on, grouped into design and usability, technical "
            f"operations, and business positioning.{challenge_text} The "
            f"recommendations below are ordered so the highest-impact, "
            f"lowest-effort fixes come first."
        )

    @staticmethod
    def _framework(payload: AnalysisInput) -> FrameworkAnswers:
        """Best-effort inference without a language model.

        Deliberately conservative: only states what the page literally shows.
        A real provider replaces this with genuine inference.
        """
        site = payload.site
        business = payload.business
        headline = site.headings_h1[0] if site.headings_h1 else None

        return FrameworkAnswers(
            client_description=(
                f"{business.business_name} operates in the "
                f"{business.industry or 'unspecified'} sector at the "
                f"{business.business_stage.lower()} stage."
            ),
            user_description=None,
            problem_description=None,
            value_creation_description=(
                f"The site's headline positions the offer as: {headline}"
                if headline
                else None
            ),
            revenue_model_description=(
                f"Detected platform signals suggest {', '.join(site.detected_platform)}."
                if site.detected_platform
                else None
            ),
        )
