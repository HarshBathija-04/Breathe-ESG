# Breathe ESG

**Turn messy SAP, utility and travel exports into reviewed, audit-locked GHG Protocol emissions data, with an AI briefing on top.**

[![CI](https://github.com/HarshBathija-04/Breathe-ESG/actions/workflows/ci.yml/badge.svg)](https://github.com/HarshBathija-04/Breathe-ESG/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB)
![Django 5.2](https://img.shields.io/badge/django-5.2_LTS-0C4B33)
![React 19](https://img.shields.io/badge/react-19-149ECA)

| | |
|---|---|
| **Live demo** | `https://breathe-esg.vercel.app` *(placeholder until the first Vercel deploy)* |
| **API health** | `https://breathe-esg-api.onrender.com/health` *(placeholder until the first Render deploy)* |
| **Try it** | one-click Reviewer, Analyst and Admin logins on the sign-in page, no sign-up |

> The API runs on Render's free plan. After 15 idle minutes the first request can take 30 to 60 seconds; the app shows a "Waking up the server" notice while it starts.

## Features

- **Three messy sources, one schema**: SAP fuel CSVs (English or German headers, `;` delimiters, decimal commas), utility portal electricity exports and Concur/Navan-style travel files.
- **GHG Protocol normalization**: Scope 1/2/3 with DEFRA 2024 and IEA factors, unit conversion (MWh to kWh, tonnes to kg) and flight distances derived from airport codes.
- **Anomaly detection**: negative or zero values, consumption spikes, duplicate rows, missing airports, impossible distances. Flagged records stay out of reportable totals until a reviewer resolves them.
- **Review workflow**: analysts prepare, reviewers approve or reject with a reason, approved records lock for audit.
- **Append-only audit trail** of every ingest, edit, decision, lock and anomaly resolution, with before and after snapshots.
- **AI emissions briefing** (Groq, `openai/gpt-oss-120b`): headline, highlights, risks and next steps, generated server-side from aggregated numbers only.

## Screenshots

| Landing | Dashboard |
|---|---|
| ![Landing page](docs/screenshots/landing-desktop.png) | ![Dashboard](docs/screenshots/dashboard-desktop.png) |
| **AI briefing** | **Review queue** |
| ![AI briefing](docs/screenshots/ai-briefing-desktop.png) | ![Review queue](docs/screenshots/review-desktop.png) |
| **Ingestion** | **Mobile (375 px)** |
| ![Ingestion](docs/screenshots/ingestion-desktop.png) | ![Mobile dashboard](docs/screenshots/dashboard-mobile.png) |

More in [`docs/screenshots/`](docs/screenshots/).

## Architecture

```mermaid
flowchart LR
  subgraph Vercel
    SPA[React 19 + Vite SPA]
  end
  subgraph Render
    API[Django 5.2 + DRF<br/>gunicorn]
    PIPE[Ingestion pipeline<br/>parse, normalize, detect]
  end
  DB[(Shared Render Postgres<br/>schema breathe_esg)]
  GROQ[Groq API<br/>gpt-oss-120b]
  GHA[GitHub Actions<br/>keep-alive]

  SPA -- JWT, JSON --> API
  API --> PIPE
  API -- search_path --> DB
  PIPE --> DB
  API -- aggregated stats only --> GROQ
  GHA -- GET /health every 10 min --> API
```

Each upload flows `CSV -> RawRecord (immutable, hashed) -> NormalizedActivity (scope, factor, CO2e) -> AnomalyFlag -> ReviewDecision -> LOCKED`, writing an `AuditLog` entry at each step. The data model is in [`docs/MODEL.md`](docs/MODEL.md) and the reasoning in [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Engineering highlights

- **Schema-per-app on a shared database.** Several portfolio apps share one Render Postgres. This one keeps every table in its own schema: `DB_SCHEMA` is validated as a plain identifier, set as the connection `search_path`, and created on connect so `migrate` works on an empty database.
- **Transaction-safe review decisions.** Each approve/reject runs in one transaction with a row lock (`select_for_update`), so two reviewers clicking at once cannot both decide the same record, and the decision, status change and audit entry are saved together or not at all. The demo seed is all-or-nothing too.
- **Raw data is never overwritten.** Source rows are stored untouched with a SHA-256 hash of the payload. Duplicate detection runs on that hash, and every CO2e figure links back to the exact line it came from.
- **Unreviewed data stays out of the numbers.** Dashboard totals and the AI context exclude flagged and rejected records, and the flagged volume is reported separately as a data-quality risk.
- **One parser pipeline, three formats.** A shared base parser sniffs delimiters, handles BOMs, latin-1 and German decimal commas, and validates rows; each source only declares its column map and rules.
- **The LLM never sees raw rows.** The backend sends Groq an aggregated, numbers-only context, asks for JSON, retries once in plain mode, and coerces whatever comes back into a fixed shape. The endpoint is rate-limited and degrades to a clear 503 when no key is set.
- **Built for a free tier.** The SPA times slow requests and shows a wake-up notice, and a GitHub Actions cron pings `/health` (which also runs `SELECT 1`) every 10 minutes.
- **Hardened by default.** Argon2 password hashing, per-endpoint throttles on login, uploads and AI, upload size and type checks, HSTS and security headers, tenant-scoped queries everywhere, and one JSON error shape for every failure.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS 3, Radix primitives (shadcn/ui), Recharts, Sonner |
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework, PyJWT, Argon2, WhiteNoise, gunicorn |
| Data | PostgreSQL 16, one schema per app via `search_path` |
| AI | Groq Python SDK, `openai/gpt-oss-120b` |
| Quality | pytest + pytest-django, ruff, ESLint, Prettier, Vitest, GitHub Actions |
| Hosting | Render (API), Render Postgres, Vercel (SPA) |

## Quick start

Prerequisites: Python 3.13, Node 20+ and PostgreSQL. No local Postgres? Start one with Docker:

```bash
docker run -d --name breathe-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=portfolio -p 5433:5432 postgres:16-alpine
```

```bash
# 1. Configuration (defaults match the Docker command above)
cp .env.example .env          # optionally add GROQ_API_KEY for the AI briefing

# 2. Backend on http://localhost:5110
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate      # creates the breathe_esg schema
python manage.py seed_db      # demo tenant, users and sample data (idempotent)
python manage.py runserver 5110

# 3. Frontend on http://localhost:5205 (new terminal)
cd app
cp .env.example .env          # VITE_API_URL=http://localhost:5110/api
npm install
npm run dev
```

Open http://localhost:5205 and pick a demo role. For a production-like stack instead, run `docker compose up --build` (frontend on :5205, API on :5110).

### Checks

```bash
cd backend && ruff check . && pytest      # uses DATABASE_URL; pytest creates its own test database
cd app && npm run lint && npm run format:check && npm test && npm run build
```

### Demo accounts

| Role | Email | Password | Can |
|---|---|---|---|
| Reviewer | reviewer@democorp.com | reviewer123 | approve, reject, lock, resolve anomalies |
| Analyst | analyst@democorp.com | analyst123 | upload and browse |
| Admin | admin@democorp.com | admin123 | everything, plus Django `/admin` |

These are public demo credentials for a seeded demo tenant. Do not reuse them anywhere real.

## Environment variables

**Backend** (`.env` locally, Render dashboard in production)

| Variable | Required | Default / example | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | `postgresql://postgres:postgres@localhost:5433/portfolio` | the shared Postgres |
| `DB_SCHEMA` | no | `breathe_esg` | schema that holds this app's tables |
| `SECRET_KEY` | in prod | generated by Render | required when `DEBUG=False` |
| `JWT_SECRET` | in prod | generated by Render | signs access tokens |
| `DEBUG` | no | `False` | `True` only for local development |
| `FRONTEND_URL` | yes in prod | `http://localhost:5205` | CORS/CSRF allow-list, comma-separated |
| `GROQ_API_KEY` | no | unset | enables the AI briefing |
| `GROQ_TEXT_MODEL` | no | `openai/gpt-oss-120b` | |
| `ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Render's hostname is added automatically |
| `MAX_UPLOAD_SIZE_MB` | no | `5` | |
| `THROTTLE_AUTH` / `THROTTLE_AI` / `THROTTLE_UPLOAD` | no | `10/min` / `6/min` / `20/hour` | rate limits |
| `JWT_EXPIRATION_HOURS` | no | `24` | |

**Frontend** (`app/.env` locally, Vercel in production)

| Variable | Example | Notes |
|---|---|---|
| `VITE_API_URL` | `https://breathe-esg-api.onrender.com/api` | must end with `/api` |

**GitHub Actions**

| Repository variable | Example | Used by |
|---|---|---|
| `BACKEND_URL` | `https://breathe-esg-api.onrender.com` | `keep-alive.yml` |

## Deploy

Full walkthrough: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

1. **API on Render.** New > Blueprint > this repo ([`render.yaml`](render.yaml)). Set `DATABASE_URL` to the shared Render Postgres internal URL; `DB_SCHEMA=breathe_esg` is preset so the app keeps to its own schema. Also set `FRONTEND_URL` (your Vercel URL) and `GROQ_API_KEY`. `SECRET_KEY` and `JWT_SECRET` are generated. The build installs, migrates and seeds. The Blueprint deliberately has no `databases:` block because the database is shared.
2. **SPA on Vercel.** Import the repo with **Root Directory `app`** and set `VITE_API_URL=https://<render-service>.onrender.com/api`. `vercel.json` handles SPA rewrites, security headers and asset caching.
3. **Keep-alive.** In GitHub, Settings > Secrets and variables > Actions > Variables, add `BACKEND_URL=https://<render-service>.onrender.com`. The workflow skips itself until it is set.

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + `SELECT 1` (`{"status":"ok","db":"ok"}`, 503 if the DB is down) |
| POST | `/api/auth/login/` | email + password -> JWT (rate limited) |
| POST | `/api/ingest/{sap,utility,travel}/` | upload a CSV and run the pipeline (rate limited) |
| GET | `/api/ingest/jobs/` | ingestion history |
| GET | `/api/dashboard/stats/` | KPIs, scope/category/monthly totals |
| POST | `/api/dashboard/insights/` | AI emissions briefing (rate limited) |
| GET | `/api/review/pending/` | review queue (paginated) |
| POST | `/api/review/{id}/action/` | approve or reject (reviewer/admin) |
| POST | `/api/activities/{id}/lock/` | lock an approved record (reviewer/admin) |
| GET | `/api/anomalies/`, `/api/anomalies/stats/` | anomaly flags and counts |
| POST | `/api/anomalies/{id}/resolve/` | resolve, confirm or ignore (reviewer/admin) |
| GET | `/api/audit/` | audit timeline |

Every error is JSON: `{"error": "message", "code": "machine_code", "details": {...}}`.

## Project structure

```
.
├── app/                    React SPA (Vercel root directory)
│   ├── public/             favicon, OG image, downloadable sample CSVs
│   └── src/
│       ├── api/            typed API clients (axios, JWT, cold-start tracking)
│       ├── components/     app shell, shared states, AI briefing, ui/ primitives
│       ├── context/        auth session
│       ├── lib/            formatting, HTTP helpers, theme constants (+ tests)
│       └── pages/          landing, login, dashboard, ingestion, review, anomalies, audit
├── backend/                Django API (Render root directory)
│   ├── apps/               tenant, auth_core, sources, ingestion, normalization,
│   │                       emissions (dashboard + AI), review, audit, anomaly
│   ├── esg_platform/       settings, URLs, error handler, throttles
│   ├── sample_data/        CSVs used by the seed command
│   ├── tests/              pytest suite (parsing logic + API flows)
│   └── build.sh            Render build: install, collectstatic, migrate, seed
├── docs/                   model, decisions, trade-offs, sources, deployment, screenshots
├── .github/workflows/      ci.yml (lint, test, build), keep-alive.yml
├── docker-compose.yml      local production-like stack
└── render.yaml             Render Blueprint (API only)
```

## Further reading

- [`docs/MODEL.md`](docs/MODEL.md): data model, multi-tenancy, audit design
- [`docs/DECISIONS.md`](docs/DECISIONS.md): architectural decisions
- [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md): what was deliberately left out
- [`docs/SOURCES.md`](docs/SOURCES.md): research on real-world source formats
