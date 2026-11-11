"""
Seed the database with a demo tenant, users, source systems and realistic data.

Idempotent: users/sources use get_or_create, and the sample CSVs are only
ingested when the demo tenant has no ingestion jobs yet. The sample files go
through the real pipeline (parse -> normalize -> anomaly detection), then a
deterministic slice is approved, rejected and locked so the demo shows every
workflow state.

Usage: python manage.py seed_db
"""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.audit.services.audit_service import AuditService
from apps.ingestion.models import DataIngestionJob
from apps.ingestion.services.sap_parser import SAPParserService
from apps.ingestion.services.travel_parser import TravelParserService
from apps.ingestion.services.utility_parser import UtilityParserService
from apps.ingestion.views import _run_pipeline
from apps.normalization.models import NormalizedActivity
from apps.review.models import ReviewDecision
from apps.review.services.review_service import ReviewService
from apps.sources.models import SourceSystem
from apps.tenant.models import Tenant

User = get_user_model()

SAMPLE_DIR = Path(settings.BASE_DIR) / 'sample_data'

DEMO_USERS = [
    ('admin@democorp.com', 'admin123', 'Avery', 'Morgan', User.ROLE_ADMIN, True),
    ('analyst@democorp.com', 'analyst123', 'Sarah', 'Chen', User.ROLE_ANALYST, False),
    ('reviewer@democorp.com', 'reviewer123', 'Daniel', 'Okafor', User.ROLE_REVIEWER, False),
]

SAMPLE_FILES = [
    (SourceSystem.SOURCE_SAP, 'SAP Production', 'sap_fuel.csv', SAPParserService),
    (SourceSystem.SOURCE_SAP, 'SAP Production', 'sap_fuel_german.csv', SAPParserService),
    (SourceSystem.SOURCE_UTILITY, 'Utility Portal East', 'utility_electricity.csv', UtilityParserService),
    (SourceSystem.SOURCE_TRAVEL, 'Concur Travel', 'travel_data.csv', TravelParserService),
]


class Command(BaseCommand):
    help = 'Seed database with demo tenant, users and sample emissions data (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument('--noinput', action='store_true', help='Accepted for compatibility; never prompts.')
        parser.add_argument('--skip-data', action='store_true', help='Only create tenant, users and sources.')

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug='demo-corp',
            defaults={
                'name': 'Northwind Manufacturing',
                'contact_email': 'admin@democorp.com',
                'contact_name': 'Avery Morgan',
            },
        )

        users = {}
        for email, password, first, last, role, is_staff in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'first_name': first, 'last_name': last, 'tenant': tenant,
                          'role': role, 'is_staff': is_staff},
            )
            if created:
                user.set_password(password)
                user.save()
            users[role] = user
        self.stdout.write(f'Tenant "{tenant.name}" with {len(users)} demo users ready.')

        sources = {}
        for source_type, name in [
            (SourceSystem.SOURCE_SAP, 'SAP Production'),
            (SourceSystem.SOURCE_UTILITY, 'Utility Portal East'),
            (SourceSystem.SOURCE_UTILITY, 'Utility Portal West'),
            (SourceSystem.SOURCE_TRAVEL, 'Concur Travel'),
        ]:
            sources[name], _ = SourceSystem.objects.get_or_create(
                tenant=tenant, name=name, defaults={'source_type': source_type, 'is_active': True},
            )

        if options['skip_data']:
            return
        if DataIngestionJob.objects.filter(tenant=tenant).exists():
            self.stdout.write('Sample data already ingested; skipping.')
            return

        # All-or-nothing, so a failed seed is retried on the next deploy instead of half-skipped.
        with transaction.atomic():
            self._ingest_samples(tenant, users, sources)
        self.stdout.write(self.style.SUCCESS('Seeding complete.'))

    def _ingest_samples(self, tenant, users, sources):
        analyst = users[User.ROLE_ANALYST]
        audit = AuditService(tenant)
        for _source_type, source_name, filename, parser in SAMPLE_FILES:
            path = SAMPLE_DIR / filename
            with path.open('rb') as fh:
                job = DataIngestionJob.objects.create(
                    tenant=tenant,
                    source_system=sources[source_name],
                    status=DataIngestionJob.STATUS_UPLOADED,
                    uploaded_file=File(fh, name=filename),
                    original_filename=filename,
                    file_size_bytes=path.stat().st_size,
                    created_by=analyst,
                )
            job = _run_pipeline(job, parser)
            audit.log_ingestion(job, analyst)
            self.stdout.write(f'  {filename}: {job.normalized_rows} normalized, {job.flagged_rows} flags ({job.status})')

        self._review_sample(tenant, users[User.ROLE_REVIEWER])

    def _review_sample(self, tenant, reviewer):
        """Approve ~40%, reject ~8% and lock half of the approved pending records."""
        review = ReviewService(tenant)
        pending = list(
            NormalizedActivity.objects.filter(tenant=tenant, status=NormalizedActivity.STATUS_PENDING_REVIEW)
            .order_by('period_start', 'id').values_list('id', flat=True)
        )
        approved = []
        for i, activity_id in enumerate(pending):
            if i % 12 == 5:
                review.submit_decision(activity_id, reviewer, ReviewDecision.DECISION_REJECT,
                                       'Duplicate of an invoice already reported.')
            elif i % 5 in (0, 2):
                ok, _ = review.submit_decision(activity_id, reviewer, ReviewDecision.DECISION_APPROVE,
                                               'Matches source invoice.')
                if ok:
                    approved.append(activity_id)

        audit = AuditService(tenant)
        for activity in NormalizedActivity.objects.filter(id__in=approved[::2]):
            if activity.lock_for_audit():
                audit.log_lock(activity, reviewer)
        self.stdout.write(f'  Reviewed sample: {len(approved)} approved, {len(approved[::2])} locked.')
