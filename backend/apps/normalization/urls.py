from django.urls import path
from . import views

urlpatterns = [
    path('<str:activity_id>/', views.activity_detail, name='activity-detail'),
    path('<str:activity_id>/edit/', views.activity_edit, name='activity-edit'),
    path('<str:activity_id>/lock/', views.activity_lock, name='activity-lock'),
]
