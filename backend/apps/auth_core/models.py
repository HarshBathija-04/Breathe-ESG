"""
Custom User model with tenant scoping.
Every user belongs to exactly one tenant (for this prototype).
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
import uuid

from apps.tenant.models import Tenant


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user with email as username, scoped to tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    # Tenant scoping - every user belongs to one tenant
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
    )

    # Role-based access control
    ROLE_ADMIN = 'admin'
    ROLE_ANALYST = 'analyst'
    ROLE_REVIEWER = 'reviewer'
    ROLE_VIEWER = 'viewer'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_ANALYST, 'Analyst'),
        (ROLE_REVIEWER, 'Reviewer'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ANALYST,
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['email']

    def __str__(self):
        return f"{self.email} ({self.tenant.name})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def can_review(self):
        return self.role in [self.ROLE_ADMIN, self.ROLE_REVIEWER]

    @property
    def can_approve(self):
        return self.role in [self.ROLE_ADMIN, self.ROLE_REVIEWER]
