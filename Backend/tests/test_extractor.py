from app.services.scraper.extractor import extract, has_cta


def test_extracts_core_metadata(good_html):
    page = extract(good_html, "https://damascus.example")
    assert page.title.startswith("Damascus Restaurant")
    assert page.meta_description
    assert page.lang == "en"
    assert page.has_viewport_meta is True
    assert page.has_favicon is True
    assert len(page.h1) == 1
    assert len(page.h2) == 2
    assert page.og_title == "Damascus Restaurant"


def test_detects_contact_and_conversion_surface(good_html):
    page = extract(good_html, "https://damascus.example")
    assert "orders@damascus.example" in page.emails
    assert page.phones
    assert len(page.forms) == 1
    assert page.forms[0].has_email_field is True
    assert any("instagram.com" in link for link in page.social_links)
    assert has_cta(page.buttons, page.links) is True


def test_detects_analytics_and_structured_data(good_html):
    page = extract(good_html, "https://damascus.example")
    assert "google_analytics" in page.analytics_detected
    assert page.has_structured_data is True
    assert "Restaurant" in page.structured_data_types


def test_bad_page_reports_its_gaps(bad_html):
    page = extract(bad_html, "http://damascus.example")
    assert page.has_viewport_meta is False
    assert page.meta_description == ""
    assert len(page.h1) == 2  # two H1s is a real defect we must catch
    assert sum(1 for i in page.images if not i.has_alt) == 2
    assert page.analytics_detected == []
    assert has_cta(page.buttons, page.links) is False
