"""
Tenant utilities for queryset scoping.
"""
from .models import Tenant


def get_tenant_queryset(model_class, tenant):
    """Return queryset scoped to tenant."""
    if tenant is None:
        return model_class.objects.none()
    return model_class.objects.filter(tenant=tenant)
