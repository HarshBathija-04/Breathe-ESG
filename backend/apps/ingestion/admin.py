from django.contrib import admin
from .models import DataIngestionJob, RawRecord

@admin.register(DataIngestionJob)
class DataIngestionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_system', 'status', 'original_filename', 'total_rows', 'created_at']
    list_filter = ['status', 'source_system__source_type', 'tenant']

@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'ingestion_job', 'source_system', 'parse_status', 'row_number', 'created_at']
    list_filter = ['parse_status', 'source_system__source_type']
