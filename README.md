# Breathe ESG Ingestion Platform

A production-style prototype for ingesting, normalizing, and reviewing ESG (Environmental, Social, and Governance) emissions data from multiple enterprise systems.

## Architecture

### Backend
- **Django 5** with Django REST Framework
- **PostgreSQL** for data persistence
- **JWT Authentication** via PyJWT
- **9 Django apps** with service layer pattern:
  - `tenant` - Multi-tenant isolation
  - `auth_core` - Custom user model with roles
  - `sources` - Source system configuration
  - `ingestion` - File upload and parsing pipeline
  - `normalization` - Canonical activity conversion
  - `emissions` - Dashboard aggregation APIs
  - `review` - Analyst approval workflow
  - `audit` - Immutable audit trail
  - `anomaly` - Data quality detection

### Frontend
- **React 19** with TypeScript
- **Vite** build tooling
- **Tailwind CSS** for styling
- **shadcn/ui** component library
- **Recharts** for data visualization

### Data Sources
1. **SAP** - Fuel and procurement CSV exports (German/English headers)
2. **Utility** - Electricity portal CSV exports
3. **Travel** - Concur/Navan-style travel CSV exports

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.12+ (for local backend development)

### Docker Setup

```bash
# Clone and start all services
docker-compose up -d

# Run migrations and seed data
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_db

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000/api
# Admin: http://localhost:8000/admin
```

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database credentials
python manage.py migrate
python manage.py seed_db
python manage.py runserver
```

**Frontend:**
```bash
cd app
npm install
cp .env.example .env
# Edit .env with your API URL
npm run dev
```

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@democorp.com | admin123 |
| Analyst | analyst@democorp.com | analyst123 |
| Reviewer | reviewer@democorp.com | reviewer123 |

## Project Structure

```
├── backend/                 # Django backend
│   ├── apps/               # Django applications
│   │   ├── tenant/         # Multi-tenant core
│   │   ├── auth_core/      # Authentication
│   │   ├── sources/        # Source systems
│   │   ├── ingestion/      # Upload & parsing
│   │   ├── normalization/  # Data normalization
│   │   ├── emissions/      # Dashboard APIs
│   │   ├── review/         # Review workflow
│   │   ├── audit/          # Audit trail
│   │   └── anomaly/        # Anomaly detection
│   ├── esg_platform/       # Django project config
│   ├── requirements.txt
│   └── Dockerfile
├── app/                     # React frontend
│   ├── src/
│   │   ├── api/            # API clients
│   │   ├── components/     # React components
│   │   ├── context/        # Auth context
│   │   └── pages/          # Page components
│   ├── Dockerfile
│   └── package.json
├── data/                    # Sample CSV files
│   ├── sap_fuel.csv
│   ├── sap_fuel_german.csv
│   ├── utility_electricity.csv
│   └── travel_data.csv
├── docs/                    # Documentation
│   ├── MODEL.md            # Data model design
│   ├── DECISIONS.md        # Architectural decisions
│   ├── TRADEOFFS.md        # Deliberate omissions
│   └── SOURCES.md          # Source research
└── docker-compose.yml
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login with email/password
- `GET /api/auth/me/` - Get current user

### Ingestion
- `POST /api/ingest/sap/` - Upload SAP CSV
- `POST /api/ingest/utility/` - Upload utility CSV
- `POST /api/ingest/travel/` - Upload travel CSV
- `GET /api/ingest/jobs/` - List ingestion jobs

### Review
- `GET /api/review/pending/` - Get pending activities
- `POST /api/review/{id}/action/` - Approve/reject activity
- `POST /api/review/bulk-approve/` - Bulk approve

### Dashboard
- `GET /api/dashboard/stats/` - Dashboard statistics

### Audit
- `GET /api/audit/` - Audit timeline
- `GET /api/audit/{type}/{id}/` - Entity history

### Anomalies
- `GET /api/anomalies/` - List anomaly flags
- `POST /api/anomalies/{id}/resolve/` - Resolve flag

## Documentation

