from django.contrib import admin
from .models import AnomalyFlag

@admin.register(AnomalyFlag)
class AnomalyFlagAdmin(admin.ModelAdmin):
    list_display = ['id', 'anomaly_type', 'activity', 'confidence', 'status', 'created_at']
    list_filter = ['status', 'anomaly_type', 'tenant']
