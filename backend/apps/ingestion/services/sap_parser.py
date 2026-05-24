"""
SAPParserService - parses SAP fuel and procurement CSV exports.

SAP exports are notoriously inconsistent:
- German vs English column headers (Werk vs Plant, Menge vs Quantity)
- Mixed units (L, kg, ton) requiring normalization
- Plant codes that need lookup tables
- Date formats like DD.MM.YYYY or YYYYMMDD
- Empty rows and footer metadata

This parser handles the most common flat-file CSV export format.
"""
import re
from datetime import datetime
from .base_parser import BaseParserService


class SAPParserService(BaseParserService):
    """Parser for SAP fuel and procurement CSV exports."""

    # Column header mapping: handle both German and English
    COLUMN_MAP = {
        # German → English internal
        'bukrs': 'company_code',
        'werk': 'plant_code',
        'matnr': 'material_number',
        'menge': 'quantity',
        'meins': 'unit',
        'postingdate': 'posting_date',
        'datum': 'posting_date',
        'fueltype': 'fuel_type',
        'kraftstofftyp': 'fuel_type',
        'vendor': 'vendor',
        'lieferant': 'vendor',
        'costcenter': 'cost_center',
        'kostenstelle': 'cost_center',
        'werks': 'plant_code',
        'menge_einheit': 'unit',
    }

    # Unit normalization map
    UNIT_MAP = {
        'l': 'L',
        'ltr': 'L',
        'liter': 'L',
        'kg': 'kg',
        'kgs': 'kg',
        'kilogram': 'kg',
        't': 'ton',
        'ton': 'ton',
        'tons': 'ton',
        'to': 'ton',  # German: Tonnen
    }

    # Known fuel types mapped to emission factor categories
    FUEL_TYPE_MAP = {
        'diesel': 'DIESEL',
        'petrol': 'PETROL',
        'gasoline': 'PETROL',
        'benzin': 'PETROL',  # German
        'natural_gas': 'NATURAL_GAS',
        'erdgas': 'NATURAL_GAS',  # German
        'lpg': 'LPG',
        'propane': 'LPG',
        'biofuel': 'BIOFUEL',
        'biodiesel': 'BIODIESEL',
        'heating_oil': 'HEATING_OIL',
        'fuel_oil': 'HEATING_OIL',
    }

    def parse_file(self, file_obj):
        """Parse SAP CSV export and create RawRecords."""
        rows = self.read_csv(file_obj)

        if not rows:
            self.log_error(0, "No data rows found in file")
            return 0, 0, self.errors

        # Normalize headers from first row
        raw_headers = list(rows[0].keys())
        normalized_headers = self._normalize_headers(raw_headers)

        self.job.add_log('INFO', f'Detected {len(rows)} rows with headers: {normalized_headers}')

        for idx, raw_row in enumerate(rows, start=1):
            try:
                # Skip empty rows and SAP footer rows
                if self._is_empty_or_footer(raw_row):
                    continue

                # Normalize the row
                normalized = self._normalize_row(raw_row, normalized_headers)

                # Validate required fields
                validation_errors = self._validate_row(normalized)

                if validation_errors:
                    self.create_raw_record(
                        payload=normalized,
                        row_number=idx,
                        parse_status='FAILED',
                        parse_error='; '.join(validation_errors)
                    )
                    self.failed_count += 1
                    self.log_error(idx, 'Validation failed', {'errors': validation_errors})
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
            f'SAP parsing complete: {self.parsed_count} success, {self.failed_count} failed'
        )
        return self.parsed_count, self.failed_count, self.errors

    def _normalize_headers(self, raw_headers):
        """Map raw headers (possibly German) to normalized English keys."""
        normalized = {}
        for h in raw_headers:
            key = h.strip().lower().replace(' ', '_').replace('-', '_')
            normalized[h] = self.COLUMN_MAP.get(key, key)
        return normalized

    def _normalize_row(self, raw_row, header_map):
        """Convert raw CSV row to normalized payload."""
        result = {
            '_raw': {k: v for k, v in raw_row.items()},
            '_parser_version': 'sap_v1',
        }

        for raw_key, value in raw_row.items():
            norm_key = header_map.get(raw_key, raw_key.lower().strip())
            result[norm_key] = value.strip() if value else ''

        # Normalize unit
        raw_unit = result.get('unit', '')
        if raw_unit:
            result['unit_normalized'] = self.UNIT_MAP.get(raw_unit.lower(), raw_unit.upper())

        # Normalize fuel type
        raw_fuel = result.get('fuel_type', '')
        if raw_fuel:
            result['fuel_type_normalized'] = self.FUEL_TYPE_MAP.get(
                raw_fuel.lower(), raw_fuel.upper()
            )

        # Parse date
        raw_date = result.get('posting_date', '')
        if raw_date:
            parsed_date = self._parse_date(raw_date)
            if parsed_date:
                result['posting_date_parsed'] = parsed_date.isoformat()

        return result

    def _parse_date(self, date_str):
        """Parse various SAP date formats."""
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%Y%m%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def _validate_row(self, normalized):
        """Validate required fields. Returns list of error messages."""
        errors = []

        if not normalized.get('quantity'):
            errors.append('Missing quantity')
        else:
            try:
                qty = float(normalized['quantity'].replace(',', ''))
                if qty <= 0:
                    errors.append('Quantity must be positive')
            except ValueError:
                errors.append(f'Invalid quantity: {normalized["quantity"]}')

        if not normalized.get('unit_normalized'):
            errors.append('Missing or unrecognized unit')

        if not normalized.get('plant_code'):
            errors.append('Missing plant code')

        if not normalized.get('posting_date_parsed'):
            errors.append('Unparseable posting date')

        return errors

    def _is_empty_or_footer(self, raw_row):
        """Detect SAP footer rows and completely empty rows."""
        values = [v for v in raw_row.values() if v and v.strip()]
        if not values:
            return True

        # SAP often ends with summary rows
        first_val = list(raw_row.values())[0] if raw_row.values() else ''
        if first_val and first_val.strip().upper() in ['TOTAL', 'SUMME', '****']:
            return True

        return False
