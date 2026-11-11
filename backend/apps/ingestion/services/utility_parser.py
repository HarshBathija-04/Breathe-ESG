"""
UtilityParserService - parses utility electricity CSV exports.

Utility data typically comes from:
1. Portal CSV exports (what we handle here)
2. PDF bills (too complex for MVP - see TRADEOFFS.md)
3. API integrations (rare in enterprise)

Challenges:
- Billing periods don't align with calendar months
- Units vary (kWh, MWh)
- Meter IDs may not be globally unique
- Tariff structures vary by utility
"""
from datetime import datetime

from .base_parser import BaseParserService


class UtilityParserService(BaseParserService):
    """Parser for utility electricity portal CSV exports."""

    COLUMN_MAP = {
        'meter_id': 'meter_id',
        'meter': 'meter_id',
        'zaehler': 'meter_id',  # German
        'billing_period_start': 'billing_period_start',
        'period_start': 'billing_period_start',
        'start_date': 'billing_period_start',
        'billing_period_end': 'billing_period_end',
        'period_end': 'billing_period_end',
        'end_date': 'billing_period_end',
        'kwh': 'kwh',
        'consumption_kwh': 'kwh',
        'consumption': 'kwh',
        'usage': 'kwh',
        'verbrauch': 'kwh',  # German
        'mwh': 'mwh',
        'tariff': 'tariff',
        'rate': 'tariff',
        'tarif': 'tariff',  # German
        'cost': 'cost',
        'amount': 'cost',
        'betrag': 'cost',  # German
        'facility': 'facility',
        'location': 'facility',
        'site': 'facility',
        'standort': 'facility',  # German
    }

    def parse_file(self, file_obj):
        """Parse utility CSV export and create RawRecords."""
        rows = self.read_csv(file_obj)

        if not rows:
            self.log_error(0, "No data rows found in file")
            return 0, 0, self.errors

        raw_headers = list(rows[0].keys())
        normalized_headers = self._normalize_headers(raw_headers)

        self.job.add_log('INFO', f'Detected {len(rows)} rows with headers: {list(normalized_headers.values())}')

        for idx, raw_row in enumerate(rows, start=1):
            try:
                if self._is_empty_row(raw_row):
                    continue

                normalized = self._normalize_row(raw_row, normalized_headers)
                validation_errors = self._validate_row(normalized)

                if validation_errors:
                    self.create_raw_record(
                        payload=normalized,
                        row_number=idx,
                        parse_status='FAILED',
                        parse_error='; '.join(validation_errors)
                    )
                    self.failed_count += 1
                else:
                    self.create_raw_record(
                        payload=normalized,
                        row_number=idx,
                    )
                    self.parsed_count += 1

            except Exception as e:
                self.failed_count += 1
                self.log_error(idx, f'Parse exception: {str(e)}')

        self.job.add_log(
            'INFO',
            f'Utility parsing complete: {self.parsed_count} success, {self.failed_count} failed'
        )
        return self.parsed_count, self.failed_count, self.errors

    def _normalize_headers(self, raw_headers):
        """Map raw headers to normalized keys."""
        normalized = {}
        for h in raw_headers:
            key = h.strip().lower().replace(' ', '_').replace('-', '_')
            normalized[h] = self.COLUMN_MAP.get(key, key)
        return normalized

    def _normalize_row(self, raw_row, header_map):
        """Convert raw row to normalized payload."""
        result = {
            '_raw': {k: v for k, v in raw_row.items()},
            '_parser_version': 'utility_v1',
        }

        for raw_key, value in raw_row.items():
            norm_key = header_map.get(raw_key, raw_key.lower().strip())
            result[norm_key] = value.strip() if value else ''

        # Parse dates
        for date_field in ['billing_period_start', 'billing_period_end']:
            raw_date = result.get(date_field, '')
            if raw_date:
                parsed = self._parse_date(raw_date)
                if parsed:
                    result[f'{date_field}_parsed'] = parsed.isoformat()

        # Normalize consumption to kWh
        kwh_raw = result.get('kwh', '')
        mwh_raw = result.get('mwh', '')

        kwh_value = None
        if kwh_raw:
            try:
                kwh_value = float(kwh_raw.replace(',', ''))
            except ValueError:
                pass
        elif mwh_raw:
            try:
                kwh_value = float(mwh_raw.replace(',', '')) * 1000
            except ValueError:
                pass

        if kwh_value is not None:
            result['consumption_kwh'] = kwh_value
            result['consumption_unit'] = 'kWh'

        # Parse cost
        cost_raw = result.get('cost', '')
        if cost_raw:
            try:
                result['cost_parsed'] = float(cost_raw.replace(',', '').replace('$', '').replace('€', ''))
            except ValueError:
                pass

        return result

    def _parse_date(self, date_str):
        """Parse various date formats."""
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%d.%m.%Y',
            '%Y%m%d',
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def _validate_row(self, normalized):
        """Validate required fields."""
        errors = []

        if not normalized.get('meter_id'):
            errors.append('Missing meter ID')

        if normalized.get('consumption_kwh') is None:
            errors.append('Missing or invalid consumption value')
        elif normalized['consumption_kwh'] <= 0:
            errors.append('Consumption must be positive')

        if not normalized.get('billing_period_start_parsed'):
            errors.append('Missing billing period start')

        if not normalized.get('billing_period_end_parsed'):
            errors.append('Missing billing period end')

        return errors

    def _is_empty_row(self, raw_row):
        """Check if row is effectively empty."""
        values = [v for v in raw_row.values() if v and v.strip()]
        return not values
