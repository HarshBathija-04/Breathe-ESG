# Railway Deployment

## Backend
1. Create a new Railway project
2. Add a PostgreSQL database (Railway provides this)
3. Add the backend directory as a service
4. Set environment variables from .env.example
5. Railway will auto-detect the Dockerfile

Required env vars:
- SECRET_KEY (generate a strong random string)
- DATABASE_URL (Railway provides this automatically)
- JWT_SECRET (generate a strong random string)
- CORS_ALLOWED_ORIGINS (your Vercel frontend URL)

## Build Command
Dockerfile will be used automatically.

## Start Command
Default (from Dockerfile CMD).
