"""
NormalizationService - converts RawRecords into NormalizedActivities.

This is the core transformation logic. Each source type has different
normalization rules but all produce the same canonical schema.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from apps.ingestion.models import RawRecord, DataIngestionJob
from apps.sources.models import SourceSystem
from ..models import NormalizedActivity


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

    # Unit conversion factors (convert to base unit)
    UNIT_CONVERSIONS = {
        'L': Decimal('1'),
        'l': Decimal('1'),
        'kg': Decimal('1'),
        'ton': Decimal('1000'),
        'kWh': Decimal('1'),
        'mwh': Decimal('1000'),
        'km': Decimal('1'),
        'night': Decimal('1'),
        'nights': Decimal('1'),
    }

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

        # Extract values from normalized payload
        quantity = self._parse_decimal(payload.get('quantity', '0'))
        unit = payload.get('unit_normalized', '')
        fuel_type = payload.get('fuel_type_normalized', '').lower()
        plant_code = payload.get('plant_code', '')
        posting_date = payload.get('posting_date_parsed', '')
        vendor = payload.get('vendor', '')

        # Normalize unit
        normalized_unit = self._normalize_unit(unit)

        # Convert quantity to base unit
        converted_value = self._convert_to_base_unit(quantity, unit)

        # Map fuel type to emission factor
        ef_key = ('fuel', fuel_type)
        emission_factor = self.EMISSION_FACTORS.get(ef_key, Decimal('0'))

        # If unit is mass (kg/ton), use mass-based EF
        if unit.lower() in ['kg', 'ton', 'tons', 't']:
            ef_key = ('fuel', f'{fuel_type}_mass')
            mass_ef = self.EMISSION_FACTORS.get(ef_key)
            if mass_ef:
                emission_factor = mass_ef

        # Parse period
        period = self._parse_period(posting_date)

        # Calculate CO2e
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

        # Emission factor for grid electricity
        emission_factor = self.EMISSION_FACTORS.get(
            ('electricity', 'grid_electricity'),
            Decimal('0.309')
        )

        co2e = consumption * emission_factor

        period = self._parse_period_range(period_start, period_end)

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

        emission_factor = self.EMISSION_FACTORS.get(
            ('travel', sub_category),
            Decimal('0')
        )

        co2e = activity_value * emission_factor

        # Parse trip date
        trip_date = payload.get('trip_date_parsed', '')
        period = self._parse_period(trip_date)

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

    def _convert_to_base_unit(self, quantity, raw_unit):
        """Convert quantity to base unit."""
        factor = self.UNIT_CONVERSIONS.get(raw_unit.lower(), Decimal('1'))
        return quantity * factor

    def _parse_period(self, date_str):
        """Parse a date string and create a month-long period."""
        from datetime import date

        if isinstance(date_str, str) and date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                start = dt.date()
            except (ValueError, TypeError):
                start = date.today()
        elif isinstance(date_str, date):
            start = date_str
        else:
            start = date.today()

        # End of month
        if start.month == 12:
            end = date(start.year, 12, 31)
        else:
            end = date(start.year, start.month + 1, 1)
            end = date(end.year, end.month, 1)
            # Go back one day
            from datetime import timedelta
            end = date(start.year, start.month + 1, 1) if start.month < 12 else date(start.year + 1, 1, 1)
            end = end - __import__('datetime').timedelta(days=1)

        return {'start': start, 'end': end}

    def _parse_period_range(self, start_str, end_str):
        """Parse explicit period start and end."""
        from datetime import date

        start = self._parse_date(start_str) or date.today()
        end = self._parse_date(end_str) or date.today()

        return {'start': start, 'end': end}

    def _parse_date(self, date_str):
        """Parse date string to date object."""
        from datetime import date

        if isinstance(date_str, str) and date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.date()
            except (ValueError, TypeError):
                pass
        return None

    def _parse_decimal(self, val, default=Decimal('0')):
        """Safely parse decimal value."""
        if val is None:
            return default
        val_str = str(val).strip().replace(',', '')
        if not val_str:
            return default
        try:
            return Decimal(val_str)
        except (InvalidOperation, TypeError, ValueError):
            return default


