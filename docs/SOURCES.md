# SOURCES.md

## Source Research and Design

### 1. SAP Fuel and Procurement Data

#### Real-World Research

SAP stores fuel and procurement data in several modules:
- **MM (Materials Management)**: Purchase orders, goods receipts, invoice verification
- **FI (Financial Accounting)**: Accounts payable, cost center postings
- **PM (Plant Maintenance)**: Equipment fuel consumption (for fleet)
- **IS-Oil**: Industry-specific oil & gas module (rarely used for general sustainability)

The most common export format is a flat-file CSV from a custom ABAP report or SAP Query. Fields typically include:
- `BUKRS` (Company Code)
- `WERKS` (Plant)
- `MATNR` (Material Number)
- `MENGE` (Quantity)
- `MEINS` (Unit of Measure)
- `BUDAT` or `PostingDate` (Posting Date)
- Custom fields for fuel type

German SAP systems use German field names: `Werk`, `Menge`, `Datum`, `Kraftstofftyp`.

#### Our Implementation

We handle **flat-file CSV exports** with the following features:
- Header normalization (German → English)
- Unit normalization (L, kg, ton, to)
- Plant code extraction for facility tracking
- Date parsing (ISO, German DD.MM.YYYY, YYYYMMDD)
- Validation of required fields (quantity > 0, valid unit, valid date)

**Sample data rationale**: 54 rows covering diesel, petrol, natural gas, LPG, and heating oil across 6 plants. Includes deliberate errors (negative quantity, zero value, unparseable date, duplicate) to test anomaly detection.

**Production limitations**:
- Does not handle SAP IDoc format
- Does not validate material numbers against SAP master data
- Does not handle currency conversion
- Plant codes are not looked up against a facility registry
- No support for SAP BW/4HANA direct connection

---

### 2. Utility Electricity Data

#### Real-World Research

Enterprise electricity data typically comes from:

1. **Utility portals**: Web portals where facilities teams download CSV/Excel exports. Most common.
2. **PDF bills**: Paper or electronic bills. Hard to parse automatically.
3. **EDI 810**: Electronic data interchange invoices. Common in large enterprises but requires EDI parser.
4. **Green Button**: Standardized energy data format (mainly North America, adoption limited).
5. **Smart meter APIs**: Direct meter reads via API (rare, requires utility partnership).

Typical CSV fields from a portal:
- `meter_id` (unique identifier)
- `billing_period_start` / `billing_period_end`
- `kWh` or `MWh` (consumption)
- `tariff` (rate structure)
- `cost` (total bill amount)
- `facility` or `location`

Key challenges:
- Billing periods vary (28-35 days) and don't align with calendar months
- Some utilities report in MWh, others in kWh
- Net metering (solar) can produce negative readings
- Multiple meters per facility
- Tariff structures vary significantly

#### Our Implementation

We handle **portal CSV exports** with:
- Flexible header mapping
- Billing period extraction (arbitrary date ranges)
- Unit conversion (MWh → kWh)
- Cost parsing with currency symbol stripping
- Facility/meter tracking

**Sample data rationale**: 41 rows across 5 meters and 3 facilities. Includes a consumption spike (4.5x historical average) to test anomaly detection. One row with empty kWh but cost present tests missing-data handling.

**Production limitations**:
- No PDF parsing
- No EDI support
- No Green Button support
- No validation against utility rate schedules
- No handling of demand charges (kW) or time-of-use rates
- Global average emission factor used instead of regional grid factors

---

### 3. Corporate Travel Data

#### Real-World Research

Corporate travel platforms (Concur, Navan, Expensify, Amex GBT) typically export:

**Concur**: "Travel Request" and "Expense Report" exports with:
- Traveler name and employee ID
- Trip type (flight, hotel, car, rail)
- Origin/destination airports (IATA codes)
- Hotel nights
- Distance (sometimes provided by Concur, often missing)
- Cost and currency
- Booking date and travel date

**Navan**: Similar fields but different CSV layout. Sometimes includes carbon estimates.

Key challenges:
- Distance is often missing for flights (must derive from airport codes)
- Mixed categories in one file (flights, hotels, ground)
- Personal vs. business travel separation
- Class of service (economy, business) affects emission factors
- Round-trips sometimes reported as two one-ways

#### Our Implementation

We handle **generic travel platform CSV exports** with:
- Flexible header mapping (handles Concur, Navan, and custom formats)
- Trip type categorization (flight, hotel, ground_transport, rail)
- Airport code extraction and distance derivation
- Hotel night counting
- Scope 3 classification for all travel

**Distance derivation**: We include a lookup table for common airport pairs (JFK-LHR, LHR-FRA, etc.). For unknown pairs, we attempt hub routing (e.g., JFK-FRA via LHR). If no route can be derived, the record is flagged for analyst review.

**Sample data rationale**: 63 rows covering flights (short and long haul), hotels, ground transport, and rail. Includes duplicate rows, missing airport codes, missing distances, and an invalid trip type ("spaceship") to test edge cases.

**Production limitations**:
- No direct Concur/Navan API integration
- Airport distance table is static (should use aviation API like Airports-Data or Great Circle Mapper)
- No class-of-service differentiation (economy vs. business)
- Hotel emission factor is global average (should be country/city-specific)
- No rental car fuel type modeling
- No radiative forcing index (RFI) for flights (industry standard is 1.9x-2x multiplier)

---

## Summary Table

| Source | Format Handled | Real-World Alternatives | Limitations |
|--------|---------------|------------------------|-------------|
| SAP | CSV flat-file | IDoc, OData, BAPI, RFC | No direct SAP connection |
| Utility | Portal CSV | PDF, EDI, Green Button | No PDF/EDI, global EF |
| Travel | Platform CSV | Concur API, Navan API | Static distances, no RFI |
