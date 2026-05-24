# MODEL.md

## Data Model Architecture

### Design Principles

1. **Multi-tenancy at the application layer**: Every table has a `tenant_id` foreign key. There is no row-level security in PostgreSQL - the application enforces tenant isolation through query scoping. This was chosen over schema-per-tenant or database-per-tenant because:
   - Simpler operational overhead (one database to backup, monitor)
   - Cross-tenant analytics possible when needed (system-level dashboards)
   - Simpler migration strategy (one schema to migrate)
   - Trade-off: less isolation than schema-per-tenant; acceptable for prototype

2. **Immutable audit trail**: The `AuditLog` table is append-only. Django admin prevents edits and deletes. This gives auditors confidence that the log has not been tampered with. In production, this would be supplemented with cryptographic signing or a write-once storage layer.

3. **Raw data preservation**: `RawRecord` stores the exact source payload as JSON. Normalized data never overwrites raw data. If corrections are needed, a new ingestion job is created. This ensures analysts can always trace back to the original source.

4. **Lock after approve**: Once an activity is approved and then locked for audit, it becomes immutable. The lifecycle is: PENDING_REVIEW → APPROVED → LOCKED. No further edits are possible.

---

## Entity-Relationship Diagram

```
Tenant (1)
  ├── SourceSystem (N)
  │     └── DataIngestionJob (N)
  │           └── RawRecord (N) ← immutable
  │                 └── NormalizedActivity (1:1) ← canonical
  │                       ├── ReviewDecision (N)
  │                       └── AnomalyFlag (N)
  ├── AuditLog (N) ← immutable
  └── User (N) ← auth_core
```

---

## Core Entities

### Tenant

The root of the multi-tenant hierarchy. Every other entity has a `tenant` foreign key. A user belongs to exactly one tenant. In a real B2B SaaS, you might have a `TenantMembership` join table for users who belong to multiple tenants.

**Key fields**: `id` (UUID PK), `name`, `slug`, `is_active`, `contact_email`

### SourceSystem

Represents an external data source configured for a tenant. Each source has a type (`SAP`, `UTILITY`, `TRAVEL`) and a configuration JSON blob for source-specific settings (e.g., SAP plant code mappings, utility API credentials).

**Key fields**: `id` (UUID PK), `tenant` (FK), `source_type`, `name`, `config` (JSON), `is_active`

### DataIngestionJob

Tracks a single ingestion run. Provides visibility into pipeline progress and errors. Contains structured logs for debugging.

**Key fields**: `id` (UUID PK), `tenant` (FK), `source_system` (FK), `status`, `uploaded_file`, `original_filename`, `total_rows`, `parsed_rows`, `failed_rows`, `normalized_rows`, `flagged_rows`, `logs` (JSON array), `created_at`, `completed_at`

**Status lifecycle**: `PENDING → UPLOADED → PARSING → NORMALIZING → DETECTING_ANOMALIES → [COMPLETED | PARTIAL | FAILED]`

### RawRecord

Stores exactly what came from the source, untouched. The `original_payload` is JSON so it can handle any source shape. The `row_hash` (SHA256 of sorted JSON) enables duplicate detection across ingestion jobs.

**Key fields**: `id` (UUID PK), `tenant` (FK), `ingestion_job` (FK), `source_system` (FK), `original_payload` (JSON), `row_hash` (SHA256), `source_timestamp`, `parse_status` (`SUCCESS` | `FAILED` | `SKIPPED`), `parse_error`, `row_number`

**Why immutable**: Raw data is the source of truth. If it is wrong, the source system is wrong. We don't "fix" raw data - we create corrected records through new ingestion jobs or analyst edits at the normalized layer.

### NormalizedActivity

The canonical representation of an emissions-producing activity. All source data normalizes into this schema. This is what analysts review and what feeds into emissions reporting.

