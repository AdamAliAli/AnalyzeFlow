### 1. `users` gained auth columns

**Added:** `password_hash`, `role`, `is_active`, `email_verified_at`,
`last_login_at`.

The original table had no way to authenticate anyone. `role` is
`user` | `admin`; the report's Section 10 ERD already mentioned a `Role`
attribute, so this aligns the SQL with the documented design.

### 2. `audit_submissions.primary_goal` → `goal_id` FK

The column was `VARCHAR(30)` free text, but the wizard offers exactly four
fixed choices. Free text means no referential integrity, no way to list valid
options, and typos becoming permanent data.

**New table:** `goals`, seeded with the four wizard options, same shape as the
existing `challenges` and `business_stages` lookups.

### 3. `business_profiles.industry` → `industry_id` FK (+ `industry_other`)

Same reasoning — the wizard dropdown has six fixed values.
`industry_other` keeps a free-text fallback so an unrecognised industry is
stored rather than rejected.

**New table:** `industries`.

### 4. `audit_submissions` gained `target_url` and `public_id`

- `target_url` freezes the URL that was actually analysed. A business profile's
  URL can change later; a report has to stay reproducible against what was
  measured.
- `public_id` (UUID) is what the API and front end use. Sequential integer IDs
  in URLs let anyone enumerate other people's audits.

### 5. `audit_submissions.status` gained two values

Was `draft | submitted | analyzed`. Now also `analyzing` and `failed` — an
async pipeline needs to represent "in progress" and "this didn't work".

### 6. The five framework columns changed meaning

`client_description`, `user_description`, `problem_description`,
`value_creation_description`, `revenue_model_description` are still on
`audit_submissions`, but they are now **AI-inferred outputs, not user inputs**,
and are nullable.

This resolves a genuine contradiction in the original design: the schema had
these as user-supplied, but the four-step wizard never collects them. Under the
current product direction — infer everything from the website URL — the AI
derives them from the fetched page and writes them back.

### 7. `recommendations` gained structure

**Added:** `category` (`visual`/`technical`/`business`), `effort`, `impact`,
`first_step`, `report_id`, `report_finding_id`.

It now hangs off `reports` rather than directly off `audit_submissions`, since
a report is the thing that gets generated. `category` is what lets the front
end split recommendations into the three promised sections.

### 8. `case_studies` reconciles the two conflicting versions

The SQL draft had `title, industry, summary, content`. The report's Section 10
ERD had `ClientType, UserType, Goal, ValueProposition, KeyInsight`. **Both are
now present** — the first set for listing, the second for the worked framework
example. Also added `slug` for clean URLs.

---

## New tables

| Table | Purpose |
|---|---|
| `goals` | Wizard step 2 choices (was a free-text column) |
| `industries` | Wizard step 1 choices (was a free-text column) |
| `site_snapshots` | What we fetched: HTTP status, timing, extracted content, computed signals, page text. One per audit. Makes reports reproducible and auditable |
| `analysis_jobs` | The async queue: status, stage, progress, attempts, errors |
| `reports` | One per audit: four scores, executive summary, provider/model provenance, raw AI output |
| `report_findings` | Individual issues, grouped by category and severity, each with evidence |
| `refresh_tokens` | Issued refresh tokens, so logout and rotation can revoke them |

---

## Design decisions worth defending in the viva

**Why lookup tables instead of CHECK constraints or enums?**
Adding an industry becomes an admin API call instead of a database migration,
and `GET /lookups` lets the front end stop hard-coding the same lists.

**Why store `site_snapshots` rather than re-fetching?**
A report must be explainable months later. Without the snapshot, "why did it
say that?" is unanswerable — the site has changed since.

**Why a job table instead of Celery or Redis?**
No budget for extra infrastructure, and every team member has to be able to run
the whole stack with one command. `SELECT … FOR UPDATE SKIP LOCKED` gives safe
concurrency if a second worker is ever added.

**Why `public_id` UUIDs alongside integer primary keys?**
Integers stay efficient for joins and foreign keys; UUIDs prevent enumeration
in public URLs. Standard practice, and cheap to add now versus painful later.

**Why keep `raw_output` JSONB on `reports`?**
The AI provider will change. Keeping its raw response means a report generated
under one model can still be inspected after switching to another.
