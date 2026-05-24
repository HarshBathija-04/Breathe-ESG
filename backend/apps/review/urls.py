from django.urls import path
from . import views

urlpatterns = [
    path('pending/', views.pending_review, name='pending-review'),
    path('<str:activity_id>/action/', views.review_action, name='review-action'),
    path('bulk-approve/', views.bulk_approve, name='bulk-approve'),
    path('<str:activity_id>/history/', views.activity_history, name='activity-history'),
]
