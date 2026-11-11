from django.contrib import admin

from .models import NormalizedActivity


@admin.register(NormalizedActivity)
class NormalizedActivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'scope', 'category', 'sub_category', 'co2e', 'status', 'period_end']
    list_filter = ['status', 'scope', 'category', 'tenant']
    search_fields = ['facility_code', 'vendor']
