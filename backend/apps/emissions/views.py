"""
Dashboard API - aggregated statistics for the frontend dashboard.
"""
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.anomaly.models import AnomalyFlag
from apps.ingestion.models import DataIngestionJob
from apps.normalization.models import NormalizedActivity
from apps.normalization.serializers import NormalizedActivitySerializer
from esg_platform.throttles import AIThrottle

from .insights import InsightsUnavailable, generate_briefing

EXCLUDED_STATUSES = [NormalizedActivity.STATUS_FLAGGED, NormalizedActivity.STATUS_REJECTED]
ORDERING_FIELDS = {'created_at', 'period_start', 'co2e', 'activity_value', 'status', 'scope', 'category'}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """KPIs, CO2e by scope/category/month, recent jobs and anomaly counts for the tenant."""
    tenant = request.user.tenant

    activity_stats = NormalizedActivity.objects.filter(
        tenant=tenant
    ).values('status').annotate(count=Count('id'))

    status_counts = {
        'pending_review': 0,
        'flagged': 0,
        'approved': 0,
        'locked': 0,
        'rejected': 0,
        'total': 0,
    }

    for stat in activity_stats:
        status_key = stat['status'].lower()
        status_counts[status_key] = stat['count']
        status_counts['total'] += stat['count']

    # CO2e charts count only "reportable" records: flagged (suspect until resolved)
    # and rejected records are excluded, and their flagged total is reported separately.
    reportable = NormalizedActivity.objects.filter(tenant=tenant).exclude(status__in=EXCLUDED_STATUSES)
    scope_emissions = reportable.values('scope').annotate(total_co2e=Sum('co2e'), count=Count('id')).order_by('scope')
    category_emissions = reportable.values('category').annotate(
        total_co2e=Sum('co2e'), count=Count('id')).order_by('-total_co2e')
    flagged_co2e = NormalizedActivity.objects.filter(
        tenant=tenant, status=NormalizedActivity.STATUS_FLAGGED).aggregate(total=Sum('co2e'))['total'] or 0

    recent_jobs = DataIngestionJob.objects.filter(
        tenant=tenant
    ).select_related('source_system').order_by('-created_at')[:5]

    # Monthly CO2e trend by scope
    monthly = reportable.annotate(month=TruncMonth('period_start')).values('month', 'scope').annotate(
        total_co2e=Sum('co2e')
    ).order_by('month')
    by_month = {}
    for row in monthly:
        if row['month']:
            key = row['month'].strftime('%Y-%m')
            by_month.setdefault(key, {'month': key})[row['scope']] = float(row['total_co2e'] or 0)

    job_list = [{
        'id': str(job.id),
        'source_type': job.source_system.source_type,
        'status': job.status,
        'original_filename': job.original_filename,
        'total_rows': job.total_rows,
        'parsed_rows': job.parsed_rows,
        'normalized_rows': job.normalized_rows,
        'created_at': job.created_at.isoformat(),
    } for job in recent_jobs]

    anomaly_summary = AnomalyFlag.objects.filter(
        tenant=tenant
    ).values('status').annotate(count=Count('id'))

    anomaly_counts = {'open': 0, 'resolved': 0, 'confirmed': 0, 'ignored': 0}
    for a in anomaly_summary:
        anomaly_counts[a['status'].lower()] = a['count']

    return Response({
        'activities': status_counts,
        'emissions_by_scope': list(scope_emissions),
        'emissions_by_category': list(category_emissions),
        'emissions_by_month': list(by_month.values()),
        'flagged_co2e': float(flagged_co2e),
        'recent_jobs': job_list,
        'anomalies': anomaly_counts,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activities_list(request):
    """
    List normalized activities with filtering.
    """
    tenant = request.user.tenant
    activities = NormalizedActivity.objects.filter(
        tenant=tenant
    ).select_related('source_record', 'source_record__source_system')

    status = request.query_params.get('status')
    if status:
        activities = activities.filter(status=status)

    scope = request.query_params.get('scope')
    if scope:
        activities = activities.filter(scope=scope)

    category = request.query_params.get('category')
    if category:
        activities = activities.filter(category=category)

    # Search
    search = request.query_params.get('search')
    if search:
        activities = activities.filter(
            Q(facility_code__icontains=search) |
            Q(vendor__icontains=search) |
            Q(sub_category__icontains=search)
        )

    # Ordering (whitelisted: arbitrary field names would raise FieldError)
    ordering = request.query_params.get('ordering', '-created_at')
    if ordering.lstrip('-') not in ORDERING_FIELDS:
        ordering = '-created_at'
    activities = activities.order_by(ordering)

    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(activities, request)
    serializer = NormalizedActivitySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AIThrottle])
def ai_insights(request):
    """Generate an AI executive briefing (Groq) from the tenant's aggregated emissions."""
    try:
        return Response(generate_briefing(request.user.tenant))
    except InsightsUnavailable as exc:
        return Response({'error': str(exc), 'code': 'ai_unavailable'}, status=exc.status_code)
