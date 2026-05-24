"""
JWT Authentication for Django REST Framework.
Extracts JWT from Authorization header, validates it, and sets user + tenant.
"""
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from apps.tenant.models import Tenant

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header.')
        if len(auth_header) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header.')

        try:
            token = auth_header[1].decode('utf-8')
        except UnicodeError:
            raise exceptions.AuthenticationFailed('Invalid token encoding.')

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, token, request=None):
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token.')

        try:
            user = User.objects.select_related('tenant').get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found.')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive.')

        # Set tenant on request for middleware to pick up
        if request:
            request.tenant = user.tenant

        return (user, token)


def generate_token(user):
    """Generate JWT token for user."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'tenant_id': str(user.tenant.id),
        'role': user.role,
        'iat': now,
        'exp': now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
