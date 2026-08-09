# DaaviSetu — Claim & Pre-Authorization Document Automation

DaaviSetu automates the pre-authorization and reimbursement claim form filling process by mapping extracted patient information, diagnoses, and procedures to blank insurer templates.

## Scope
- Sourced from blank claim form templates that insurers publish publicly.
- Outputs a submission-ready PDF package for user review and manual upload to the insurer's portal.
- Integrates with Kadi to pull patient details, billing line items, and medical history.
- Explicitly does not submit claims directly to insurers (as no public cross-payer claim APIs are available yet).
