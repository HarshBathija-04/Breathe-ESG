"""
NormalizationService - converts RawRecords into NormalizedActivities.

This is the core transformation logic. Each source type has different
normalization rules but all produce the same canonical schema.
"""
import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.ingestion.models import DataIngestionJob, RawRecord
from apps.sources.models import SourceSystem

from ..models import NormalizedActivity


def normalize_number_string(val):
    """
    Turn '1,234.5', '1.234,5' or German '6709,84' into a plain '1234.5'-style string.
    The separator that appears last is the decimal mark; a lone comma followed by
    exactly three digits is treated as a thousands separator (English convention).
    """
    s = str(val).strip().replace(' ', '')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif s.count(',') == 1 and len(s.split(',')[1]) != 3:
        s = s.replace(',', '.')
    else:
        s = s.replace(',', '')
    return s


class NormalizationService:
    """
    Service for normalizing raw records into canonical activities.

    Handles:
    - Unit normalization (L→kg, MWh→kWh, etc.)
    - Scope/category classification
    - Emission factor lookup
    - CO2e calculation
    - Period extraction
    """

    # Emission factors (kg CO2e per unit) - simplified for prototype
    # In production, these would come from a managed emission factor database
    EMISSION_FACTORS = {
        # Fuel: kg CO2e per liter
        ('fuel', 'diesel'): Decimal('2.68'),
        ('fuel', 'petrol'): Decimal('2.31'),
        ('fuel', 'natural_gas'): Decimal('1.96'),  # per kg
        ('fuel', 'lpg'): Decimal('1.51'),  # per liter
        ('fuel', 'heating_oil'): Decimal('3.15'),  # per liter
        ('fuel', 'biofuel'): Decimal('0.39'),  # per liter (biodiesel)

        # Electricity: kg CO2e per kWh
        ('electricity', 'grid_electricity'): Decimal('0.309'),  # IEA global avg
        ('electricity', 'renewable_electricity'): Decimal('0.0'),

        # Travel: kg CO2e per km
        ('travel', 'flight_short_haul'): Decimal('0.158'),  # per passenger km
        ('travel', 'flight_long_haul'): Decimal('0.195'),  # per passenger km
        ('travel', 'hotel'): Decimal('20.0'),  # per night (global avg)
        ('travel', 'ground_transport'): Decimal('0.12'),  # per km (car avg)
        ('travel', 'rail'): Decimal('0.041'),  # per passenger km
    }

    # Multipliers to the base unit, keyed by lowercase unit; anything else is already base.
    UNIT_CONVERSIONS = {'ton': Decimal('1000'), 'mwh': Decimal('1000')}

    def __init__(self, ingestion_job):
        self.job = ingestion_job
        self.normalized_count = 0
        self.failed_count = 0

    def normalize_all(self):
        """Normalize all parsed raw records for this job."""
        raw_records = RawRecord.objects.filter(
            ingestion_job=self.job,
            parse_status=RawRecord.PARSE_SUCCESS,
        ).select_related('source_system')

        self.job.status = DataIngestionJob.STATUS_NORMALIZING
        self.job.save(update_fields=['status'])

        source_type = self.job.source_system.source_type

        for record in raw_records:
            try:
                if source_type == SourceSystem.SOURCE_SAP:
                    self._normalize_sap(record)
                elif source_type == SourceSystem.SOURCE_UTILITY:
                    self._normalize_utility(record)
                elif source_type == SourceSystem.SOURCE_TRAVEL:
                    self._normalize_travel(record)

                self.normalized_count += 1

            except Exception as e:
                self.failed_count += 1
                self.job.add_log('ERROR', f'Normalization failed for record {record.id}', {
                    'error': str(e),
                    'row_number': record.row_number,
                })

        self.job.normalized_rows = self.normalized_count
        self.job.save(update_fields=['normalized_rows'])

        return self.normalized_count, self.failed_count

    def _normalize_sap(self, raw_record):
        """Normalize SAP fuel record."""
        payload = raw_record.original_payload

        quantity = self._parse_decimal(payload.get('quantity', '0'))
        unit = payload.get('unit_normalized', '')
        fuel_type = payload.get('fuel_type_normalized', '').lower()
        plant_code = payload.get('plant_code', '')
        posting_date = payload.get('posting_date_parsed', '')
        vendor = payload.get('vendor', '')

        normalized_unit = self._normalize_unit(unit)
        converted_value = quantity * self.UNIT_CONVERSIONS.get(unit.lower(), Decimal('1'))
        emission_factor = self.EMISSION_FACTORS.get(('fuel', fuel_type), Decimal('0'))
        period = self._parse_period(posting_date)
        co2e = converted_value * emission_factor

        activity = NormalizedActivity(
            tenant=raw_record.tenant,
            scope=NormalizedActivity.SCOPE_1,
            category=NormalizedActivity.CATEGORY_FUEL,
            sub_category=fuel_type,
            activity_value=converted_value,
            normalized_unit=normalized_unit,
            emission_factor=emission_factor,
            co2e=co2e,
            emission_factor_source='DEFRA 2024 (prototype values)',
            period_start=period['start'],
            period_end=period['end'],
            status=NormalizedActivity.STATUS_PENDING_REVIEW,
            source_record=raw_record,
            ingestion_job=self.job,
            facility_code=plant_code,
            vendor=vendor,
        )
        activity.save()
        return activity

    def _normalize_utility(self, raw_record):
        """Normalize utility electricity record."""
        payload = raw_record.original_payload

        consumption = self._parse_decimal(payload.get('consumption_kwh', '0'))
        meter_id = payload.get('meter_id', '')
        facility = payload.get('facility', '')
        period_start = payload.get('billing_period_start_parsed', '')
        period_end = payload.get('billing_period_end_parsed', '')

        emission_factor = self.EMISSION_FACTORS[('electricity', 'grid_electricity')]
        co2e = consumption * emission_factor
        period = {
            'start': self._parse_date(period_start) or date.today(),
            'end': self._parse_date(period_end) or date.today(),
        }

        activity = NormalizedActivity(
            tenant=raw_record.tenant,
            scope=NormalizedActivity.SCOPE_2,
            category=NormalizedActivity.CATEGORY_ELECTRICITY,
            sub_category='grid_electricity',
            activity_value=consumption,
            normalized_unit='kWh',
            emission_factor=emission_factor,
            co2e=co2e,
            emission_factor_source='IEA 2023 Global Average',
            period_start=period['start'],
            period_end=period['end'],
            status=NormalizedActivity.STATUS_PENDING_REVIEW,
            source_record=raw_record,
            ingestion_job=self.job,
            facility_code=meter_id,
            facility_name=facility,
        )
        activity.save()
        return activity

    def _normalize_travel(self, raw_record):
        """Normalize travel record."""
        payload = raw_record.original_payload

        trip_type = payload.get('trip_type_normalized', '')
        distance = self._parse_decimal(payload.get('distance_km', '0'))
        hotel_nights = int(payload.get('hotel_nights', '0') or '0')

        # Determine sub-category and activity value
        if trip_type == 'flight':
            sub_category = 'flight_long_haul' if distance > 1500 else 'flight_short_haul'
            activity_value = distance
            unit = 'km'
        elif trip_type == 'hotel':
            sub_category = 'hotel'
            activity_value = Decimal(hotel_nights)
            unit = 'night'
            distance = Decimal('0')
        elif trip_type == 'rail':
            sub_category = 'rail'
            activity_value = distance
            unit = 'km'
        else:  # ground transport
            sub_category = 'ground_transport'
            activity_value = distance
            unit = 'km'

        emission_factor = self.EMISSION_FACTORS.get(('travel', sub_category), Decimal('0'))
        co2e = activity_value * emission_factor
        period = self._parse_period(payload.get('trip_date_parsed', ''))

        activity = NormalizedActivity(
            tenant=raw_record.tenant,
            scope=NormalizedActivity.SCOPE_3,
            category=NormalizedActivity.CATEGORY_TRAVEL,
            sub_category=sub_category,
            activity_value=activity_value,
            normalized_unit=unit,
            emission_factor=emission_factor,
            co2e=co2e,
            emission_factor_source='DEFRA 2024 / GHG Protocol',
            period_start=period['start'],
            period_end=period['end'],
            status=NormalizedActivity.STATUS_PENDING_REVIEW,
            source_record=raw_record,
            ingestion_job=self.job,
            notes=f"Traveler: {payload.get('traveler', '')}",
        )
        activity.save()
        return activity

    def _normalize_unit(self, raw_unit):
        """Normalize unit string."""
        unit_map = {
            'l': 'L', 'ltr': 'L', 'liter': 'L',
            'kg': 'kg', 'kgs': 'kg',
            'ton': 'kg', 'tons': 'kg', 't': 'kg', 'to': 'kg',
            'kwh': 'kWh', 'mwh': 'kWh',
            'km': 'km', 'night': 'night', 'nights': 'night',
        }
        return unit_map.get(raw_unit.lower(), raw_unit)

    def _parse_period(self, date_str):
        """ISO date string -> the calendar month containing it (today if missing)."""
        start = self._parse_date(date_str) or date.today()
        end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        return {'start': start, 'end': end}

    def _parse_date(self, date_str):
        """ISO date/datetime string -> date, or None."""
        if isinstance(date_str, str) and date_str:
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            except ValueError:
                pass
        return None

    def _parse_decimal(self, val, default=Decimal('0')):
        """Safely parse decimal value."""
        if val is None:
            return default
        val_str = normalize_number_string(val)
        if not val_str:
            return default
        try:
            return Decimal(val_str)
        except (InvalidOperation, TypeError, ValueError):
            return default


