"""Turn raw HTML into a structured, JSON-serialisable PageContent.

Everything the AI provider sees about the website comes from here. Keeping
extraction separate from analysis means the AI teammate never has to touch
HTML parsing, and we can unit-test extraction without any API calls.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

MAX_TEXT_CHARS = 20_000
MAX_LIST_ITEMS = 60

_WHITESPACE = re.compile(r"\s+")

CTA_PATTERNS = (
    "buy", "shop", "order", "book", "get started", "sign up", "signup",
    "subscribe", "contact", "call", "request", "quote", "demo", "start",
    "join", "download", "reserve", "apply", "try",
)

SOCIAL_DOMAINS = (
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com", "wa.me", "whatsapp.com",
)

ANALYTICS_MARKERS = {
    "google_analytics": ("google-analytics.com", "gtag/js", "googletagmanager.com"),
    "meta_pixel": ("connect.facebook.net", "fbevents.js"),
    "hotjar": ("hotjar.com",),
    "clarity": ("clarity.ms",),
    "plausible": ("plausible.io",),
}

ECOMMERCE_MARKERS = {
    "shopify": ("cdn.shopify.com", "shopify"),
    "woocommerce": ("woocommerce", "wp-content/plugins/woocommerce"),
    "wix": ("wix.com", "wixstatic"),
    "squarespace": ("squarespace.com",),
    "webflow": ("webflow.com",),
    "wordpress": ("wp-content", "wp-includes"),
}


def _clean(text: str | None) -> str:
    return _WHITESPACE.sub(" ", (text or "")).strip()


@dataclass(slots=True)
class LinkInfo:
    text: str
    href: str
    is_internal: bool


@dataclass(slots=True)
class ImageInfo:
    src: str
    alt: str
    has_alt: bool


@dataclass(slots=True)
class FormInfo:
    action: str
    method: str
    field_count: int
    field_types: list[str]
    has_email_field: bool


@dataclass(slots=True)
class PageContent:
    """The structured view of one page. Persisted as site_snapshots.extracted."""

    url: str
    title: str
    meta_description: str
    meta_keywords: str
    canonical_url: str
    lang: str

    og_title: str
    og_description: str
    og_image: str
    has_favicon: bool
    has_viewport_meta: bool

    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)

    paragraphs: list[str] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    forms: list[FormInfo] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)

    social_links: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)

    analytics_detected: list[str] = field(default_factory=list)
    platform_detected: list[str] = field(default_factory=list)
    has_structured_data: bool = False
    structured_data_types: list[str] = field(default_factory=list)

    script_count: int = 0
    stylesheet_count: int = 0
    inline_style_count: int = 0
    word_count: int = 0
    text_content: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _detect(haystack: str, markers: dict[str, tuple[str, ...]]) -> list[str]:
    found = []
    for name, needles in markers.items():
        if any(needle in haystack for needle in needles):
            found.append(name)
    return found


def extract(html: str, base_url: str) -> PageContent:
    tree = HTMLParser(html)
    base_host = urlparse(base_url).netloc.lower()
    lowered_html = html.lower()

    def meta(name_or_prop: str, is_property: bool = False) -> str:
        key = "property" if is_property else "name"
        for node in tree.css("meta"):
            if node.attributes.get(key, "").lower() == name_or_prop:
                return _clean(node.attributes.get("content", ""))
        return ""

    # --- headings & text ---
    def texts(selector: str) -> list[str]:
        out = []
        for node in tree.css(selector):
            value = _clean(node.text())
            if value:
                out.append(value)
            if len(out) >= MAX_LIST_ITEMS:
                break
        return out

    for node in tree.css("script, style, noscript, svg"):
        node.decompose()

    body = tree.css_first("body")
    text_content = _clean(body.text()) if body else ""
    text_content = text_content[:MAX_TEXT_CHARS]

    # --- links ---
    links: list[LinkInfo] = []
    social: set[str] = set()
    for node in tree.css("a[href]")[:300]:
        href = node.attributes.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        host = urlparse(absolute).netloc.lower()
        if any(domain in host for domain in SOCIAL_DOMAINS):
            social.add(absolute)
        if len(links) < MAX_LIST_ITEMS:
            links.append(
                LinkInfo(
                    text=_clean(node.text())[:120],
                    href=absolute,
                    is_internal=(host == base_host or not host),
                )
            )

    # --- images ---
    images: list[ImageInfo] = []
    for node in tree.css("img")[:MAX_LIST_ITEMS]:
        alt = node.attributes.get("alt")
        images.append(
            ImageInfo(
                src=urljoin(base_url, node.attributes.get("src", "") or ""),
                alt=_clean(alt)[:120],
                has_alt=alt is not None and bool(_clean(alt)),
            )
        )

    # --- forms ---
    forms: list[FormInfo] = []
    for node in tree.css("form")[:20]:
        inputs = node.css("input, textarea, select")
        types = [i.attributes.get("type", i.tag) or i.tag for i in inputs]
        forms.append(
            FormInfo(
                action=urljoin(base_url, node.attributes.get("action", "") or ""),
                method=(node.attributes.get("method", "get") or "get").lower(),
                field_count=len(inputs),
                field_types=types[:20],
                has_email_field=any(t == "email" for t in types)
                or any("email" in (i.attributes.get("name", "") or "").lower() for i in inputs),
            )
        )

    # --- buttons / CTAs ---
    buttons = []
    for node in tree.css("button, a.btn, .button, [role='button'], input[type='submit']")[:40]:
        label = _clean(node.text()) or _clean(node.attributes.get("value", ""))
        if label:
            buttons.append(label[:80])

    # --- contact details ---
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", html)))[:10]
    phones = sorted(set(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", text_content)))[:10]

    # --- structured data ---
    sd_types: list[str] = []
    for node in HTMLParser(html).css('script[type="application/ld+json"]'):
        sd_types.extend(re.findall(r'"@type"\s*:\s*"([^"]+)"', node.text() or ""))

    word_count = len(text_content.split())

    return PageContent(
        url=base_url,
        title=_clean(tree.css_first("title").text() if tree.css_first("title") else ""),
        meta_description=meta("description"),
        meta_keywords=meta("keywords"),
        canonical_url=next(
            (
                _clean(n.attributes.get("href", ""))
                for n in HTMLParser(html).css('link[rel="canonical"]')
            ),
            "",
        ),
        lang=_clean(
            tree.css_first("html").attributes.get("lang", "") if tree.css_first("html") else ""
        ),
        og_title=meta("og:title", is_property=True),
        og_description=meta("og:description", is_property=True),
        og_image=meta("og:image", is_property=True),
        has_favicon=bool(HTMLParser(html).css('link[rel*="icon"]')),
        has_viewport_meta=bool(meta("viewport")),
        h1=texts("h1"),
        h2=texts("h2"),
        h3=texts("h3"),
        paragraphs=[p for p in texts("p") if len(p) > 40][:30],
        links=links,
        images=images,
        forms=forms,
        buttons=buttons,
        social_links=sorted(social)[:15],
        emails=emails,
        phones=phones,
        analytics_detected=_detect(lowered_html, ANALYTICS_MARKERS),
        platform_detected=_detect(lowered_html, ECOMMERCE_MARKERS),
        has_structured_data=bool(sd_types),
        structured_data_types=sorted(set(sd_types))[:10],
        script_count=len(HTMLParser(html).css("script")),
        stylesheet_count=len(HTMLParser(html).css('link[rel="stylesheet"]')),
        inline_style_count=len(HTMLParser(html).css("[style]")),
        word_count=word_count,
        text_content=text_content,
    )


def has_cta(buttons: list[str], links: list[LinkInfo]) -> bool:
    labels = [b.lower() for b in buttons] + [link.text.lower() for link in links]
    return any(any(pattern in label for pattern in CTA_PATTERNS) for label in labels)
