"""
Ingestion models - tracks upload jobs and stores raw, untouched source data.
RawRecord is immutable - it stores exactly what came from the source.
"""
import hashlib
import json
import uuid
from datetime import UTC

from django.db import models

from apps.auth_core.models import User
from apps.sources.models import SourceSystem
from apps.tenant.models import Tenant


class DataIngestionJob(models.Model):
    """
    Tracks a single ingestion run (file upload + processing).
    Provides visibility into pipeline state and errors.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_UPLOADED = 'UPLOADED'
    STATUS_PARSING = 'PARSING'
    STATUS_NORMALIZING = 'NORMALIZING'
    STATUS_DETECTING_ANOMALIES = 'DETECTING_ANOMALIES'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_PARTIAL = 'PARTIAL'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_UPLOADED, 'Uploaded'),
        (STATUS_PARSING, 'Parsing'),
        (STATUS_NORMALIZING, 'Normalizing'),
        (STATUS_DETECTING_ANOMALIES, 'Detecting Anomalies'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_PARTIAL, 'Partial'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='ingestion_jobs',
    )
    source_system = models.ForeignKey(
        SourceSystem,
        on_delete=models.CASCADE,
        related_name='ingestion_jobs',
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # The uploaded file
    uploaded_file = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        null=True,
        blank=True,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)

    # Pipeline metrics
    total_rows = models.IntegerField(default=0)
    parsed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    normalized_rows = models.IntegerField(default=0)
    flagged_rows = models.IntegerField(default=0)

    # Logs - structured pipeline output
    logs = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingestion_jobs',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Job {self.id} ({self.source_system.source_type}) - {self.status}"

    def add_log(self, level, message, details=None):
        """Append structured log entry."""
        from datetime import datetime
        entry = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': level,
            'message': message,
        }
        if details:
            entry['details'] = details
        self.logs.append(entry)
        self.save(update_fields=['logs'])


class RawRecord(models.Model):
    """
    Immutable raw record from source. Stores EXACTLY what came from the source.
    Never modified after creation. If data needs correction, a new ingestion job is run.

    This is the source of truth for all downstream processing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='raw_records',
    )
    ingestion_job = models.ForeignKey(
        DataIngestionJob,
        on_delete=models.CASCADE,
        related_name='raw_records',
    )
    source_system = models.ForeignKey(
        SourceSystem,
        on_delete=models.CASCADE,
        related_name='raw_records',
    )

    # The raw payload - exact data from source
    original_payload = models.JSONField()

    # Hash of original_payload for duplicate detection
    row_hash = models.CharField(max_length=64, db_index=True)

    # Source timestamp if available
    source_timestamp = models.DateTimeField(null=True, blank=True)

    # Row-level parsing state
    PARSE_SUCCESS = 'SUCCESS'
    PARSE_FAILED = 'FAILED'
    PARSE_SKIPPED = 'SKIPPED'

    PARSE_CHOICES = [
        (PARSE_SUCCESS, 'Success'),
        (PARSE_FAILED, 'Failed'),
        (PARSE_SKIPPED, 'Skipped'),
    ]

    parse_status = models.CharField(
        max_length=20,
        choices=PARSE_CHOICES,
        default=PARSE_SUCCESS,
    )
    parse_error = models.TextField(blank=True)

    # Original row number in file (for error tracing)
    row_number = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'row_hash']),
            models.Index(fields=['ingestion_job', 'parse_status']),
            models.Index(fields=['source_system', 'created_at']),
        ]

    def __str__(self):
        return f"RawRecord {self.id} (job: {self.ingestion_job_id})"

    def compute_hash(self):
        """Compute SHA256 hash of original_payload for duplicate detection."""
        payload_str = json.dumps(self.original_payload, sort_keys=True, default=str)
        self.row_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        return self.row_hash

    def save(self, *args, **kwargs):
        if not self.row_hash:
            self.compute_hash()
        super().save(*args, **kwargs)
