"""esg_platform URL configuration."""
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """Liveness + DB check for Render and the keep-alive workflow. No auth."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'error', 'db': 'error'}, status=503)
    return JsonResponse({'status': 'ok', 'db': 'ok'})


urlpatterns = [
    path('health', health_check, name='health-check'),
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.auth_core.urls')),
    path('api/ingest/', include('apps.ingestion.urls')),
    path('api/activities/', include('apps.normalization.urls')),
    path('api/review/', include('apps.review.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/anomalies/', include('apps.anomaly.urls')),
    path('api/dashboard/', include('apps.emissions.urls')),
]

handler404 = 'esg_platform.errors.json_404'
handler500 = 'esg_platform.errors.json_500'
