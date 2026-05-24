# Render Deployment

## Backend (Web Service)
1. Create a new Web Service on Render
2. Connect your GitHub repo
3. Set root directory to `backend/`
4. Render will auto-detect the Dockerfile
5. Add a PostgreSQL database (Render provides this)

Required env vars:
- SECRET_KEY
- DATABASE_URL (Render provides this)
- JWT_SECRET
- CORS_ALLOWED_ORIGINS

## Frontend (Static Site)
1. Create a new Static Site on Render
2. Connect your GitHub repo
3. Set root directory to `app/`
4. Build command: `npm install && npm run build`
5. Publish directory: `dist/`

Or deploy frontend to Vercel for better performance.
