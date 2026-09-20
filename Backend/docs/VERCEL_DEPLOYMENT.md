# Deploying AnalyzeFlow to Vercel

Two Vercel projects from the same GitHub repo. This is the standard pattern
when a repo holds both a static site and an API, and it keeps each project's
settings simple.

| Project | Root Directory | What it serves |
|---|---|---|
| `analyzeflow-web` | `/` (repo root) | `index.html`, `report.html`, `case-study.html`, `style.css`, `js.js`, `api.js` |
| `analyzeflow-api` | `Backend` | The FastAPI app as one Python function |

---

## Before you start — apply the fixes

Nothing below works until `analyzeflow-fixes.patch` is applied. It contains
the login fix without which no signed-in feature functions at all.

```bash
cd AnalyzeFlow
git checkout -b fix/deploy-ready
git apply /path/to/analyzeflow-fixes.patch
# then copy the 5 files from analyzeflow-vercel-files/ into the repo,
# preserving their paths (vercel.json and .vercelignore at the root,
# Backend/vercel.json, Backend/.vercelignore, Backend/api/index.py)
git add -A && git commit -m "Fix auth token handling, add Vercel deployment config"
git push -u origin fix/deploy-ready
```

---

## Step 1 — Create the database

Vercel has no database. Use **Neon** (free tier, Postgres, integrates with
Vercel directly).

1. In your Vercel dashboard: **Storage → Create Database → Neon**, or sign up
   at neon.tech and create a project.
2. Copy the **pooled** connection string. Neon gives you two; the pooled one
   has `-pooler` in the hostname. **Use the pooled one** — serverless functions
   open and close connections constantly and the direct URL will hit the
   connection limit.
3. Convert it to the async driver form the app expects — change the scheme
   from `postgresql://` to `postgresql+asyncpg://`:

```
postgresql+asyncpg://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?ssl=require
```

Note `?ssl=require`, not `?sslmode=require` — asyncpg uses a different
parameter name than psycopg2, and this trips people up.

---

## Step 2 — Run the migrations

Vercel does not run migrations. Do it once from your machine, against the
**direct** (non-pooled) URL:

```bash
cd Backend
export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/neondb?ssl=require"
alembic upgrade head
python -m scripts.seed
```

Re-run `alembic upgrade head` whenever a new migration is added.

**Change the seeded admin password immediately** — `scripts/seed.py` creates
`admin@analyzeflow.dev / Admin12345`. Set `SEED_ADMIN_EMAIL` and
`SEED_ADMIN_PASSWORD` before seeding, or change it afterwards.

---

## Step 3 — Deploy the API project

1. Vercel → **Add New → Project** → import `AdamAliAli/AnalyzeFlow`.
2. Name it `analyzeflow-api`.
3. **Root Directory: `Backend`** ← this is the setting people miss.
4. Framework Preset: **Other**. Leave build/output commands empty.
5. Add these environment variables (Settings → Environment Variables):

| Variable | Value |
|---|---|
| `DATABASE_URL` | your **pooled** Neon URL, `postgresql+asyncpg://…?ssl=require` |
| `SECRET_KEY` | generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `SERVERLESS` | `true` |
| `JOB_RUNNER` | `request` |
| `SCRAPER_ALLOW_PRIVATE_HOSTS` | `false` |
| `CORS_ORIGINS` | your web URL, e.g. `https://analyzeflow-web.vercel.app` |
| `AI_PROVIDER` | `openrouter` (or `mock` to demo without spending credits) |
| `AI_API_KEY` | your OpenRouter key |
| `AI_MODEL` | the model slug you tested with |
| `AI_TIMEOUT_SECONDS` | `120` |

6. Deploy, then check `https://analyzeflow-api.vercel.app/api/v1/health`.
   You want `{"status":"ok","database":"ok",...}`. If `database` is not `ok`,
   the `DATABASE_URL` is wrong — check the scheme and `?ssl=require`.

