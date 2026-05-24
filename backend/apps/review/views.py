"""
Review API views.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.normalization.models import NormalizedActivity
from apps.normalization.serializers import NormalizedActivitySerializer
from .services.review_service import ReviewService
from .serializers import ReviewDecisionSerializer, ReviewActionSerializer
from .models import ReviewDecision


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_review(request):
    """Get all activities pending review for tenant."""
    service = ReviewService(request.user.tenant)
    activities = service.get_pending_activities()
    serializer = NormalizedActivitySerializer(activities, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_action(request, activity_id):
    """Submit approve/reject for an activity."""
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
    activity_ids = request.data.get('activity_ids', [])
    reason = request.data.get('reason', '')

    service = ReviewService(request.user.tenant)
    results = service.bulk_approve(activity_ids, request.user, reason)
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