**Key fields**:
- `id` (UUID PK), `tenant` (FK)
- `scope` (`Scope1` | `Scope2` | `Scope3`) - GHG Protocol classification
- `category` (`fuel` | `electricity` | `travel`)
- `sub_category` - fuel type, electricity type, travel type
- `activity_value`, `normalized_unit` - normalized quantity
- `emission_factor` - kg CO2e per unit
- `co2e` - computed total CO2 equivalent
- `period_start`, `period_end` - reporting period
- `status` (`PENDING_REVIEW` | `FLAGGED` | `APPROVED` | `REJECTED` | `LOCKED`)
- `source_record` (OneToOne to RawRecord) - traceability
- `edited_flag`, `edit_reason` - tracks analyst modifications

**Status lifecycle**: `PENDING_REVIEW → [APPROVED → LOCKED | REJECTED]`. Flagged records return to PENDING_REVIEW after anomalies are resolved.

### ReviewDecision

Records an analyst's decision (approve/reject) on a normalized activity. Creates an audit trail of who approved what and why.

**Key fields**: `id` (UUID PK), `tenant` (FK), `activity` (FK), `decision`, `reason`, `reviewed_by` (FK), `created_at`

### AnomalyFlag

Records a detected data quality issue. Does not block processing - informational only. Analysts can resolve (false positive), confirm (real issue), or ignore.

**Key fields**: `id` (UUID PK), `tenant` (FK), `activity` (FK), `anomaly_type`, `description`, `confidence` (0-1), `details` (JSON), `status` (`OPEN` | `RESOLVED` | `CONFIRMED` | `IGNORED`), `resolution_note`, `resolved_by` (FK), `resolved_at`

### AuditLog

Immutable append-only log of all significant system actions. Every action type has before/after snapshots for full traceability.

**Key fields**: `id` (UUID PK), `tenant` (FK), `action`, `entity_type`, `entity_id`, `before` (JSON), `after` (JSON), `actor` (FK), `actor_email`, `reason`, `ip_address`, `user_agent`, `timestamp`

**Actions**: `INGEST`, `NORMALIZE`, `REVIEW`, `EDIT`, `STATUS_CHANGE`, `LOCK`, `ANOMALY_FLAG`, `ANOMALY_CLEAR`

---

## Scope Handling

GHG Protocol scopes are assigned at normalization time based on category:

| Category | Scope | Rationale |
|----------|-------|-----------|
| fuel | Scope 1 | Direct combustion emissions at company facilities |
| electricity | Scope 2 | Purchased energy (indirect) |
| travel | Scope 3 | Value chain emissions (business travel) |

Sub-categories (e.g., `diesel`, `flight_short_haul`) determine which emission factor is applied.

---

## Audit Design

The audit system has three layers:

1. **Raw data preservation**: RawRecord stores untouched source data. Hash-based deduplication prevents duplicate ingestion.

2. **Immutable audit log**: Every significant action creates an AuditLog entry with before/after snapshots. The Django admin prevents edits/deletes.

3. **Lock workflow**: Approved records can be locked, making them permanently immutable. This is the final state for audit-ready data.

### Query patterns

- `AuditLog.objects.filter(tenant=tenant, entity_type='NormalizedActivity', entity_id=activity_id).order_by('-timestamp')` - Full history for one activity
- `AuditLog.objects.filter(tenant=tenant, action='REVIEW', timestamp__gte=start_date)` - All review decisions in a period
- `NormalizedActivity.objects.filter(tenant=tenant, status='LOCKED', period_end__year=2024)` - All audit-ready 2024 data

---

## Normalization Pipeline

1. **Parse**: Source-specific parser reads CSV, normalizes headers (handles German/English), validates required fields, creates RawRecords
2. **Normalize**: NormalizationService converts RawRecords to NormalizedActivities, applies emission factors, computes CO2e
3. **Detect Anomalies**: AnomalyService flags suspicious patterns (spikes, negatives, duplicates)
4. **Review**: Analysts review flagged and pending records
5. **Lock**: Approved records are locked for audit

---

## Multi-tenancy Query Pattern

Every queryset is scoped to the request user's tenant:

```python
# In services
class SomeService:
    def __init__(self, tenant):
        self.tenant = tenant

    def get_queryset(self):
        return Model.objects.filter(tenant=self.tenant)
```

The `TenantMiddleware` sets `request.tenant` from the authenticated user's tenant. API views pass this to services. There are no global queries that omit the tenant filter.
