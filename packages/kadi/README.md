# Kadi (कड़ी — "link")

**Shared context layer** for ArogyaRakshak. Not a fourth module — infrastructure that all three modules (BillNyay, SchemeSetu, DawaCheck) depend on.

## Future Role

- **Case & entity model**: `kadi_cases`, `kadi_entities`, `kadi_case_entities` tables anchoring all extracted data
- **Shared extraction agent**: normalises any input document (bill, prescription, rejection letter) into a common entity schema
- **Entity resolution pipeline**: string similarity + IndicXlit transliteration matching + IndicSBERT cross-lingual semantic matching → confidence-scored merge/ask-user/new-entity decisions
- **Auto-triggering**: proactively fires other modules when enough context exists in the case

See [Technical Documentation §4](../docs/ArogyaRakshak_Technical_Documentation.md) for full design.
