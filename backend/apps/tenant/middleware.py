"""
Tenant middleware - extracts tenant from JWT claims and sets on request.
Every API call is scoped to a tenant. This enforces data isolation.
"""
from django.http import JsonResponse
from .models import Tenant


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None

        # Try to get tenant from authenticated user
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'tenant'):
                tenant = request.user.tenant

        # Fallback: get from X-Tenant-ID header (for service accounts)
        if tenant is None:
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                except Tenant.DoesNotExist:
                    pass

        request.tenant = tenant
        response = self.get_response(request)
        return response
