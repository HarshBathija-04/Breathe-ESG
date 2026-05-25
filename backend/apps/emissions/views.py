"""
Dashboard API - aggregated statistics for the frontend dashboard.
"""
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.normalization.models import NormalizedActivity
from apps.ingestion.models import DataIngestionJob
from apps.anomaly.models import AnomalyFlag
from apps.review.models import ReviewDecision


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics for the current tenant.

    Returns:
    - Total imported records
    - Pending review count
    - Flagged count
    - Approved count
    - Locked count
    - Total CO2e by scope
    - Recent ingestion jobs
    - Anomaly summary
    """
    tenant = request.user.tenant

    # Activity counts by status
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

    # CO2e by scope — include all statuses so charts show data even before approval
    scope_emissions = NormalizedActivity.objects.filter(
        tenant=tenant,
    ).values('scope').annotate(
        total_co2e=Sum('co2e'),
        count=Count('id')
    )

    # CO2e by category — include all statuses
    category_emissions = NormalizedActivity.objects.filter(
        tenant=tenant,
    ).values('category').annotate(
        total_co2e=Sum('co2e'),
        count=Count('id')
    )

    # Recent ingestion jobs
    recent_jobs = DataIngestionJob.objects.filter(
        tenant=tenant
    ).order_by('-created_at')[:5]

    job_list = []
    for job in recent_jobs:
        job_list.append({
            'id': str(job.id),
            'source_type': job.source_system.source_type,
            'status': job.status,
            'original_filename': job.original_filename,
            'total_rows': job.total_rows,
            'parsed_rows': job.parsed_rows,
            'normalized_rows': job.normalized_rows,
            'created_at': job.created_at.isoformat(),
        })

    # Anomaly summary
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

    # Filter by status
    status = request.query_params.get('status')
    if status:
        activities = activities.filter(status=status)

    # Filter by scope
    scope = request.query_params.get('scope')
    if scope:
        activities = activities.filter(scope=scope)

    # Filter by category
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

    # Ordering
    ordering = request.query_params.get('ordering', '-created_at')
    activities = activities.order_by(ordering)

    # Pagination
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(activities, request)

    from apps.normalization.serializers import NormalizedActivitySerializer
    serializer = NormalizedActivitySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
