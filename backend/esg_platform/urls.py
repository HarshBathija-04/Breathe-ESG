"""esg_platform URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Render monitoring. No auth required."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.auth_core.urls')),
    path('api/ingest/', include('apps.ingestion.urls')),
    path('api/activities/', include('apps.normalization.urls')),
    path('api/review/', include('apps.review.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/anomalies/', include('apps.anomaly.urls')),
    path('api/dashboard/', include('apps.emissions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

