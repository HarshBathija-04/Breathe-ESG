"""
Anomaly serializers.
"""
from rest_framework import serializers

from .models import AnomalyFlag


class AnomalyFlagSerializer(serializers.ModelSerializer):
    activity_details = serializers.SerializerMethodField()
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True, default='')

    class Meta:
        model = AnomalyFlag
        fields = ['id', 'activity', 'activity_details', 'anomaly_type', 'description',
                  'confidence', 'details', 'status', 'resolved_by', 'resolved_by_name',
                  'resolution_note', 'resolved_at', 'created_at']
        read_only_fields = ['id', 'created_at', 'resolved_by']

    def get_activity_details(self, obj):
        return {
            'id': str(obj.activity.id),
            'category': obj.activity.category,
            'sub_category': obj.activity.sub_category,
            'scope': obj.activity.scope,
            'co2e': str(obj.activity.co2e),
            'status': obj.activity.status,
            'period_start': obj.activity.period_start.isoformat(),
            'period_end': obj.activity.period_end.isoformat(),
        }


class AnomalyResolutionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        AnomalyFlag.STATUS_RESOLVED,
        AnomalyFlag.STATUS_CONFIRMED,
        AnomalyFlag.STATUS_IGNORED,
    ])
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
