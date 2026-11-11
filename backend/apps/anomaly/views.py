"""
Anomaly API views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnomalyFlag
from .serializers import AnomalyFlagSerializer, AnomalyResolutionSerializer
from .services.anomaly_service import AnomalyService


class AnomalyPagination(PageNumberPagination):
    page_size = 50


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anomaly_list(request):
    """List anomaly flags for tenant."""
    flags = AnomalyFlag.objects.filter(
        tenant=request.user.tenant
    ).select_related('activity', 'resolved_by')

    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter:
        flags = flags.filter(status=status_filter)

    # Filter by type
    anomaly_type = request.query_params.get('type')
    if anomaly_type:
        flags = flags.filter(anomaly_type=anomaly_type)

    paginator = AnomalyPagination()
    page = paginator.paginate_queryset(flags, request)
    serializer = AnomalyFlagSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anomaly_stats(request):
    """Get anomaly statistics for dashboard."""
    from django.db.models import Count

    stats = AnomalyFlag.objects.filter(
        tenant=request.user.tenant
    ).values('status').annotate(count=Count('id'))

    by_type = AnomalyFlag.objects.filter(
        tenant=request.user.tenant
    ).values('anomaly_type').annotate(count=Count('id'))

    return Response({
        'by_status': list(stats),
        'by_type': list(by_type),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_anomaly(request, flag_id):
    """Resolve an anomaly flag."""
    flag = AnomalyFlag.objects.filter(
        id=flag_id,
        tenant=request.user.tenant,
    ).first()

    if not flag:
        return Response({'error': 'Flag not found'}, status=404)

    serializer = AnomalyResolutionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = AnomalyService(request.user.tenant)
    service.resolve_flag(
        flag=flag,
        user=request.user,
        status=serializer.validated_data['status'],
        note=serializer.validated_data.get('note', ''),
    )

    return Response({'message': 'Flag resolved'})
