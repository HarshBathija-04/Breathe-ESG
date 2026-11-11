"""
Auth views - login, me, tenant users.

Self-service registration was removed: it let anonymous callers pick their own
role and tenant. Users are provisioned by the seed command or Django admin.
"""
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from esg_platform.throttles import AuthThrottle

from .authentication import generate_token
from .serializers import LoginSerializer, UserSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login_view(request):
    """Login with email/password, return JWT token."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    return Response({
        'access': generate_token(user),
        'user': UserSerializer(user).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return current user info."""
    return Response(UserSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tenant_users_view(request):
    """List users in current tenant."""
    users = User.objects.filter(tenant=request.user.tenant)
    return Response(UserSerializer(users, many=True).data)
