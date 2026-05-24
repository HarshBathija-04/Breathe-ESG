"""
Review serializers.
"""
from rest_framework import serializers
from .models import ReviewDecision
from apps.normalization.models import NormalizedActivity


class ReviewDecisionSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)

    class Meta:
        model = ReviewDecision
        fields = ['id', 'activity', 'decision', 'reason', 'reviewed_by', 
                  'reviewed_by_name', 'created_at']
        read_only_fields = ['id', 'created_at', 'reviewed_by']


class ReviewActionSerializer(serializers.Serializer):
    """Serializer for review actions."""
    decision = serializers.ChoiceField(choices=ReviewDecision.DECISION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
