"""
AnomalyService - detects suspicious patterns in normalized data.

Runs after normalization. Flags records for analyst review.
Does not block processing - flags are informational.
"""
from datetime import UTC, datetime
from decimal import Decimal

from django.db.models import Avg

from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.normalization.models import NormalizedActivity

from ..models import AnomalyFlag


class AnomalyService:
    """
    Detects anomalies in normalized activities.

    Detection rules:
    1. Electricity consumption spikes vs. historical average
    2. Negative fuel values
    3. Zero consumption values
    4. Missing airport codes (travel)
    5. Duplicate records
    6. Values significantly outside normal range
    7. Missing derived distances
    """

    ELECTRICITY_SPIKE_PCT = Decimal('300')  # flag above 300% of the meter's approved history

    def __init__(self, tenant):
        self.tenant = tenant
        self.flags_created = 0

    def detect_all(self, activities=None):
        """
        Run all anomaly detectors on activities.
        If activities is None, checks all PENDING_REVIEW activities.
        """
        if activities is None:
            activities = NormalizedActivity.objects.filter(
                tenant=self.tenant,
                status=NormalizedActivity.STATUS_PENDING_REVIEW,
            ).select_related('source_record')

        for activity in activities:
            self._detect_electricity_spike(activity)
            self._detect_negative_value(activity)
            self._detect_zero_value(activity)
            self._detect_missing_airport(activity)
            self._detect_duplicate(activity)
            self._detect_out_of_range(activity)
            self._detect_missing_distance(activity)

        return self.flags_created

    def _create_flag(self, activity, anomaly_type, description, confidence, details=None):
        """Create an anomaly flag if one doesn't already exist."""
        if AnomalyFlag.objects.filter(
            activity=activity, anomaly_type=anomaly_type, status=AnomalyFlag.STATUS_OPEN,
        ).exists():
            return

        AnomalyFlag.objects.create(
            tenant=self.tenant,
            activity=activity,
            anomaly_type=anomaly_type,
            description=description,
            confidence=confidence,
            details=details or {},
        )
        self.flags_created += 1

        if activity.status == NormalizedActivity.STATUS_PENDING_REVIEW:
            activity.status = NormalizedActivity.STATUS_FLAGGED
            activity.save(update_fields=['status'])

    def _detect_electricity_spike(self, activity):
        """Detect electricity consumption spikes."""
        if activity.category != NormalizedActivity.CATEGORY_ELECTRICITY:
            return

        # Get historical average for same meter/facility
        history = NormalizedActivity.objects.filter(
            tenant=self.tenant,
            category=NormalizedActivity.CATEGORY_ELECTRICITY,
            facility_code=activity.facility_code,
            status__in=[
                NormalizedActivity.STATUS_APPROVED,
                NormalizedActivity.STATUS_LOCKED,
            ],
            period_end__lt=activity.period_start,
        ).aggregate(avg=Avg('activity_value'))

        historical_avg = history['avg']
        if historical_avg and historical_avg > 0:
            current = activity.activity_value
            pct = (current / historical_avg) * Decimal('100')

            if pct > self.ELECTRICITY_SPIKE_PCT:
                self._create_flag(
                    activity,
                    AnomalyFlag.TYPE_ELECTRICITY_SPIKE,
                    f'Electricity consumption ({current} kWh) is {pct:.0f}% above historical average ({historical_avg:.0f} kWh)',
                    min(Decimal('0.99'), pct / Decimal('500')),
                    {'historical_avg': float(historical_avg), 'current': float(current), 'pct_above': float(pct)}
                )

    def _detect_negative_value(self, activity):
        """Detect negative activity values."""
        if activity.activity_value < 0:
            self._create_flag(
                activity,
                AnomalyFlag.TYPE_NEGATIVE_VALUE,
                f'Negative activity value detected: {activity.activity_value} {activity.normalized_unit}',
                Decimal('0.95'),
                {'value': float(activity.activity_value)}
            )

    def _detect_zero_value(self, activity):
        """Detect zero activity values."""
        if activity.activity_value == 0:
            self._create_flag(
                activity,
                AnomalyFlag.TYPE_ZERO_VALUE,
                f'Zero activity value for {activity.category} - {activity.sub_category}',
                Decimal('0.6'),
                {}
            )

    def _detect_missing_airport(self, activity):
        """Detect missing airport codes in travel data."""
        if activity.category != NormalizedActivity.CATEGORY_TRAVEL:
            return

        if 'flight' in activity.sub_category:
            raw = activity.source_record.original_payload
            origin = raw.get('origin_airport', '')
            dest = raw.get('destination_airport', '')

            if not origin or not dest:
                self._create_flag(
                    activity,
                    AnomalyFlag.TYPE_MISSING_AIRPORT,
                    'Missing airport code(s) for flight record',
                    Decimal('0.85'),
                    {'origin': origin, 'destination': dest}
                )

    def _detect_duplicate(self, activity):
        """Detect potential duplicate records."""
        duplicate = NormalizedActivity.objects.filter(
            tenant=self.tenant,
            source_record__row_hash=activity.source_record.row_hash,
        ).exclude(id=activity.id).first()

        if duplicate:
            self._create_flag(
                activity,
                AnomalyFlag.TYPE_DUPLICATE,
                f'Same source row was already ingested on {duplicate.created_at:%b %d, %Y}',
                Decimal('0.8'),
                {'duplicate_of': str(duplicate.id)}
            )

    def _detect_out_of_range(self, activity):
        """Detect values that seem physically implausible."""
        value = activity.activity_value

        # Sanity checks by category
        if activity.category == NormalizedActivity.CATEGORY_ELECTRICITY:
            # > 1 GWh for a single meter in a month is suspicious
            if value > Decimal('1000000'):
                self._create_flag(
                    activity,
                    AnomalyFlag.TYPE_OUT_OF_RANGE,
                    f'Electricity value {value:,.0f} kWh seems implausibly high for a single facility',
                    Decimal('0.75'),
                    {'value': float(value)}
                )

        elif activity.category == NormalizedActivity.CATEGORY_FUEL:
            # > 1 million liters is suspicious for a single entry
            if value > Decimal('1000000'):
                self._create_flag(
                    activity,
                    AnomalyFlag.TYPE_OUT_OF_RANGE,
                    f'Fuel quantity {value:,.0f} {activity.normalized_unit} seems implausibly high for one entry',
                    Decimal('0.75'),
                    {'value': float(value)}
                )

        elif activity.category == NormalizedActivity.CATEGORY_TRAVEL:
            # A single trip longer than one lap of the Earth (~40,000 km) is not plausible
            if activity.normalized_unit == 'km' and value > Decimal('40000'):
                self._create_flag(
                    activity,
                    AnomalyFlag.TYPE_OUT_OF_RANGE,
                    f'Trip distance {value:,.0f} km exceeds the circumference of the Earth',
                    Decimal('0.95'),
                    {'value': float(value)}
                )

    def _detect_missing_distance(self, activity):
        """Detect travel records with missing/derived distance."""
        if activity.category != NormalizedActivity.CATEGORY_TRAVEL:
            return

        if 'flight' in activity.sub_category and activity.activity_value <= 0:
            self._create_flag(
                activity,
                AnomalyFlag.TYPE_MISSING_DISTANCE,
                'Flight record has zero or missing distance',
                Decimal('0.9'),
                {}
            )

    def resolve_flag(self, flag, user, status, note=''):
        """Close a flag (audited); the activity returns to review once no open flags remain."""
        flag.status = status
        flag.resolved_by = user
        flag.resolution_note = note
        flag.resolved_at = datetime.now(UTC)
        flag.save()

        AuditService(self.tenant).log(
            action=AuditLog.ACTION_ANOMALY_CLEAR,
            entity_type='AnomalyFlag',
            entity_id=flag.id,
            actor=user,
            before={'status': 'OPEN'},
            after={'status': status, 'note': note},
        )

        if status in [AnomalyFlag.STATUS_RESOLVED, AnomalyFlag.STATUS_IGNORED]:
            remaining = AnomalyFlag.objects.filter(
                activity=flag.activity,
                status=AnomalyFlag.STATUS_OPEN,
            ).exists()
            if not remaining and flag.activity.status == NormalizedActivity.STATUS_FLAGGED:
                flag.activity.status = NormalizedActivity.STATUS_PENDING_REVIEW
                flag.activity.save(update_fields=['status'])

        return flag
