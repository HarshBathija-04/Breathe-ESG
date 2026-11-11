from django.urls import path

from . import views

urlpatterns = [
    path('<uuid:activity_id>/', views.activity_detail, name='activity-detail'),
    path('<uuid:activity_id>/edit/', views.activity_edit, name='activity-edit'),
    path('<uuid:activity_id>/lock/', views.activity_lock, name='activity-lock'),
]
