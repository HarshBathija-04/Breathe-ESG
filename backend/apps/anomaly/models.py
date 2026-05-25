"""
AnomalyFlag - records suspicious data patterns detected by the anomaly service.

Anomalies are informational flags - they don't block processing but
alert analysts to inspect the data.

Status lifecycle:
  OPEN → RESOLVED (analyst confirmed it's fine or fixed it)
  OPEN → CONFIRMED (analyst confirmed it's a real issue)
"""
from django.db import models
import uuid
from decimal import Decimal

from apps.tenant.models import Tenant
from apps.auth_core.models import User
from apps.normalization.models import NormalizedActivity


class AnomalyFlag(models.Model):
    """
    A detected anomaly on a normalized activity.
    """

    # Anomaly types
    TYPE_ELECTRICITY_SPIKE = 'ELECTRICITY_SPIKE'
    TYPE_NEGATIVE_VALUE = 'NEGATIVE_VALUE'
    TYPE_ZERO_VALUE = 'ZERO_VALUE'
    TYPE_MISSING_AIRPORT = 'MISSING_AIRPORT'
    TYPE_DUPLICATE = 'DUPLICATE'
    TYPE_INVALID_UNIT = 'INVALID_UNIT'
    TYPE_OUT_OF_RANGE = 'OUT_OF_RANGE'
    TYPE_MISSING_DISTANCE = 'MISSING_DISTANCE'
    TYPE_DATE_INCONSISTENCY = 'DATE_INCONSISTENCY'

    TYPE_CHOICES = [
        (TYPE_ELECTRICITY_SPIKE, 'Electricity Spike'),
        (TYPE_NEGATIVE_VALUE, 'Negative Value'),
        (TYPE_ZERO_VALUE, 'Zero Value'),
        (TYPE_MISSING_AIRPORT, 'Missing Airport Code'),
        (TYPE_DUPLICATE, 'Duplicate Record'),
        (TYPE_INVALID_UNIT, 'Invalid Unit'),
        (TYPE_OUT_OF_RANGE, 'Value Out of Range'),
        (TYPE_MISSING_DISTANCE, 'Missing Distance'),
        (TYPE_DATE_INCONSISTENCY, 'Date Inconsistency'),
    ]

    STATUS_OPEN = 'OPEN'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_IGNORED = 'IGNORED'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_IGNORED, 'Ignored'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='anomaly_flags',
    )
    activity = models.ForeignKey(
        NormalizedActivity,
        on_delete=models.CASCADE,
        related_name='anomaly_flags',
    )
    anomaly_type = models.CharField(max_length=30, choices=TYPE_CHOICES)

    # Human-readable description
    description = models.TextField()

    # Confidence score 0-1
    confidence = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.5'))

    # Details for debugging
    details = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)

    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_anomalies',
    )
    resolution_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'anomaly_type']),
            models.Index(fields=['activity', 'status']),
        ]

    def __str__(self):
        return f"{self.anomaly_type} on {self.activity_id} ({self.status})"


# Need Decimal import
from decimal import Decimal
