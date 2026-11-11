"""
Ingestion serializers.
"""
from rest_framework import serializers

from .models import DataIngestionJob


class IngestionJobSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(source='source_system.source_type', read_only=True)
    source_name = serializers.CharField(source='source_system.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='System')

    class Meta:
        model = DataIngestionJob
        fields = [
            'id', 'source_system', 'source_type', 'source_name',
            'status', 'original_filename', 'file_size_bytes',
            'total_rows', 'parsed_rows', 'failed_rows',
            'normalized_rows', 'flagged_rows',
            'logs', 'created_by', 'created_by_name',
            'created_at', 'started_at', 'completed_at',
        ]
        read_only_fields = fields
