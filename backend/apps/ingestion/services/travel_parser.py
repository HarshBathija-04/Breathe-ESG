"""
TravelParserService - parses corporate travel CSV exports.

Inspired by Concur/Navan-style exports. Handles:
- Flights (origin/destination airports)
- Hotels (nights stayed)
- Ground transport

Challenges:
- Distance not always provided (must derive from airport codes)
- Mixed travel categories in one file
- Airport codes need validation
- Hotel emissions depend on location (country-level factors)
"""
from datetime import datetime
from .base_parser import BaseParserService


class TravelParserService(BaseParserService):
    """Parser for corporate travel platform CSV exports."""

    COLUMN_MAP = {
        'traveler': 'traveler',
        'employee': 'traveler',
        'mitarbeiter': 'traveler',  # German
        'trip_type': 'trip_type',
        'category': 'trip_type',
        'type': 'trip_type',
        'origin_airport': 'origin_airport',
        'origin': 'origin_airport',
        'departure_airport': 'origin_airport',
        'from': 'origin_airport',
        'destination_airport': 'destination_airport',
        'destination': 'destination_airport',
        'arrival_airport': 'destination_airport',
        'to': 'destination_airport',
        'transport_type': 'transport_type',
        'transport': 'transport_type',
        'hotel_nights': 'hotel_nights',
        'nights': 'hotel_nights',
        'distance_km': 'distance_km',
        'distance': 'distance_km',
        'entfernung': 'distance_km',  # German
        'trip_date': 'trip_date',
        'travel_date': 'trip_date',
        'date': 'trip_date',
        'datum': 'trip_date',  # German
        'booking_date': 'booking_date',
        'cost': 'cost',
        'amount': 'cost',
        'currency': 'currency',
    }

    # Trip type categorization
    TRIP_FLIGHT = 'flight'
    TRIP_HOTEL = 'hotel'
    TRIP_GROUND = 'ground_transport'
    TRIP_RAIL = 'rail'

    TRIP_TYPE_MAP = {
        'flight': TRIP_FLIGHT,
        'air': TRIP_FLIGHT,
        'flug': TRIP_FLIGHT,  # German
        'hotel': TRIP_HOTEL,
        'accommodation': TRIP_HOTEL,
        'unterkunft': TRIP_HOTEL,  # German
        'ground': TRIP_GROUND,
        'car': TRIP_GROUND,
        'taxi': TRIP_GROUND,
        'bus': TRIP_GROUND,
        'rental': TRIP_GROUND,
        'rail': TRIP_RAIL,
        'train': TRIP_RAIL,
        'zug': TRIP_RAIL,  # German
    }

    # Simple airport distance lookup table (km) for common routes
    # In production, this would call an aviation distance API
    AIRPORT_DISTANCES = {
        ('JFK', 'LHR'): 5540,
        ('LHR', 'JFK'): 5540,
        ('JFK', 'LAX'): 3980,
        ('LAX', 'JFK'): 3980,
        ('JFK', 'FRA'): 6200,
        ('FRA', 'JFK'): 6200,
        ('LHR', 'FRA'): 800,
        ('FRA', 'LHR'): 800,
        ('LHR', 'DXB'): 5500,
        ('DXB', 'LHR'): 5500,
        ('SIN', 'LHR'): 10800,
        ('LHR', 'SIN'): 10800,
        ('JFK', 'CDG'): 5850,
        ('CDG', 'JFK'): 5850,
        ('FRA', 'CDG'): 500,
        ('CDG', 'FRA'): 500,
        ('JFK', 'ORD'): 1180,
        ('ORD', 'JFK'): 1180,
        ('LAX', 'SFO'): 540,
        ('SFO', 'LAX'): 540,
        ('FRA', 'VIE'): 620,
        ('VIE', 'FRA'): 620,
        ('LHR', 'AMS'): 370,
        ('AMS', 'LHR'): 370,
        ('JFK', 'MIA'): 1750,
        ('MIA', 'JFK'): 1750,
        ('DXB', 'SIN'): 5850,
        ('SIN', 'DXB'): 5850,
    }

    def parse_file(self, file_obj):
        """Parse travel CSV export and create RawRecords."""
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
            f'Travel parsing complete: {self.parsed_count} success, {self.failed_count} failed'
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
            '_parser_version': 'travel_v1',
        }

        for raw_key, value in raw_row.items():
            norm_key = header_map.get(raw_key, raw_key.lower().strip())
            result[norm_key] = value.strip() if value else ''

        # Categorize trip type
        raw_type = result.get('trip_type', '')
        if raw_type:
            result['trip_type_normalized'] = self.TRIP_TYPE_MAP.get(
                raw_type.lower(), raw_type.lower()
            )

        # Uppercase airport codes
        for field in ['origin_airport', 'destination_airport']:
            val = result.get(field, '')
            if val:
                result[field] = val.upper()

        # Derive distance if missing
        distance_raw = result.get('distance_km', '')
        if not distance_raw:
            origin = result.get('origin_airport', '')
            dest = result.get('destination_airport', '')
            if origin and dest:
                derived = self._derive_distance(origin, dest)
                if derived:
                    result['distance_km'] = str(derived)
                    result['distance_derived'] = True
                else:
                    result['distance_derived'] = False
        else:
            result['distance_derived'] = False

        # Parse dates
        for date_field in ['trip_date', 'booking_date']:
            raw_date = result.get(date_field, '')
            if raw_date:
                parsed = self._parse_date(raw_date)
                if parsed:
                    result[f'{date_field}_parsed'] = parsed.isoformat()

        # Parse cost
        cost_raw = result.get('cost', '')
        if cost_raw:
            try:
                result['cost_parsed'] = float(cost_raw.replace(',', '').replace('$', '').replace('€', ''))
            except ValueError:
                pass

        return result

    def _derive_distance(self, origin, destination):
        """Derive flight distance from airport lookup table."""
        if origin == destination:
            return 0

        # Direct lookup
        dist = self.AIRPORT_DISTANCES.get((origin, destination))
        if dist:
            return dist

        # Try common hub connections for unknown routes
        hubs = ['LHR', 'FRA', 'JFK', 'DXB', 'SIN']
        for hub in hubs:
            leg1 = self.AIRPORT_DISTANCES.get((origin, hub))
            leg2 = self.AIRPORT_DISTANCES.get((hub, destination))
            if leg1 and leg2:
                # Add 10% for hub routing inefficiency
                return int((leg1 + leg2) * 1.1)

        # If we can't derive, return None - anomaly detector will flag
        return None

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
        """Validate required fields based on trip type."""
        errors = []

        trip_type = normalized.get('trip_type_normalized', '')

        if not trip_type:
            errors.append('Missing or unrecognizable trip type')
            return errors

        if not normalized.get('traveler'):
            errors.append('Missing traveler')

        if trip_type == self.TRIP_FLIGHT:
            if not normalized.get('origin_airport'):
                errors.append('Missing origin airport')
            if not normalized.get('destination_airport'):
                errors.append('Missing destination airport')
            if not normalized.get('distance_km'):
                errors.append('Missing distance and could not derive from airports')

        elif trip_type == self.TRIP_HOTEL:
            nights = normalized.get('hotel_nights', '')
            if not nights:
                errors.append('Missing hotel nights')
            else:
                try:
                    n = int(nights)
                    if n <= 0:
                        errors.append('Hotel nights must be positive')
                except ValueError:
                    errors.append(f'Invalid hotel nights: {nights}')

        elif trip_type == self.TRIP_GROUND:
            if not normalized.get('transport_type'):
                errors.append('Missing transport type for ground transport')

        return errors

    def _is_empty_row(self, raw_row):
        """Check if row is effectively empty."""
        values = [v for v in raw_row.values() if v and v.strip()]
        return not values
