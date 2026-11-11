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
from .base_parser import BaseParserService, parse_cost, parse_date


class UtilityParserService(BaseParserService):
    """Parser for utility electricity portal CSV exports."""

    NAME = 'Utility'
    PARSER_VERSION = 'utility_v1'

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

    def enrich_row(self, result):
        for date_field in ['billing_period_start', 'billing_period_end']:
            raw_date = result.get(date_field, '')
            parsed = parse_date(raw_date) if raw_date else None
            if parsed:
                result[f'{date_field}_parsed'] = parsed.isoformat()

        # Consumption in kWh; MWh columns are converted.
        kwh_raw = result.get('kwh', '')
        mwh_raw = result.get('mwh', '')
        kwh_value = None
        try:
            if kwh_raw:
                kwh_value = float(kwh_raw.replace(',', ''))
            elif mwh_raw:
                kwh_value = float(mwh_raw.replace(',', '')) * 1000
        except ValueError:
            pass
        if kwh_value is not None:
            result['consumption_kwh'] = kwh_value
            result['consumption_unit'] = 'kWh'

        cost = parse_cost(result['cost']) if result.get('cost') else None
        if cost is not None:
            result['cost_parsed'] = cost

    def validate_row(self, normalized):
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
