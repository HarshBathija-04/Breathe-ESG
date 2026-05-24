# Backend Dockerfile – optimized for Render deployment
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files (whitenoise serves them in production)
# Use a dummy SECRET_KEY for collectstatic during build – the real one
# is injected at runtime via environment variables.
RUN SECRET_KEY=build-placeholder \
    DATABASE_URL=sqlite:///placeholder.db \
    python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn (Render injects $PORT at runtime; fallback to 8000)
CMD gunicorn esg_platform.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4
