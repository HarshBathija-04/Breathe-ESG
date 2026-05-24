# TRADEOFFS.md

## Three Things Deliberately Not Built

### 1. Async ETL Orchestration (Celery/Redis/RQ)

**What I didn't build**: Background task processing for ingestion pipelines. All parsing and normalization happens synchronously in the HTTP request.

**Why I skipped it**: For a prototype with files under 50MB, synchronous processing keeps the architecture simple and debuggable. Users get immediate feedback on their upload. Adding Celery would require Redis, worker processes, and result polling - significant operational complexity.

**What breaks without it**: Large files (>1000 rows) will block the HTTP request. Concurrent uploads may timeout. No visibility into long-running job progress.

**When to add it**: When clients start uploading multi-megabyte files regularly, or when we need to support API-pull ingestion (scheduled jobs). The code is structured to make this easy - the `_run_pipeline` function in ingestion views can be moved to a Celery task with minimal changes.

---

### 2. OCR PDF Utility Bill Parsing

**What I didn't build**: PDF parsing for utility bills. The system only handles CSV exports.

**Why I skipped it**: PDF parsing requires OCR (Tesseract/pymupdf) or template-based extraction. OCR is error-prone - a single misread digit in a meter reading corrupts the entire record. Building robust PDF extraction would require:
- Per-utility PDF templates (hundreds of variations)
- Confidence scoring on OCR output
- Human-in-the-loop verification for low-confidence reads
- Significant testing across different bill formats

This is weeks of work, not days.

**What breaks without it**: Clients who only receive PDF bills must manually enter data into CSV format (or use utility portals if available).

**When to add it**: When a major client cannot provide CSV/Excel exports and PDF is the only option. Start with template-based extraction for the top 10 utility formats, not generic OCR.

---

### 3. Live ERP Connectors (SAP RFC, Oracle, NetSuite)

**What I didn't build**: Direct database/API connections to client ERP systems.

**Why I skipped it**: Direct ERP integration requires:
- VPN or private-link network access to client systems
- ERP-specific client libraries (SAP JCo, Oracle ODP.NET)
- Authentication coordination (service accounts, certificates)
- Schema mapping for each client's ERP configuration
- Change data capture (CDC) or polling mechanisms
- Error handling for ERP downtime

Every client's ERP is configured differently. Building a generic SAP connector that works across clients is months of work. CSV exports are the pragmatic 80% solution.

**What breaks without it**: Data ingestion is batch-based (file upload) rather than real-time. Analysts must wait for clients to provide exports.

**When to add it**: When we have 5+ clients on the same ERP platform (e.g., SAP S/4HANA) with similar configurations. Build client-specific connectors, not generic ones.

---

## Other Smaller Trade-offs

### Single-tenant user model
Each user belongs to exactly one tenant. In a real B2B SaaS, users might need access to multiple tenants (e.g., consultants, auditors). This would require a `TenantMembership` join table with role-per-tenant.

### Hardcoded emission factors
Emission factors are hardcoded in Python rather than stored in a database table. This is fine for a prototype but would need a managed emission factor database in production with versioning, regional factors, and audit trails.

### No email notifications
The system doesn't send emails when anomalies are detected or reviews are pending. In production, we'd integrate with SendGrid/AWS SES for analyst notifications.

### No data export
There's no way to export approved data to Excel/PDF for auditors. This would be a high-priority feature for production.
