Base URL in development: `http://localhost:8000/api/v1`
Interactive API docs (try every endpoint in the browser): `http://localhost:8000/docs`

---
## New screens you need to build

### A. Login / Register

There is no auth UI today, and the API requires a signed-in user to submit an
audit. Two small forms:

- **Register** → `POST /auth/register` with `{full_name, email, password}`
  (password: min 8 chars, must mix letters and numbers)
- **Login** → `POST /auth/login` with `{email, password}`

Both return:

```json
{
  "user":   { "user_id": 1, "full_name": "…", "email": "…", "role": "user" },
  "tokens": { "access_token": "…", "refresh_token": "…", "expires_at": "…" }
}
```

Store `access_token` in memory (or `sessionStorage`) and send it on every
protected request:

```js
headers: { "Authorization": `Bearer ${accessToken}` }
```

When a request returns `401`, call `POST /auth/refresh` with
`{refresh_token}` to get a new pair, then retry once. Refresh tokens rotate —
the old one stops working the moment you use it, so always store the new one.

### B. Analysis progress screen

This is the important new one. Analysis takes 5–60 seconds, so the flow is:
submit → progress screen → report.

`job.stage` gives you text to show:

| `stage`               | Suggested label                  |
|-----------------------|----------------------------------|
| `queued`              | Getting ready…                   |
| `fetching_site`       | Fetching your website…           |
| `extracting_signals`  | Measuring the page…              |
| `running_analysis`    | Analysing…                       |
| `saving_report`       | Preparing your report…           |
| `done`                | Done                             |

`job.progress` is 0–100 — wire it straight to a progress bar.

### C. Report screen

The payload is designed to map onto sections you already have. See Part 4.

---

## The three calls that matter

### 1. Submit the wizard

```js
POST /api/v1/audits
Authorization: Bearer <access_token>

{
  "business_name":  "Damascus Restaurant",
  "website_url":    "damascus.example",
  "industry":       "Restaurant",
  "goal":           "Increase Sales",
  "challenges":     ["Low Online Visibility", "Low Conversion Rate"],
  "business_stage": "Small Business"
}
```

This is exactly the object `js.js` already builds at step 4 — just rename
`businessName` → `business_name`, `websiteUrl` → `website_url`, `goal` stays,
`challenges` stays, `stage` → `business_stage`.

Responds `201` immediately (the report is **not** ready yet):

```json
{
  "audit": { "audit_id": "fee66f7e-…", "status": "submitted", … },
  "job":   { "job_id": "c7550b15-…", "status": "queued", "stage": "queued", "progress": 0 },
  "poll_url": "/api/v1/audits/fee66f7e-…/job"
}
```

### 2. Poll until it's finished

```js
GET /api/v1/audits/{audit_id}/job
```

Poll every **2 seconds**. Stop when `status` is `"succeeded"` or `"failed"`.
Give up after ~90 seconds and show the retry button.

```json
{ "status": "running", "stage": "running_analysis", "progress": 55,
  "error_code": null, "error_message": null }
```

On `"failed"`, `error_message` is written for end users — show it directly.
Common ones: the site was unreachable, blocked our request, or timed out.
`POST /api/v1/audits/{audit_id}/retry` starts it again.

### 3. Fetch the report

```js
GET /api/v1/audits/{audit_id}/report
```

---

## The report payload, mapped to your existing UI

```json
{
  "audit_id": "fee66f7e-…",
  "generated_at": "2026-09-12T08:40:00Z",
  "scores":  { "overall": 78, "visual": 87, "technical": 46, "business": 100 },
  "executive_summary": "Damascus Restaurant's website scores 78/100 …",
  "framework": {
    "client_description": "…", "user_description": "…",
    "problem_description": "…", "value_creation_description": "…",
    "revenue_model_description": "…"
  },
  "site": {
    "requested_url": "https://damascus.example",
    "final_url": "https://damascus.example/",
    "http_status": 200, "fetch_duration_ms": 340,
    "page_title": "Damascus Restaurant", "status": "ok"
  },
  "findings": [
    { "category": "technical", "severity": "critical",
      "title": "Site is not served over HTTPS",
      "description": "…",
      "evidence": "Served over HTTPS: http" }
  ],
  "recommendations": [
    { "title": "Enable HTTPS with a free certificate", "description": "…",
      "category": "technical", "priority": 1,
      "effort": "low", "impact": "high",
      "first_step": "Check whether your host offers one-click SSL." }
  ],
  "signals": [
    { "key": "https", "label": "Served over HTTPS", "ok": false,
      "value": "http", "category": "technical" }
  ],
  "provider": "mock", "model": "rule-engine-v1"
}
---

## Error handling

**Every** non-2xx response has the same shape, so you can write one handler:

```json
{ "error": { "code": "validation_error", "message": "…", "details": {} } }
```

| Code | Meaning | What to show |
|---|---|---|
| `validation_error` | 422 — a field is wrong | `details.fields` lists them; for a bad lookup value, `details.allowed` has the valid options |
| `unauthenticated` | 401 — no/expired token | Try refresh once, then send to login |
| `forbidden` | 403 — not your audit | "You don't have access to that." |
| `not_found` | 404 | — |
| `conflict` | 409 — email taken | "That email is already registered." |
| `upstream_error` | 502 — site or AI failed | `message` is user-safe, show it |

---
