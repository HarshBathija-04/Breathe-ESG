from django.urls import path
from . import views

urlpatterns = [
    path('sap/', views.ingest_sap, name='ingest-sap'),
    path('utility/', views.ingest_utility, name='ingest-utility'),
    path('travel/', views.ingest_travel, name='ingest-travel'),
    path('jobs/', views.job_list, name='job-list'),
    path('jobs/<str:job_id>/', views.job_detail, name='job-detail'),
]
