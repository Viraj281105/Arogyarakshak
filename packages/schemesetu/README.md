# SchemeSetu

**Government healthcare scheme eligibility** module for ArogyaRakshak. ("Setu" = bridge)

## Future Role

- User answers a short intake or uploads a bill/prescription
- RAG layer over PMJAY (national) and MJPJAY (Maharashtra state) scheme documents
- Agent reasons through eligibility rules → outputs which scheme(s) apply and a step-by-step claim guide
- DB table prefix: `schemesetu_` (e.g. `schemesetu_pmjay_rules`)
- API route prefix: `/api/schemesetu/...`

See [Technical Documentation §3](../docs/ArogyaRakshak_Technical_Documentation.md) for full design.
