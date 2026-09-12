## The one thing to read

`backend/app/services/ai/contract.py`

It defines exactly what you receive and exactly what you must return. Both are
Pydantic models, so you can hand the JSON schema straight to a structured-output
or tool-calling API and validate the response in one line.

---

## What you receive: `AnalysisInput`

```python
AnalysisInput(
    business = BusinessContext(
        business_name      = "Damascus Restaurant",
        website_url        = "https://damascus.example",
        industry           = "Restaurant",
        goal               = "Increase Sales",              # wizard step 2
        challenges         = ["Low Online Visibility", …],  # wizard step 3
        business_stage     = "Small Business",              # wizard step 4
        business_description = None,
    ),
    site = SiteEvidence(
        final_url          = "https://damascus.example/",
        http_status        = 200,
        fetch_duration_ms  = 340,
        page_title         = "Damascus Restaurant",
        meta_description   = "",
        headings_h1        = ["Welcome"],
        headings_h2        = ["Menu", "Delivery"],
        visible_text       = "…up to 20,000 chars of clean page text…",
        cta_labels         = ["Order now"],
        form_count         = 1,
        image_count        = 12,
        images_missing_alt = 9,
        social_links       = ["https://instagram.com/…"],
        detected_platform  = ["wordpress"],
        detected_analytics = [],
        rule_signals       = [ {key, label, ok, value, category, weight}, … ],
        rule_scores        = {"visual": 60, "technical": 46, "business": 33, "overall": 46},
    ),
    max_findings_per_category = 5,
    max_recommendations       = 8,
)
```

**`rule_signals` is the important part.** The backend has already run 25
deterministic checks against the live page — HTTPS, viewport meta, alt text,
security headers, CTA presence, contact routes, analytics, structured data and
so on. Each one is a measured fact with evidence attached.

Do **not** re-derive these. Your value is interpretation: what these facts mean
*for this specific business*, given their stated goal, their challenges and
their stage. A restaurant with no CTA has a different problem from an agency
with no CTA, and that difference is what a model can see and a rule engine
cannot.

---

## What you must return: `AnalysisOutput`

```python
AnalysisOutput(
    scores = Scores(overall=46, visual=60, technical=46, business=33),
    executive_summary = "3-5 sentences the owner reads first.",
    framework = FrameworkAnswers(
        client_description         = "Who the business serves.",
        user_description           = "Who actually uses the product.",
        problem_description        = "The problem being solved.",
        value_creation_description = "How value is created.",
        revenue_model_description  = "How it makes money.",
    ),
    findings = [
        Finding(
            category = "visual" | "technical" | "business",
            severity = "critical" | "high" | "medium" | "low" | "info",
            title    = "No clear call to action",
            description = "2-4 sentences: what is wrong and what it costs them.",
            evidence = "Has a clear call to action: none found",
            related_challenge = "low_conversion_rate",   # optional
        ),
    ],
    recommendations = [
        RecommendationOut(
            category = "business",
            title    = "Add one primary call to action above the fold",
            description = "…",
            priority = 1,          # 1 = do this first
            effort   = "low" | "medium" | "high",
            impact   = "low" | "medium" | "high",
            first_step = "One concrete action to take today.",
        ),
    ],
    provider = "openai",
    model    = "…",
)
```

### The three categories are the product

The whole promise is a report covering **all three**, so produce findings in
each:

- **`visual`** — design, layout, UX, accessibility, mobile experience
- **`technical`** — backend operations, performance, security, SEO mechanics
- **`business`** — positioning, value proposition, conversion, monetisation

A report with nine technical findings and nothing about the business is a
failed report, even if every finding is correct.


## Rules the backend enforces on your output

- A finding with neither `evidence` nor `description` is **dropped**.
- Recommendations are re-sorted by `priority` ascending.
- Scores must be 0–100.
- `rule_scores` is your baseline. Deviating is fine when you have a reason, but
  a score far from the baseline with no findings to justify it will look wrong
  sitting next to the evidence list the front end renders.

## Never invent facts about the site

If `SiteEvidence` does not support a claim, leave the field `None` and say
nothing. The entire product promise is that the report is grounded in the
actual page — a single fabricated detail ("your checkout flow has three steps"
when we never saw a checkout) destroys trust in all of it. Empty beats invented.

This matters most for `framework`: if the page gives no basis for inferring the
revenue model, return `None`. The front end hides null fields.

## Failure behaviour (already handled)

If your provider raises `AnalyzerError`, the pipeline retries per
`AI_MAX_RETRIES`, then falls back to the rule-based analyzer so the user still
gets a report, tagged `provider: "mock-fallback"`. Errors are recorded on the
job row. You do not need to build any of this.

