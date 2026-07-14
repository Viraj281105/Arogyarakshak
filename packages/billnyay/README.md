# BillNyay

**Hospital bill audit + IRDAI appeal generation** module for ArogyaRakshak. ("Nyay" = justice)

## Future Role

- Upload a hospital bill → OCR extracts line items → benchmark against CGHS government rates → flag overcharges
- 5-agent pipeline: Document Auditor → Clinical Reviewer → Regulatory Advisor → Appeal Drafter → QA Judge
- Generates IRDAI-compliant appeal letters as downloadable PDFs
- DB table prefix: `billnyay_` (e.g. `billnyay_cghs_rates`)
- API route prefix: `/api/billnyay/...`

See [Technical Documentation §3](../docs/ArogyaRakshak_Technical_Documentation.md) for full design.
