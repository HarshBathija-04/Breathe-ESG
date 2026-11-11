"""
NormalizedActivity - the canonical representation of an emissions-producing activity.

All source data (SAP fuel, utility electricity, travel) normalizes into this schema.
This is what analysts review and auditors see.

Status lifecycle:
  PENDING_REVIEW → APPROVED → LOCKED
  PENDING_REVIEW → FLAGGED → PENDING_REVIEW → APPROVED → LOCKED
  PENDING_REVIEW → REJECTED

Once LOCKED, the record is immutable (for audit compliance).
"""
import uuid

from django.db import models

from apps.auth_core.models import User
from apps.ingestion.models import DataIngestionJob, RawRecord
from apps.tenant.models import Tenant


class NormalizedActivity(models.Model):
    """
    Canonical normalized activity record.
    This is what analysts review and what feeds into emissions reporting.
    """

    # GHG Protocol scopes
    SCOPE_1 = 'Scope1'
    SCOPE_2 = 'Scope2'
    SCOPE_3 = 'Scope3'

    SCOPE_CHOICES = [
        (SCOPE_1, 'Scope 1 - Direct'),
        (SCOPE_2, 'Scope 2 - Indirect (Energy)'),
        (SCOPE_3, 'Scope 3 - Value Chain'),
    ]

    # Activity categories
    CATEGORY_FUEL = 'fuel'
    CATEGORY_ELECTRICITY = 'electricity'
    CATEGORY_TRAVEL = 'travel'

    CATEGORY_CHOICES = [
        (CATEGORY_FUEL, 'Fuel'),
        (CATEGORY_ELECTRICITY, 'Electricity'),
        (CATEGORY_TRAVEL, 'Travel'),
    ]

    # Sub-categories (examples, not exhaustive)
    SUB_FUEL_DIESEL = 'diesel'
    SUB_FUEL_PETROL = 'petrol'
    SUB_FUEL_NATURAL_GAS = 'natural_gas'
    SUB_FUEL_LPG = 'lpg'
    SUB_FUEL_HEATING_OIL = 'heating_oil'
    SUB_FUEL_BIOFUEL = 'biofuel'

    SUB_ELEC_GRID = 'grid_electricity'
    SUB_ELEC_RENEWABLE = 'renewable_electricity'

    SUB_TRAVEL_FLIGHT_SHORT = 'flight_short_haul'
    SUB_TRAVEL_FLIGHT_LONG = 'flight_long_haul'
    SUB_TRAVEL_HOTEL = 'hotel'
    SUB_TRAVEL_GROUND = 'ground_transport'
    SUB_TRAVEL_RAIL = 'rail'

    # Status
    STATUS_PENDING_REVIEW = 'PENDING_REVIEW'
    STATUS_FLAGGED = 'FLAGGED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_LOCKED = 'LOCKED'

    STATUS_CHOICES = [
        (STATUS_PENDING_REVIEW, 'Pending Review'),
        (STATUS_FLAGGED, 'Flagged'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_LOCKED, 'Locked (Audit)'),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenancy
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='normalized_activities',
    )

    # GHG Protocol classification
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sub_category = models.CharField(max_length=30)

    # Activity value and unit (normalized)
    activity_value = models.DecimalField(max_digits=20, decimal_places=6)
    normalized_unit = models.CharField(max_length=20)

    # Emission factor used
    emission_factor = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text='kg CO2e per normalized_unit'
    )
    emission_factor_source = models.CharField(
        max_length=100,
        blank=True,
        help_text='Source of emission factor (e.g., DEFRA 2024, EPA)'
    )

    # Computed CO2e
    co2e = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        help_text='Total CO2 equivalent in kg'
    )

    # Reporting period
    period_start = models.DateField()
    period_end = models.DateField()

    # Status and review
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_REVIEW,
    )

    # Source tracking - critical for audit
    source_record = models.OneToOneField(
        RawRecord,
        on_delete=models.PROTECT,
        related_name='normalized_activity',
        help_text='The raw record that produced this normalized activity',
    )
    ingestion_job = models.ForeignKey(
        DataIngestionJob,
        on_delete=models.PROTECT,
        related_name='normalized_activities',
    )

    # Edit tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_activities',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_activities',
    )
    edited_flag = models.BooleanField(
        default=False,
        help_text='True if an analyst modified the normalized values'
    )
    edit_reason = models.TextField(
        blank=True,
        help_text='Reason for edit (required if edited_flag=True)'
    )

    # Additional context
    facility_code = models.CharField(max_length=50, blank=True)
    facility_name = models.CharField(max_length=255, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'scope', 'category']),
            models.Index(fields=['tenant', 'period_start', 'period_end']),
            models.Index(fields=['source_record']),
        ]
        verbose_name_plural = 'Normalized Activities'

    def __str__(self):
        return f"{self.category} | {self.sub_category} | {self.co2e} kg CO2e | {self.status}"

    def compute_co2e(self):
        """Recalculate CO2e from activity_value and emission_factor."""
        if self.activity_value and self.emission_factor:
            self.co2e = self.activity_value * self.emission_factor

    def can_edit(self):
        """Only open records (pending or flagged) can be edited or reviewed."""
        return self.status in [self.STATUS_PENDING_REVIEW, self.STATUS_FLAGGED]

    def lock_for_audit(self):
        """Lock this record for audit."""
        if self.status == self.STATUS_APPROVED:
            self.status = self.STATUS_LOCKED
            self.save(update_fields=['status'])
            return True
        return False
