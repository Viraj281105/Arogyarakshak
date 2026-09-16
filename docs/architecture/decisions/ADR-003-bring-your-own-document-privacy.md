# ADR-003: Bring-Your-Own-Document (BYOD) Zero-Retention Privacy

## Status
Accepted

## Context
ArogyaRakshak processes sensitive Protected Health Information (PHI), including diagnostic reports, hospital discharge summaries, prescription medications, and financial insurance records.

## Problem
Persistent server-side storage of raw medical records introduces extreme privacy liabilities, high storage costs, and compliance burdens under Indian Digital Personal Data Protection Act (DPDP) and DISHA guidelines.

## Decision
We adopted a strict **Bring-Your-Own-Document (BYOD)** architecture:
1. **Zero Persistent Storage**: Raw uploaded documents (PDFs, images) are held only in temporary in-memory buffers (RAM) during active text extraction and are explicitly deleted from memory once extraction concludes.
2. **Transient Case Session**: Database records (`kadi_cases`, `kadi_entities`) store clinical
   and billing metadata (diagnosis, hospital, procedures, medicines, line items) linked to a
   temporary case UUID. The patient's name is extracted in memory for the duration of the
   request but is **never persisted**, and the retained document excerpt is passed through
   `kadi.redaction.redact_pii`, which removes names, phone numbers, email addresses,
   Aadhaar/PAN identifiers and postal addresses.

   **Scope limit:** this is direct-identifier removal, not formal anonymisation. A diagnosis
   combined with a hospital name may remain re-identifying in a small population. Do not
   describe the stored data as anonymous.

3. **Enforced Consent Boundary**: `consent_opt_in` defaults to `false` and is enforced
   server-side from the stored case record. Routes that read Kadi case context return `403`
   without it (the current per-route list is maintained in `apps/api/app/consent.py`); a
   client cannot grant consent by sending a flag on the module request.
4. **Opt-in Consent Boundary**: Data is never shared across modules without explicit patient consent via `consent_opt_in`. Auto-triggered module checks (#32) re-read the stored consent before running. Only a SHA-256 digest of each ingested document is kept, for duplicate detection — never the document.

## Consequences
### Positive
- Exceptional user trust and compliance with healthcare data privacy norms.
- Minimal server storage footprint; no database bloat from large multi-page scans.
### Negative
- If a patient clears their session or loses their connection before saving reports, they must re-upload the document for fresh analysis.
