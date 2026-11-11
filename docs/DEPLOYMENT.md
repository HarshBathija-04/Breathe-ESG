# Production Deployment Architecture Guide

This guide details the steps to deploy the **Breathe-ESG** platform using a robust, multi-cloud production architecture:
*   **Backend API**: Django REST Framework on **Render** (Web Service via Docker or Native Python)
*   **Database**: Managed PostgreSQL on **Supabase**
*   **Frontend**: React (Vite / TS / Tailwind) on **Vercel**

```mermaid
graph TD
    User([User's Browser]) -->|HTTPS| Frontend[Vercel Frontend]
    User -->|API Requests| Backend[Render Django API]
    Backend -->|PostgreSQL Protocol| DB[(Supabase Database)]
```

---

## 1. Database Setup (Supabase)

Supabase provides a powerful, managed PostgreSQL database that handles our schema and data securely.

### Step 1: Create a Database Instance
1. Go to [Supabase](https://supabase.com) and sign in.
2. Click **New Project** and select your organization.
3. Configure your project:
   - **Name**: `Breathe-ESG`
   - **Database Password**: *Generate a secure password and save it.*
   - **Region**: Choose a region close to your target users (e.g., Singapore/Sydney for APAC, North Virginia for US).
4. Click **Create New Project** and wait for provisioning to complete (~2 minutes).

### Step 2: Retrieve the Connection String
1. In your Supabase dashboard, go to **Project Settings** > **Database**.
2. Scroll to the **Connection string** section and select **URI**.
3. Select the **Transaction** mode or **Session** mode pooler URL.
   - **Example format**: `postgresql://postgres.[username]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
   - *Note: Replace `[password]` with your actual database password.*

> [!IMPORTANT]
> If your password contains special characters (like `@`, `:`, `/`, etc.), ensure they are URL-encoded in the connection string to prevent parsing errors.

---

## 2. Backend Deployment (Render)

Render hosts our Django backend Web Service. It can be deployed using the optimized `Dockerfile` (recommended) or as a native Python service.

### Option A: Docker Deployment (Recommended)
1. Sign in to [Render](https://render.com).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the Web Service:
   - **Name**: `breathe-esg-backend`
   - **Root Directory**: `backend` (CRITICAL)
   - **Runtime**: `Docker`
5. Render will automatically detect and build using `backend/Dockerfile`.

### Option B: Native Python Deployment
1. Connect your repository to a new **Web Service** on Render.
2. Configure the Web Service:
   - **Name**: `breathe-esg-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python`
   - **Build Command**: `./build.sh` (This installs packages, runs migrations, and seeds initial data)
   - **Start Command**: `gunicorn esg_platform.wsgi:application --bind 0.0.0.0:$PORT`

### Environment Variables
Under the **Environment** tab, click **Add Environment Variable** and define:

| Key | Value | Description |
|---|---|---|
| `DEBUG` | `False` | Disables debug mode in production |
| `SECRET_KEY` | *[Generate secure random string]* | Django signature key |
| `JWT_SECRET` | *[Generate secure random string]* | Secret for signing JWT authentication tokens |
| `DATABASE_URL` | *[Your Supabase connection URI]* | Connection string copied from Supabase |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app` | The production domain of your Vercel frontend |
| `ALLOWED_HOSTS` | `your-backend.onrender.com` | Your backend's Render service domain (without `https://`) |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum payload size limit for uploads |

> [!TIP]
> If using **Option A (Docker)**, run database migrations and seed data locally targeting the Supabase URL, or run them from Render's shell command line.

---

## 3. Frontend Deployment (Vercel)

Vercel provides ultra-fast CDN delivery for our React single-page application (SPA).

### Step 1: Initialize Vercel Project
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New** > **Project**.
3. Import your GitHub repository.
4. Configure the settings:
   - **Project Name**: `breathe-esg-frontend`
   - **Root Directory**: `app` (CRITICAL)
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Step 2: Environment Variables
Add the following key-value pair under **Environment Variables**:

*   **Key**: `VITE_API_URL`
*   **Value**: `https://your-backend.onrender.com/api` (The URL of your deployed Render Web Service, ending with `/api`)

### Step 3: Deploy & Verify
1. Click **Deploy**. Vercel will build the frontend, automatically applying the SPA routing logic from `app/vercel.json` (which redirects all frontend routes to `index.html`).
2. Once complete, copy the deployment URL and add it to the backend's `CORS_ALLOWED_ORIGINS` environment variable.

---

## 4. Post-Deployment Verification

After setting up all components, perform this verification checklist:

1. **API Health Check**: Visit `https://your-backend.onrender.com/health/` in your browser. It should return status code `200` with `{"status": "healthy"}`.
2. **Review Queue Verification**: Log in to the Vercel frontend. Ensure that you can load the **Review Queue** without pagination timeouts.
3. **Audit Trails**: Trigger an upload, or perform an Approve/Reject action in the **Review Queue**. Verify that the event successfully logs to the **Audit Log** timeline page.
4. **Anomalies Visualizer**: Check the **Anomalies** dashboard to ensure charts are populating via the backend anomaly detection system.
