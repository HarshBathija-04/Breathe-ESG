"""
Normalization serializers.
"""
from rest_framework import serializers

from .models import NormalizedActivity


class NormalizedActivitySerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(source='source_record.source_system.source_type', read_only=True)
    source_payload = serializers.JSONField(source='source_record.original_payload', read_only=True)
    source_hash = serializers.CharField(source='source_record.row_hash', read_only=True)
    ingestion_job_id = serializers.CharField(source='ingestion_job.id', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='System')

    class Meta:
        model = NormalizedActivity
        fields = [
            'id', 'tenant', 'scope', 'category', 'sub_category',
            'activity_value', 'normalized_unit', 'emission_factor',
            'emission_factor_source', 'co2e',
            'period_start', 'period_end',
            'status', 'edited_flag', 'edit_reason',
            'facility_code', 'facility_name', 'vendor', 'notes',
            'source_record', 'source_type', 'source_payload', 'source_hash',
            'ingestion_job_id',
            'created_by', 'created_by_name',
            'updated_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'co2e', 'created_at', 'updated_at',
            'created_by_name', 'source_type', 'source_payload',
            'source_hash', 'ingestion_job_id',
        ]


class ActivityEditSerializer(serializers.Serializer):
    """Serializer for editing a normalized activity."""
    activity_value = serializers.DecimalField(max_digits=20, decimal_places=6, required=False)
    emission_factor = serializers.DecimalField(max_digits=20, decimal_places=10, required=False)
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    facility_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    edit_reason = serializers.CharField(required=True, max_length=1000)
