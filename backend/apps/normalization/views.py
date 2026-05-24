"""
Normalization views.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import NormalizedActivity
from .serializers import NormalizedActivitySerializer, ActivityEditSerializer
from apps.audit.services.audit_service import AuditService


class ActivityPagination(PageNumberPagination):
    page_size = 50


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_detail(request, activity_id):
    """Get a single activity detail."""
    try:
        activity = NormalizedActivity.objects.select_related(
            'source_record', 'source_record__source_system'
        ).get(id=activity_id, tenant=request.user.tenant)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found'}, status=404)

    serializer = NormalizedActivitySerializer(activity)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def activity_edit(request, activity_id):
    """Edit a normalized activity (with audit trail)."""
    try:
        activity = NormalizedActivity.objects.get(
            id=activity_id,
            tenant=request.user.tenant,
        )
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found'}, status=404)

    if not activity.can_edit():
        return Response(
            {'error': f'Activity is {activity.status} and cannot be edited'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = ActivityEditSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Capture before state
    before = {
        'activity_value': str(activity.activity_value),
        'emission_factor': str(activity.emission_factor),
        'co2e': str(activity.co2e),
        'facility_code': activity.facility_code,
        'notes': activity.notes,
    }

    # Apply changes
    data = serializer.validated_data
    for field in ['activity_value', 'emission_factor', 'period_start', 'period_end', 'facility_code', 'notes']:
        if field in data:
            setattr(activity, field, data[field])

    # Recalculate CO2e if value or factor changed
    if 'activity_value' in data or 'emission_factor' in data:
        activity.compute_co2e()

    activity.edited_flag = True
    activity.edit_reason = data.get('edit_reason', '')
    activity.updated_by = request.user
    activity.save()

    # Capture after state
    after = {
        'activity_value': str(activity.activity_value),
        'emission_factor': str(activity.emission_factor),
        'co2e': str(activity.co2e),
        'facility_code': activity.facility_code,
        'notes': activity.notes,
    }

    # Audit log
    audit = AuditService(request.user.tenant)
    audit.log_edit(
        activity=activity,
        actor=request.user,
        before_data=before,
        after_data=after,
        reason=data.get('edit_reason', ''),
        ip_address=getattr(request, 'ip_address', None),
        user_agent=getattr(request, 'user_agent', ''),
    )

    return Response(NormalizedActivitySerializer(activity).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activity_lock(request, activity_id):
    """Lock an approved activity for audit."""
    try:
        activity = NormalizedActivity.objects.get(
            id=activity_id,
            tenant=request.user.tenant,
            status=NormalizedActivity.STATUS_APPROVED,
        )
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found or not approved'}, status=404)

    if not request.user.can_approve:
        return Response({'error': 'Permission denied'}, status=403)

    activity.lock_for_audit()

    # Audit log
    audit = AuditService(request.user.tenant)
    audit.log_lock(
        activity=activity,
        actor=request.user,
        ip_address=getattr(request, 'ip_address', None),
        user_agent=getattr(request, 'user_agent', ''),
    )

    return Response({'message': 'Activity locked for audit'})
