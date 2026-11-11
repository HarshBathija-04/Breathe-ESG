from django.contrib import admin

from .models import ReviewDecision


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ['id', 'activity', 'decision', 'reviewed_by', 'created_at']
    list_filter = ['decision', 'tenant']
