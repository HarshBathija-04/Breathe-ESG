"""
SourceSystem - represents external data sources that feed into the platform.
Each source type has its own ingestion logic and parser.
"""
from django.db import models
import uuid

from apps.tenant.models import Tenant


class SourceSystem(models.Model):
    """
    A data source configured for a tenant.
    Examples: SAP instance, Utility portal, Travel platform.
    """
    SOURCE_SAP = 'SAP'
    SOURCE_UTILITY = 'UTILITY'
    SOURCE_TRAVEL = 'TRAVEL'
    SOURCE_MANUAL = 'MANUAL'

    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP'),
        (SOURCE_UTILITY, 'Utility Portal'),
        (SOURCE_TRAVEL, 'Travel Platform'),
        (SOURCE_MANUAL, 'Manual Entry'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='source_systems',
    )
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    # Configuration JSON for source-specific settings
    config = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.source_type})"
