"""
AuditLog - immutable record of all changes.

Every significant action in the system is logged here:
- Data ingestion
- Normalization
- Review decisions (approve/reject)
- Edits to normalized data
- Status changes

The audit log is append-only. No updates, no deletes.
This is critical for compliance.
"""
from django.db import models
import uuid

from apps.tenant.models import Tenant
from apps.auth_core.models import User


class AuditLog(models.Model):
    """
    Immutable audit log entry.

    Tracks: who changed what, before/after values, when.
    """

    # Action types
    ACTION_INGEST = 'INGEST'
    ACTION_NORMALIZE = 'NORMALIZE'
    ACTION_REVIEW = 'REVIEW'
    ACTION_EDIT = 'EDIT'
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_LOCK = 'LOCK'
    ACTION_ANOMALY_FLAG = 'ANOMALY_FLAG'
    ACTION_ANOMALY_CLEAR = 'ANOMALY_CLEAR'

    ACTION_CHOICES = [
        (ACTION_INGEST, 'Data Ingested'),
        (ACTION_NORMALIZE, 'Data Normalized'),
        (ACTION_REVIEW, 'Review Decision'),
        (ACTION_EDIT, 'Data Edited'),
        (ACTION_STATUS_CHANGE, 'Status Changed'),
        (ACTION_LOCK, 'Record Locked'),
        (ACTION_ANOMALY_FLAG, 'Anomaly Flagged'),
        (ACTION_ANOMALY_CLEAR, 'Anomaly Cleared'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    # What changed
    entity_type = models.CharField(
        max_length=50,
        help_text='Type of entity affected (e.g., NormalizedActivity, DataIngestionJob)'
    )
    entity_id = models.CharField(
        max_length=36,
        help_text='UUID of the affected entity'
    )

    # Before/after snapshots
    before = models.JSONField(
        default=dict,
        blank=True,
        help_text='Snapshot of entity before change'
    )
    after = models.JSONField(
        default=dict,
        blank=True,
        help_text='Snapshot of entity after change'
    )

    # Who made the change
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions',
    )
    actor_email = models.EmailField(
        blank=True,
        help_text='Denormalized for audit safety'
    )

    # Context
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Immutable timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id} by {self.actor_email}"

    def save(self, *args, **kwargs):
        # Ensure actor_email is set
        if self.actor and not self.actor_email:
            self.actor_email = self.actor.email
        super().save(*args, **kwargs)