`SERVERLESS=true` and `JOB_RUNNER=request` are the two that matter most;
[why is explained below](#why-job_runnerrequest).

---

## Step 4 — Deploy the web project

1. Vercel → **Add New → Project** → import the same repo again.
2. Name it `analyzeflow-web`.
3. **Root Directory: `/`** (leave it at the repo root).
4. Framework Preset: **Other**. No build command, output directory `.`.
5. Deploy.

Then point the front end at the API. In `api.js`, line 10:

```js
const PRODUCTION_API_BASE = "https://analyzeflow-api.vercel.app/api/v1";
```

Commit and push. Local development still uses `localhost:8000` automatically —
the file checks the hostname, so you never have to switch it back.

---

## Step 5 — Close the CORS loop

Go back to the API project and make sure `CORS_ORIGINS` contains the web
project's real URL, including `https://` and no trailing slash. Redeploy the
API after changing it — environment variable changes only take effect on a new
deployment.

If you want preview deployments to work too, add those origins as well;
Vercel gives every branch its own URL.

---

## Why `JOB_RUNNER=request`

This is the one genuine architectural problem with putting this backend on
Vercel, and it's worth understanding rather than just copying the setting.

The analysis takes 5–60 seconds — too long to hold a browser request open, so
the backend was built to return immediately and do the work in a FastAPI
background task while the front end polls for progress.

**Background tasks are not reliable on Vercel.** A serverless function is
expected to finish when it sends its response; anything still running
afterwards may be frozen or killed. Vercel's own community guidance is to
await the work instead of backgrounding it.

So the deployed build uses a third mode, `request`:

1. `POST /audits` creates the audit and a queued job, returns `201` immediately.
2. The browser fires `POST /audits/{id}/run` **without awaiting it**. That
   request runs the whole pipeline and returns when the report is done.
3. Meanwhile the browser polls `GET /audits/{id}/job`, which reads the job row
   that `/run` is updating — so the progress bar moves normally.

The work happens inside a real request, so Vercel never kills it early. The
`maxDuration: 300` in `Backend/vercel.json` gives it five minutes, which is the
Hobby plan's ceiling and far more than an analysis needs.

`/run` is idempotent and access-controlled — calling it twice returns the
existing result rather than re-running, and another user gets a 403.

Nothing changes for local development: leave `JOB_RUNNER=inline` in your `.env`
and background tasks work as before. The front end calls `/run` either way; on
an always-on backend it's a harmless no-op.

---

## Alternative worth considering

Vercel is an excellent host for the static front end and an awkward one for
this backend. If the analysis ever needs to outgrow a single request — batch
audits, scheduled re-checks, a real queue — move the API to a host that runs a
normal process: **Render**, **Railway**, or **Fly.io**, all of which have free
tiers and support `JOB_RUNNER=worker` with the standalone worker that's already
written.

The trade-off for a demo: Render's free tier sleeps after 15 minutes idle and
takes ~50 seconds to wake. If your lecturer opens the link cold, they wait.
Vercel has no sleep, so for a graded presentation Vercel is the safer choice
despite the awkwardness. That's why the `request` mode exists.

---

## Deployment checklist

- [ ] `analyzeflow-fixes.patch` applied and pushed
- [ ] Neon database created, **pooled** URL copied, scheme changed to `+asyncpg`
- [ ] `alembic upgrade head` and `python -m scripts.seed` run against it
- [ ] Seeded admin password changed
- [ ] API project deployed with Root Directory `Backend`
- [ ] `SERVERLESS=true` and `JOB_RUNNER=request` set
- [ ] `SECRET_KEY` is a fresh random value, not the placeholder
- [ ] `/api/v1/health` returns `database: ok`
- [ ] Web project deployed with Root Directory `/`
- [ ] `PRODUCTION_API_BASE` set in `api.js` and pushed
- [ ] `CORS_ORIGINS` contains the web URL, API redeployed afterwards
- [ ] Registered a test account on the live site and run one real audit

---

## Troubleshooting

**`database: error` on /health** — wrong scheme (`postgresql+asyncpg://`) or
wrong SSL parameter (`?ssl=require`, not `?sslmode=require`).

**CORS errors in the browser console** — `CORS_ORIGINS` doesn't exactly match
the web origin, or the API wasn't redeployed after the change.

**Login appears to work but everything returns 401** — the auth fix wasn't
applied. Check `api.js` reads `data.tokens.access_token`.

**Analysis never finishes** — `JOB_RUNNER` isn't `request`, so nothing ever
runs the job. Check `/api/v1/health` shows `"job_runner": "request"`.

**"too many connections"** — you used the direct Neon URL instead of the
pooled one, or `SERVERLESS` isn't `true`.

**504 FUNCTION_INVOCATION_TIMEOUT** — a target website is very slow. The
scraper's own 15s timeout normally prevents this; check `Backend/vercel.json`
still has `maxDuration: 300`.

---

Sources: [Vercel Functions limits](https://vercel.com/docs/functions/limitations) ·
[Configuring maximum duration](https://vercel.com/docs/functions/configuring-functions/duration) ·
[FastAPI background tasks on Vercel](https://community.vercel.com/t/fastapi-background-tasks-recently-broken/24189)
