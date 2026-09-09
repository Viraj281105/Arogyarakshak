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
2. **Transient Case Session**: Database records (`kadi_cases`, `kadi_entities`) store only de-identified clinical metadata (procedure codes, medicines, prices) linked to a temporary session UUID.
3. **Opt-in Consent Boundary**: Data is never shared across modules without explicit patient consent via `consent_opt_in`.

## Consequences
### Positive
- Exceptional user trust and compliance with healthcare data privacy norms.
- Minimal server storage footprint; no database bloat from large multi-page scans.
### Negative
- If a patient clears their session or loses their connection before saving reports, they must re-upload the document for fresh analysis.
