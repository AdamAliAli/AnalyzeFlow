# AnalyzeFlow Frontend Changes

All changes made to connect the static frontend to the FastAPI backend and fix existing bugs.

---

## Task 1 — Fixed four existing bugs

### 1.1 data-value on wrong element

Two cards had `data-value` on a child `<i>` instead of the card `<div>`, causing `card.dataset.value` to return `undefined`.

**index.html line 585 — "Customer Journey" goal card:**

```html
<!-- Before (broken) -->
<div class="goal-card">
  <i class="fa-solid fa-users" data-value="Customer Journey"></i>

<!-- After (fixed) -->
<div class="goal-card" data-value="Customer Journey">
  <i class="fa-solid fa-users"></i>
```

**index.html line 647 — "Low Conversion Rate" challenge card:**

```html
<!-- Before (broken) -->
<div class="challenge-card">
  <i class="fa-solid fa-chart-simple" data-value="Low Conversion Rate"></i>

<!-- After (fixed) -->
<div class="challenge-card" data-value="Low Conversion Rate">
  <i class="fa-solid fa-chart-simple"></i>
```

### 1.2 Typo in data-value

**index.html line 565:**

```html
<!-- Before -->
data-value="Increae Sales"

<!-- After -->
data-value="Increase Sales"
```

### 1.3 Step 1 validation added

**js.js** — Added a `currentFormStep === 0` branch in the `nextBtn` click handler:

- `businessName` — required, non-empty after trimming
- `websiteUrl` — required (the thing being analysed)
- `industry` — must not be the placeholder (empty value)

Uses the same `alert()` pattern as steps 2, 3, and 4.

### 1.4 Option values added

**index.html** — The `<select id="industry">` options now have explicit `value` attributes:

```html
<option value="" selected disabled>Select Industry</option>
<option value="restaurant">Restaurant</option>
<option value="ecommerce">E-commerce</option>
<option value="agency">Agency</option>
<option value="portfolio">Portfolio</option>
<option value="education">Education</option>
<option value="healthcare">Healthcare</option>
```

### 1.5 Dead code

The `DOMContentLoaded` block at js.js lines 53–83 (score ring animation) was left in place. It is guarded by an early return (`if (!score || !circle) return`) and does nothing on index.html. The logic was reused on the report page (Task 6).

---

## Task 2 — Created api.js

New file: **api.js** — loaded in index.html before js.js.

Exports `window.API` with the following methods:

| Method | Description |
|--------|-------------|
| `API.register(fullName, email, password)` | POST /auth/register |
| `API.login(email, password)` | POST /auth/login |
| `API.logout()` | Clears session tokens |
| `API.me()` | GET /auth/me |
| `API.getLookups()` | GET /lookups |
| `API.createAudit(payload)` | POST /audits |
| `API.getJob(auditId)` | GET /audits/{id}/job |
| `API.getReport(auditId)` | GET /audits/{id}/report |
| `API.retryAudit(auditId)` | POST /audits/{id}/retry |
| `API.getStats()` | GET /stats |
| `API.getCaseStudies()` | GET /case-studies |
| `API.getCaseStudy(slug)` | GET /case-studies/{slug} |
| `API.isSignedIn()` | Returns boolean |
| `API.currentUser()` | Returns cached user object or null |

Key implementation details:

- **Base URL** configurable at top of file: `const API_BASE = "http://localhost:8000/api/v1"`
- **Token storage**: `access_token` and `refresh_token` in `sessionStorage`
- **Auto-refresh on 401**: attempts one refresh via POST /auth/refresh, stores the new token pair (tokens rotate server-side), retries the original request once. If refresh fails, clears storage.
- **Error normalization**: every non-2xx response throws an `Error` with `.code`, `.message`, and `.details` properties parsed from the API's `{ error: { code, message, details } }` shape.

---

## Task 3 — Login and register screens

### Auth modals (index.html)

Added two forms inside a single modal (`id="authModalOverlay"`):

- **Login form**: email + password, with a "Create one" link to switch to register
- **Register form**: full name + email + password, with a "Sign in" link to switch back

Both reuse the existing `.modal-overlay`, `.modal`, `.modal-content`, `.close-modal`, `.input-group`, and `.next-btn` classes.

### Client-side validation (js.js)

- Full name: minimum 2 characters
- Email: basic format check via regex
- Password: minimum 8 characters, must contain both letters and numbers

Errors display inline (red text below the form), not as alerts.

### Header auth state (index.html + js.js)

Added `<a class="auth-nav-link" id="authNavLink">Sign in</a>` to the nav bar.

- **Signed out**: shows "Sign in", clicking opens login modal
- **Signed in**: shows the user's full name, clicking signs out

### Wizard gating (js.js)

Clicking "Start Analyzing" (`.Primary` button) while signed out opens the login modal instead of the audit wizard. After successful sign-in, the wizard opens automatically.

---

## Task 4 — Submit wizard to backend

**js.js** — The step-4 handler was changed from `console.log(auditData); return;` to an actual API call.

Payload keys renamed to match the API:

```js
{
  business_name:  "Damascus Restaurant",   // was businessName
  website_url:    "damascus.example",      // was websiteUrl
  industry:       "restaurant",            // the <option value>
  goal:           "Increase Sales",        // .goal-card data-value
  challenges:     ["Low Online Visibility", "Low Conversion Rate"],
  business_stage: "Small Business"         // was stage
}
```

