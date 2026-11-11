"""
Anomaly API views.
"""
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnomalyFlag
from .serializers import AnomalyFlagSerializer, AnomalyResolutionSerializer
from .services.anomaly_service import AnomalyService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anomaly_list(request):
    """List anomaly flags for tenant."""
    flags = AnomalyFlag.objects.filter(
        tenant=request.user.tenant
    ).select_related('activity', 'resolved_by')

    status_filter = request.query_params.get('status')
    if status_filter:
        flags = flags.filter(status=status_filter)

    anomaly_type = request.query_params.get('type')
    if anomaly_type:
        flags = flags.filter(anomaly_type=anomaly_type)

    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(flags, request)
    serializer = AnomalyFlagSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anomaly_stats(request):
    """Flag counts by status and by type."""
    flags = AnomalyFlag.objects.filter(tenant=request.user.tenant)
    return Response({
        'by_status': list(flags.values('status').annotate(count=Count('id'))),
        'by_type': list(flags.values('anomaly_type').annotate(count=Count('id'))),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_anomaly(request, flag_id):
    """Resolve an anomaly flag (reviewers and admins only)."""
    if not request.user.can_review:
        return Response({'error': 'Your role cannot resolve anomalies.', 'code': 'permission_denied'}, status=403)
    flag = AnomalyFlag.objects.filter(
        id=flag_id,
        tenant=request.user.tenant,
    ).first()

    if not flag:
        return Response({'error': 'Flag not found'}, status=404)

    serializer = AnomalyResolutionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    AnomalyService(request.user.tenant).resolve_flag(
        flag=flag,
        user=request.user,
        status=serializer.validated_data['status'],
        note=serializer.validated_data.get('note', ''),
    )

    return Response({'message': 'Flag resolved'})
