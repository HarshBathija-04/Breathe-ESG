"""
Review API views.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.normalization.serializers import NormalizedActivitySerializer

from .serializers import BulkApproveSerializer, ReviewActionSerializer, ReviewDecisionSerializer
from .services.review_service import ReviewService


class ReviewPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_review(request):
    """Get activities pending review for tenant (paginated)."""
    service = ReviewService(request.user.tenant)
    activities = service.get_pending_activities()

    status_filter = request.query_params.get('status')
    if status_filter:
        activities = activities.filter(status=status_filter)

    paginator = ReviewPagination()
    page = paginator.paginate_queryset(activities, request)
    serializer = NormalizedActivitySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_action(request, activity_id):
    """Submit approve/reject for an activity."""
    if not request.user.can_review:
        return Response({'error': 'Your role cannot review activities.', 'code': 'permission_denied'},
                        status=status.HTTP_403_FORBIDDEN)
    serializer = ReviewActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = ReviewService(request.user.tenant)
    success, message = service.submit_decision(
        activity_id=activity_id,
        user=request.user,
        decision=serializer.validated_data['decision'],
        reason=serializer.validated_data.get('reason', ''),
    )

    if success:
        return Response({'message': message})
    return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_approve(request):
    """Bulk approve activities."""
    if not request.user.can_review:
        return Response({'error': 'Your role cannot review activities.', 'code': 'permission_denied'},
                        status=status.HTTP_403_FORBIDDEN)
    serializer = BulkApproveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service = ReviewService(request.user.tenant)
    results = service.bulk_approve(
        serializer.validated_data['activity_ids'], request.user, serializer.validated_data.get('reason', ''))
    return Response({'results': results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_history(request, activity_id):
    """Get review history for an activity."""
    service = ReviewService(request.user.tenant)
    history = service.get_activity_history(activity_id)

    if history is None:
        return Response({'error': 'Activity not found'}, status=404)

    return Response({
        'activity': NormalizedActivitySerializer(history['activity']).data,
        'decisions': ReviewDecisionSerializer(history['decisions'], many=True).data,
    })
