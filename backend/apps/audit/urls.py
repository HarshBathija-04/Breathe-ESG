from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_timeline, name='audit-timeline'),
    path('<str:entity_type>/<str:entity_id>/', views.entity_audit, name='entity-audit'),
]
