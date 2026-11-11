# Breathe ESG

**Turn messy SAP, utility and travel exports into reviewed, audit-locked GHG Protocol emissions data, with an AI briefing on top.**

[![CI](https://github.com/HarshBathija-04/Breathe-ESG/actions/workflows/ci.yml/badge.svg)](https://github.com/HarshBathija-04/Breathe-ESG/actions/workflows/ci.yml)

| | |
|---|---|
| **Live demo** | `https://breathe-esg.vercel.app` *(placeholder, set after the first Vercel deploy)* |
| **API** | `https://breathe-esg-api.onrender.com/health` *(placeholder, set after the first Render deploy)* |
| **Demo logins** | one-click on the sign-in page: Reviewer, Analyst, Admin |

> The API runs on Render's free plan. If it has been idle, the first request can take 30 to 60 seconds; the app shows a "waking up the server" notice while it starts.

## Features

- **Multi-source ingestion**: SAP fuel/procurement CSVs (English or German headers, semicolon delimiters, decimal commas), utility portal electricity exports, and Concur/Navan-style travel files.
- **Normalization to GHG Protocol scopes** with DEFRA 2024 and IEA emission factors, unit conversion (MWh to kWh, tonnes to kg) and flight distances derived from airport codes.
- **Anomaly detection**: negative or zero values, consumption spikes, duplicates, missing airports and distances, physically impossible values. Flagged records are held out of reportable totals until resolved.
- **Review workflow** with role-based permissions: analysts prepare, reviewers approve or reject with reasons, approved records lock for audit.
- **Immutable audit trail** of every ingest, edit, decision, lock and anomaly resolution, with before and after snapshots.
- **AI emissions briefing** (Groq, `openai/gpt-oss-120b`): an executive summary with highlights, data-quality risks and next steps, generated server-side from aggregated numbers only.
- **Multi-tenant data model**: every row is scoped to a tenant; raw source rows are stored untouched with a SHA-256 hash.

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

Upload flow: `CSV -> RawRecord (immutable, hashed) -> NormalizedActivity (scope, factor, CO2e) -> AnomalyFlag -> ReviewDecision -> LOCKED`, with an `AuditLog` entry at each step. See [`docs/MODEL.md`](docs/MODEL.md) for the data model and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the reasoning.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS 3, Radix primitives (shadcn/ui), Recharts, Sonner |
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework, PyJWT, Argon2, WhiteNoise, gunicorn |
| Data | PostgreSQL 16 (one schema per app via `search_path`) |
| AI | Groq Python SDK, `openai/gpt-oss-120b` |
| Quality | pytest + pytest-django, ruff, ESLint, Prettier, Vitest, GitHub Actions |
| Hosting | Render (API), Render Postgres, Vercel (SPA) |

## Local setup

Prerequisites: Python 3.13, Node 20+, and a PostgreSQL database (Docker works).

```bash
# 1. Configuration
cp .env.example .env          # set DATABASE_URL, optionally GROQ_API_KEY

# 2. Backend (http://localhost:5110)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate      # creates the breathe_esg schema
python manage.py seed_db      # demo tenant, users and sample data (idempotent)
python manage.py runserver 5110

# 3. Frontend (http://localhost:5205)
cd ../app
cp .env.example .env          # VITE_API_URL=http://localhost:5110/api
npm install
npm run dev
```

Or run the production-like stack with Docker: `docker compose up --build`
(frontend on http://localhost:5205, API on http://localhost:5110).

### Tests and linting

```bash
cd backend && ruff check . && pytest          # needs DATABASE_URL; creates a test database
cd app && npm run lint && npm run format:check && npm test && npm run build
```

### Demo accounts

| Role | Email | Password | Can |
|---|---|---|---|
| Reviewer | reviewer@democorp.com | reviewer123 | approve, reject, resolve anomalies |
| Analyst | analyst@democorp.com | analyst123 | upload and browse |
| Admin | admin@democorp.com | admin123 | everything, plus `/admin` |

These are public demo credentials seeded into a demo tenant; do not reuse them anywhere real.

## Environment variables

### Backend (Render)

| Variable | Required | Example / default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | `postgresql://user:pass@host:5432/db` | the shared Render Postgres |
| `DB_SCHEMA` | no | `breathe_esg` | Postgres schema for this app's tables |
| `SECRET_KEY` | prod | generated by Render | required when `DEBUG=False` |
| `JWT_SECRET` | prod | generated by Render | signs access tokens |
| `DEBUG` | no | `False` | never `True` in production |
| `FRONTEND_URL` | yes | `https://breathe-esg.vercel.app` | CORS/CSRF allow-list, comma-separated |
| `GROQ_API_KEY` | no | `your-groq-api-key` | enables the AI briefing |
| `GROQ_TEXT_MODEL` | no | `openai/gpt-oss-120b` | |
| `ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Render hostname is added automatically |
| `MAX_UPLOAD_SIZE_MB` | no | `5` | |
| `THROTTLE_AUTH` / `THROTTLE_AI` / `THROTTLE_UPLOAD` | no | `10/min` / `6/min` / `20/hour` | rate limits |
| `PYTHON_VERSION` | Render | `3.13.5` | set in `render.yaml` |

### Frontend (Vercel)

| Variable | Example | Notes |
|---|---|---|
| `VITE_API_URL` | `https://breathe-esg-api.onrender.com/api` | must end with `/api` |

### GitHub Actions

| Repository variable | Example | Used by |
|---|---|---|
| `BACKEND_URL` | `https://breathe-esg-api.onrender.com` | `keep-alive.yml` |

## Deploy

Full walkthrough: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

1. **Render API**: New -> Blueprint -> this repo. Set `DATABASE_URL` to the shared Render Postgres URL, `FRONTEND_URL` to the Vercel URL and `GROQ_API_KEY`. The build migrates and seeds automatically. The Blueprint deliberately has no `databases:` block.
2. **Vercel SPA**: import the repo with **Root Directory `app`**, set `VITE_API_URL=https://<render-service>.onrender.com/api`.
3. **Keep-alive**: add the repository variable `BACKEND_URL=https://<render-service>.onrender.com`.

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + `SELECT 1` (`{"status":"ok","db":"ok"}`, 503 if the DB is down) |
| POST | `/api/auth/login/` | email + password -> JWT (rate limited) |
| GET | `/api/auth/me/` | current user |
| POST | `/api/ingest/{sap,utility,travel}/` | upload a CSV and run the pipeline |
| GET | `/api/ingest/jobs/` | ingestion history |
| GET | `/api/dashboard/stats/` | KPIs, scope/category/monthly totals |
| POST | `/api/dashboard/insights/` | AI emissions briefing (rate limited) |
| GET | `/api/review/pending/` | review queue (paginated) |
| POST | `/api/review/{id}/action/` | approve or reject (reviewer/admin) |
| POST | `/api/activities/{id}/lock/` | lock an approved record |
| GET | `/api/anomalies/`, `/api/anomalies/stats/` | anomaly flags |
| POST | `/api/anomalies/{id}/resolve/` | resolve, confirm or ignore (reviewer/admin) |
| GET | `/api/audit/` | audit timeline |

Errors always come back as JSON: `{"error": "message", "code": "machine_code", "details": {...}}`.

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
│   ├── tests/              pytest suite
│   └── build.sh            Render build: install, collectstatic, migrate, seed
├── docs/                   model, decisions, trade-offs, sources, deployment, screenshots
├── .github/workflows/      ci.yml, keep-alive.yml
├── docker-compose.yml      local production-like stack
└── render.yaml             Render Blueprint (API only)
```

## Further reading

- [`docs/MODEL.md`](docs/MODEL.md): data model, multi-tenancy, audit design
- [`docs/DECISIONS.md`](docs/DECISIONS.md): architectural decisions
- [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md): what was deliberately not built
- [`docs/SOURCES.md`](docs/SOURCES.md): research on real-world source formats
