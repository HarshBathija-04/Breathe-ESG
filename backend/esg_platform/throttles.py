"""Rate limits for sensitive endpoints (rates live in settings.REST_FRAMEWORK)."""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthThrottle(AnonRateThrottle):
    scope = 'auth'


class AIThrottle(UserRateThrottle):
    scope = 'ai'


class UploadThrottle(UserRateThrottle):
    scope = 'upload'
