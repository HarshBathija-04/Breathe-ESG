"""
Audit serializers.
"""
from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True, default='System')

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'entity_type', 'entity_id', 'before', 'after',
                  'actor', 'actor_name', 'actor_email', 'reason', 'timestamp']
        read_only_fields = fields
