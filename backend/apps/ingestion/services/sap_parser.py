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
from .base_parser import BaseParserService, parse_date


class SAPParserService(BaseParserService):
    """Parser for SAP fuel and procurement CSV exports."""

    NAME = 'SAP'
    PARSER_VERSION = 'sap_v1'
    LOG_VALIDATION_FAILURES = True

    # German and English headers -> internal keys
    COLUMN_MAP = {
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

    def enrich_row(self, result):
        raw_unit = result.get('unit', '')
        if raw_unit:
            result['unit_normalized'] = self.UNIT_MAP.get(raw_unit.lower(), raw_unit.upper())

        raw_fuel = result.get('fuel_type', '')
        if raw_fuel:
            result['fuel_type_normalized'] = self.FUEL_TYPE_MAP.get(raw_fuel.lower(), raw_fuel.upper())

        raw_date = result.get('posting_date', '')
        parsed_date = parse_date(raw_date) if raw_date else None
        if parsed_date:
            result['posting_date_parsed'] = parsed_date.isoformat()

    def validate_row(self, normalized):
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

    def is_skipped_row(self, raw_row):
        """Skip empty rows and SAP summary/footer rows."""
        if super().is_skipped_row(raw_row):
            return True
        first_val = next(iter(raw_row.values()), '')
        return bool(first_val) and first_val.strip().upper() in ['TOTAL', 'SUMME', '****']
