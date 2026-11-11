"""
Tenant model - foundation of multi-tenant architecture.
Every record in the system is scoped to a tenant.
This isolates client data at the application layer.
"""
import uuid

from django.db import models


class Tenant(models.Model):
    """
    Enterprise client tenant. All data is scoped to a tenant.
    No cross-tenant queries are allowed at the application layer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Contact info for the sustainability lead at this tenant
    contact_email = models.EmailField()
    contact_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