On submit:
- Button is disabled and shows "Submitting..."
- Calls `API.createAudit(payload)`
- On success: transitions to progress screen (Task 5)
- On `validation_error` (422): shows `error.message` via alert; if `error.details.allowed` exists, appends the list of valid values

---

## Task 5 — Analysis progress screen

**js.js** — `showProgressScreen(auditId)` replaces the wizard body inside the same modal.

- Hides the wizard header and footer
- Detaches (not destroys) the audit form element so it can be restored later
- Shows a progress bar using existing `.progress` / `.fill` classes
- Polls `GET /audits/{id}/job` every 2 seconds
- Displays `job.stage` as human-readable text:

| Stage | Label |
|-------|-------|
| `queued` | Getting ready... |
| `fetching_site` | Fetching your website... |
| `extracting_signals` | Measuring the page... |
| `running_analysis` | Analysing... |
| `saving_report` | Preparing your report... |
| `done` | Done |

- **On "succeeded"**: opens `report.html?audit={id}` in a new tab, closes modal
- **On "failed"**: shows `job.error_message` with a "Try Again" button that calls `POST /audits/{id}/retry`
- **Safety timeout**: gives up after 90 seconds, shows the failure/retry UI
- **Leak prevention**: `clearPolling()` is called on success, failure, timeout, and modal close

---

## Task 6 — Report page

New file: **report.html** — opened with `?audit=<audit_id>`.

On load:
1. Reads `audit` query parameter
2. Checks sign-in state (shows prompt if not signed in)
3. Calls `GET /audits/{id}/report`
4. Renders all sections

### Sections rendered

| Section | Description |
|---------|-------------|
| **Header** | Business name (from `site.page_title`), linked URL (`site.final_url`), formatted date |
| **Score ring** | `scores.overall` as SVG circular progress ring using the dead code from Task 1.5, with `.health-score` and `.score-circle` CSS classes |
| **Sub-scores** | Three bars (Design & UX, Technical, Business) using `.metric` / `.progress` / `.fill` |
| **Executive summary** | Uses `.executive-summary` and `.summary-card` CSS classes |
| **Findings** | Tabbed by category (Design & UX / Technical / Business), each finding shows severity badge (colour-coded), title, description, and evidence |
| **Recommendations** | Ordered list with numbered circles, effort/impact badges, and first-step callout |
| **What we checked** | Collapsed `<details>` with all signals, showing checkmark/cross and measured value |
| **Business Framework** | Five-question framework cards, null fields hidden entirely |

### Severity colours

| Severity | Colour |
|----------|--------|
| critical | #dc2626 |
| high | #ea580c |
| medium | #fbbf24 |
| low | #64748b |
| info | #2563eb |

---

## Task 7 — Dynamic data from API

**js.js** — Added `loadDynamicData()` async IIFE that runs on page load.

### Stats counters
- Calls `GET /api/v1/stats`
- Updates `data-target` on `.counter` elements before the IntersectionObserver fires
- Falls back to hard-coded values (100, 50, 5) if the API call fails

### Wizard lookups
- Calls `GET /api/v1/lookups`
- Dynamically rebuilds industry `<select>` options, goal cards, challenge cards, and stage cards
- Each dynamically created card gets proper `data-value` and click handlers
- Falls back to existing hard-coded markup if the API call fails

### Case studies
- Calls `GET /api/v1/case-studies`
- Updates the case study card title, subtitle, key insight, and link href
- Falls back to existing hard-coded content if the API call fails

---

## Task 8 — Case study page

New file: **case-study.html** — linked from index.html's "View Full Analysis" button.

- Reads `?slug=` query parameter (defaults to `damascus-restaurant`)
- Calls `GET /api/v1/case-studies/{slug}`
- Renders using existing CSS classes: `.case-hero`, `.overview`, `.overview-card`, `.analysis`, `.section-title`, `.executive-summary`, `.summary-card`

### Markdown rendering
Includes a tiny inline converter that handles:
- `#`, `##`, `###` headings
- `**bold**` text
- Paragraph breaks on empty lines

No external markdown library used.

---

## CSS additions (style.css)

Added new rules at the end of style.css for:

- `.auth-nav-link` — sign-in/sign-out link in nav bar
- `.report-header` — report page header section
- `.report-scores` / `.sub-scores` — score layout
- `.findings-section` / `.findings-tabs` / `.findings-tab` / `.finding-card` / `.finding-evidence` — findings UI
- `.severity-badge` — colour-coded severity labels
- `.recommendations-section` / `.rec-card` / `.rec-number` / `.rec-body` / `.rec-badges` / `.rec-badge` / `.rec-first-step` — recommendations UI
- `.signals-section` / `.signal-row` / `.signal-label` / `.signal-value` — signals checklist
- `.framework-section` / `.framework-qa-card` — framework Q&A cards
- `.report-sign-in` — sign-in prompt for unauthenticated users

All colours match the existing palette. No existing CSS rules were modified.

---

## File summary

| File | Status | Lines |
|------|--------|-------|
| index.html | Modified | ~770 |
| js.js | Rewritten | ~706 |
| style.css | Appended | ~2170 |
| api.js | **New** | ~180 |
| report.html | **New** | ~220 |
| case-study.html | **New** | ~160 |

---

## Deployment notes

- `API_BASE` in api.js must be changed to the production backend URL before deploying
- Frontend is served as static files on GitHub Pages — no build step
- Backend CORS is configured for `http://localhost:5500`, `http://127.0.0.1:5500`, and `https://adamaliali.github.io`
- If developing on a different port, add that origin to the backend's `CORS_ORIGINS` env var
