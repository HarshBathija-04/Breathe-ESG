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
from .base_parser import BaseParserService, parse_cost, parse_date


class TravelParserService(BaseParserService):
    """Parser for corporate travel platform CSV exports."""

    NAME = 'Travel'
    PARSER_VERSION = 'travel_v1'

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

    def enrich_row(self, result):
        raw_type = result.get('trip_type', '')
        if raw_type:
            result['trip_type_normalized'] = self.TRIP_TYPE_MAP.get(raw_type.lower(), raw_type.lower())

        for field in ['origin_airport', 'destination_airport']:
            if result.get(field):
                result[field] = result[field].upper()

        # Derive distance from the airport table when the export leaves it out.
        # The key is left out when there is nothing to derive from (keeps row hashes stable).
        origin = result.get('origin_airport', '')
        dest = result.get('destination_airport', '')
        if result.get('distance_km', ''):
            result['distance_derived'] = False
        elif origin and dest:
            derived = self._derive_distance(origin, dest)
            result['distance_derived'] = bool(derived)
            if derived:
                result['distance_km'] = str(derived)

        for date_field in ['trip_date', 'booking_date']:
            raw_date = result.get(date_field, '')
            parsed = parse_date(raw_date) if raw_date else None
            if parsed:
                result[f'{date_field}_parsed'] = parsed.isoformat()

        cost = parse_cost(result['cost']) if result.get('cost') else None
        if cost is not None:
            result['cost_parsed'] = cost

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

    def validate_row(self, normalized):
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
