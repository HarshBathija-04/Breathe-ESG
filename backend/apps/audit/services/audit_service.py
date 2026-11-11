"""
AuditService - central service for creating audit log entries.

All audit logging goes through here to ensure consistency.
"""
from ..models import AuditLog


class AuditService:
    """
    Service for creating immutable audit log entries.

    All significant system actions are logged here for compliance.
    """

    def __init__(self, tenant):
        self.tenant = tenant

    def log(self, action, entity_type, entity_id, actor=None, before=None,
            after=None, reason='', ip_address=None, user_agent=None):
        """Create an audit log entry."""
        entry = AuditLog(
            tenant=self.tenant,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor=actor,
            actor_email=actor.email if actor else '',
            before=before or {},
            after=after or {},
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent or '',
        )
        entry.save()
        return entry

    def log_ingestion(self, ingestion_job, actor, ip_address=None, user_agent=None):
        """Log data ingestion."""
        return self.log(
            action=AuditLog.ACTION_INGEST,
            entity_type='DataIngestionJob',
            entity_id=ingestion_job.id,
            actor=actor,
            after={
                'source_type': ingestion_job.source_system.source_type,
                'file_name': ingestion_job.original_filename,
                'total_rows': ingestion_job.total_rows,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_normalization(self, activity, actor, ip_address=None, user_agent=None):
        """Log normalization of a raw record."""
        return self.log(
            action=AuditLog.ACTION_NORMALIZE,
            entity_type='NormalizedActivity',
            entity_id=activity.id,
            actor=actor,
            after={
                'scope': activity.scope,
                'category': activity.category,
                'activity_value': str(activity.activity_value),
                'co2e': str(activity.co2e),
                'source_record_id': str(activity.source_record_id),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_review_decision(self, activity, actor, decision, reason='', ip_address=None, user_agent=None):
        """Log a review decision."""
        return self.log(
            action=AuditLog.ACTION_REVIEW,
            entity_type='NormalizedActivity',
            entity_id=activity.id,
            actor=actor,
            before={'status': activity.status},
            after={'status': decision, 'reason': reason},
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_edit(self, activity, actor, before_data, after_data, reason, ip_address=None, user_agent=None):
        """Log an edit to normalized activity."""
        return self.log(
            action=AuditLog.ACTION_EDIT,
            entity_type='NormalizedActivity',
            entity_id=activity.id,
            actor=actor,
            before=before_data,
            after=after_data,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_lock(self, activity, actor, ip_address=None, user_agent=None):
        """Log record lock for audit."""
        return self.log(
            action=AuditLog.ACTION_LOCK,
            entity_type='NormalizedActivity',
            entity_id=activity.id,
            actor=actor,
            before={'status': 'APPROVED'},
            after={'status': 'LOCKED'},
            reason='Record locked for audit',
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_anomaly_flag(self, activity, anomaly_type, details, ip_address=None, user_agent=None):
        """Log anomaly flagging."""
        return self.log(
            action=AuditLog.ACTION_ANOMALY_FLAG,
            entity_type='NormalizedActivity',
            entity_id=activity.id,
            before={'status': activity.status},
            after={'status': 'FLAGGED', 'anomaly_type': anomaly_type},
            reason=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def get_entity_history(self, entity_type, entity_id):
        """Get full audit history for an entity."""
        return AuditLog.objects.filter(
            tenant=self.tenant,
            entity_type=entity_type,
            entity_id=str(entity_id),
        ).order_by('-timestamp')

    def get_tenant_activity(self, limit=100):
        """Get recent audit activity for tenant."""
        return AuditLog.objects.filter(
            tenant=self.tenant,
        ).order_by('-timestamp')[:limit]