- **MODEL.md** - Detailed data model with multi-tenancy, audit design, and scope handling
- **DECISIONS.md** - Every architectural decision and its rationale
- **TRADEOFFS.md** - Three deliberately skipped features and why
- **SOURCES.md** - Research on real-world data formats for each source

## Ingestion Pipeline

1. **Upload** - File uploaded via API
2. **Parse** - Source-specific parser reads CSV, handles headers, validates rows
3. **Normalize** - Raw records converted to canonical activities with emission factors
4. **Anomaly Detection** - Flags suspicious patterns (spikes, negatives, duplicates)
5. **Review** - Analysts approve/reject activities
6. **Lock** - Approved records locked for audit

## Key Features

- **Multi-tenant architecture** - Data isolation at the application layer
- **Immutable audit trail** - Append-only logging with before/after snapshots
- **Anomaly detection** - Automatic flagging of suspicious data patterns
- **German header support** - SAP exports with German column names
- **Unit normalization** - Automatic conversion (MWh→kWh, ton→kg)
- **Distance derivation** - Flight distances derived from airport codes
- **Role-based access** - Admin, Analyst, Reviewer, Viewer roles
- **Review workflow** - Approve, reject, with reason tracking

## Deployment (Supabase + Render + Vercel)

This project is configured for deployment with:
- **Database**: [Supabase](https://supabase.com) (managed PostgreSQL)
- **Backend**: [Render](https://render.com) (Django + Gunicorn)
- **Frontend**: [Vercel](https://vercel.com) (Vite React SPA)

### Step 1: Supabase Database

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string → URI**
3. Copy the connection string (format: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`)
4. Save it — you'll need it for the Render backend setup
5. No manual schema setup is needed; Django migrations handle everything

### Step 2: Render Backend

**Option A: Blueprint (recommended)**
1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repo — Render will auto-detect `render.yaml`
4. Set the required env vars marked `sync: false`:
   - `DATABASE_URL` → paste your Supabase connection string
   - `ALLOWED_HOSTS` → `your-service-name.onrender.com`
   - `CORS_ALLOWED_ORIGINS` → `https://your-app.vercel.app`
   - `CSRF_TRUSTED_ORIGINS` → `https://your-app.vercel.app`
5. Deploy — the build script will auto-run migrations and seed demo data

**Option B: Manual Setup**
1. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn esg_platform.wsgi:application --bind 0.0.0.0:$PORT --workers 4`
4. Set environment variables:

| Variable | Value |
|----------|-------|
| `DEBUG` | `False` |
| `SECRET_KEY` | *(generate a 64-char random string)* |
| `DATABASE_URL` | *(Supabase connection string)* |
| `JWT_SECRET` | *(generate a 64-char random string)* |
| `ALLOWED_HOSTS` | `your-service-name.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.vercel.app` |
| `PYTHON_VERSION` | `3.12.0` |
| `MAX_UPLOAD_SIZE_MB` | `50` |

5. Set **Health Check Path**: `/health/`
6. Deploy

### Step 3: Vercel Frontend

1. Go to [Vercel Dashboard](https://vercel.app) → **New Project**
2. Import your GitHub repo
3. Configure:
   - **Root Directory**: `app`
   - **Framework Preset**: Vite *(auto-detected)*
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Set environment variable:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-service-name.onrender.com/api` |

5. Deploy

### Post-Deploy Verification

1. ✅ Visit your Vercel URL — the login page should load
2. ✅ Login with `admin@democorp.com` / `admin123`
3. ✅ Navigate the dashboard — data should load from the API
4. ✅ Check `https://your-backend.onrender.com/health/` returns `{"status": "ok"}`

### Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors in browser console | Verify `CORS_ALLOWED_ORIGINS` on Render matches your exact Vercel URL (with `https://`) |
| 500 errors on backend | Check Render logs; likely `DATABASE_URL` is incorrect or Supabase project is paused |
| Login fails silently | Confirm `VITE_API_URL` on Vercel points to the correct Render URL with `/api` suffix |
| Static files 404 | Ensure `whitenoise` is in middleware and `collectstatic` ran in the build step |

## License

This is a technical assignment prototype for Breathe ESG.

