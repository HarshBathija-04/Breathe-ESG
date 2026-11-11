# Backend image (used by docker-compose; Render uses the native Python runtime via render.yaml).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# collectstatic needs settings to import; these placeholders never reach runtime.
RUN SECRET_KEY=build JWT_SECRET=build DATABASE_URL=sqlite:///tmp/build.db \
    python manage.py collectstatic --noinput \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /app/media && chown -R app /app/media

USER app
EXPOSE 8000

CMD ["sh", "-c", "gunicorn esg_platform.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads 4 --timeout 120 --access-logfile -"]
