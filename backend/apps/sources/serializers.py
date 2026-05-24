"""
SourceSystem serializers.
"""
from rest_framework import serializers
from .models import SourceSystem


class SourceSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceSystem
        fields = ['id', 'name', 'source_type', 'config', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
