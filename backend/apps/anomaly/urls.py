from django.urls import path
from . import views

urlpatterns = [
    path('', views.anomaly_list, name='anomaly-list'),
    path('stats/', views.anomaly_stats, name='anomaly-stats'),
    path('<str:flag_id>/resolve/', views.resolve_anomaly, name='resolve-anomaly'),
]
