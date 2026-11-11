"""
Ingestion API views.

Handles file uploads for all three source types:
- SAP fuel/procurement CSV
- Utility electricity CSV
- Travel platform CSV

Orchestrates the pipeline: upload -> parse -> normalize -> detect anomalies.
"""
import logging
import os
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.anomaly.services.anomaly_service import AnomalyService
from apps.audit.services.audit_service import AuditService
from apps.normalization.services.normalization_service import NormalizationService
from apps.sources.models import SourceSystem
from esg_platform.throttles import UploadThrottle

from .models import DataIngestionJob
from .serializers import IngestionJobSerializer
from .services.sap_parser import SAPParserService
from .services.travel_parser import TravelParserService
from .services.utility_parser import UtilityParserService

logger = logging.getLogger(__name__)


def _run_pipeline(job, parser_service_class):
    """Parse -> normalize -> detect anomalies, recording counts and final status on the job."""
    job.status = DataIngestionJob.STATUS_PARSING
    job.save(update_fields=['status'])

    parser = parser_service_class(job, job.source_system)
    parsed, failed, _errors = parser.parse_file(job.uploaded_file)

    job.parsed_rows = parsed
    job.failed_rows = failed
    job.total_rows = parsed + failed
    job.save(update_fields=['parsed_rows', 'failed_rows', 'total_rows'])

    if parsed > 0:
        normalized, _norm_failed = NormalizationService(job).normalize_all()  # also saves normalized_rows
        if normalized > 0:
            job.flagged_rows = AnomalyService(job.tenant).detect_all()
            job.save(update_fields=['flagged_rows'])

    if job.normalized_rows == 0:
        job.status = DataIngestionJob.STATUS_FAILED
    elif failed > 0:
        job.status = DataIngestionJob.STATUS_PARTIAL
    else:
        job.status = DataIngestionJob.STATUS_COMPLETED
    job.save(update_fields=['status'])
    return job


def _upload_view(source_type, parser_class):
    """
    POST multipart/form-data with `file` (CSV) and optional `source_system_id`
    (UUID of an existing source of this type; otherwise an "Auto-<type>" source is used).
    """
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    @throttle_classes([UploadThrottle])
    def view(request):
        return _handle_upload(request, source_type, parser_class)
    return view


ingest_sap = _upload_view(SourceSystem.SOURCE_SAP, SAPParserService)
ingest_utility = _upload_view(SourceSystem.SOURCE_UTILITY, UtilityParserService)
ingest_travel = _upload_view(SourceSystem.SOURCE_TRAVEL, TravelParserService)


def _handle_upload(request, source_type, parser_class):
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'No file provided'}, status=400)

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_obj.size > max_size:
        return Response(
            {'error': f'File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB'},
            status=400
        )

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ['.csv', '.txt']:
        return Response({'error': 'Only CSV files are supported'}, status=400)

    source_id = request.data.get('source_system_id')
    if source_id:
        try:
            source_id = uuid.UUID(str(source_id))
        except ValueError:
            return Response({'error': 'source_system_id must be a UUID', 'code': 'validation_error'}, status=400)
        try:
            source = SourceSystem.objects.get(
                id=source_id,
                tenant=request.user.tenant,
                source_type=source_type,
            )
        except SourceSystem.DoesNotExist:
            return Response({'error': 'Source system not found'}, status=404)
    else:
        source, _ = SourceSystem.objects.get_or_create(
            tenant=request.user.tenant,
            source_type=source_type,
            name=f'Auto-{source_type}',
            defaults={'is_active': True, 'config': {}},
        )

    job = DataIngestionJob(
        tenant=request.user.tenant,
        source_system=source,
        status=DataIngestionJob.STATUS_UPLOADED,
        uploaded_file=file_obj,
        original_filename=file_obj.name,
        file_size_bytes=file_obj.size,
        created_by=request.user,
    )
    job.save()

    try:
        job = _run_pipeline(job, parser_class)
        AuditService(request.user.tenant).log_ingestion(job, request.user)
        return Response(IngestionJobSerializer(job).data)

    except Exception as e:
        logger.exception('Ingestion pipeline failed for job %s', job.id)
        job.status = DataIngestionJob.STATUS_FAILED
        job.add_log('ERROR', f'Pipeline failed: {e}')
        job.save()
        return Response(
            {'error': 'The file could not be processed. Check the job logs for details.',
             'code': 'pipeline_failed', 'job_id': str(job.id)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    """Get ingestion job details."""
    try:
        job = DataIngestionJob.objects.select_related('source_system').get(
            id=job_id,
            tenant=request.user.tenant,
        )
    except DataIngestionJob.DoesNotExist:
        return Response({'error': 'Job not found'}, status=404)

    return Response(IngestionJobSerializer(job).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_list(request):
    """List ingestion jobs for tenant."""
    jobs = DataIngestionJob.objects.filter(
        tenant=request.user.tenant
    ).select_related('source_system').order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    source_type = request.query_params.get('source_type')
    if source_type:
        jobs = jobs.filter(source_system__source_type=source_type)

    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(jobs, request)
    serializer = IngestionJobSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
