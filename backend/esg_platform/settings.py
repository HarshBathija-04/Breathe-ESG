"""
ESG Platform - Django settings.

All configuration comes from environment variables (see ../.env.example).
Deploy target: Render web service + shared Render PostgreSQL, where this app
keeps its tables in its own Postgres schema (env DB_SCHEMA).
"""
import os
import re
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Local development: read backend/.env, then the repo-root .env. Real env vars win.
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR.parent / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip().rstrip('/') for item in os.environ.get(name, default).split(',') if item.strip()]


DEBUG = env_bool('DEBUG', False)

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is false.')
    SECRET_KEY = 'dev-only-insecure-secret-key'

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
# Render injects the public hostname of the service automatically.
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.tenant',
    'apps.auth_core',
    'apps.sources',
    'apps.ingestion',
    'apps.normalization',
    'apps.emissions',
    'apps.review',
    'apps.audit',
    'apps.anomaly',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'esg_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'esg_platform.wsgi.application'

# ---------------------------------------------------------------------------
# Database: DATABASE_URL only. Tables live in their own schema (DB_SCHEMA) so
# several apps can share one Postgres database.
# ---------------------------------------------------------------------------
DB_SCHEMA = os.environ.get('DB_SCHEMA', 'breathe_esg')
if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', DB_SCHEMA):
    raise ImproperlyConfigured('DB_SCHEMA must be a lowercase Postgres identifier.')

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL:
    raise ImproperlyConfigured('DATABASE_URL must be set (see .env.example).')

DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)}
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    DATABASES['default'].setdefault('OPTIONS', {})['options'] = f'-c search_path={DB_SCHEMA}'
    # The schema itself is created on connect (apps.tenant.apps), before migrations need it.

AUTH_USER_MODEL = 'auth_core.User'

# Argon2 first; PBKDF2 kept so any existing hashes still verify (and get upgraded on login).
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# REST framework: JWT auth, consistent JSON errors, throttling.
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['apps.auth_core.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'esg_platform.errors.api_exception_handler',
    # Throttles are attached per view (esg_platform.throttles); 1 proxy hop on Render.
    'NUM_PROXIES': int(os.environ.get('NUM_PROXIES', '1')),
    'DEFAULT_THROTTLE_RATES': {
        'auth': os.environ.get('THROTTLE_AUTH', '10/min'),
        'ai': os.environ.get('THROTTLE_AI', '6/min'),
        'upload': os.environ.get('THROTTLE_UPLOAD', '20/hour'),
    },
}
if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append('rest_framework.renderers.BrowsableAPIRenderer')

# shortcut: in-process cache backs the throttles, fine for 1 gunicorn worker; use Redis/DB cache if scaled out.
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# CORS: only the deployed frontend(s). FRONTEND_URL may be comma-separated.
FRONTEND_URLS = env_list('FRONTEND_URL', 'http://localhost:5205,http://127.0.0.1:5205')
CORS_ALLOWED_ORIGINS = FRONTEND_URLS
CSRF_TRUSTED_ORIGINS = FRONTEND_URLS

# JWT
JWT_SECRET = os.environ.get('JWT_SECRET', '')
if not JWT_SECRET:
    if not DEBUG:
        raise ImproperlyConfigured('JWT_SECRET must be set when DEBUG is false.')
    JWT_SECRET = SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# Groq (AI insights). Optional: the endpoint answers 503 when unset.
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_TEXT_MODEL = os.environ.get('GROQ_TEXT_MODEL', 'openai/gpt-oss-120b')

# Ingestion
MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', '5'))
DATA_UPLOAD_MAX_MEMORY_SIZE = (MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024
INGESTION_BATCH_SIZE = int(os.environ.get('INGESTION_BATCH_SIZE', '1000'))

ANOMALY_THRESHOLDS = {
    'ELECTRICITY_SPIKE_PCT': float(os.environ.get('ELECTRICITY_SPIKE_PCT', '300')),
    'FUEL_NEGATIVE_VALUE': True,
    'DUPLICATE_WINDOW_DAYS': int(os.environ.get('DUPLICATE_WINDOW_DAYS', '30')),
}

# ---------------------------------------------------------------------------
# Security headers (SecurityMiddleware + clickjacking middleware).
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    # Render terminates TLS at its proxy and forwards X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_REDIRECT_EXEMPT = [r'^health/?$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
}
