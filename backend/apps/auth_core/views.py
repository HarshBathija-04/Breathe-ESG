"""
Auth views - login, register, me.
"""
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .authentication import generate_token
from .serializers import LoginSerializer, UserSerializer, UserCreateSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login with email/password, return JWT token."""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    token = generate_token(user)
    return Response({
        'access': token,
        'user': UserSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Register a new user (for demo/seeding purposes)."""
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token = generate_token(user)
    return Response({
        'access': token,
        'user': UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


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
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)
