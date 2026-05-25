"""
ReviewService - handles analyst review workflow.

Enforces:
- Only authorized users can review
- Audit trail on every decision
- Immutable decisions (no changing after fact)
"""
from apps.normalization.models import NormalizedActivity
from apps.audit.services.audit_service import AuditService
from ..models import ReviewDecision


class ReviewService:
    """
    Service for managing the review workflow.

    Separated from views to keep business logic testable
    and independent of HTTP concerns.
    """

    def __init__(self, tenant):
        self.tenant = tenant

    def get_pending_activities(self):
        """Get all activities pending review for tenant."""
        return NormalizedActivity.objects.filter(
            tenant=self.tenant,
            status__in=[
                NormalizedActivity.STATUS_PENDING_REVIEW,
                NormalizedActivity.STATUS_FLAGGED,
            ]
        ).select_related('source_record', 'source_record__source_system')

    def get_activity_history(self, activity_id):
        """Get full review history for an activity."""
        try:
            activity = NormalizedActivity.objects.get(
                id=activity_id,
                tenant=self.tenant,
            )
        except NormalizedActivity.DoesNotExist:
            return None

        decisions = ReviewDecision.objects.filter(
            activity=activity
        ).select_related('reviewed_by').order_by('-created_at')

        return {
            'activity': activity,
            'decisions': decisions,
        }

    def submit_decision(self, activity_id, user, decision, reason=''):
        """
        Submit a review decision. Returns (success, message).

        Enforces business rules:
        - User must have review permission
        - Activity must be in reviewable state
        - Decision is recorded and applied atomically
        """
        if not user.can_review:
            return False, 'User does not have review permission'

        try:
            activity = NormalizedActivity.objects.get(
                id=activity_id,
                tenant=self.tenant,
            )
        except NormalizedActivity.DoesNotExist:
            return False, 'Activity not found'

        if not activity.can_approve():
            return False, f'Activity is in {activity.status} state and cannot be reviewed'

        # Create the decision record
        review_decision = ReviewDecision(
            tenant=self.tenant,
            activity=activity,
            decision=decision,
            reason=reason,
            reviewed_by=user,
        )
        review_decision.save()

        # Apply the decision
        review_decision.apply_decision()

        # Audit log the decision
        audit = AuditService(self.tenant)
        audit.log_review_decision(activity, user, decision, reason)

        return True, f'Activity {decision.lower()}d successfully'

    def bulk_approve(self, activity_ids, user, reason=''):
        """Bulk approve multiple activities."""
        results = []
        for aid in activity_ids:
            success, message = self.submit_decision(aid, user, ReviewDecision.DECISION_APPROVE, reason)
            results.append({'id': str(aid), 'success': success, 'message': message})
        return results
