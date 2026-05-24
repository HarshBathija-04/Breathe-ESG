"""
Review models - tracks analyst decisions on normalized activities.

Every approval/rejection is recorded with who made it and why.
This feeds into the audit trail.
"""
from django.db import models
import uuid

from apps.tenant.models import Tenant
from apps.auth_core.models import User
from apps.normalization.models import NormalizedActivity


class ReviewDecision(models.Model):
    """
    A single review decision (approve/reject) on a normalized activity.
    """
    DECISION_APPROVE = 'APPROVE'
    DECISION_REJECT = 'REJECT'
    DECISION_REQUEST_INFO = 'REQUEST_INFO'

    DECISION_CHOICES = [
        (DECISION_APPROVE, 'Approve'),
        (DECISION_REJECT, 'Reject'),
        (DECISION_REQUEST_INFO, 'Request More Info'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='review_decisions',
    )
    activity = models.ForeignKey(
        NormalizedActivity,
        on_delete=models.CASCADE,
        related_name='review_decisions',
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='review_decisions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.decision} by {self.reviewed_by} on {self.activity_id}"

    def apply_decision(self):
        """Apply this decision to the activity."""
        if self.decision == self.DECISION_APPROVE:
            self.activity.status = NormalizedActivity.STATUS_APPROVED
        elif self.decision == self.DECISION_REJECT:
            self.activity.status = NormalizedActivity.STATUS_REJECTED
        self.activity.save(update_fields=['status'])
