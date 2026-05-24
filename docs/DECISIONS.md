# DECISIONS.md

## Architectural Decisions

### Why CSV for SAP

I chose CSV flat-file exports for SAP ingestion because:

1. **Real-world prevalence**: Most SAP emissions data comes from custom reports or BW exports, not direct IDoc/OData connections. CSV is the lowest common denominator that every SAP team can produce.

2. **No SAP license needed**: Direct RFC/BAPI connections require SAP client libraries, JCo connectors, and licensed access. CSV export requires none of that.

3. **German header support**: SAP systems in European companies often have German column headers (`Werk`, `Menge`, `Datum`). The parser maps both German and English headers to internal normalized keys.

4. **Validation**: CSV allows us to validate structure before processing. If a required column is missing, we fail fast.

**What I ignored**: IDoc integration, OData services, BAPI calls, SAP PI/PO. These would require SAP BASIS team involvement and are overkill for a prototype.

**What I'd ask the PM**: "Do any clients have direct SAP RFC access? What's the typical technical capability of their SAP team? Can they produce custom ABAP reports?"

---

### Why CSV for Utility Data

I chose portal CSV exports for utility data because:

1. **Universally available**: Every utility portal offers CSV/Excel export. API access is rare and requires utility-specific integrations.

2. **Billing period reality**: Utility billing periods almost never align with calendar months (e.g., Jan 15 - Feb 14). The model handles arbitrary periods via `period_start` and `period_end`.

3. **Unit conversion**: Some utilities report in MWh, others in kWh. The parser normalizes everything to kWh.

**What I ignored**: PDF bill parsing (OCR), EDI 810 invoices, Green Button data, direct utility APIs. PDF parsing is high-complexity and OCR errors would require significant validation. EDI is common in large enterprises but requires specialized parsing.

**What I'd ask the PM**: "Do clients receive utility data as PDF bills, portal exports, or through an energy management system? How many different utilities do we need to support?"

---

### Why Concur/Navan-Style CSV for Travel

I chose a generic travel platform CSV export because:

1. **Platform fragmentation**: Travel data comes from Concur, Navan, Expensify, Amex GBT, and custom systems. A generic CSV covers all of them.

2. **Distance derivation**: Flight distances aren't always provided. The parser includes a lookup table for common airport pairs and hub-routing estimation for unknown pairs.

3. **Category mapping**: Flights, hotels, and ground transport all map to Scope 3 but use different emission factors. The parser categorizes and normalizes appropriately.

**What I ignored**: Direct Concur API integration, IATA carbon calculator API, hotel-specific emission factors by country. A real system would integrate with aviation distance APIs and location-specific hotel factors.

**What I'd ask the PM**: "Which travel platform do most clients use? Do we get distance data, or do we need to derive it from airport codes? Should hotel emissions vary by country?"

---

### Why JWT Authentication

JWT (JSON Web Tokens) was chosen over Django session authentication because:

1. **API-first**: The frontend is a separate SPA that talks to the backend via API. JWT is stateless and fits this pattern.
2. **No session storage**: No database session table to manage.
3. **Easy scaling**: JWT validation is purely cryptographic - no DB lookup needed for authentication.
4. **Standard**: JWT is widely supported and understood.

**Trade-off**: JWTs cannot be revoked without a blacklist mechanism. For a prototype, token expiration (24 hours) is sufficient. In production, we'd add a token blacklist for logout.

---

### Why Service Layer Pattern

Business logic is separated from views into dedicated services:

1. **Testability**: Services can be unit-tested without HTTP requests.
2. **Reusability**: The same normalization logic can be called from management commands, admin actions, or future API endpoints.
3. **Clarity**: Views handle HTTP concerns (parsing, serialization) while services handle business logic.

```
View (HTTP) → Serializer (validation) → Service (business logic) → Model (persistence)
```

---

### Why PostgreSQL

PostgreSQL was chosen for:

1. **JSON support**: Native JSONB for storing raw payloads and audit snapshots with indexing.
2. **ACID compliance**: Critical for financial/emissions data integrity.
3. **Full-text search**: Can be used for audit log searching.
4. **Operational maturity**: Excellent tooling, monitoring, hosted options (RDS, Cloud SQL, etc.).

---

### Emission Factor Source

For this prototype, emission factors are hardcoded in the `NormalizationService`. Values come from:

- **DEFRA 2024** (UK Department for Environment, Food and Rural Affairs) for fuel and travel
- **IEA 2023 Global Average** for electricity grid factors

**In production**, emission factors would come from:
- A managed emission factor database (e.g., Climeworks, Watershed)
- Client-specific factors verified by auditors
- Regional grid factors rather than global averages
- Regularly updated as new science becomes available
