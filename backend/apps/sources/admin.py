from django.contrib import admin

from .models import SourceSystem


@admin.register(SourceSystem)
class SourceSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'tenant', 'is_active']
    list_filter = ['source_type', 'is_active', 'tenant']
