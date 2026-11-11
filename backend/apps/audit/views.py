"""
Audit API views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import AuditLogSerializer
from .services.audit_service import AuditService


class AuditPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_timeline(request):
    """Get audit timeline for tenant."""
    from .models import AuditLog
    logs = AuditLog.objects.filter(
        tenant=request.user.tenant
    ).order_by('-timestamp')

    # Filter by entity type if provided
    entity_type = request.query_params.get('entity_type')
    if entity_type:
        logs = logs.filter(entity_type=entity_type)

    # Filter by action if provided
    action = request.query_params.get('action')
    if action:
        logs = logs.filter(action=action)

    paginator = AuditPagination()
    page = paginator.paginate_queryset(logs, request)
    serializer = AuditLogSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def entity_audit(request, entity_type, entity_id):
    """Get audit history for a specific entity."""
    service = AuditService(request.user.tenant)
    history = service.get_entity_history(entity_type, entity_id)
    serializer = AuditLogSerializer(history, many=True)
    return Response(serializer.data)
