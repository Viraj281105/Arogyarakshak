# ADR-005: Separation of DaaviSetu (Pre-Claim) and BimaNyay (Post-Denial)

## Status
Accepted

## Context
Commercial health insurance involves two distinct stages: (1) filing the initial claim or requesting cashless pre-authorization, and (2) disputing wrongful rejections, deductions, or delays. Early discussions considered combining all insurance logic into a single monolithic package.

## Problem
Merging pre-claim form automation with post-denial regulatory dispute reasoning creates conflicting requirements. Claim filing requires standard form field coordinate mapping and insurer PDF template population, whereas denial disputing requires deep legal auditing against IRDAI regulations, Ombudsman Form VI generation, and statutory SLA escalation tracking.

## Decision
We partitioned the insurance workflow into two dedicated, non-overlapping modules:
1. **`DaaviSetu` (`packages/daavisetu`) — Pre-Claim Phase**:
   - Focuses strictly on pre-filling cashless pre-authorization forms and assembling initial reimbursement claim packages.
2. **`BimaNyay` (`packages/bimanyay`) — Post-Denial Dispute & Grievance Phase**:
   - Focuses strictly on parsing repudiation letters, auditing violations of the IRDAI 2024 Master Circular, generating 3-tier appeals (GRO, Bima Bharosa, Ombudsman), and tracking statutory SLAs.

## Consequences
### Positive
- Crisp separation of concerns with zero overlapping responsibilities.
- Clean user journey: patient files via DaaviSetu; if approved, the process concludes; if denied, BimaNyay is automatically activated via Kadi context.
### Negative
- Requires maintaining two separate Python packages and database table namespaces (`daavisetu_*` vs `bimanyay_*`).
